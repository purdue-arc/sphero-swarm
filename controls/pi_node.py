"""Pi-side HTTP controls node for the Sphero swarm (spec: docs/swarm-control.md, Contract 1).

One process per Raspberry Pi. It owns the BLE links to the balls assigned to this
Pi and serves the JSON API the mini-PC coordinator drives:

    uv run python controls/pi_node.py [config.json] [--port P] [--fake N]

--fake N runs N simulated balls (sphero_fake.py) so the node can be exercised on
a laptop without Bluetooth.

Config is DEFAULTS, then controls/pi_node_config.json, then the optional operator
override ~/.config/sphero-node.json (where the install script puts the token).

Every response is {"ok": true, "data": ...} or {"ok": false, "error": ...}.
/system/* endpoints need the X-Agent-Token header; /robots/* do not, matching the
trust model of the rest of controls/.
"""
import argparse
import functools
import hmac
import json
import math
import os
import re
import signal
import socket
import subprocess
import sys
import threading
import time
import traceback
import uuid
from pathlib import Path
from typing import Any, Callable

from flask import Flask, current_app, jsonify, request
from werkzeug.exceptions import HTTPException

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
DEFAULT_CONFIG_PATH = SCRIPT_DIR / "pi_node_config.json"
OVERRIDE_CONFIG_PATH = Path.home() / ".config" / "sphero-node.json"
DEFAULTS = {
    "port": 5000,
    "token": "change-me",
    "connect_timeout_seconds": 30,
    "max_scan_attempts": 20,
    "scan_seconds": 8,
}
RELEASE_TIMEOUT_SECONDS = 10.0
EXIT_DELAY_SECONDS = 0.5
RETRY_PAUSE_SECONDS = 0.5
POLL_SECONDS = 0.01
TURN_SECONDS_PER_REVOLUTION = 0.45
MAX_DRIVE_MS = 60_000
MAX_COMMAND_SECONDS = 60.0
MAX_TURN_DEGREES = 3600.0
STOP_TIMEOUT_SECONDS = 2.0
ZERO_MAC = "00:00:00:00:00:00"
BRANCH_PATTERN = re.compile(r"^[A-Za-z0-9._/-]+$")
GIT_ERRORS = (RuntimeError, OSError, subprocess.SubprocessError)
NO_LONGER_REQUESTED = "no longer requested"


class BusyError(Exception):
    """A scan or connect is in progress, so the request conflicts with it."""


class ConnectTimeout(Exception):
    """A hw.connect call did not return within the ball's connect budget."""


class _NoLongerRequested(Exception):
    """The ball was released while its connect was still in progress."""


# ---------------------------------------------------------------------------
# Config, response helpers, validation
# ---------------------------------------------------------------------------

def _read_json_object(path: Path) -> dict:
    with open(path) as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def load_config(path: Path, override_path: Path = OVERRIDE_CONFIG_PATH) -> tuple[dict, list[Path]]:
    """DEFAULTS <- repo config <- override (optional). Returns (config, files actually read)."""
    config = {**DEFAULTS, **_read_json_object(path)}
    loaded = [path]
    if override_path.is_file():
        config.update(_read_json_object(override_path))
        loaded.append(override_path)
    return config, loaded


def ok(data=None):
    return jsonify({"ok": True, "data": data})


def bad(error: str, status: int = 400):
    return jsonify({"ok": False, "error": error}), status


def _json_body() -> dict:
    payload = request.get_json(silent=True)
    return payload if isinstance(payload, dict) else {}


def _int_in(value: Any, name: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return value


def _number(value: Any, name: str, minimum: float = -math.inf, maximum: float = math.inf) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be a number")
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return float(value)


def _robot_ids(value: Any) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(r, str) and r for r in value):
        raise ValueError("robots must be a list of robot ids")
    return list(dict.fromkeys(value))


def _duration(payload: dict) -> float:
    return _number(payload.get("duration"), "duration", minimum=0, maximum=MAX_COMMAND_SECONDS)


def parse_instruction(payload: dict) -> dict:
    """Validate a /command body (controls/Instruction.py types 0-3)."""
    kind = _int_in(payload.get("type"), "type", 0, 3)
    if kind == 0:
        return {"type": 0, "r": _int_in(payload.get("r"), "r", 0, 255),
                "g": _int_in(payload.get("g"), "g", 0, 255), "b": _int_in(payload.get("b"), "b", 0, 255)}
    if kind == 1:
        return {"type": 1, "speed": _int_in(payload.get("speed"), "speed", -255, 255),
                "duration": _duration(payload)}
    if kind == 2:
        degrees = _number(payload.get("degrees"), "degrees", minimum=-MAX_TURN_DEGREES, maximum=MAX_TURN_DEGREES)
        return {"type": 2, "degrees": degrees, "duration": _duration(payload)}
    return {"type": 3, "duration": _duration(payload)}


def parse_drive(payload: dict) -> tuple[int, int, int]:
    return (_int_in(payload.get("speed"), "speed", -255, 255),
            _int_in(payload.get("heading"), "heading", 0, 359),
            _int_in(payload.get("duration_ms"), "duration_ms", 0, MAX_DRIVE_MS))


# ---------------------------------------------------------------------------
# Instruction execution (mirrors Controls_Server.run_command). Each command gets an
# is_cancelled predicate from NodeState.cancel_check; it is polled every POLL_SECONDS.
# ---------------------------------------------------------------------------

def _wait(duration: float, is_cancelled: Callable[[], bool]) -> bool:
    """Sleep in 10 ms slices. Returns False as soon as is_cancelled() is true."""
    deadline = time.monotonic() + duration
    while not is_cancelled():
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return True
        time.sleep(min(POLL_SECONDS, remaining))
    return False


def _run_roll(hw, handle, speed: int, duration: float, is_cancelled: Callable[[], bool]) -> str:
    try:
        hw.roll_raw(handle, speed)
        finished = _wait(duration, is_cancelled)
    finally:
        hw.stop(handle)
    return "complete" if finished else "cancelled"


def _run_turn(hw, handle, degrees: float, duration: float, is_cancelled: Callable[[], bool]) -> str:
    """Turn RELATIVE to the current heading, ramped over duration like run_command."""
    # set_heading takes whole degrees, so the target must be whole too - a float
    # target like 360/7 would leave the loop chasing a fraction it can never reach.
    abs_angle = round(abs(degrees))
    if abs_angle == 0:
        return "complete"
    duration = max(duration, TURN_SECONDS_PER_REVOLUTION * abs_angle / 360)
    sign = 1 if degrees > 0 else -1
    start = time.monotonic()
    turned = 0
    while turned < abs_angle:
        if is_cancelled():
            return "cancelled"
        target = round(min((time.monotonic() - start) / duration, 1.0) * abs_angle)
        delta = target - turned
        if delta:
            hw.set_heading(handle, hw.get_heading(handle) + sign * delta)
            turned += delta
        time.sleep(POLL_SECONDS)
    return "complete"


def run_instruction(hw, handle, instruction: dict, is_cancelled: Callable[[], bool]) -> str:
    kind = instruction["type"]
    if kind == 0:
        hw.set_led(handle, instruction["r"], instruction["g"], instruction["b"])
        return "complete"
    if kind == 1:
        return _run_roll(hw, handle, instruction["speed"], instruction["duration"], is_cancelled)
    if kind == 2:
        return _run_turn(hw, handle, instruction["degrees"], instruction["duration"], is_cancelled)
    return "complete" if _wait(instruction["duration"], is_cancelled) else "cancelled"


# ---------------------------------------------------------------------------
# Robot state
# ---------------------------------------------------------------------------

def _new_record(status: str) -> dict:
    return {"status": status, "error": None, "address": None, "handle": None, "toy": None}


def _best_effort(action: Callable[..., Any], *args: Any) -> bool:
    try:
        action(*args)
        return True
    except Exception as e:
        print(f"[robot] {action.__name__} failed: {type(e).__name__}: {e}")
        return False


def run_with_timeout(action: Callable[[], None], timeout: float) -> bool:
    """Run action in a daemon thread. True only if it finished without raising in time."""
    outcome = {"ok": False}

    def target() -> None:
        try:
            action()
            outcome["ok"] = True
        except Exception as e:
            print(f"[release] {type(e).__name__}: {e}")

    worker = threading.Thread(target=target, daemon=True)
    worker.start()
    worker.join(timeout)
    return outcome["ok"]


class _ConnectAttempt:
    """One hw.connect call in a daemon thread. The waiter may give up on it; if the call
    returns after that, the attempt's own thread closes the handle and never stores it."""

    def __init__(self, hw, toy):
        self._hw = hw
        self._toy = toy
        self._guard = threading.Lock()
        self._done = threading.Event()
        self._abandoned = False
        self.handle = None
        self.error: BaseException | None = None
        threading.Thread(target=self._run, name="connect-attempt", daemon=True).start()

    def _run(self) -> None:
        handle, error = None, None
        try:
            handle = self._hw.connect(self._toy)
        except Exception as e:
            error = e
        with self._guard:
            if not self._abandoned:
                self.handle, self.error = handle, error
                self._done.set()
                return
        if handle is not None:
            print("[connect] attempt returned after its waiter gave up; closing the late handle")
            _best_effort(self._hw.close, handle)

    def wait(self, seconds: float) -> bool:
        return self._done.wait(seconds)

    def abandon(self) -> bool:
        """Stop waiting. False if the attempt had already finished (use its result instead)."""
        with self._guard:
            if self._done.is_set():
                return False
            self._abandoned = True
            return True


class NodeState:
    """Everything this Pi knows about its balls. All mutable fields are guarded by self.lock.

    Cancellation uses epochs, never flags that get cleared: stop_epoch rises on every
    stop-all and _release_epochs[rid] rises on every release of that ball. A command
    snapshots both on arrival (cancel_check) and is cancelled if either has moved.

    Lock order: robot lock -> self.lock. Never wait on a robot lock while holding self.lock.
    Connects run without the robot lock, so release never waits behind a connect.
    ble_lock serialises scans and find_toys, which share the Bluetooth radio.
    """

    def __init__(self, hardware, config: dict):
        self.hw = hardware
        self.connect_timeout = float(config["connect_timeout_seconds"])
        self.max_scan_attempts = int(config["max_scan_attempts"])
        self.scan_seconds = float(config["scan_seconds"])
        self.release_timeout = float(config.get("release_timeout_seconds", RELEASE_TIMEOUT_SECONDS))
        self.lock = threading.RLock()
        self.ble_lock = threading.Lock()
        self.stop_epoch = 0
        self.robots: dict[str, dict] = {}
        self.desired: list[str] = []
        self._release_epochs: dict[str, int] = {}
        self._robot_locks: dict[str, threading.Lock] = {}
        self._connect_thread: threading.Thread | None = None

    # -- queries -----------------------------------------------------------

    def robot_lock(self, robot_id: str) -> threading.Lock:
        with self.lock:
            return self._robot_locks.setdefault(robot_id, threading.Lock())

    def overall_state(self) -> str:
        with self.lock:
            if self._connect_thread is not None:
                return "connecting"
            any_connected = self.connected_count_locked() > 0
        if self.ble_lock.locked():
            return "scanning"
        return "ready" if any_connected else "idle"

    def connected_count(self) -> int:
        with self.lock:
            return self.connected_count_locked()

    def connected_count_locked(self) -> int:
        return sum(1 for rec in self.robots.values() if rec["status"] == "connected")

    def connected_ids(self) -> list[str]:
        with self.lock:
            return [rid for rid, rec in self.robots.items() if rec["status"] == "connected"]

    def robot_list(self) -> list[dict]:
        with self.lock:
            return [
                {"robot_id": rid, "status": rec["status"], "connected": rec["status"] == "connected",
                 "error": rec["error"], "address": rec["address"]}
                for rid, rec in sorted(self.robots.items())
            ]

    def handle_of(self, robot_id: str):
        with self.lock:
            rec = self.robots.get(robot_id)
            if rec is None or rec["status"] != "connected":
                return None
            return rec["handle"]

    def cancel_check(self, robot_id: str) -> Callable[[], bool]:
        """Snapshot the stop and release epochs now (on arrival, before waiting for the robot
        lock). The returned predicate turns True once stop-all or a release of this robot
        happens after this call. Nothing is ever cleared, so later commands are unaffected."""
        with self.lock:
            ticket = (self.stop_epoch, self._release_epochs.get(robot_id, 0))

        def cancelled() -> bool:
            with self.lock:
                return ticket != (self.stop_epoch, self._release_epochs.get(robot_id, 0))

        return cancelled

    # -- scan --------------------------------------------------------------

    def scan(self, seconds: float) -> list[dict]:
        with self.lock:
            if self._connect_thread is not None:
                raise BusyError("connecting; scan again when the connect finishes")
        if not self.ble_lock.acquire(blocking=False):
            raise BusyError("bluetooth busy (scan already running)")
        try:
            found = self.hw.scan(seconds)
        finally:
            self.ble_lock.release()
        return sorted(found, key=lambda robot: robot["rssi"], reverse=True)

    # -- assign / connect ----------------------------------------------------

    def assign(self, robot_ids: list[str]) -> list[str]:
        """Make this Pi's set exactly robot_ids. Removed balls are released synchronously
        (cancel, stop, close; bounded by release_timeout). New ones are connected by a single
        background worker. Returns released ids."""
        with self.lock:
            removed = [rid for rid, rec in self.robots.items()
                       if rid not in robot_ids and rec["status"] != "released"]
        released, _ = self.release_ids(removed)
        with self.lock:
            self.desired = list(robot_ids)
            for rid in robot_ids:
                self._queue(rid)
            self._ensure_worker()
        return released

    def _queue(self, robot_id: str) -> None:
        rec = self.robots.get(robot_id)
        if rec is None or rec["status"] in ("released", "failed"):
            self.robots[robot_id] = _new_record("queued")

    def _is_queued(self, robot_id: str) -> bool:
        return robot_id in self.desired and self.robots.get(robot_id, {}).get("status") == "queued"

    def _is_desired(self, robot_id: str) -> bool:
        with self.lock:
            return robot_id in self.desired

    def _ensure_worker(self) -> None:
        if self._connect_thread is not None or not any(self._is_queued(r) for r in self.desired):
            return
        self._connect_thread = threading.Thread(target=self._connect_worker, name="connect-worker", daemon=True)
        self._connect_thread.start()

    def _connect_worker(self) -> None:
        try:
            self._connect_queued()
        except Exception as e:
            print(f"[connect] worker crashed: {type(e).__name__}: {e}")
            traceback.print_exc()
            self._fail_queued_all(f"{type(e).__name__}: {e}")
        finally:
            with self.lock:
                if self._connect_thread is threading.current_thread():
                    self._connect_thread = None

    def _connect_queued(self) -> None:
        while True:
            batch = self._take_queued()
            if not batch:
                return
            found = self._scan_for(batch)
            for rid in batch:
                toy = found.get(rid)
                if toy is None:
                    self._fail_queued(rid, "not found in scan")
                else:
                    self._connect_one(rid, toy)

    def _take_queued(self) -> list[str]:
        """Snapshot the queued batch. Clears the worker slot atomically when nothing is left,
        so an assign arriving right after always starts a fresh worker."""
        with self.lock:
            batch = [rid for rid in self.desired if self._is_queued(rid)]
            if not batch:
                self._connect_thread = None
            return batch

    def _scan_for(self, robot_ids: list[str]) -> dict:
        with self.ble_lock:
            try:
                return self.hw.find(robot_ids, self.max_scan_attempts)
            except Exception as e:
                print(f"[scan] find failed: {type(e).__name__}: {e}")
                return {}

    def _connect_one(self, robot_id: str, toy) -> None:
        if not self._claim(robot_id):
            return
        address = getattr(toy, "address", None)
        with self.lock:
            self.robots[robot_id].update(address=address, toy=toy)
        handle, error = self._attempt_connect(robot_id, toy)
        self._store_result(robot_id, handle, address, error)

    def _claim(self, robot_id: str) -> bool:
        with self.lock:
            if not self._is_queued(robot_id):
                return False
            self.robots[robot_id].update(status="connecting", error=None)
            return True

    def _attempt_connect(self, robot_id: str, toy) -> tuple[Any, str | None]:
        """Retry hw.connect until the ball's wall-clock connect budget runs out."""
        deadline = time.monotonic() + self.connect_timeout
        error = "connect failed"
        while time.monotonic() < deadline:
            if not self._is_desired(robot_id):
                return None, NO_LONGER_REQUESTED
            try:
                return self._connect_once(robot_id, toy, deadline), None
            except ConnectTimeout:
                return None, f"connect timed out after {self.connect_timeout:g}s"
            except _NoLongerRequested:
                return None, NO_LONGER_REQUESTED
            except Exception as e:
                error = f"{type(e).__name__}: {e}"
                print(f"[connect] {robot_id} attempt failed: {error}")
                time.sleep(min(RETRY_PAUSE_SECONDS, max(0.0, deadline - time.monotonic())))
        return None, f"gave up after {self.connect_timeout:g}s: {error}"

    def _connect_once(self, robot_id: str, toy, deadline: float):
        """Run one hw.connect and wait for it until deadline. Stops waiting early if the ball
        is released meanwhile, so a released ball never holds the connect worker."""
        attempt = _ConnectAttempt(self.hw, toy)
        while not attempt.wait(POLL_SECONDS):
            if not self._is_desired(robot_id) and attempt.abandon():
                raise _NoLongerRequested(robot_id)
            if time.monotonic() >= deadline and attempt.abandon():
                raise ConnectTimeout(robot_id)
        if attempt.error is not None:
            raise attempt.error
        return attempt.handle

    def _store_result(self, robot_id: str, handle, address: str | None, error: str | None) -> None:
        with self.lock:
            rec = self.robots[robot_id]
            if rec["status"] == "connecting":
                if handle is not None:
                    rec.update(status="connected", handle=handle, address=address, error=None)
                    print(f"[connect] {robot_id} connected")
                else:
                    rec.update(status="failed", error=error)
                return
        # Released or re-queued while connecting: this handle must never be stored.
        if handle is not None:
            print(f"[connect] {robot_id} finished after it was released; closing it")
            self._teardown(handle, address)

    def _fail_queued(self, robot_id: str, reason: str) -> None:
        with self.lock:
            if self._is_queued(robot_id):
                self.robots[robot_id].update(status="failed", error=reason)

    def _fail_queued_all(self, reason: str) -> None:
        with self.lock:
            for rid in self.desired:
                self._fail_queued(rid, reason)

    # -- release -----------------------------------------------------------

    def release_ids(self, robot_ids: list[str] | None = None) -> tuple[list[str], list[str]]:
        """Gracefully release the given robots (None = all). Returns (released, forced).
        In-flight commands are cancelled before this waits for them, so a long roll does
        not hold up the release. A connecting ball is marked released and not waited on."""
        with self.lock:
            requested = list(self.robots) if robot_ids is None else robot_ids
            targets = []
            for rid in requested:
                rec = self.robots.get(rid)
                if rec is None or rec["status"] == "released":
                    continue
                targets.append((rid, rec["handle"], rec["address"]))
                self.desired = [d for d in self.desired if d != rid]
                self._release_epochs[rid] = self._release_epochs.get(rid, 0) + 1
                rec.update(status="released", handle=None, error=None)
        # In parallel: each ball's worst case is ~30 s when its BLE link is wedged, and
        # done one after another that would outlast systemd's TimeoutStopSec.
        forced_flags: dict[str, bool] = {}

        def release_one(rid: str, handle, address: str | None) -> None:
            forced_flags[rid] = self._release_handle(rid, handle, address)

        workers = [threading.Thread(target=release_one, args=target, daemon=True) for target in targets]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join()
        released = [rid for rid, _, _ in targets]
        return released, [rid for rid in released if forced_flags.get(rid)]

    def _release_handle(self, robot_id: str, handle, address: str | None) -> bool:
        """Close one ball's link. True if the bluetoothctl fallback was used.
        Caller must not hold the robot lock."""
        if handle is not None:
            # Unblock a running command before queueing for its lock - bounded, because a
            # wedged BLE call must not stall release/restart/shutdown/SIGTERM.
            run_with_timeout(lambda: self.hw.stop(handle), STOP_TIMEOUT_SECONDS)
        lock = self.robot_lock(robot_id)
        if not lock.acquire(timeout=self.release_timeout):
            print(f"[release] {robot_id}: command still busy after {self.release_timeout:g}s; forcing disconnect")
            with self.lock:
                # The stuck command may never let go of this lock; a later reconnect
                # of the same ball must get a fresh one instead of queueing behind it.
                if self._robot_locks.get(robot_id) is lock:
                    del self._robot_locks[robot_id]
            return handle is not None and self._force_disconnect(address)
        try:
            return handle is not None and self._teardown(handle, address)
        finally:
            lock.release()

    def _teardown(self, handle, address: str | None) -> bool:
        """Stop, LED off, close. Falls back to bluetoothctl if that hangs or raises.
        Returns True if the fallback was used."""
        if run_with_timeout(lambda: self._graceful_steps(handle), self.release_timeout):
            return False
        print(f"[release] graceful close failed for {address}; forcing disconnect")
        return self._force_disconnect(address)

    def _force_disconnect(self, address: str | None) -> bool:
        if address is None:
            return False
        _best_effort(self.hw.force_disconnect, address)
        return True

    def _graceful_steps(self, handle) -> None:
        _best_effort(self.hw.stop, handle)
        _best_effort(self.hw.set_led, handle, 0, 0, 0)
        self.hw.close(handle)

    def stop_all(self) -> list[str]:
        """Bump the stop epoch so every command still in flight (including ones queued on a
        robot lock) ends cancelled, then stop every connected ball."""
        with self.lock:
            self.stop_epoch += 1
        # No robot locks here: the epoch bump already cancels running and queued work,
        # and waiting on a wedged ball's lock would delay stopping every ball after it.
        # All stops go out in parallel, each bounded.
        results: dict[str, bool] = {}

        def stop_one(rid: str, handle) -> None:
            results[rid] = run_with_timeout(lambda: self.hw.stop(handle), STOP_TIMEOUT_SECONDS)

        workers = []
        for rid in self.connected_ids():
            handle = self.handle_of(rid)
            if handle is not None:
                worker = threading.Thread(target=stop_one, args=(rid, handle), daemon=True)
                worker.start()
                workers.append(worker)
        for worker in workers:
            worker.join(STOP_TIMEOUT_SECONDS + 1)
        return sorted(rid for rid, ok in results.items() if ok)

    # -- commands ----------------------------------------------------------

    def run_command(self, robot_id: str, instruction: dict) -> dict:
        is_cancelled = self.cancel_check(robot_id)
        if self.handle_of(robot_id) is None:
            return {"robot_id": robot_id, "outcome": "disconnected"}
        with self.robot_lock(robot_id):
            if is_cancelled():
                return {"robot_id": robot_id, "outcome": "cancelled"}
            handle = self.handle_of(robot_id)
            if handle is None:
                return {"robot_id": robot_id, "outcome": "disconnected"}
            try:
                outcome = run_instruction(self.hw, handle, instruction, is_cancelled)
            except Exception as e:
                return {"robot_id": robot_id, "outcome": "failed", "error": f"{type(e).__name__}: {e}"}
        return {"robot_id": robot_id, "outcome": outcome}

    def drive(self, robot_id: str, speed: int, heading: int, duration_ms: int) -> dict | None:
        """Roll at a fixed heading for duration_ms. None if the ball is not connected."""
        is_cancelled = self.cancel_check(robot_id)
        if self.handle_of(robot_id) is None:
            return None
        with self.robot_lock(robot_id):
            handle = self.handle_of(robot_id)
            if handle is None:
                return None
            outcome = "cancelled"
            if not is_cancelled():
                self.hw.set_heading(handle, heading)
                outcome = _run_roll(self.hw, handle, speed, duration_ms / 1000.0, is_cancelled)
        return {"speed": speed, "heading": heading, "duration_ms": duration_ms,
                "cancelled": outcome == "cancelled"}


# ---------------------------------------------------------------------------
# System helpers: git, MAC addresses, exit/shutdown
# ---------------------------------------------------------------------------

def run_git(*args: str) -> str:
    result = subprocess.run(["git", "-C", str(REPO_ROOT), *args], capture_output=True, text=True, timeout=30)
    output = (result.stdout + result.stderr).strip()
    if result.returncode != 0:
        raise RuntimeError(output or f"git {' '.join(args)} failed")
    return output


def read_git_version() -> dict:
    return {"branch": run_git("rev-parse", "--abbrev-ref", "HEAD"), "commit": run_git("rev-parse", "--short", "HEAD")}


def _restore_stash() -> str:
    try:
        run_git("stash", "pop")
        return "local changes restored from the stash"
    except GIT_ERRORS as e:
        return f"git stash pop also failed ({e}); local changes are still in `git stash list`"


def git_update(branch: str) -> dict:
    """Fetch, auto-stash local edits, checkout and pull. If checkout or pull fails after the
    stash, pop it back so the operator's edits are not stranded, and say so in the error."""
    fetch_out = run_git("fetch", "origin")
    status_out = run_git("status", "--porcelain")
    stash_out = run_git("stash", "push", "-u", "-m", "pi_node auto-stash before update") if status_out else ""
    try:
        checkout_out = run_git("checkout", branch)
        pull_out = run_git("pull", "origin", branch)
    except GIT_ERRORS as e:
        if not status_out:
            raise
        raise RuntimeError(f"{e}; {_restore_stash()}") from e
    return {"branch": branch, "fetch_output": fetch_out, "stashed_local_changes": bool(status_out),
            "stash_output": stash_out, "checkout_output": checkout_out, "pull_output": pull_out}


def format_mac(node: int) -> str:
    return ":".join(f"{(node >> shift) & 0xFF:02x}" for shift in range(40, -1, -8))


def read_macs() -> dict[str, str]:
    macs = {}
    for path in sorted(Path("/sys/class/net").glob("*/address")):
        try:
            mac = path.read_text().strip()
        except OSError:
            continue
        if path.parent.name != "lo" and mac and mac != ZERO_MAC:
            macs[path.parent.name] = mac
    return macs or {"node": format_mac(uuid.getnode())}


def _exit_process() -> None:
    print("[system] exiting so systemd restarts the node", flush=True)
    os._exit(0)


def _power_off() -> None:
    result = subprocess.run(["sudo", "-n", "/sbin/shutdown", "-h", "now"], timeout=30, check=False)
    print(f"[system] shutdown command exited {result.returncode}", flush=True)


def _schedule_exit(app: Flask, state: NodeState, final_action: str) -> None:
    """Respond first, then release every ball and run final_action (EXIT_PROCESS or POWER_OFF)."""
    def run() -> None:
        time.sleep(app.config["EXIT_DELAY_SECONDS"])
        try:
            state.release_ids(None)
        finally:
            app.config[final_action]()

    threading.Thread(target=run, name="system-exit", daemon=True).start()


def _token_ok() -> bool:
    supplied = request.headers.get("X-Agent-Token", "")
    return hmac.compare_digest(supplied.encode(), current_app.config["TOKEN"].encode())


def require_token(view: Callable) -> Callable:
    @functools.wraps(view)
    def wrapper(*args, **kwargs):
        if not _token_ok():
            return bad("unauthorized", 401)
        return view(*args, **kwargs)
    return wrapper


# ---------------------------------------------------------------------------
# Flask app
# ---------------------------------------------------------------------------

def _not_connected(robot_id: str):
    return bad(f"{robot_id} is not connected on this Pi", 404)


def _on_handle(state: NodeState, robot_id: str, action: Callable[[Any], dict], label: str):
    handle = state.handle_of(robot_id)
    if handle is None:
        return _not_connected(robot_id)
    try:
        data = action(handle)
    except Exception as e:
        return bad(f"{label} failed: {type(e).__name__}: {e}", 500)
    return ok({"robot_id": robot_id, **data})


def _register_cors(app: Flask) -> None:
    @app.after_request
    def _add_cors_headers(response):
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Agent-Token"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        return response

    @app.route("/<path:_path>", methods=["OPTIONS"])
    def _cors_preflight(_path):
        return ("", 204)


def _register_error_handlers(app: Flask) -> None:
    @app.errorhandler(HTTPException)
    def _http_error(err: HTTPException):
        return bad(err.description or err.name, err.code or 500)

    @app.errorhandler(Exception)
    def _unhandled(err: Exception):
        traceback.print_exc()
        return bad(f"internal error: {type(err).__name__}", 500)


def _register_status_routes(app: Flask, state: NodeState) -> None:
    @app.get("/health")
    def health():
        return ok({
            "status": "alive",
            "hostname": socket.gethostname(),
            "macs": read_macs(),
            "version": app.config["VERSION"],
            "state": state.overall_state(),
            "connected_count": state.connected_count(),
        })

    @app.post("/scan")
    def scan():
        try:
            seconds = _number(_json_body().get("seconds", state.scan_seconds), "seconds", 1, 60)
        except ValueError as e:
            return bad(str(e), 400)
        try:
            return ok({"robots": state.scan(seconds)})
        except BusyError as e:
            return bad(str(e), 409)

    @app.get("/system/version")
    def version():
        try:
            return ok(read_git_version())
        except GIT_ERRORS as e:
            return bad(str(e), 500)


def _register_robot_routes(app: Flask, state: NodeState) -> None:
    @app.get("/robots")
    def list_robots():
        return ok({"state": state.overall_state(), "robots": state.robot_list()})

    @app.post("/robots/assign")
    def assign():
        """Make this Pi's set exactly the given list.

        Synchronous for removed balls: each one is cancelled, stopped and closed before the
        response, so `released` is accurate. A busy ball is cancelled within ~10 ms; a close
        that hangs costs up to release_timeout_seconds per ball. Connecting balls are not
        waited for. New balls connect in a background worker: the response returns without
        waiting for connects, so poll GET /robots for their status.
        """
        try:
            robot_ids = _robot_ids(_json_body().get("robots"))
        except ValueError as e:
            return bad(str(e), 400)
        return ok({"accepted": robot_ids, "released": state.assign(robot_ids)})

    @app.post("/robots/release")
    def release():
        body = _json_body()
        try:
            robot_ids = None if body.get("robots") is None else _robot_ids(body["robots"])
        except ValueError as e:
            return bad(str(e), 400)
        released, forced = state.release_ids(robot_ids)
        return ok({"released": released, "forced": forced})

    @app.post("/robots/stop-all")
    def stop_all():
        return ok({"stopped": state.stop_all()})


def _register_command_routes(app: Flask, state: NodeState) -> None:
    @app.post("/robots/<robot_id>/command")
    def command(robot_id: str):
        try:
            instruction = parse_instruction(_json_body())
        except ValueError as e:
            return bad(str(e), 400)
        return ok(state.run_command(robot_id, instruction))

    @app.post("/robots/<robot_id>/drive")
    def drive(robot_id: str):
        try:
            speed, heading, duration_ms = parse_drive(_json_body())
        except ValueError as e:
            return bad(str(e), 400)
        try:
            result = state.drive(robot_id, speed, heading, duration_ms)
        except Exception as e:
            return bad(f"drive failed: {type(e).__name__}: {e}", 500)
        if result is None:
            return _not_connected(robot_id)
        return ok({"robot_id": robot_id, **result})

    @app.post("/robots/<robot_id>/stop")
    def stop(robot_id: str):
        def action(handle):
            state.hw.stop(handle)
            return {}

        return _on_handle(state, robot_id, action, "stop")

    @app.post("/robots/<robot_id>/led")
    def led(robot_id: str):
        body = _json_body()
        try:
            r, g, b = (_int_in(body.get(k), k, 0, 255) for k in ("r", "g", "b"))
        except ValueError as e:
            return bad(str(e), 400)

        def action(handle):
            state.hw.set_led(handle, r, g, b)
            return {"r": r, "g": g, "b": b}

        return _on_handle(state, robot_id, action, "led")

    @app.post("/robots/<robot_id>/aim")
    def aim(robot_id: str):
        on = _json_body().get("on")
        if not isinstance(on, bool):
            return bad("aim requires boolean on", 400)

        def action(handle):
            if on:
                state.hw.set_back_led(handle, 255)
            else:
                state.hw.reset_aim(handle)
                state.hw.set_back_led(handle, 0)
            return {"on": on}

        return _on_handle(state, robot_id, action, "aim")

    @app.get("/robots/<robot_id>/battery")
    def battery(robot_id: str):
        return _on_handle(state, robot_id, lambda h: {"voltage": state.hw.battery(h)}, "battery read")


def _register_system_routes(app: Flask, state: NodeState) -> None:
    @app.post("/system/restart")
    @require_token
    def restart():
        _schedule_exit(app, state, "EXIT_PROCESS")
        return ok({"action": "restart"})

    @app.post("/system/update")
    @require_token
    def update():
        branch = _json_body().get("branch", "main")
        if not isinstance(branch, str) or not BRANCH_PATTERN.fullmatch(branch) or branch.startswith("-"):
            return bad("invalid branch name", 400)
        try:
            result = git_update(branch)
        except GIT_ERRORS as e:
            return bad(f"git command failed: {e}", 500)
        _schedule_exit(app, state, "EXIT_PROCESS")
        return ok({**result, "action": "update"})

    @app.post("/system/shutdown")
    @require_token
    def shutdown():
        _schedule_exit(app, state, "POWER_OFF")
        return ok({"action": "shutdown"})


def create_app(config: dict, hardware) -> Flask:
    cfg = {**DEFAULTS, **config}
    app = Flask(__name__)
    try:
        version = read_git_version()
    except GIT_ERRORS:
        version = {"branch": "unknown", "commit": "unknown"}
    app.config.update(
        TOKEN=str(cfg["token"]),
        VERSION=version,
        EXIT_PROCESS=_exit_process,
        POWER_OFF=_power_off,
        EXIT_DELAY_SECONDS=EXIT_DELAY_SECONDS,
    )
    state = NodeState(hardware, cfg)
    app.extensions["node"] = state
    _register_cors(app)
    _register_error_handlers(app)
    _register_status_routes(app, state)
    _register_robot_routes(app, state)
    _register_command_routes(app, state)
    _register_system_routes(app, state)
    return app


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def install_signal_handlers(state: NodeState) -> None:
    def on_signal(signum, _frame):
        print(f"[signal] {signal.Signals(signum).name}: releasing robots", flush=True)
        state.release_ids(None)
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, on_signal)
    signal.signal(signal.SIGINT, on_signal)


def build_hardware(fake_count: int | None):
    if fake_count is not None:
        from sphero_fake import FakeHardware
        return FakeHardware(fake_count), f"FAKE hardware, {fake_count} simulated balls"
    from sphero_hardware import SpheroHardware
    return SpheroHardware(), "real BLE hardware"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Sphero swarm Pi node")
    parser.add_argument("config", nargs="?", default=str(DEFAULT_CONFIG_PATH), help="config JSON path")
    parser.add_argument("--fake", type=int, metavar="N", help="simulate N balls instead of using BLE")
    parser.add_argument("--port", type=int, help="override the port from the config")
    args = parser.parse_args(argv)

    config, loaded = load_config(Path(args.config))
    print("[config] read " + ", ".join(str(p) for p in loaded), flush=True)
    if OVERRIDE_CONFIG_PATH not in loaded:
        print(f"[config] no override file at {OVERRIDE_CONFIG_PATH} (the install script creates one with the token)")
    if args.port is not None:
        config["port"] = args.port
    if config["token"] == DEFAULTS["token"]:
        print(f"WARNING: token is still the default; set \"token\" in {OVERRIDE_CONFIG_PATH} "
              "and copy it into coordinator/pis.json.")

    hardware, mode = build_hardware(args.fake)
    app = create_app(config, hardware)
    install_signal_handlers(app.extensions["node"])
    print(f"Pi node serving on port {config['port']} ({mode})", flush=True)
    app.run(host="0.0.0.0", port=int(config["port"]), threaded=True)


if __name__ == "__main__":
    sys.exit(main())
