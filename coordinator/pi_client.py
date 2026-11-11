"""HTTP/JSON client for one Pi's controls node (controls/pi_node.py, Contract 1).

One instance per Pi — the registry below creates and reuses these rather
than opening a fresh client per call. Synchronous (requests), matching the
rest of this codebase rather than mixing async and sync HTTP for no reason
yet.

Network failures (Pi offline, unreachable, timed out) are caught here and
normalized into the same {"ok": false, "error": ...} shape the Pi itself
returns for application-level errors — callers only need to handle
one shape, not "the Pi said no" vs. "the Pi never answered" separately.

Calls that legitimately block for longer than the default timeout (scan,
release, a timed command) pass a per-call timeout instead of raising the
global one, so a stuck Pi still fails in seconds on the cheap calls.
"""
import requests

DEFAULT_PORT = 5000
DEFAULT_TIMEOUT_SECONDS = 10
SCAN_EXTRA_SECONDS = 10       # /scan listens for `seconds` before answering
RELEASE_TIMEOUT_SECONDS = 60  # graceful disconnect of every ball, one at a time
ASSIGN_TIMEOUT_SECONDS = 60   # /robots/assign releases moved balls before returning
COMMAND_EXTRA_SECONDS = 15    # /command blocks for the command's own duration
DRIVE_EXTRA_SECONDS = 15      # /drive blocks for duration_ms before answering
SYSTEM_TIMEOUT_SECONDS = 60   # /system/update runs git before restarting


class PiClient:
    def __init__(self, host: str, port: int = DEFAULT_PORT, timeout: float = DEFAULT_TIMEOUT_SECONDS):
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
        self.timeout = timeout
        self._session = requests.Session()

    def _request(self, method: str, path: str, json_body: dict = None, headers: dict = None,
                 timeout: float = None) -> dict:
        try:
            resp = self._session.request(
                method, self.base_url + path,
                json=json_body, headers=headers,
                timeout=self.timeout if timeout is None else timeout,
            )
        except requests.exceptions.RequestException as e:
            return {"ok": False, "error": f"{type(e).__name__}: {e}"}

        try:
            return resp.json()
        except ValueError:
            return {"ok": False, "error": f"non-JSON response (status {resp.status_code})"}

    def health(self) -> dict:
        return self._request("GET", "/health")

    def list_robots(self) -> dict:
        return self._request("GET", "/robots")

    def robots_status(self) -> dict:
        return self.list_robots()

    def scan(self, seconds: float = 8.0) -> dict:
        return self._request("POST", "/scan", {"seconds": seconds},
                             timeout=seconds + SCAN_EXTRA_SECONDS)

    def assign(self, robot_ids) -> dict:
        return self._request("POST", "/robots/assign", {"robots": list(robot_ids)},
                             timeout=ASSIGN_TIMEOUT_SECONDS)

    def release(self, robot_ids=None) -> dict:
        body = {} if robot_ids is None else {"robots": list(robot_ids)}
        return self._request("POST", "/robots/release", body, timeout=RELEASE_TIMEOUT_SECONDS)

    def stop_all(self) -> dict:
        return self._request("POST", "/robots/stop-all")

    def command(self, robot_id: str, body: dict) -> dict:
        duration = float(body.get("duration") or 0)
        return self._request("POST", f"/robots/{robot_id}/command", body,
                             timeout=duration + COMMAND_EXTRA_SECONDS)

    def drive(self, robot_id: str, speed: int, heading: int, duration_ms: int) -> dict:
        return self._request("POST", f"/robots/{robot_id}/drive",
                             {"speed": speed, "heading": heading, "duration_ms": duration_ms},
                             timeout=float(duration_ms) / 1000 + DRIVE_EXTRA_SECONDS)

    def stop(self, robot_id: str) -> dict:
        return self._request("POST", f"/robots/{robot_id}/stop")

    def set_led(self, robot_id: str, r: int, g: int, b: int) -> dict:
        return self._request("POST", f"/robots/{robot_id}/led", {"r": r, "g": g, "b": b})

    def aim(self, robot_id: str, on: bool) -> dict:
        return self._request("POST", f"/robots/{robot_id}/aim", {"on": bool(on)})

    def battery(self, robot_id: str) -> dict:
        return self._request("GET", f"/robots/{robot_id}/battery")

    def system(self, action: str, token: str, body: dict = None) -> dict:
        return self._request("POST", f"/system/{action}", body or {},
                             headers={"X-Agent-Token": token}, timeout=SYSTEM_TIMEOUT_SECONDS)
