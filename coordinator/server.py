"""Mini-PC coordinator: the HTTP API the dashboard talks to (docs/swarm-control.md, Contract 2).

Never talks to Spheros directly. Each Pi owns its balls; this server asks the
selected Pis, relays commands to whichever Pi owns a ball, and runs routines
by sending batches through BatchExecutor.

Start with start_dashboard.bat (or `uv run python coordinator/server.py`),
then open http://localhost:8000. Every response is {"ok": true, "data": ...}
or {"ok": false, "error": "..."}.
"""
import argparse
import json
import logging
import threading
import time
import webbrowser
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable, Iterable, Optional

from flask import Flask, jsonify, request, send_file
from werkzeug.exceptions import HTTPException

from assign import auto_assign, merge_scans, shuffle_assign
from discovery import PiInfo, discover, save_last_ips
from executor import BatchExecutor
from jsonfile import write_json_atomic
from pi_client import PiClient
from controls_bridge import ControlsBridge
from routines import ROUTINES, get as get_routine
from routines.base import Routine, Slot, colour_batch

logger = logging.getLogger(__name__)

COORDINATOR_DIR = Path(__file__).resolve().parent
DASHBOARD_PATH = COORDINATOR_DIR / "static" / "dashboard.html"
PLACEHOLDER_HTML = (
    "<!doctype html><title>Sphero dashboard</title>"
    "<p>dashboard.html is not built yet. The API is up at /api/pis.</p>"
)
DEFAULT_WEB_PORT = 8000
DEFAULT_BRIDGE_PORT = 1235
DEFAULT_PI_PORT = 5000
SCAN_DEFAULT_SECONDS = 8
SCAN_MAX_SECONDS = 30
FANOUT_WORKERS = 32
SYSTEM_ACTIONS = ("restart", "update", "shutdown")
UNSAFE_METHODS = ("POST", "PUT", "PATCH", "DELETE")
ROUTINE_STOP_JOIN_SECONDS = 5
ROUTINE_RESTOP_INTERVAL_SECONDS = 0.5
ROBOT_ACTIONS: dict[str, tuple[str, ...]] = {
    "drive": ("speed", "heading", "duration_ms"),
    "stop": (),
    "led": ("r", "g", "b"),
    "aim": ("on",),
    "battery": (),
}


class ApiError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.message = message
        self.status = status


class Session:
    """What the coordinator remembers between requests.

    One lock guards the fields. Long work (network calls, discovery) happens
    outside it; the lock is only held to read or swap state. Snapshots are
    replaced whole rather than mutated, so readers never see half an update.
    """

    def __init__(self, config: dict, config_path: Path, client_factory: Callable, discover_fn: Callable):
        self.lock = threading.RLock()
        self.config = config
        self.config_path = config_path
        self.infos: dict[int, PiInfo] = {}
        self.discovered = False
        self.selected: Optional[tuple[int, ...]] = None
        self.last_scan: list[dict] = []
        self.owners: dict[str, int] = {}
        self.pi_robots: dict[int, dict] = {}
        self.order: tuple[str, ...] = ()
        self.cancel = threading.Event()
        self.dispatch_lock = threading.Lock()
        self.progress = _idle_progress()
        self.routine_thread: Optional[threading.Thread] = None
        self.bridge: Optional[ControlsBridge] = None
        self._client_factory = client_factory
        self._discover_fn = discover_fn
        self._clients: dict[int, tuple[str, Any]] = {}
        self._discovery_lock = threading.Lock()

    # Pis
    def pi_port(self) -> int:
        return self.config.get("port", DEFAULT_PI_PORT)

    def token(self) -> str:
        return self.config["token"]

    def pi_numbers(self) -> tuple[int, ...]:
        return tuple(pi["number"] for pi in self.config["pis"])

    def discover(self, refresh: bool = False) -> None:
        with self.lock:
            if self.discovered and not refresh:
                return
        # Dashboard load fires several requests at once. Only one may probe the network;
        # the others wait here and find the result already applied. The session lock is
        # not held while probing, so stop-all is never stuck behind discovery.
        with self._discovery_lock:
            with self.lock:
                if self.discovered and not refresh:
                    return
            infos = self._discover_fn(self.config, self.config.get("subnet_sweep", True))
            new_config = save_last_ips(self.config_path, self.config, infos)
            with self.lock:
                self.config = new_config
                self.infos = {info.number: info for info in infos}
                self.discovered = True
                if self.selected is None:
                    self.selected = tuple(info.number for info in infos if info.online)

    def selected_numbers(self) -> tuple[int, ...]:
        self.discover()
        with self.lock:
            return tuple(self.selected or ())

    def online_numbers(self) -> tuple[int, ...]:
        """Every Pi that answered discovery, selected or not. Stop, release and ownership use these:
        a ball on an unselected Pi is still moving and still needs stopping."""
        self.discover()
        with self.lock:
            return tuple(sorted(number for number, info in self.infos.items() if info.online))

    def select(self, numbers: list[int]) -> None:
        known = set(self.pi_numbers())
        unknown = [number for number in numbers if number not in known]
        if unknown:
            raise ApiError(f"unknown Pi number(s): {unknown}")
        with self.lock:
            self.selected = tuple(numbers)

    def info(self, number: int) -> Optional[PiInfo]:
        with self.lock:
            return self.infos.get(number)

    def client(self, number: int) -> Any:
        info = self.info(number)
        with self.lock:
            cached = self._clients.get(number)
            if cached and cached[0] == info.ip:
                return cached[1]
            client = self._client_factory(info.ip, self.pi_port())
            self._clients[number] = (info.ip, client)
            return client

    # Robots and snapshots
    def replace_snapshot(self, owners: dict[str, int], pi_robots: dict[int, dict]) -> None:
        with self.lock:
            self.owners = owners
            self.pi_robots = pi_robots

    def owners_snapshot(self) -> dict[str, int]:
        with self.lock:
            return dict(self.owners)

    def owner_of(self, robot_id: str) -> Optional[int]:
        with self.lock:
            return self.owners.get(robot_id)

    def pi_robots_snapshot(self) -> dict[int, dict]:
        with self.lock:
            return dict(self.pi_robots)

    def set_last_scan(self, merged: list[dict]) -> None:
        with self.lock:
            self.last_scan = merged

    def last_scan_snapshot(self) -> list[dict]:
        with self.lock:
            return list(self.last_scan)

    def set_order(self, order: tuple[str, ...]) -> None:
        with self.lock:
            self.order = order

    # Routines and bridge
    def claim_routine(self, key: str, batch_count: int) -> bool:
        with self.lock:
            if self.progress["running"]:
                return False
            with self.dispatch_lock:
                self.cancel.clear()
            self.progress = {**_idle_progress(), "running": True, "key": key, "batch_count": batch_count}
            return True

    def request_cancel(self) -> None:
        with self.dispatch_lock:
            self.cancel.set()

    def may_dispatch(self) -> bool:
        """Checked by the routine worker before each batch. Same lock as request_cancel, so once
        stop-all has set cancel, no batch that has not already been dispatched will start."""
        with self.dispatch_lock:
            return not self.cancel.is_set()

    def routine_snapshot(self) -> Optional[threading.Thread]:
        with self.lock:
            return self.routine_thread

    def update_progress(self, **changes: Any) -> None:
        with self.lock:
            self.progress = {**self.progress, **changes}

    def progress_snapshot(self) -> dict:
        with self.lock:
            return dict(self.progress)

    def bridge_snapshot(self) -> Optional[ControlsBridge]:
        with self.lock:
            return self.bridge


def _idle_progress() -> dict:
    return {"running": False, "key": None, "batch_index": 0, "batch_count": 0,
            "last_outcomes": {}, "error": None, "cancelled": False}


def create_app(config_path, client_factory: Callable = PiClient, discover_fn: Callable = discover,
               web_port: int = DEFAULT_WEB_PORT) -> Flask:
    path = Path(config_path)
    session = Session(json.loads(path.read_text()), path, client_factory, discover_fn)
    app = Flask(__name__)
    app.extensions["sphero_session"] = session
    _register_errors(app)
    _register_request_guards(app, web_port)
    _register_pages(app)
    _register_pi_routes(app, session)
    _register_robot_routes(app, session)
    _register_routine_routes(app, session)
    _register_bridge_routes(app, session)
    return app


def _ok(data: Any = None, status: int = 200):
    return jsonify({"ok": True, "data": data}), status


def _fail(message: str, status: int):
    return jsonify({"ok": False, "error": message}), status


def _register_errors(app: Flask) -> None:
    @app.errorhandler(ApiError)
    def api_error(error: ApiError):
        return _fail(error.message, error.status)

    @app.errorhandler(HTTPException)
    def http_error(error: HTTPException):
        return _fail(error.description, error.code or 500)

    @app.errorhandler(Exception)
    def unexpected(error: Exception):
        logger.exception("unhandled error")
        return _fail(f"internal error: {error}", 500)


def _register_request_guards(app: Flask, web_port: int) -> None:
    """Refuse requests that a web page on another origin could make in the operator's browser.

    CSRF: a cross-site form POST cannot send application/json without a CORS preflight,
    and this server never grants one, so requiring the JSON content type stops it.
    DNS rebinding: a hostile name that resolves to 127.0.0.1 still sends its own Host header.
    Foreign Origin: any request a browser tags with another origin is refused.
    """
    allowed_hosts = {f"localhost:{web_port}", f"127.0.0.1:{web_port}"}
    allowed_origins = {f"http://{host}" for host in allowed_hosts}

    @app.before_request
    def guard_request():
        if request.headers.get("Host", "").lower() not in allowed_hosts:
            return _fail("Host header is not the local dashboard", 403)
        origin = request.headers.get("Origin")
        if origin is not None and origin.lower() not in allowed_origins:
            return _fail("Origin is not the local dashboard", 403)
        if request.method in UNSAFE_METHODS and not request.is_json:
            return _fail("request body must be application/json", 415)
        return None


def _register_pages(app: Flask) -> None:
    @app.get("/")
    def index():
        if DASHBOARD_PATH.exists():
            return send_file(DASHBOARD_PATH)
        return PLACEHOLDER_HTML

    @app.get("/favicon.ico")
    def favicon():
        return ("", 204)


def _register_pi_routes(app: Flask, session: Session) -> None:
    @app.get("/api/pis")
    def list_pis():
        session.discover(refresh=request.args.get("refresh") == "1")
        return _ok({"pis": _pi_listing(session)})

    @app.post("/api/pis/select")
    def select_pis():
        numbers = [_pi_number(value) for value in _list_field(_body(), "numbers")]
        session.select(numbers)
        return _ok({"pis": _pi_listing(session)})

    @app.post("/api/scan")
    def scan():
        seconds = _number("seconds", _body().get("seconds", SCAN_DEFAULT_SECONDS), 1, SCAN_MAX_SECONDS)
        numbers = _require_selected(session)
        results = fan_out(numbers, lambda n: call_pi(session, n, lambda c: c.scan(seconds)))
        per_pi, errors = {}, {}
        for key, resp in results.items():
            if resp.get("ok"):
                per_pi[int(key)] = resp["data"]["robots"]
            else:
                errors[key] = resp.get("error", "scan failed")
        merged = merge_scans(per_pi)
        session.set_last_scan(merged)
        return _ok({"robots": merged, "errors": errors})

    @app.post("/api/assign/auto")
    def assign_auto():
        body = _body()
        mode = body.get("mode")
        if mode not in ("signal", "shuffle"):
            raise ApiError("mode must be 'signal' or 'shuffle'")
        numbers = _require_selected(session)
        ids, merged = _assignment_pool(session, body.get("robots"))
        if mode == "shuffle":
            assignment = shuffle_assign(ids, numbers)
        else:
            assignment = auto_assign(merged, numbers)
        return _ok({"assignment": assignment})

    @app.get("/api/assignment/last")
    def last_assignment():
        return _ok({"assignment": _load_last_assignment(_last_assignment_path(session))})

    @app.post("/api/connect")
    def connect():
        numbers = _require_selected(session)
        assignment = _parse_assignment(_body().get("assignment"), numbers)
        owners = refresh_robots(session)
        released = _release_moved(session, _moves(owners, assignment))
        per_pi = fan_out(numbers, lambda n: call_pi(session, n, lambda c: c.assign(assignment[n])))
        per_pi = _mark_release_failures(per_pi, released)
        _save_last_assignment(_last_assignment_path(session), assignment)
        return _ok({"per_pi": per_pi})

    @app.get("/api/status")
    def status():
        refresh_robots(session)
        pi_robots = session.pi_robots_snapshot()
        pis = {}
        for number, info in ((n, session.info(n)) for n in session.pi_numbers()):
            data = pi_robots.get(number, {})
            pis[str(number)] = {
                "online": bool(info and info.online),
                "state": data.get("state"),
                "robots": data.get("robots", []),
            }
        return _ok({"pis": pis})

    @app.post("/api/stop-all")
    def stop_all():
        was_running = session.progress_snapshot()["running"]
        thread = session.routine_snapshot()  # before the fan-out, so a routine started meanwhile isn't caught
        session.request_cancel()
        per_pi = _stop_everywhere(session)
        # A batch dispatched just before the cancel can reach its Pi after the stop above.
        # Keep re-stopping while the routine thread is still alive so that batch is
        # cancelled too, rather than letting it run its full duration.
        deadline = time.monotonic() + ROUTINE_STOP_JOIN_SECONDS
        while thread is not None and thread.is_alive() and time.monotonic() < deadline:
            thread.join(timeout=ROUTINE_RESTOP_INTERVAL_SECONDS)
            if thread.is_alive():
                per_pi = _stop_everywhere(session)
        return _ok({"per_pi": per_pi, "routine_cancelled": was_running})

    @app.post("/api/release")
    def release_all():
        numbers = session.online_numbers()
        per_pi = fan_out(numbers, lambda n: call_pi(session, n, lambda c: c.release()))
        return _ok({"per_pi": per_pi})

    @app.post("/api/system/<action>")
    def system(action: str):
        if action not in SYSTEM_ACTIONS:
            raise ApiError(f"unknown system action: {action}", 404)
        body = _body()
        payload = {"branch": body["branch"]} if "branch" in body else None
        numbers = session.selected_numbers()
        per_pi = fan_out(numbers, lambda n: call_pi(
            session, n, lambda c: c.system(action, session.token(), payload)))
        return _ok({"per_pi": per_pi})


def _register_robot_routes(app: Flask, session: Session) -> None:
    @app.route("/api/robots/<robot_id>/<action>", methods=["GET", "POST"])
    def robot_action(robot_id: str, action: str):
        if action not in ROBOT_ACTIONS:
            raise ApiError(f"unknown robot action: {action}", 404)
        fields = _fields(_body(), ROBOT_ACTIONS[action])
        owner = _owner_or_refresh(session, robot_id)
        if owner is None:
            raise ApiError(f"no connected Pi owns {robot_id}", 404)
        resp = dispatch_robot(session.client(owner), robot_id, action, fields)
        if not resp.get("ok"):
            return _fail(resp.get("error", "Pi error"), 502)
        return _ok(resp.get("data"))

    @app.post("/api/all/<action>")
    def all_robots(action: str):
        if action not in ROBOT_ACTIONS:
            raise ApiError(f"unknown robot action: {action}", 404)
        return _ok({"results": _robot_fanout(session, action, _fields(_body(), ROBOT_ACTIONS[action]))})

    @app.post("/api/aim")
    def aim_all():
        return _ok({"results": _robot_fanout(session, "aim", _fields(_body(), ("on",)))})


def _register_routine_routes(app: Flask, session: Session) -> None:
    @app.get("/api/routines")
    def list_routines():
        return _ok({"routines": [routine.to_dict() for routine in ROUTINES.values()]})

    @app.post("/api/routines/<key>/formation")
    def formation(key: str):
        routine = _routine(key)
        body = _body()
        params = _params(body)
        order = _validated_order(session, routine, body)
        session.set_order(order)
        slots = routine.formation(len(order), params)
        return _ok({"slots": [_slot_json(slot, order) for slot in slots]})

    @app.post("/api/routines/<key>/identify")
    def identify(key: str):
        routine = _routine(key)
        body = _body()
        order = _validated_order(session, routine, body)
        session.set_order(order)
        slots = routine.formation(len(order), _params(body))
        executor = _executor_for(session, order, session.owners_snapshot())
        return _ok({"outcomes": executor.run_batch(colour_batch(slots))})

    @app.post("/api/routines/<key>/run")
    def run(key: str):
        routine = _routine(key)
        return _ok(_start_routine(session, routine, _body()))

    @app.get("/api/routines/progress")
    def progress():
        return _ok(session.progress_snapshot())


def _register_bridge_routes(app: Flask, session: Session) -> None:
    @app.post("/api/bridge/start")
    def bridge_start():
        port = _number("port", _body().get("port", DEFAULT_BRIDGE_PORT), 0, 65535, integer=True)
        current = session.bridge_snapshot()
        if current is not None and current.running:
            raise ApiError("controls bridge is already running", 409)
        order = session.order or tuple(sorted(refresh_robots(session)))
        if not order:
            raise ApiError("no connected balls to bridge", 409)
        executor = _executor_for(session, order, owners=None)
        bridge = ControlsBridge(executor, order, port=port)
        try:
            bridge.start()
        except OSError as error:
            raise ApiError(f"could not listen on port {port}: {error}", 409)
        with session.lock:
            session.bridge = bridge
        return _ok(_bridge_state(session))

    @app.post("/api/bridge/stop")
    def bridge_stop():
        with session.lock:
            bridge, session.bridge = session.bridge, None
        if bridge is not None:
            bridge.stop()
        return _ok(_bridge_state(session))


# Shared helpers

def fan_out(keys: Iterable[Any], call: Callable[[Any], dict]) -> dict[str, dict]:
    """Run call(key) for every key in parallel. Results are keyed by str(key)."""
    keys = list(keys)
    if not keys:
        return {}
    with ThreadPoolExecutor(max_workers=min(FANOUT_WORKERS, len(keys))) as pool:
        futures = {str(key): pool.submit(call, key) for key in keys}
    return {key: future.result() for key, future in futures.items()}


def call_pi(session: Session, number: int, call: Callable[[Any], dict]) -> dict:
    info = session.info(number)
    if info is None or not info.online:
        return {"ok": False, "error": "offline"}
    return call(session.client(number))


def _stop_everywhere(session: Session) -> dict[str, dict]:
    return fan_out(session.online_numbers(), lambda n: call_pi(session, n, lambda c: c.stop_all()))


def refresh_robots(session: Session) -> dict[str, int]:
    """Rebuild robot -> Pi ownership from every online Pi's /robots. Only connected balls count."""
    numbers = session.online_numbers()
    results = fan_out(numbers, lambda n: call_pi(session, n, lambda c: c.robots_status()))
    owners: dict[str, int] = {}
    pi_robots: dict[int, dict] = {}
    for key, resp in results.items():
        if not resp.get("ok"):
            continue
        number = int(key)
        pi_robots[number] = resp["data"]
        for robot in resp["data"].get("robots", []):
            if robot.get("connected"):
                owners[robot["robot_id"]] = number
    session.replace_snapshot(owners, pi_robots)
    return owners


def dispatch_robot(client: Any, robot_id: str, action: str, fields: dict) -> dict:
    if action == "drive":
        return client.drive(robot_id, fields["speed"], fields["heading"], fields["duration_ms"])
    if action == "stop":
        return client.stop(robot_id)
    if action == "led":
        return client.set_led(robot_id, fields["r"], fields["g"], fields["b"])
    if action == "aim":
        return client.aim(robot_id, fields["on"])
    return client.battery(robot_id)


def _robot_fanout(session: Session, action: str, fields: dict) -> dict[str, dict]:
    owners = refresh_robots(session)
    return fan_out(list(owners), lambda rid: dispatch_robot(session.client(owners[rid]), rid, action, fields))


def _owner_or_refresh(session: Session, robot_id: str) -> Optional[int]:
    owner = session.owner_of(robot_id)
    if owner is None:
        refresh_robots(session)
        owner = session.owner_of(robot_id)
    return owner


def _pi_listing(session: Session) -> list[dict]:
    selected = set(session.selected_numbers())
    with session.lock:
        infos = list(session.infos.values())
    return [{**asdict(info), "selected": info.number in selected} for info in infos]


def _body() -> dict:
    body = request.get_json(silent=True)
    if body is None:
        return {}
    if not isinstance(body, dict):
        raise ApiError("body must be a JSON object")
    return body


def _list_field(body: dict, name: str) -> list:
    value = body.get(name)
    if not isinstance(value, list):
        raise ApiError(f"{name} must be a list")
    return value


def _pi_number(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ApiError(f"not a Pi number: {value!r}")


def _number(name: str, value: Any, low: float, high: float, integer: bool = False) -> float:
    try:
        number = int(value) if integer else float(value)
    except (TypeError, ValueError, OverflowError):
        raise ApiError(f"{name} must be a number")
    if not low <= number <= high:
        raise ApiError(f"{name} must be between {low} and {high}")
    return number


def _fields(body: dict, names: tuple[str, ...]) -> dict:
    fields = {}
    for name in names:
        if name not in body:
            raise ApiError(f"missing field: {name}")
        value = body[name]
        if name == "on":
            if not isinstance(value, bool):
                raise ApiError("on must be true or false")
            fields[name] = value
        else:
            fields[name] = _number(name, value, float("-inf"), float("inf"), integer=True)
    return fields


def _require_selected(session: Session) -> tuple[int, ...]:
    numbers = session.selected_numbers()
    if not numbers:
        raise ApiError("select at least one Pi first")
    return numbers


def _assignment_pool(session: Session, requested: Any) -> tuple[list[str], list[dict]]:
    scan = session.last_scan_snapshot()
    if requested is None:
        if not scan:
            raise ApiError("scan first, or pass robots", 409)
        return [row["robot_id"] for row in scan], scan
    ids = _robot_id_list(requested, "robots")
    by_id = {row["robot_id"]: row for row in scan}
    rows = [by_id.get(rid) or {"robot_id": rid, "rssi_by_pi": {}, "best_pi": None} for rid in ids]
    return ids, rows


def _robot_id_list(value: Any, name: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(rid, str) for rid in value):
        raise ApiError(f"{name} must be a list of robot ids")
    return value


def _parse_assignment(raw: Any, selected: tuple[int, ...]) -> dict[int, list[str]]:
    if not isinstance(raw, dict):
        raise ApiError("assignment must be an object keyed by Pi number")
    parsed: dict[int, list[str]] = {}
    for key, ids in raw.items():
        number = _pi_number(key)
        if number not in selected:
            raise ApiError(f"Pi {number} is not selected")
        parsed[number] = _robot_id_list(ids, f"assignment[{key}]")
    flat = [rid for ids in parsed.values() for rid in ids]
    if len(set(flat)) != len(flat):
        raise ApiError("a robot is assigned to more than one Pi")
    return {number: list(parsed.get(number, [])) for number in selected}


def _moves(owners: dict[str, int], assignment: dict[int, list[str]]) -> dict[int, list[str]]:
    """Balls whose current Pi differs from the new one, grouped by their old Pi."""
    target = {rid: number for number, ids in assignment.items() for rid in ids}
    moves: dict[int, list[str]] = {}
    for rid, new_pi in target.items():
        old_pi = owners.get(rid)
        if old_pi is not None and old_pi != new_pi:
            moves.setdefault(old_pi, []).append(rid)
    return moves


def _release_moved(session: Session, moves: dict[int, list[str]]) -> dict[str, dict]:
    return fan_out(list(moves), lambda n: call_pi(session, n, lambda c: c.release(moves[n])))


def _mark_release_failures(per_pi: dict[str, dict], released: dict[str, dict]) -> dict[str, dict]:
    marked = dict(per_pi)
    for key, resp in released.items():
        if not resp.get("ok"):
            marked[key] = {**marked.get(key, {}), "ok": False,
                           "error": f"release of moved balls failed: {resp.get('error')}"}
    return marked


def _last_assignment_path(session: Session) -> Path:
    return session.config_path.with_name("last_assignment.json")


def _save_last_assignment(path: Path, assignment: dict[int, list[str]]) -> None:
    write_json_atomic(path, {str(n): ids for n, ids in assignment.items()})


def _load_last_assignment(path: Path) -> Optional[dict]:
    if not path.exists():
        return None
    return json.loads(path.read_text())


def _routine(key: str) -> Routine:
    routine = get_routine(key)
    if routine is None:
        raise ApiError(f"unknown routine: {key}", 404)
    return routine


def _params(body: dict) -> dict:
    params = body.get("params") or {}
    if not isinstance(params, dict):
        raise ApiError("params must be an object")
    return params


def _validated_order(session: Session, routine: Routine, body: dict) -> tuple[str, ...]:
    order = _robot_id_list(body.get("order"), "order")
    if len(set(order)) != len(order):
        raise ApiError("order contains duplicate robot ids")
    if not routine.min_robots <= len(order) <= routine.max_robots:
        raise ApiError(f"{routine.name} needs {routine.min_robots}-{routine.max_robots} robots, got {len(order)}")
    connected = refresh_robots(session)
    unknown = [rid for rid in order if rid not in connected]
    if unknown:
        raise ApiError(f"unknown robot(s), not connected: {', '.join(unknown)}")
    return tuple(order)


def _slot_json(slot: Slot, order: tuple[str, ...]) -> dict:
    return {
        "slot": slot.slot,
        "robot_id": order[slot.slot - 1],
        "x_ft": slot.x_ft,
        "y_ft": slot.y_ft,
        "heading_deg": slot.heading_deg,
        "color": list(slot.color),
    }


def online_clients(session: Session) -> list[Any]:
    return [session.client(n) for n in session.online_numbers()]


def make_resolver(session: Session, order: tuple[str, ...], owners: Optional[dict[str, int]] = None):
    """sphero_id (1-based slot in order) -> (PiClient, robot_id). owners=None reads the live snapshot."""
    def resolve(sphero_id: int):
        index = sphero_id - 1
        if not 0 <= index < len(order):
            return None
        robot_id = order[index]
        owner = owners.get(robot_id) if owners is not None else session.owner_of(robot_id)
        if owner is None:
            return None
        return session.client(owner), robot_id
    return resolve


def _executor_for(session: Session, order: tuple[str, ...], owners: Optional[dict[str, int]]) -> BatchExecutor:
    return BatchExecutor(make_resolver(session, order, owners), clients=lambda: online_clients(session))


def _start_routine(session: Session, routine: Routine, body: dict) -> dict:
    params = _params(body)
    order = _validated_order(session, routine, body)
    batches = routine.batches(len(order), params)
    if not session.claim_routine(routine.key, len(batches)):
        raise ApiError("a routine is already running", 409)
    session.set_order(order)
    executor = _executor_for(session, order, session.owners_snapshot())
    thread = threading.Thread(target=_routine_worker, args=(session, batches, executor),
                              name=f"routine-{routine.key}", daemon=True)
    with session.lock:
        session.routine_thread = thread
    thread.start()
    return session.progress_snapshot()


def _routine_worker(session: Session, batches: list[list[dict]], executor: BatchExecutor) -> None:
    stopped_early = False
    try:
        for index, batch in enumerate(batches):
            if not session.may_dispatch():
                stopped_early = True
                break
            outcomes = executor.run_batch(batch)
            session.update_progress(batch_index=index + 1, last_outcomes=outcomes)
    except Exception as error:
        logger.exception("routine run failed")
        session.update_progress(error=str(error))
    finally:
        session.update_progress(running=False, cancelled=stopped_early)


def _bridge_state(session: Session) -> dict:
    bridge = session.bridge_snapshot()
    if bridge is None or not bridge.running:
        return {"running": False, "port": None, "robots": []}
    return {"running": True, "port": bridge.port, "robots": bridge.robot_ids}


def main(argv: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Sphero swarm coordinator dashboard server")
    parser.add_argument("--port", type=int, default=DEFAULT_WEB_PORT)
    parser.add_argument("--no-browser", action="store_true", help="do not open the dashboard in a browser")
    parser.add_argument("--config", type=Path, default=COORDINATOR_DIR / "pis.json")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO)
    app = create_app(args.config, web_port=args.port)
    if not args.no_browser:
        threading.Timer(1.0, webbrowser.open, args=[f"http://localhost:{args.port}/"]).start()
    app.run(host="127.0.0.1", port=args.port, threaded=True)


if __name__ == "__main__":
    main()
