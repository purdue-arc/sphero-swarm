import asyncio
import json
import threading
import time
from queue import Queue, Empty
import websockets

# ----------------------------------------------------------------------------
# Command support
#
# The GUI client can send simple JSON commands over the same WebSocket
# connection that is used for state broadcasting.  We enqueue them so that
# the algorithm driver can consume them at its own pace.  Typical commands are
# {"type": "pause"} or {"type": "resume"} but the format is open-ended.
#
# The queue is intentionally small since only the most recent command matters and
# the algorithm loop polls it frequently.  Commands that cannot be parsed are
# ignored with a log message.
# ----------------------------------------------------------------------------

command_queue: Queue[dict] = Queue(maxsize=4)


def get_next_command(timeout: float | None = None) -> dict | None:
    """Return next command from GUI or ``None`` if the queue is empty.

    ``timeout`` behaves like :py:meth:`queue.Queue.get` so the caller can
    block briefly while waiting for input.  The algorithm driver uses a
    non-blocking poll (timeout=0) in its main loop.

    To keep the simulation responsive we collapse successive ``speed``
    commands: if multiple speed adjustments arrive before the driver
    processes them, only the last one is returned and earlier ones are
    discarded.  Other commands remain in the queue in their original
    order.
    """
    try:
        cmd = command_queue.get(timeout=timeout)
    except Empty:
        return None

    # special-case speed: drop any later speed commands, preserving the
    # most recent value while leaving other pending commands untouched.
    if isinstance(cmd, dict) and cmd.get("type") == "speed":
        latest = cmd
        to_requeue: list[dict] = []
        # drain the queue
        while True:
            try:
                nxt = command_queue.get_nowait()
            except Empty:
                break
            if isinstance(nxt, dict) and nxt.get("type") == "speed":
                latest = nxt
            else:
                to_requeue.append(nxt)
        # put back any non-speed commands we removed
        for item in to_requeue:
            try:
                command_queue.put_nowait(item)
            except Exception:
                # if the queue is full (unlikely) just drop the item; newer
                # commands are more important
                pass
        return latest

    return cmd


state_queue = Queue(maxsize=1)
connected_clients = set()

async def broadcast_state():
    while True:
        try:
            state = state_queue.get_nowait()
        except Empty:
            await asyncio.sleep(0.01)
            continue

        message = json.dumps(state)

        if connected_clients:
            await asyncio.gather(*(client.send(message) for client in connected_clients))

        await asyncio.sleep(0.03)


async def handler(websocket):
    """Register clients, keep connection alive, and accept simple commands.

    The client may send JSON strings; anything that parses to a dict is
    enqueued for the driver to consume.  We still round‑trip state on the
    broadcast task so clients see live updates.
    """
    connected_clients.add(websocket)
    print(f"Client connected: {websocket.remote_address}")
    try:
        async for message in websocket:
            # every incoming message is treated as a command
            try:
                cmd = json.loads(message)
                if isinstance(cmd, dict):
                    # drop oldest if queue full so that newer commands win
                    if command_queue.full():
                        try:
                            command_queue.get_nowait()
                        except Empty:
                            pass
                    command_queue.put_nowait(cmd)
                else:
                    print(f"[gui_server] ignored non-dict command: {cmd}")
            except Exception as e:
                print(f"[gui_server] failed to parse command {message!r}: {e}")
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        connected_clients.remove(websocket)
        print(f"Client disconnected: {websocket.remote_address}")


async def run_server():
    """Run both the WebSocket server and state broadcaster."""
    async with websockets.serve(handler, "localhost", 6769):
        await broadcast_state()


def start_server():
    """Start the WebSocket server in a new event loop."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(run_server())
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()


server_thread = threading.Thread(target=start_server, daemon=True)
server_thread.start()
print("Algorithm WebSocket server started on ws://localhost:6769")


def build_state_payload(algorithm) -> dict:
    """
    Serialize the current algorithm state into a JSON-serializable dict.

    Payload structure:
    {
        "timestamp": float,
        "grid": { "width": int, "height": int },
        "spheros": [
            {
                "id": int,
                "x": int,
                "y": int,
                "color": <color>,
                "direction": int
            },
            ...
        ],
        "bonded_groups": [
            [id1, id2, ...],   # one list per bonded group
            ...
        ]
    }
    """
    if hasattr(algorithm, "find_all_spheros"):
        spheros_list = algorithm.find_all_spheros()
    else:
        spheros_list = [s for s in getattr(algorithm, "spheros", []) if s is not None]

    spheros_payload = [
        {
            "id": sphero.id,
            "x": sphero.x,
            "y": sphero.y,
            "color": sphero.color,
            "direction": sphero.direction,
        }
        for sphero in spheros_list
    ]

    if hasattr(algorithm, "bonded_groups"):
        bonded_groups_payload = [
            [sphero.id for sphero in group.spheros]
            for group in algorithm.bonded_groups
            if len(group.spheros) > 0
        ]
    else:
        bonded_groups_payload = getattr(getattr(algorithm, "swarm", None), "bonded_groups", [])

    return {
        "timestamp": time.time(),
        "grid": {
            "width": algorithm.grid_width,
            "height": algorithm.grid_height,
        },
        "spheros": spheros_payload,
        "bonded_groups": bonded_groups_payload,
    }


def send_algorithm_state(algorithm):
    """
    Call this after each algorithm step to broadcast the current state.
    Drops the previous frame if it hasn't been sent yet (non-blocking).
    """
    try:
        state = build_state_payload(algorithm)
        if state_queue.full():
            try:
                state_queue.get_nowait()
            except Empty:
                pass
        state_queue.put_nowait(state)
    except Exception as e:
        print(f"[algorithm_server] Failed to enqueue state: {e}")