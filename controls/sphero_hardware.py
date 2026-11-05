"""Real Sphero hardware for pi_node.py. The only module that talks to bleak/spherov2.

Calls mirror the proven ones in controls/pi_agent.py. controls/sphero_fake.py
implements the same interface in memory, so keep the two in sync.
"""
import asyncio
import subprocess

import bleak

from ble_reliability import apply_ble_reliability_patches

apply_ble_reliability_patches()

from spherov2 import scanner  # noqa: E402
from spherov2.commands.drive import DriveFlags  # noqa: E402
from spherov2.commands.power import Power  # noqa: E402
from spherov2.sphero_edu import SpheroEduAPI  # noqa: E402
from spherov2.types import Color  # noqa: E402

SPHERO_NAME_PREFIXES = ("SB-", "SM-", "SK-", "SR-")


def _toy_of(handle):
    return handle._SpheroEduAPI__toy


class SpheroHardware:
    """BLE hardware. A handle is an already-entered SpheroEduAPI."""

    def scan(self, seconds: float) -> list[dict]:
        devices = asyncio.run(bleak.BleakScanner.discover(timeout=seconds, return_adv=True))
        results = []
        for address, (device, adv) in devices.items():
            name = adv.local_name or device.name or ""
            if name.startswith(SPHERO_NAME_PREFIXES):
                results.append({"robot_id": name, "address": address, "rssi": adv.rssi})
        return results

    def find(self, names: list[str], max_attempts: int) -> dict:
        """Accumulate find_toys results across attempts, keyed by robot name."""
        found: dict = {}
        for attempt in range(max_attempts):
            print(f"[scan] attempt {attempt + 1}/{max_attempts}")
            for toy in scanner.find_toys(toy_names=names):
                found[str(toy).split()[0]] = toy
            if all(name in found for name in names):
                break
        return found

    def connect(self, toy):
        api = SpheroEduAPI(toy)
        api.__enter__()
        return api

    def address_of(self, toy) -> str | None:
        return getattr(toy, "address", None)

    def stop(self, handle) -> None:
        handle.stop_roll()

    def set_led(self, handle, r: int, g: int, b: int) -> None:
        handle.set_main_led(Color(r, g, b))

    def set_heading(self, handle, deg: int) -> None:
        handle.set_heading(deg % 360)

    def get_heading(self, handle) -> int:
        return handle.get_heading()

    def roll_raw(self, handle, speed: int) -> None:
        flag = DriveFlags.BACKWARD if speed < 0 else DriveFlags.FORWARD
        _toy_of(handle).drive_with_heading(abs(speed), handle.get_heading(), flag)

    def set_back_led(self, handle, value: int) -> None:
        handle.set_back_led(value)

    def reset_aim(self, handle) -> None:
        handle.reset_aim()

    def battery(self, handle) -> float:
        return Power.get_battery_voltage(_toy_of(handle))

    def close(self, handle) -> None:
        handle.__exit__(None, None, None)

    def force_disconnect(self, address: str) -> None:
        subprocess.run(["bluetoothctl", "disconnect", address], timeout=10)
