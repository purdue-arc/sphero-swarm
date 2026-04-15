# Connection test server: same scan / connect / disconnect path as Fall_2025_Sphero_Swarm_Server,
# but after connect only sets main LED colors (no TCP command socket, no roll / turn / heading).

# PLEASE READ:
#   - Have Bluetooth on this device prior to running code, to avoid getting a WIN error if you are on Windows OS

from spherov2 import scanner
from spherov2.sphero_edu import SpheroEduAPI
from spherov2.types import Color
from spherov2.commands.power import Power
import threading
import argparse
import time
import asyncio
import websockets
import json
import logging

from queue import Queue, Empty

control_cmd_queue: Queue[dict] = Queue()

KILL_FLAG = 0

parser = argparse.ArgumentParser(description="Sphero connection test (LED only)")
parser.add_argument('--server', '-s', action='store_true', help="Listen for WebSocket GUI connect (same port as swarm server).")
args = parser.parse_args()

# Distinct colors per ball index (cycles if there are more balls than entries)
_LED_PALETTE = (
    Color(255, 0, 0),
    Color(0, 255, 0),
    Color(0, 0, 255),
    Color(255, 255, 0),
    Color(255, 0, 255),
    Color(0, 255, 255),
    Color(255, 128, 0),
    Color(180, 180, 255),
    Color(255, 180, 180),
    Color(180, 255, 180),
)


def generate_dict_map(sorted_names):
    mapping = {}
    for i in range(len(sorted_names)):
        mapping[sorted_names[i]] = i
    return mapping


def _toy_list_prefix(toy) -> str:
    """Prefix token of toy string (e.g. SB-XXXX) for matching GUI names."""
    return str(toy).split()[0]


def find_balls(names, max_attempts, ws=None, loop=None):
    """Scan up to max_attempts times; connect only to toys that appear in ``names`` and are found.
    Names in the list that never show up in a scan are skipped (no error if at least one is found)."""
    if ws:
        ws_send(loop, ws, {
            "type": "scan_start",
            "balls": names
        })

    best = []
    for attempts in range(max_attempts):
        print("Attempts to find Spheros: " + str(attempts + 1))
        toys = scanner.find_toys(toy_names=names)
        print("Balls found: {}".format(toys))
        if len(toys) == len(names):
            print("Found all Sphero balls")
            return toys
        if len(toys) > len(best):
            best = list(toys)
        print("Partial scan ({} / {}), retrying...".format(len(toys), len(names)))

    if best:
        found_names = {_toy_list_prefix(t) for t in best}
        missing = [n for n in names if n not in found_names]
        print(
            "Connecting to {} ball(s) from the list; not in range / not found (skipped): {}".format(
                len(best), missing
            )
        )
        return best

    if ws:
        ws_send(loop, ws, {
            "type": "scan_failed",
            "balls": names,
            "reason": "No Spheros from the list could be found"
        })

    raise RuntimeError("No balls from the provided list were found")


def address_sort(addresses, map_to_location):
    addresses.sort(key=lambda address: map_to_location[address.__str__().split()[0]])
    print("Sorted Addresses: {}".format(addresses))


def connect_ball(toy_address, ret_list, location, max_attempts, ws=None, loop=None):
    attempts = 0
    while attempts < max_attempts:
        try:
            sb = SpheroEduAPI(toy_address).__enter__()
            ret_list[location] = sb

            if ws:
                ws_send(loop, ws, {
                    "type": "ball_connected",
                    "ball": str(toy_address),
                    "index": location
                })

            return
        except Exception:
            attempts += 1
            print("Trying to connect with: {}, attempt {}".format(toy_address, attempts))
            continue

    if ws:
        ws_send(loop, ws, {
            "type": "ball_failed",
            "ball": str(toy_address),
            "reason": "Connection attempts exceeded"
        })


def connect_multi_ball(toy_addresses, ret_list, max_attempts, ws=None, loop=None):
    print("Connecting to Spheros...")

    threads = []
    for index in range(len(toy_addresses)):
        thread = threading.Thread(
            target=connect_ball,
            args=[toy_addresses[index], ret_list, index, max_attempts, ws, loop],
        )
        threads.append(thread)
        thread.start()

    while True:
        try:
            for thread in threads:
                thread.join(timeout=None)
            break
        except KeyboardInterrupt:
            print("Connection ongoing... please don't interrupt.")
            continue

    print("Balls Connected: {}".format(ret_list))


def check_voltage(sb):
    return Power.get_battery_voltage(sb._SpheroEduAPI__toy)


def terminate_ball(sb):
    if sb is not None:
        sb.__exit__(None, None, None)


def terminate_multi_ball(sb_list):
    print("Ending processes — disconnecting Spheros")
    threads = []
    for sb in sb_list:
        if type(sb) is SpheroEduAPI:
            thread = threading.Thread(target=terminate_ball, args=[sb])
            threads.append(thread)
            thread.start()

    while True:
        try:
            for thread in threads:
                thread.join(timeout=None)
            break
        except KeyboardInterrupt:
            print("KeyboardInterrupt caught, please do not terminate prematurely")
            continue


def apply_led_colors(sb_list):
    """Set each connected ball to a fixed palette color (no motion)."""
    for i, sb in enumerate(sb_list):
        if sb is None:
            continue
        try:
            sb.set_main_led(_LED_PALETTE[i % len(_LED_PALETTE)])
        except Exception:
            logging.exception("apply_led_colors: failed for index %s", i)


def run_connection_test(ball_names, ws=None, loop=None):
    global KILL_FLAG
    KILL_FLAG = 0

    name_to_location_dict = generate_dict_map(ball_names)
    toys_addresses = find_balls(ball_names, 5, ws, loop)
    address_sort(toys_addresses, name_to_location_dict)
    found_prefixes = {_toy_list_prefix(t) for t in toys_addresses}
    names_in_order = sorted(
        [n for n in ball_names if n in found_prefixes],
        key=lambda n: name_to_location_dict[n],
    )
    print("Names linked to connected balls only (sorted): {}".format(names_in_order))

    sb_list = [None] * len(toys_addresses)

    try:
        connect_multi_ball(toys_addresses, sb_list, 10, ws, loop)

        for sb in sb_list:
            if sb is not None:
                print(check_voltage(sb))

        apply_led_colors(sb_list)
        print("LED colors set — idle (no movement). Ctrl+C in terminal or disconnect from GUI to exit.")

        while KILL_FLAG == 0:
            try:
                ctrl = control_cmd_queue.get_nowait()
            except Empty:
                ctrl = None

            if ctrl is not None:
                ctype = ctrl.get("type")
                if ctype == "rehome":
                    # LED-only test: re-apply colors (no set_heading — that would move the ball)
                    apply_led_colors(sb_list)
                elif ctype == "disconnect":
                    ball = ctrl.get("ball")
                    if ball is not None:
                        try:
                            idx = names_in_order.index(ball)
                            if sb_list[idx] is not None:
                                terminate_ball(sb_list[idx])
                                sb_list[idx] = None
                        except ValueError:
                            pass

            time.sleep(0.1)

    finally:
        KILL_FLAG = 1
        terminate_multi_ball(sb_list)


async def handle_client(websocket):
    print("Client connected")
    loop = asyncio.get_running_loop()

    async for message in websocket:
        data = json.loads(message)
        typ = data.get("type")

        if typ == "connect":
            ball_names = data["spheros"]
            await loop.run_in_executor(
                None,
                run_connection_test,
                ball_names,
                websocket,
                loop,
            )
        else:
            try:
                control_cmd_queue.put_nowait(data)
            except Exception:
                pass


def ws_send(loop, websocket, payload):
    asyncio.run_coroutine_threadsafe(
        websocket.send(json.dumps(payload)),
        loop,
    )


async def start_web_server():
    host = "localhost"
    port = 6768
    print("Connection test WebSocket on ws://{}:{}".format(host, port))

    async with websockets.serve(handle_client, host, port):
        try:
            while True:
                await asyncio.sleep(3600)
        except asyncio.CancelledError:
            pass


def local_cli_test(ball_names):
    """Run scan + connect + LED colors without WebSocket (edit the list in __main__)."""
    run_connection_test(ball_names, ws=None, loop=None)


if __name__ == "__main__":
    if args.server:
        asyncio.run(start_web_server())
    else:
        # Example: replace with your SB- tags
        local_cli_test([ "SB-B5A9", "SB-0439", "SB-7672", "SB-76B3", "SB-3881", "SB-8262", "SB-D950", "SB-C596", "SB-1A8C", "SB-387B", "SB-4D8E", "SB-1730"])
