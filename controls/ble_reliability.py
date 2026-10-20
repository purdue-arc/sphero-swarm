"""Shared BLE reliability patches for any script connecting to Spheros.

Import and call apply_ble_reliability_patches() once, before any Sphero
connection is attempted (at module import time is fine). Extracted from
Controls_Test_Server.py so controls/pi_agent.py doesn't have to duplicate
patches that were only proven correct through real hardware testing.
"""
import asyncio
import logging
import threading

import bleak
import spherov2.adapter.bleak_adapter as _bleak_adapter_module

BLE_CONNECT_TIMEOUT_SECONDS = 30.0


def _patched_bleak_adapter_init(self, address):
    """Replaces BleakAdapter.__init__ (spherov2/adapter/bleak_adapter.py).

    The installed library hardcodes a 5-second BLE GATT connect timeout
    (bleak.BleakClient(address, timeout=5.0)) - that fires and fails a
    connection attempt well before any outer retry budget ever gets a say,
    no matter how that outer budget is configured. This patches just the
    timeout value; everything else is identical to the original.

    This isn't textually inside the real BleakAdapter class body, so the
    name-mangled private attributes (self.__x inside that class becomes
    self._BleakAdapter__x) must be referenced explicitly by their mangled
    names here - same pattern as sb._SpheroEduAPI__toy used elsewhere in
    this codebase.
    """
    self._BleakAdapter__event_loop = asyncio.new_event_loop()
    self._BleakAdapter__device = bleak.BleakClient(address, timeout=BLE_CONNECT_TIMEOUT_SECONDS)
    self._BleakAdapter__lock = threading.Lock()
    self._BleakAdapter__thread = threading.Thread(target=self._BleakAdapter__event_loop.run_forever)
    self._BleakAdapter__thread.start()
    try:
        self._BleakAdapter__execute(self._BleakAdapter__device.connect())
    except Exception:
        self.close(False)
        raise


def _quiet_thread_excepthook(args):
    """Same root cause as the asyncio logger below, different mechanism:
    spherov2's per-toy background write thread (__process_packet) raises
    straight into Python's default thread exception hook (not the logging
    module) when a write fails under connection-congestion conditions.
    Quiets it the same way - does not stop the underlying failure, only
    the noise."""
    pass


def apply_ble_reliability_patches():
    """Call once at startup, before scanning/connecting to any Sphero."""
    # Holding many simultaneous BLE connections causes spherov2's background
    # notification threads to occasionally hit corrupted/out-of-sync packets
    # (PacketDecodingException, BleakError) deep inside bleak's asyncio
    # callbacks. asyncio's default handler logs these at ERROR level with a
    # full traceback per occurrence - raising the threshold here silences
    # the noise without touching bleak/spherov2 itself. Does not fix the
    # underlying radio congestion, only stops it from flooding the terminal.
    logging.getLogger("asyncio").setLevel(logging.CRITICAL)
    threading.excepthook = _quiet_thread_excepthook
    _bleak_adapter_module.BleakAdapter.__init__ = _patched_bleak_adapter_init
