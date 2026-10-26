"""Tests for controls/pi_node.py against FakeHardware. No Bluetooth needed."""
import json
import sys
import threading
import time
from pathlib import Path

import pytest

CONTROLS_DIR = Path(__file__).resolve().parents[1]
if str(CONTROLS_DIR) not in sys.path:
    sys.path.insert(0, str(CONTROLS_DIR))

import pi_node  # noqa: E402
from sphero_fake import FakeHardware  # noqa: E402

TOKEN = "test-token"
TEST_CONFIG = {
    "token": TOKEN,
    "connect_timeout_seconds": 2,
    "max_scan_attempts": 1,
    "scan_seconds": 1,
    "release_timeout_seconds": 2,
}


class SlowCloseHardware(FakeHardware):
    """Fake whose close() hangs, to exercise the forced-disconnect fallback."""

    def __init__(self, close_delay: float):
        super().__init__(count=1)
        self.close_delay = close_delay

    def close(self, handle):
        self.calls.append(("close", handle.robot_id))
        time.sleep(self.close_delay)


def make_app(hardware=None, **overrides):
    app = pi_node.create_app({**TEST_CONFIG, **overrides}, hardware or FakeHardware(count=4))
    app.config.update(EXIT_DELAY_SECONDS=0.01)
    app.testing = True
    return app


@pytest.fixture
def hw() -> FakeHardware:
    return FakeHardware(count=4)


@pytest.fixture
def app(hw):
    return make_app(hw)


@pytest.fixture
def client(app):
    return app.test_client()


def wait_for(predicate, timeout: float = 5.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.02)
    return False


def robot_map(client) -> dict:
    robots = client.get("/robots").get_json()["data"]["robots"]
    return {r["robot_id"]: r for r in robots}


def wait_settled(client, timeout: float = 5.0) -> dict:
    """Wait until no robot is queued or connecting; return the robot map."""
    def settled():
        return all(r["status"] not in ("queued", "connecting") for r in robot_map(client).values())

    assert wait_for(settled, timeout), robot_map(client)
    return robot_map(client)


def assign(client, ids: list[str]) -> dict:
    resp = client.post("/robots/assign", json={"robots": ids})
    assert resp.status_code == 200
    return resp.get_json()["data"]


def command(client, robot_id: str, body: dict):
    return client.post(f"/robots/{robot_id}/command", json=body)


def start_command(app, robot_id: str, body: dict):
    """POST a command from a background thread. The returned dict gets 'outcome' and
    'elapsed' when the request returns."""
    results: dict = {}

    def run():
        started = time.monotonic()
        resp = app.test_client().post(f"/robots/{robot_id}/command", json=body)
        results["outcome"] = resp.get_json()["data"]["outcome"]
        results["elapsed"] = time.monotonic() - started

    worker = threading.Thread(target=run, daemon=True)
    worker.start()
    return worker, results


def test_health_reports_shape(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.get_json()["data"]
    assert data["status"] == "alive"
    assert isinstance(data["hostname"], str)
    assert isinstance(data["macs"], dict) and data["macs"]
    assert set(data["version"]) >= {"branch", "commit"}
    assert data["state"] == "idle"
    assert data["connected_count"] == 0


def test_scan_sorts_strongest_first(client):
    resp = client.post("/scan", json={})
    assert resp.status_code == 200
    robots = resp.get_json()["data"]["robots"]
    assert len(robots) == 4
    assert all(r["robot_id"].startswith("SB-F") for r in robots)
    rssi = [r["rssi"] for r in robots]
    assert rssi == sorted(rssi, reverse=True)


def test_assign_connects_all(client):
    ids = ["SB-F001", "SB-F002", "SB-F003"]
    assert assign(client, ids) == {"accepted": ids, "released": []}
    robots = wait_settled(client)
    assert all(robots[i]["status"] == "connected" and robots[i]["connected"] for i in ids)
    assert client.get("/robots").get_json()["data"]["state"] == "ready"


def test_failing_ball_is_marked_failed_while_others_connect():
    app = make_app(FakeHardware(count=3, fail={"SB-F002"}), connect_timeout_seconds=0.6)
    client = app.test_client()
    assign(client, ["SB-F001", "SB-F002", "SB-F003"])
    robots = wait_settled(client)
    assert robots["SB-F001"]["status"] == "connected"
    assert robots["SB-F003"]["status"] == "connected"
    assert robots["SB-F002"]["status"] == "failed"
    assert "simulated connect failure" in robots["SB-F002"]["error"]


def test_ball_not_in_scan_is_marked_failed(client):
    assign(client, ["SB-NOPE"])
    robots = wait_settled(client)
    assert robots["SB-NOPE"]["status"] == "failed"
    assert robots["SB-NOPE"]["error"] == "not found in scan"


def test_reassign_smaller_list_releases_removed_ball(client, hw):
    assign(client, ["SB-F001", "SB-F002"])
    wait_settled(client)
    data = assign(client, ["SB-F001"])
    assert data["released"] == ["SB-F002"]
    assert ("stop", "SB-F002") in hw.calls
    assert ("set_led", "SB-F002", 0, 0, 0) in hw.calls
    assert ("close", "SB-F002") in hw.calls
    assert robot_map(client)["SB-F002"]["status"] == "released"
    assert robot_map(client)["SB-F001"]["status"] == "connected"


def test_command_types_complete(client, hw):
    assign(client, ["SB-F001"])
    wait_settled(client)
    led = command(client, "SB-F001", {"type": 0, "r": 255, "g": 0, "b": 0})
    roll = command(client, "SB-F001", {"type": 1, "speed": 80, "duration": 0.05})
    turn = command(client, "SB-F001", {"type": 2, "degrees": 90, "duration": 0.05})
    wait = command(client, "SB-F001", {"type": 3, "duration": 0.05})
    outcomes = [r.get_json()["data"]["outcome"] for r in (led, roll, turn, wait)]
    assert all(r.status_code == 200 for r in (led, roll, turn, wait))
    assert outcomes == ["complete"] * 4
    assert ("set_led", "SB-F001", 255, 0, 0) in hw.calls
    assert ("roll", "SB-F001", 80) in hw.calls
    assert [c for c in hw.calls if c[0] == "set_heading"][-1] == ("set_heading", "SB-F001", 90)


def test_command_for_unknown_robot_is_disconnected_not_404(client):
    resp = command(client, "SB-NOPE", {"type": 0, "r": 0, "g": 0, "b": 0})
    assert resp.status_code == 200
    assert resp.get_json()["data"]["outcome"] == "disconnected"


@pytest.mark.parametrize("body", [
    {"type": 7},
    {"type": "1", "speed": 10, "duration": 1},
    {"type": True},
    {"type": 1, "speed": "fast", "duration": 1},
    {"type": 1, "speed": 10, "duration": -1},
    {"type": 0, "r": 300, "g": 0, "b": 0},
    {},
])
def test_command_rejects_bad_input(client, body):
    assert command(client, "SB-F001", body).status_code == 400


@pytest.mark.parametrize("body", [
    {"type": 1, "speed": 10, "duration": 61},
    {"type": 3, "duration": 61},
    {"type": 2, "degrees": 3601, "duration": 1},
    {"type": 2, "degrees": -3601, "duration": 1},
])
def test_command_rejects_runaway_duration_or_turn(client, body):
    assert command(client, "SB-F001", body).status_code == 400


def test_command_accepts_limits():
    assert pi_node.parse_instruction({"type": 3, "duration": 60})["duration"] == 60
    assert pi_node.parse_instruction({"type": 2, "degrees": -3600, "duration": 0})["degrees"] == -3600


def test_stop_all_cancels_running_roll(app, client, hw):
    assign(client, ["SB-F001"])
    wait_settled(client)
    roll, result = start_command(app, "SB-F001", {"type": 1, "speed": 50, "duration": 10})
    assert wait_for(lambda: ("roll", "SB-F001", 50) in hw.calls)
    stopped = client.post("/robots/stop-all").get_json()["data"]["stopped"]
    roll.join(timeout=5)
    assert stopped == ["SB-F001"]
    assert result["outcome"] == "cancelled"
    assert result["elapsed"] < 5


def test_command_after_stop_all_runs_normally(client):
    assign(client, ["SB-F001"])
    wait_settled(client)
    client.post("/robots/stop-all")
    resp = command(client, "SB-F001", {"type": 3, "duration": 0.05})
    assert resp.get_json()["data"]["outcome"] == "complete"


def test_command_queued_behind_roll_is_cancelled_by_stop_all(app, client, hw):
    assign(client, ["SB-F001"])
    wait_settled(client)
    roll, roll_result = start_command(app, "SB-F001", {"type": 1, "speed": 50, "duration": 10})
    assert wait_for(lambda: ("roll", "SB-F001", 50) in hw.calls)
    queued, queued_result = start_command(app, "SB-F001", {"type": 1, "speed": 30, "duration": 10})
    time.sleep(0.3)  # let the second request reach the robot lock before stop-all arrives
    stopped = client.post("/robots/stop-all").get_json()["data"]["stopped"]
    roll.join(timeout=5)
    queued.join(timeout=5)
    assert stopped == ["SB-F001"]
    assert roll_result["outcome"] == "cancelled"
    assert queued_result["outcome"] == "cancelled"
    assert queued_result["elapsed"] < 5
    assert ("roll", "SB-F001", 30) not in hw.calls


def test_release_cancels_long_roll_quickly(app, client, hw):
    assign(client, ["SB-F001"])
    wait_settled(client)
    roll, result = start_command(app, "SB-F001", {"type": 1, "speed": 50, "duration": 10})
    assert wait_for(lambda: ("roll", "SB-F001", 50) in hw.calls)
    started = time.monotonic()
    data = client.post("/robots/release", json={"robots": ["SB-F001"]}).get_json()["data"]
    release_elapsed = time.monotonic() - started
    roll.join(timeout=5)
    assert data == {"released": ["SB-F001"], "forced": []}
    assert release_elapsed < 2
    assert result["outcome"] == "cancelled"
    assert ("stop", "SB-F001") in hw.calls
    assert ("close", "SB-F001") in hw.calls


def test_release_cancels_drive(app, client, hw):
    assign(client, ["SB-F001"])
    wait_settled(client)
    results: dict = {}

    def run_drive():
        resp = app.test_client().post(
            "/robots/SB-F001/drive", json={"speed": 50, "heading": 90, "duration_ms": 10000})
        results["data"] = resp.get_json()["data"]

    worker = threading.Thread(target=run_drive, daemon=True)
    worker.start()
    assert wait_for(lambda: ("roll", "SB-F001", 50) in hw.calls)
    started = time.monotonic()
    client.post("/robots/release", json={"robots": ["SB-F001"]})
    worker.join(timeout=5)
    assert time.monotonic() - started < 2
    assert results["data"]["cancelled"] is True


def test_release_all_stops_led_offs_and_closes(client, hw):
    assign(client, ["SB-F001", "SB-F002"])
    wait_settled(client)
    data = client.post("/robots/release", json={}).get_json()["data"]
    assert sorted(data["released"]) == ["SB-F001", "SB-F002"]
    assert data["forced"] == []
    for rid in ("SB-F001", "SB-F002"):
        assert ("stop", rid) in hw.calls
        assert ("set_led", rid, 0, 0, 0) in hw.calls
        assert ("close", rid) in hw.calls
    assert all(r["status"] == "released" for r in robot_map(client).values() if r["robot_id"] in ("SB-F001", "SB-F002"))


def test_force_disconnect_when_close_hangs():
    hw = SlowCloseHardware(close_delay=1.0)
    app = make_app(hw, release_timeout_seconds=0.2)
    client = app.test_client()
    assign(client, ["SB-F001"])
    wait_settled(client)
    address = robot_map(client)["SB-F001"]["address"]
    data = client.post("/robots/release", json={"robots": ["SB-F001"]}).get_json()["data"]
    assert data["forced"] == ["SB-F001"]
    assert ("force_disconnect", address) in hw.calls


def test_hung_connect_times_out_and_node_recovers():
    hw = FakeHardware(count=2, hang_connect={"SB-F001"}, hang_seconds=1.5)
    app = make_app(hw, connect_timeout_seconds=0.5)
    client = app.test_client()
    assign(client, ["SB-F001", "SB-F002"])
    robots = wait_settled(client)
    assert robots["SB-F001"]["status"] == "failed"
    assert robots["SB-F001"]["error"] == "connect timed out after 0.5s"
    assert robots["SB-F002"]["status"] == "connected"
    assert wait_for(lambda: client.get("/robots").get_json()["data"]["state"] == "ready")
    assert client.post("/scan", json={}).status_code == 200
    # The abandoned attempt eventually returns: its handle is closed, never stored.
    assert wait_for(lambda: ("close", "SB-F001") in hw.calls)
    assert robot_map(client)["SB-F001"]["status"] == "failed"


def test_release_of_connecting_ball_returns_promptly_and_drops_its_handle():
    hw = FakeHardware(count=1, hang_connect={"SB-F001"}, hang_seconds=1.0)
    app = make_app(hw, connect_timeout_seconds=5)
    client = app.test_client()
    assign(client, ["SB-F001"])
    assert wait_for(lambda: ("connect", "SB-F001") in hw.calls)  # the hung connect is now in flight
    started = time.monotonic()
    data = client.post("/robots/release", json={"robots": ["SB-F001"]}).get_json()["data"]
    assert time.monotonic() - started < 0.5
    assert data["released"] == ["SB-F001"]
    assert robot_map(client)["SB-F001"]["status"] == "released"
    assert wait_for(lambda: ("close", "SB-F001") in hw.calls)
    assert robot_map(client)["SB-F001"]["status"] == "released"


@pytest.mark.parametrize("path, hook", [
    ("/system/restart", "EXIT_PROCESS"),
    ("/system/shutdown", "POWER_OFF"),
])
def test_system_endpoints_require_token_then_run_hook(app, client, path, hook):
    calls = []
    app.config[hook] = lambda: calls.append(hook)

    assert client.post(path).status_code == 401
    assert client.post(path, headers={"X-Agent-Token": "wrong"}).status_code == 401
    assert calls == []

    resp = client.post(path, headers={"X-Agent-Token": TOKEN})
    assert resp.status_code == 200
    assert resp.get_json()["ok"] is True
    assert wait_for(lambda: calls == [hook])


def test_scan_is_409_while_connecting():
    app = make_app(FakeHardware(count=2, latency=0.3), connect_timeout_seconds=5)
    client = app.test_client()
    assign(client, ["SB-F001", "SB-F002"])
    resp = client.post("/scan", json={})
    assert resp.status_code == 409
    assert resp.get_json()["ok"] is False
    wait_settled(client)


def test_override_config_is_merged_over_repo_config(tmp_path):
    repo = tmp_path / "pi_node_config.json"
    repo.write_text(json.dumps({"port": 5005, "token": "repo-token"}))
    override = tmp_path / "sphero-node.json"
    override.write_text(json.dumps({"token": "secret-token"}))

    config, loaded = pi_node.load_config(repo, override)

    assert config["token"] == "secret-token"
    assert config["port"] == 5005
    assert config["connect_timeout_seconds"] == pi_node.DEFAULTS["connect_timeout_seconds"]
    assert loaded == [repo, override]


def test_missing_override_config_is_skipped(tmp_path):
    repo = tmp_path / "pi_node_config.json"
    repo.write_text(json.dumps({"token": "repo-token"}))

    config, loaded = pi_node.load_config(repo, tmp_path / "absent.json")

    assert config["token"] == "repo-token"
    assert loaded == [repo]


def test_failed_checkout_pops_the_stash_back(monkeypatch):
    calls = []

    def fake_git(*args):
        calls.append(args)
        if args[0] == "status":
            return " M controls/pi_node_config.json"
        if args[0] == "checkout":
            raise RuntimeError("error: pathspec 'nope' did not match any file(s) known to git")
        return ""

    monkeypatch.setattr(pi_node, "run_git", fake_git)
    with pytest.raises(RuntimeError, match="restored from the stash") as exc:
        pi_node.git_update("nope")
    assert ("stash", "pop") in calls
    assert "did not match" in str(exc.value)


class HangStopHardware(FakeHardware):
    """stop() blocks for hang_seconds on one ball - a BLE write that doesn't return."""

    def __init__(self, hang_id: str, hang_seconds: float, **kwargs):
        super().__init__(count=2, **kwargs)
        self.hang_id, self.hang_seconds = hang_id, hang_seconds

    def stop(self, handle) -> None:
        if handle.robot_id == self.hang_id:
            time.sleep(self.hang_seconds)
        super().stop(handle)


class HangRollHardware(FakeHardware):
    """roll_raw() blocks for hang_seconds on one ball, so its command holds the robot lock."""

    def __init__(self, hang_id: str, hang_seconds: float, **kwargs):
        super().__init__(count=2, **kwargs)
        self.hang_id, self.hang_seconds = hang_id, hang_seconds

    def roll_raw(self, handle, speed: int) -> None:
        super().roll_raw(handle, speed)
        if handle.robot_id == self.hang_id:
            time.sleep(self.hang_seconds)


@pytest.mark.parametrize("degrees", [51.42857142857143, 10.3, -7.6])
def test_fractional_turn_finishes(client, degrees):
    assign(client, ["SB-F001"])
    wait_settled(client)
    started = time.monotonic()
    resp = command(client, "SB-F001", {"type": 2, "degrees": degrees, "duration": 0.1})
    assert resp.get_json()["data"]["outcome"] == "complete"
    assert time.monotonic() - started < 2


def test_release_is_bounded_when_stop_hangs():
    app = make_app(HangStopHardware("SB-F001", hang_seconds=4.0), release_timeout_seconds=0.5)
    client = app.test_client()
    assign(client, ["SB-F001"])
    wait_settled(client)
    started = time.monotonic()
    data = client.post("/robots/release", json={"robots": ["SB-F001"]}).get_json()["data"]
    assert data["released"] == ["SB-F001"]
    assert time.monotonic() - started < pi_node.STOP_TIMEOUT_SECONDS + 2


def test_stop_all_reaches_every_ball_when_one_is_stuck():
    hw = HangRollHardware("SB-F001", hang_seconds=4.0)
    app = make_app(hw)
    client = app.test_client()
    assign(client, ["SB-F001", "SB-F002"])
    wait_settled(client)
    start_command(app, "SB-F001", {"type": 1, "speed": 50, "duration": 5})
    assert wait_for(lambda: ("roll", "SB-F001", 50) in hw.calls)
    started = time.monotonic()
    data = client.post("/robots/stop-all", json={}).get_json()["data"]
    assert time.monotonic() - started < pi_node.STOP_TIMEOUT_SECONDS + 1.5
    assert "SB-F002" in data["stopped"]


def test_reconnected_ball_gets_a_fresh_lock_after_forced_release():
    hw = HangRollHardware("SB-F001", hang_seconds=6.0)
    app = make_app(hw, release_timeout_seconds=0.3)
    client = app.test_client()
    assign(client, ["SB-F001"])
    wait_settled(client)
    start_command(app, "SB-F001", {"type": 1, "speed": 50, "duration": 5})
    assert wait_for(lambda: ("roll", "SB-F001", 50) in hw.calls)
    data = client.post("/robots/release", json={"robots": ["SB-F001"]}).get_json()["data"]
    assert data["forced"] == ["SB-F001"]
    assign(client, ["SB-F001"])
    wait_settled(client)
    started = time.monotonic()
    resp = command(client, "SB-F001", {"type": 0, "r": 1, "g": 2, "b": 3})
    assert resp.get_json()["data"]["outcome"] == "complete"
    assert time.monotonic() - started < 1
