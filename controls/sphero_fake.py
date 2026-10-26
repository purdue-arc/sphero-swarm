"""In-memory stand-in for sphero_hardware.SpheroHardware (laptop UI work and tests).

Same method names and signatures as the real class. Every call that touches a
ball is appended to FakeHardware.calls as (method, robot_id, *args), so tests
can assert that a release really stopped, LED-offed and closed a ball.
"""
import random
import time
from dataclasses import dataclass

FAKE_PREFIX = "SB-F"


@dataclass
class FakeToy:
    robot_id: str
    address: str
    rssi: int

    def __str__(self) -> str:
        return f"{self.robot_id} (simulated)"


@dataclass
class FakeHandle:
    robot_id: str
    heading: int = 0
    led: tuple = (0, 0, 0)
    back_led: int = 0


class FakeHardware:
    """hang_connect: robot ids whose connect() sleeps hang_seconds before answering,
    to exercise the node's connect timeout."""

    def __init__(self, count: int = 6, fail: frozenset[str] | set[str] = frozenset(), latency: float = 0.0,
                 hang_connect: frozenset[str] | set[str] = frozenset(), hang_seconds: float = 0.0):
        self.latency = latency
        self.fail = frozenset(fail)
        self.hang_connect = frozenset(hang_connect)
        self.hang_seconds = hang_seconds
        self.calls: list[tuple] = []
        self.toys: dict[str, FakeToy] = {}
        for index in range(1, count + 1):
            robot_id = f"{FAKE_PREFIX}{index:03d}"
            address = f"FA:KE:00:00:00:{index:02X}"
            self.toys[robot_id] = FakeToy(robot_id, address, random.Random(robot_id).randint(-90, -40))

    def _pause(self) -> None:
        if self.latency:
            time.sleep(self.latency)

    def scan(self, seconds: float) -> list[dict]:
        self._pause()
        return [{"robot_id": t.robot_id, "address": t.address, "rssi": t.rssi} for t in self.toys.values()]

    def find(self, names: list[str], max_attempts: int) -> dict:
        self._pause()
        return {name: self.toys[name] for name in names if name in self.toys}

    def connect(self, toy: FakeToy) -> FakeHandle:
        self._pause()
        self.calls.append(("connect", toy.robot_id))
        if toy.robot_id in self.hang_connect:
            time.sleep(self.hang_seconds)
        if toy.robot_id in self.fail:
            raise ConnectionError(f"simulated connect failure for {toy.robot_id}")
        return FakeHandle(toy.robot_id)

    def address_of(self, toy: FakeToy) -> str:
        return toy.address

    def stop(self, handle: FakeHandle) -> None:
        self.calls.append(("stop", handle.robot_id))

    def set_led(self, handle: FakeHandle, r: int, g: int, b: int) -> None:
        handle.led = (r, g, b)
        self.calls.append(("set_led", handle.robot_id, r, g, b))

    def set_heading(self, handle: FakeHandle, deg: int) -> None:
        handle.heading = deg % 360
        self.calls.append(("set_heading", handle.robot_id, deg))

    def get_heading(self, handle: FakeHandle) -> int:
        return handle.heading

    def roll_raw(self, handle: FakeHandle, speed: int) -> None:
        self.calls.append(("roll", handle.robot_id, speed))

    def set_back_led(self, handle: FakeHandle, value: int) -> None:
        handle.back_led = value
        self.calls.append(("set_back_led", handle.robot_id, value))

    def reset_aim(self, handle: FakeHandle) -> None:
        self.calls.append(("reset_aim", handle.robot_id))

    def battery(self, handle: FakeHandle) -> float:
        return 3.9 + random.Random(handle.robot_id).randint(0, 20) / 100

    def close(self, handle: FakeHandle) -> None:
        self.calls.append(("close", handle.robot_id))

    def force_disconnect(self, address: str) -> None:
        self.calls.append(("force_disconnect", address))
