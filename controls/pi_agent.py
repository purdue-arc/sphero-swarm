"""Pi-side HTTP/JSON Controls Service.

This is the "Controls Service" from the target architecture
(docs/distributed-plan-review.md): owns the BLE connection to this Pi's
assigned Spheros and exposes a small HTTP API so a Coordinator (or
controls/pi_agent_tester.html) can command them without touching
Bluetooth directly.

Run on a Pi:
    uv pip install flask spherov2 bleak websockets
    uv run python controls/pi_agent.py [path/to/config.json]

Config file (defaults to pi_agent_config.json next to this file):
    {
      "port": 5000,
      "token": "change-me",
      "connect_timeout_seconds": 30,
      "max_connect_attempts": 20,
      "robots": ["SB-8262", "SB-D950"]
    }

Every response is {"ok": true, "data": ...} or {"ok": false, "error": ...}
so a caller never has to guess success from an HTTP status code alone.

SECURITY NOTE: /system/* endpoints run real git commands on this machine
and are gated by a shared-secret header (X-Agent-Token) because that's a
meaningfully dangerous capability regardless of network trust - fine for a
closed lab LAN, not something to expose beyond it. The /robots/* endpoints
are NOT gated; they only drive Sphero hardware, matching this codebase's
existing trust model (same as Controls_Server.py's unauthenticated
websocket).
"""
import json
import re
import subprocess
import sys
import time
from pathlib import Path

from flask import Flask, jsonify, request

from ble_reliability import apply_ble_reliability_patches

apply_ble_reliability_patches()

from spherov2 import scanner
from spherov2.sphero_edu import SpheroEduAPI
from spherov2.types import Color
from spherov2.commands.drive import DriveFlags
from spherov2.commands.power import Power

REPO_ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def load_config(path: Path) -> dict:
    with open(path) as f:
        config = json.load(f)
    config.setdefault("port", 5000)
    config.setdefault("token", "change-me")
    config.setdefault("connect_timeout_seconds", 30)
    config.setdefault("max_connect_attempts", 20)
    config.setdefault("robots", [])
    return config


CONFIG_PATH = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("pi_agent_config.json")
CONFIG = load_config(CONFIG_PATH)

if CONFIG["token"] == "change-me":
    print("WARNING: pi_agent_config.json still has the default token - "
          "anyone on this network can run git checkout/pull on this Pi. "
          "Change \"token\" before trusting this on a shared network.")

# ---------------------------------------------------------------------------
# Response helpers - every endpoint returns one of these two shapes
# ---------------------------------------------------------------------------

def ok(data=None):
    return jsonify({"ok": True, "data": data})


def bad(error: str, status: int = 400):
    return jsonify({"ok": False, "error": error}), status


def require_token():
    """Returns an error response if the request's token doesn't match, or
    None if the caller should proceed."""
    if request.headers.get("X-Agent-Token") != CONFIG["token"]:
        return bad("unauthorized", 401)
    return None


# ---------------------------------------------------------------------------
# Connect to this Pi's assigned Spheros once at startup. Same pattern as
# Controls_Test_Server.py: sequential (one at a time), 30s timeout each,
# accumulate scan results across attempts, skip whatever doesn't connect
# rather than hang the whole agent on one stubborn ball.
# ---------------------------------------------------------------------------

def _toy_prefix(toy) -> str:
    return str(toy).split()[0]


def find_balls(names, max_attempts: int) -> list:
    """Scan up to max_attempts times, accumulating found balls by name
    across attempts - not just keeping whichever single attempt found the
    most (see Controls_Test_Server.py::find_balls for why that distinction
    mattered in practice)."""
    found_by_name = {}
    for attempt in range(max_attempts):
        print(f"[scan] attempt {attempt + 1}/{max_attempts}")
        for toy in scanner.find_toys(toy_names=names):
            found_by_name[_toy_prefix(toy)] = toy
        print(f"[scan] accumulated {len(found_by_name)}/{len(names)}")
        if len(found_by_name) == len(names):
            break
    missing = [n for n in names if n not in found_by_name]
    if missing:
        print(f"[scan] never found: {missing}")
    return list(found_by_name.values())


def connect_all(names, timeout_seconds: int) -> dict:
    """Connect to each ball one at a time; a ball that doesn't connect in
    time is simply left out of the returned dict, not fatal to startup."""
    toys = find_balls(names, CONFIG["max_connect_attempts"])
    connected = {}
    for toy in toys:
        robot_id = _toy_prefix(toy)
        start = time.time()
        while (time.time() - start) < timeout_seconds:
            try:
                sb = SpheroEduAPI(toy).__enter__()
                connected[robot_id] = sb
                print(f"[connect] {robot_id} connected after {time.time() - start:.1f}s")
                break
            except Exception as e:
                print(f"[connect] {robot_id} attempt failed: {type(e).__name__}: {e}")
        else:
            print(f"[connect] {robot_id} giving up after {timeout_seconds}s")
    return connected


if CONFIG["robots"]:
    ROBOTS = connect_all(CONFIG["robots"], CONFIG["connect_timeout_seconds"])
else:
    ROBOTS = {}

app = Flask(__name__)


# pi_agent_tester.html is opened as a local file (or from a different
# origin than this agent), so every request to this server is
# cross-origin as far as the browser is concerned. Without these headers
# the browser blocks every call with a CORS error before it even reaches
# our routes - this isn't optional for the tester UI to work at all.
@app.after_request
def _add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Agent-Token"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


@app.route("/<path:_path>", methods=["OPTIONS"])
def _cors_preflight(_path):
    # Browsers send an OPTIONS preflight before any POST carrying a custom
    # header (X-Agent-Token) or a JSON content-type - without a route that
    # answers it, the preflight itself 404s and the real request never
    # fires. _add_cors_headers above still attaches the actual headers.
    return ("", 204)


# ---------------------------------------------------------------------------
# Health / status
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return ok({"status": "alive", "connected_count": len(ROBOTS)})


@app.get("/robots")
def list_robots():
    return ok({
        "robots": [
            {"robot_id": robot_id, "connected": robot_id in ROBOTS}
            for robot_id in CONFIG["robots"]
        ]
    })


# ---------------------------------------------------------------------------
# Robot commands
# ---------------------------------------------------------------------------

def _get_connected_robot(robot_id: str):
    return ROBOTS.get(robot_id)


@app.post("/robots/<robot_id>/drive")
def drive(robot_id):
    sb = _get_connected_robot(robot_id)
    if sb is None:
        return bad(f"{robot_id} is not connected on this Pi", 404)

    payload = request.get_json(silent=True) or {}
    try:
        speed = int(payload["speed"])
        heading = int(payload["heading"])
        duration_ms = int(payload["duration_ms"])
    except (KeyError, TypeError, ValueError):
        return bad("drive requires integer speed, heading, duration_ms", 400)

    try:
        sb.set_heading(heading)
        toy = sb._SpheroEduAPI__toy
        flag = DriveFlags.BACKWARD if speed < 0 else DriveFlags.FORWARD
        toy.drive_with_heading(abs(speed), sb.get_heading(), flag)
        time.sleep(duration_ms / 1000.0)
        sb.stop_roll()
    except Exception as e:
        return bad(f"drive failed: {type(e).__name__}: {e}", 500)

    return ok({"robot_id": robot_id, "speed": speed, "heading": heading, "duration_ms": duration_ms})


@app.post("/robots/<robot_id>/stop")
def stop(robot_id):
    sb = _get_connected_robot(robot_id)
    if sb is None:
        return bad(f"{robot_id} is not connected on this Pi", 404)
    try:
        sb.stop_roll()
    except Exception as e:
        return bad(f"stop failed: {type(e).__name__}: {e}", 500)
    return ok({"robot_id": robot_id})


@app.post("/robots/<robot_id>/led")
def led(robot_id):
    sb = _get_connected_robot(robot_id)
    if sb is None:
        return bad(f"{robot_id} is not connected on this Pi", 404)

    payload = request.get_json(silent=True) or {}
    try:
        r, g, b = int(payload["r"]), int(payload["g"]), int(payload["b"])
    except (KeyError, TypeError, ValueError):
        return bad("led requires integer r, g, b", 400)

    try:
        sb.set_main_led(Color(r, g, b))
    except Exception as e:
        return bad(f"led failed: {type(e).__name__}: {e}", 500)

    return ok({"robot_id": robot_id, "r": r, "g": g, "b": b})


@app.get("/robots/<robot_id>/battery")
def battery(robot_id):
    sb = _get_connected_robot(robot_id)
    if sb is None:
        return bad(f"{robot_id} is not connected on this Pi", 404)
    try:
        voltage = Power.get_battery_voltage(sb._SpheroEduAPI__toy)
    except Exception as e:
        return bad(f"battery read failed: {type(e).__name__}: {e}", 500)
    return ok({"robot_id": robot_id, "voltage": voltage})


# ---------------------------------------------------------------------------
# System / deployment
# ---------------------------------------------------------------------------

_BRANCH_PATTERN = re.compile(r"^[A-Za-z0-9._/-]+$")


def _run_git(*args) -> str:
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args],
        capture_output=True, text=True, timeout=30,
    )
    output = (result.stdout + result.stderr).strip()
    if result.returncode != 0:
        raise RuntimeError(output or f"git {' '.join(args)} failed")
    return output


@app.get("/system/version")
def version():
    try:
        branch = _run_git("rev-parse", "--abbrev-ref", "HEAD")
        commit = _run_git("rev-parse", "--short", "HEAD")
    except RuntimeError as e:
        return bad(str(e), 500)
    return ok({"branch": branch, "commit": commit})


@app.post("/system/git-checkout")
def git_checkout():
    unauthorized = require_token()
    if unauthorized:
        return unauthorized

    payload = request.get_json(silent=True) or {}
    branch = payload.get("branch", "main")
    if not _BRANCH_PATTERN.fullmatch(branch) or branch.startswith("-"):
        return bad("invalid branch name", 400)

    try:
        fetch_out = _run_git("fetch", "origin")
        status_out = _run_git("status", "--porcelain")
        stash_out = ""
        if status_out:
            # Don't let local edits (e.g. a ball list hand-edited via nano)
            # block a checkout - stash them instead of failing or
            # discarding. Recoverable later with `git stash pop`.
            stash_out = _run_git("stash", "push", "-u", "-m", "pi_agent auto-stash before checkout")
        checkout_out = _run_git("checkout", branch)
        pull_out = _run_git("pull", "origin", branch)
    except RuntimeError as e:
        return bad(f"git command failed: {e}", 500)

    return ok({
        "branch": branch,
        "fetch_output": fetch_out,
        "stashed_local_changes": bool(status_out),
        "stash_output": stash_out,
        "checkout_output": checkout_out,
        "pull_output": pull_out,
        "note": "Files are updated, but this running process is not - "
                "restart the agent for new code to take effect.",
    })


if __name__ == "__main__":
    print(f"Pi agent serving {len(ROBOTS)}/{len(CONFIG['robots'])} connected "
          f"robot(s) on port {CONFIG['port']}")
    app.run(host="0.0.0.0", port=CONFIG["port"], threaded=True)
