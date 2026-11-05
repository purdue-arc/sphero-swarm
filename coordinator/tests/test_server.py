import json
import threading
import time
from types import SimpleNamespace

import pytest

from discovery import PiInfo
from server import create_app, online_clients
from tests.local_client import LocalClient

CONFIG = {
    "port": 5000,
    "token": "change-me",
    "subnet_sweep": False,
    "pis": [{"number": n, "mac": "XX:XX:XX:XX:XX:XX", "last_ip": None} for n in (1, 2, 3, 4)],
}
ONLINE = {1, 2, 3}


def _ok(data):
    return {"ok": True, "data": data}


class FakePi:
    """Stands in for PiClient. Records every call to the shared log, and optionally blocks commands on a gate."""

    def __init__(self, ip, log, scan=(), connected=()):
        self.ip = ip
        self.log = log
        self.scan_results = list(scan)
        self.connected = set(connected)
        self.gate = None  # threading.Event: a command blocks on it, like a slow ball
        self.cancelled = False

    def _record(self, *event):
        self.log.append((self.ip, *event))

    def scan(self, seconds=8.0):
        self._record("scan", seconds)
        return _ok({"robots": self.scan_results})

    def robots_status(self):
        robots = [{"robot_id": rid, "status": "connected", "connected": True, "error": None, "address": None}
                  for rid in sorted(self.connected)]
        return _ok({"state": "ready", "robots": robots})

    def assign(self, robot_ids):
        self._record("assign", sorted(robot_ids))
        self.connected = set(robot_ids)
        return _ok({"accepted": list(robot_ids), "released": []})

    def release(self, robot_ids=None):
        released = sorted(self.connected if robot_ids is None else set(robot_ids) & self.connected)
        self._record("release", released)
        self.connected -= set(released)
        return _ok({"released": released, "forced": []})

    def stop_all(self):
        self._record("stop_all")
        self.cancelled = True
        if self.gate is not None:
            self.gate.set()  # like the real node: stop cancels the command that is running
        return _ok({"stopped": sorted(self.connected)})

    def command(self, robot_id, body):
        self._record("command", robot_id, body)  # recorded at dispatch, before any hold
        if self.gate is not None:
            self.gate.wait(5)
        if self.cancelled:
            return _ok({"robot_id": robot_id, "outcome": "cancelled"})
        if robot_id not in self.connected:
            return _ok({"robot_id": robot_id, "outcome": "disconnected"})
        return _ok({"robot_id": robot_id, "outcome": "complete"})

    def drive(self, robot_id, speed, heading, duration_ms):
        self._record("drive", robot_id, speed, heading, duration_ms)
        return _ok({})

    def stop(self, robot_id):
        self._record("stop", robot_id)
        return _ok({})

    def set_led(self, robot_id, r, g, b):
        self._record("led", robot_id, (r, g, b))
        return _ok({})

    def aim(self, robot_id, on):
        self._record("aim", robot_id, on)
        return _ok({})

    def battery(self, robot_id):
        self._record("battery", robot_id)
        return _ok({"voltage": 7.9})

    def system(self, action, token, body=None):
        self._record("system", action, token, body)
        return _ok({})


def _discover(config, sweep, probe=None):
    return [PiInfo(number=pi["number"], mac=pi["mac"], ip=f"10.0.0.{pi['number']}",
                   online=pi["number"] in ONLINE, hostname=f"pi{pi['number']}")
            for pi in config["pis"]]


@pytest.fixture
def env(tmp_path):
    log = []
    pis = {
        "10.0.0.1": FakePi("10.0.0.1", log, scan=[{"robot_id": "SB-1", "rssi": -50},
                                                  {"robot_id": "SB-2", "rssi": -55}],
                           connected=["SB-1", "SB-2"]),
        "10.0.0.2": FakePi("10.0.0.2", log, scan=[{"robot_id": "SB-1", "rssi": -70},
                                                  {"robot_id": "SB-3", "rssi": -40}],
                           connected=["SB-3"]),
        "10.0.0.3": FakePi("10.0.0.3", log),
    }
    config_path = tmp_path / "pis.json"
    config_path.write_text(json.dumps(CONFIG))
    app = create_app(config_path, client_factory=lambda host, port: pis[host], discover_fn=_discover)
    app.test_client_class = LocalClient
    return SimpleNamespace(client=app.test_client(), app=app, pis=pis, log=log, config_path=config_path,
                           session=app.extensions["sphero_session"])


def _wait_for(predicate, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return False



def _json(resp):
    return resp.get_json()


def _select_all_online(env):
    env.client.post("/api/pis/select", json={"numbers": [1, 2, 3]})


def _finish_routine(env):
    thread = env.session.routine_thread
    if thread is not None:
        thread.join(timeout=5)


def test_pis_lists_online_state_and_default_selection(env):
    body = _json(env.client.get("/api/pis"))

    assert body["ok"] is True
    by_number = {pi["number"]: pi for pi in body["data"]["pis"]}
    assert by_number[1]["online"] is True and by_number[1]["selected"] is True
    assert by_number[4]["online"] is False and by_number[4]["selected"] is False


def test_select_changes_selection_and_rejects_unknown_numbers(env):
    body = _json(env.client.post("/api/pis/select", json={"numbers": [2]}))
    assert [pi["number"] for pi in body["data"]["pis"] if pi["selected"]] == [2]

    resp = env.client.post("/api/pis/select", json={"numbers": [9]})
    assert resp.status_code == 400 and _json(resp)["ok"] is False


def test_scan_merges_every_selected_pi_into_per_ball_signal_rows(env):
    _select_all_online(env)

    body = _json(env.client.post("/api/scan", json={"seconds": 2}))

    rows = {row["robot_id"]: row for row in body["data"]["robots"]}
    assert rows["SB-1"]["rssi_by_pi"] == {"1": -50, "2": -70}
    assert rows["SB-1"]["best_pi"] == 1
    assert rows["SB-3"]["best_pi"] == 2
    assert body["data"]["errors"] == {}
    assert ("10.0.0.1", "scan", 2) in env.log


def test_auto_assign_then_connect_releases_a_moved_ball_on_its_old_pi_first(env):
    _select_all_online(env)
    env.client.post("/api/scan", json={})

    assignment = _json(env.client.post("/api/assign/auto", json={"mode": "signal"}))["data"]["assignment"]
    assert sorted(rid for ids in assignment.values() for rid in ids) == ["SB-1", "SB-2", "SB-3"]

    target = {"1": ["SB-1"], "2": ["SB-2", "SB-3"], "3": []}
    body = _json(env.client.post("/api/connect", json={"assignment": target}))
    assert body["ok"] is True
    assert set(body["data"]["per_pi"]) == {"1", "2", "3"}

    release_index = env.log.index(("10.0.0.1", "release", ["SB-2"]))
    assign_index = env.log.index(("10.0.0.2", "assign", ["SB-2", "SB-3"]))
    assert release_index < assign_index
    assert ("10.0.0.3", "assign", []) in env.log


def test_connect_saves_last_assignment_with_string_keys_and_it_reads_back(env):
    _select_all_online(env)
    target = {"1": ["SB-1"], "2": ["SB-2"], "3": []}

    env.client.post("/api/connect", json={"assignment": target})

    saved = json.loads(env.config_path.with_name("last_assignment.json").read_text())
    assert saved == target
    assert _json(env.client.get("/api/assignment/last"))["data"]["assignment"] == target


def test_connect_rejects_a_robot_assigned_twice_and_unselected_pis(env):
    _select_all_online(env)

    dup = env.client.post("/api/connect", json={"assignment": {"1": ["SB-1"], "2": ["SB-1"]}})
    assert dup.status_code == 400

    env.client.post("/api/pis/select", json={"numbers": [1]})
    unselected = env.client.post("/api/connect", json={"assignment": {"2": ["SB-1"]}})
    assert unselected.status_code == 400


def test_status_reports_each_pi_state_and_its_robots(env):
    _select_all_online(env)

    body = _json(env.client.get("/api/status"))

    assert body["data"]["pis"]["1"]["online"] is True
    assert body["data"]["pis"]["1"]["state"] == "ready"
    assert {r["robot_id"] for r in body["data"]["pis"]["1"]["robots"]} == {"SB-1", "SB-2"}
    assert body["data"]["pis"]["4"]["online"] is False


def test_robot_command_is_routed_to_the_pi_that_owns_it(env):
    _select_all_online(env)
    env.client.get("/api/status")

    body = _json(env.client.post("/api/robots/SB-3/led", json={"r": 1, "g": 2, "b": 3}))

    assert body["ok"] is True
    assert ("10.0.0.2", "led", "SB-3", (1, 2, 3)) in env.log


def test_robot_route_rejects_unknown_robot_unknown_action_and_missing_fields(env):
    _select_all_online(env)

    assert env.client.post("/api/robots/SB-99/stop").status_code == 404
    assert env.client.post("/api/robots/SB-1/teleport").status_code == 404
    assert env.client.post("/api/robots/SB-1/drive", json={"speed": 10}).status_code == 400


def test_all_led_fans_out_to_every_connected_ball(env):
    _select_all_online(env)

    body = _json(env.client.post("/api/all/led", json={"r": 0, "g": 255, "b": 0}))

    assert set(body["data"]["results"]) == {"SB-1", "SB-2", "SB-3"}
    assert ("10.0.0.2", "led", "SB-3", (0, 255, 0)) in env.log


def test_aim_fans_out_on_every_connected_ball(env):
    _select_all_online(env)

    body = _json(env.client.post("/api/aim", json={"on": True}))

    assert set(body["data"]["results"]) == {"SB-1", "SB-2", "SB-3"}
    assert ("10.0.0.1", "aim", "SB-1", True) in env.log


def test_routines_list_describes_both_routines(env):
    body = _json(env.client.get("/api/routines"))

    assert [r["key"] for r in body["data"]["routines"]] == ["square", "circle"]


def test_formation_maps_slots_to_the_given_order(env):
    _select_all_online(env)

    body = _json(env.client.post("/api/routines/square/formation",
                                 json={"order": ["SB-1", "SB-2", "SB-3"], "params": {"spacing_ft": 4}}))

    slots = body["data"]["slots"]
    assert [s["robot_id"] for s in slots] == ["SB-1", "SB-2", "SB-3"]
    assert [s["x_ft"] for s in slots] == [0, 4, 8]
    assert slots[0]["color"] == [230, 25, 75]


def test_identify_lights_each_ball_in_its_slot_colour(env):
    _select_all_online(env)

    body = _json(env.client.post("/api/routines/circle/identify", json={"order": ["SB-3", "SB-1"]}))

    assert body["data"]["outcomes"] == {"1": "complete", "2": "complete"}
    assert ("10.0.0.2", "command", "SB-3", {"type": 0, "r": 230, "g": 25, "b": 75}) in env.log


def test_run_plays_every_batch_and_reports_progress_to_completion(env):
    _select_all_online(env)

    started = _json(env.client.post("/api/routines/square/run", json={"order": ["SB-1", "SB-2", "SB-3"]}))
    assert started["data"]["running"] is True
    _finish_routine(env)

    progress = _json(env.client.get("/api/routines/progress"))["data"]
    assert progress["running"] is False
    assert progress["error"] is None
    assert progress["batch_index"] == progress["batch_count"] == 10
    assert progress["last_outcomes"] == {"1": "complete", "2": "complete", "3": "complete"}
    assert ("10.0.0.2", "command", "SB-3", {"type": 1, "speed": 60, "duration": 1.0}) in env.log


def test_run_refuses_a_second_routine_while_one_is_running(env):
    _select_all_online(env)
    gate = threading.Event()
    for pi in env.pis.values():
        pi.gate = gate

    env.client.post("/api/routines/square/run", json={"order": ["SB-1"]})
    second = env.client.post("/api/routines/circle/run", json={"order": ["SB-1"]})

    assert second.status_code == 409
    gate.set()
    _finish_routine(env)


def test_stop_all_cancels_the_running_routine_between_batches(env):
    _select_all_online(env)
    gate = threading.Event()
    for pi in env.pis.values():
        pi.gate = gate
    env.client.post("/api/routines/square/run", json={"order": ["SB-1", "SB-2"]})

    stop = _json(env.client.post("/api/stop-all"))
    gate.set()
    _finish_routine(env)

    assert stop["data"]["routine_cancelled"] is True
    assert ("10.0.0.1", "stop_all") in env.log
    progress = _json(env.client.get("/api/routines/progress"))["data"]
    assert progress["cancelled"] is True and progress["running"] is False
    assert progress["batch_index"] < progress["batch_count"]


def test_release_releases_every_selected_pi(env):
    _select_all_online(env)

    body = _json(env.client.post("/api/release"))

    assert set(body["data"]["per_pi"]) == {"1", "2", "3"}
    assert ("10.0.0.1", "release", ["SB-1", "SB-2"]) in env.log


def test_system_action_forwards_the_configured_token(env):
    _select_all_online(env)

    body = _json(env.client.post("/api/system/restart"))

    assert body["ok"] is True
    assert ("10.0.0.1", "system", "restart", "change-me", None) in env.log


def test_system_unknown_action_is_404(env):
    assert env.client.post("/api/system/reboot").status_code == 404


def test_unknown_routine_is_404(env):
    assert env.client.post("/api/routines/spiral/run", json={"order": ["SB-1"]}).status_code == 404


def test_routine_rejects_too_many_robots_and_unknown_robots(env):
    _select_all_online(env)
    too_many = [f"SB-{i}" for i in range(11)]

    assert env.client.post("/api/routines/square/formation", json={"order": too_many}).status_code == 400
    assert env.client.post("/api/routines/square/formation", json={"order": []}).status_code == 400
    unknown = env.client.post("/api/routines/square/formation", json={"order": ["SB-404"]})
    assert unknown.status_code == 400


def test_auto_assign_rejects_bad_mode_and_scanless_auto_without_robots(env):
    _select_all_online(env)

    assert env.client.post("/api/assign/auto", json={"mode": "random"}).status_code == 400
    assert env.client.post("/api/assign/auto", json={"mode": "signal"}).status_code == 409


def test_shuffle_assign_with_explicit_robots_needs_no_scan(env):
    _select_all_online(env)

    body = _json(env.client.post("/api/assign/auto", json={"mode": "shuffle", "robots": ["SB-1", "SB-2"]}))

    assert sorted(rid for ids in body["data"]["assignment"].values() for rid in ids) == ["SB-1", "SB-2"]


def test_bridge_start_reports_port_and_robots_then_stop_clears_it(env):
    _select_all_online(env)

    started = _json(env.client.post("/api/bridge/start", json={"port": 0}))
    assert started["data"]["running"] is True
    assert started["data"]["port"] > 0
    assert started["data"]["robots"] == ["SB-1", "SB-2", "SB-3"]

    stopped = _json(env.client.post("/api/bridge/stop"))
    assert stopped["data"] == {"running": False, "port": None, "robots": []}


def test_root_serves_the_dashboard_or_a_placeholder(env):
    resp = env.client.get("/")

    assert resp.status_code == 200
    assert b"<" in resp.data


# CSRF / DNS-rebinding guards (H4)

def test_form_post_is_refused_with_415_and_never_reaches_a_pi(env):
    _select_all_online(env)

    resp = env.client.post("/api/system/restart", data={"action": "restart"})

    assert resp.status_code == 415
    assert _json(resp)["ok"] is False
    assert not any(entry[1] == "system" for entry in env.log)


def test_cross_origin_post_is_refused_even_with_a_json_body(env):
    _select_all_online(env)

    resp = env.client.post("/api/stop-all", json={}, headers={"Origin": "https://evil.example"})

    assert resp.status_code == 403
    assert _json(resp)["ok"] is False
    assert not any(entry[1] == "stop_all" for entry in env.log)


def test_cross_origin_get_is_refused(env):
    resp = env.client.get("/api/pis", headers={"Origin": "http://evil.example"})

    assert resp.status_code == 403


def test_null_origin_from_a_sandboxed_page_is_refused(env):
    resp = env.client.get("/api/pis", headers={"Origin": "null"})

    assert resp.status_code == 403


@pytest.mark.parametrize("base_url", [
    "http://evil.example:8000",           # hostile name
    "http://localhost.evil.example:8000",  # suffix trick
    "http://localhost",                    # right name, wrong port
    "http://localhost:9999",               # right name, wrong port
])
def test_bad_host_header_is_refused_to_block_dns_rebinding(env, base_url):
    _select_all_online(env)

    get_resp = env.client.get("/api/pis", base_url=base_url)
    post_resp = env.client.post("/api/release", base_url=base_url)

    assert get_resp.status_code == 403
    assert post_resp.status_code == 403
    assert not any(entry[1] == "release" for entry in env.log)


def test_normal_json_request_from_the_dashboard_is_accepted(env):
    _select_all_online(env)

    resp = env.client.post("/api/release", json={}, headers={"Origin": "http://localhost:8000"})

    assert resp.status_code == 200
    assert _json(resp)["ok"] is True


def test_dashboard_on_127_0_0_1_is_accepted(env):
    resp = env.client.get("/api/pis", base_url="http://127.0.0.1:8000",
                          headers={"Origin": "http://127.0.0.1:8000"})

    assert resp.status_code == 200


def test_favicon_is_answered_with_204_so_the_browser_stops_logging_404(env):
    assert env.client.get("/favicon.ico").status_code == 204


# Stop, release and ownership reach every ONLINE Pi, not just the selected ones (M1, M7)

def test_stop_all_reaches_online_pis_that_are_not_selected(env):
    env.client.post("/api/pis/select", json={"numbers": [1]})

    body = _json(env.client.post("/api/stop-all"))

    assert ("10.0.0.2", "stop_all") in env.log
    assert ("10.0.0.3", "stop_all") in env.log
    assert set(body["data"]["per_pi"]) == {"1", "2", "3"}


def test_release_reaches_online_pis_that_are_not_selected(env):
    env.client.post("/api/pis/select", json={"numbers": [1]})

    body = _json(env.client.post("/api/release"))

    assert ("10.0.0.2", "release", ["SB-3"]) in env.log
    assert set(body["data"]["per_pi"]) == {"1", "2", "3"}


def test_ball_on_an_unselected_online_pi_is_still_controllable(env):
    env.client.post("/api/pis/select", json={"numbers": [1]})

    resp = env.client.post("/api/robots/SB-3/led", json={"r": 1, "g": 2, "b": 3})

    assert resp.status_code == 200
    assert ("10.0.0.2", "led", "SB-3", (1, 2, 3)) in env.log


def test_connect_releases_a_ball_held_by_an_unselected_pi_before_assigning_it(env):
    env.client.post("/api/pis/select", json={"numbers": [1]})

    body = _json(env.client.post("/api/connect", json={"assignment": {"1": ["SB-3"]}}))

    assert body["ok"] is True
    release_index = env.log.index(("10.0.0.2", "release", ["SB-3"]))
    assign_index = env.log.index(("10.0.0.1", "assign", ["SB-3"]))
    assert release_index < assign_index


def test_executor_stop_path_clients_include_online_unselected_pis(env):
    env.client.post("/api/pis/select", json={"numbers": [1]})

    clients = online_clients(env.session)

    assert {client.ip for client in clients} == {"10.0.0.1", "10.0.0.2", "10.0.0.3"}


# Routine cancel window (M2)

def test_no_batch_is_dispatched_after_stop_all_returns(env):
    _select_all_online(env)
    gate = threading.Event()
    for pi in env.pis.values():
        pi.gate = gate
    env.client.post("/api/routines/square/run", json={"order": ["SB-1", "SB-2"]})
    assert _wait_for(lambda: ("10.0.0.1", "command", "SB-1", {"type": 0, "r": 230, "g": 25, "b": 75}) in env.log)

    stop = _json(env.client.post("/api/stop-all"))

    assert stop["data"]["routine_cancelled"] is True
    assert env.session.routine_snapshot() is None or not env.session.routine_snapshot().is_alive()
    stop_index = env.log.index(("10.0.0.1", "stop_all"))
    dispatched_after_stop = [entry for entry in env.log[stop_index:] if entry[1] == "command"]
    assert dispatched_after_stop == []
    progress = _json(env.client.get("/api/routines/progress"))["data"]
    assert progress["running"] is False and progress["cancelled"] is True
    assert progress["batch_index"] < progress["batch_count"]


def test_request_cancel_blocks_further_dispatch_until_a_new_routine_claims(env):
    session = env.session

    session.request_cancel()
    assert session.may_dispatch() is False

    assert session.claim_routine("square", 3) is True
    assert session.may_dispatch() is True


# Discovery runs once even when the dashboard's first requests race (L4)

def test_first_discovery_runs_once_even_when_requests_race(tmp_path):
    calls = []

    def slow_discover(config, sweep, probe=None):
        calls.append(1)
        time.sleep(0.2)
        return _discover(config, sweep)

    config_path = tmp_path / "pis.json"
    config_path.write_text(json.dumps(CONFIG))
    app = create_app(config_path, client_factory=lambda host, port: None, discover_fn=slow_discover)
    session = app.extensions["sphero_session"]
    threads = [threading.Thread(target=session.discover) for _ in range(8)]

    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=5)

    assert len(calls) == 1
    assert session.info(1).online is True


# Strict numbers (L3)

def test_infinite_numbers_are_400_not_500(env):
    _select_all_online(env)

    drive = env.client.post("/api/robots/SB-1/drive", data='{"speed": Infinity, "heading": 0, "duration_ms": 10}',
                            content_type="application/json")
    bridge = env.client.post("/api/bridge/start", data='{"port": Infinity}', content_type="application/json")

    assert drive.status_code == 400
    assert bridge.status_code == 400
