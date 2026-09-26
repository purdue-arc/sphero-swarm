import asyncio
import base64
import threading
import time
import json
import cv2
import errno
from queue import Queue, Empty
import websockets

frame_queue = Queue(maxsize=1)
mask_queue = Queue(maxsize=1)
status_queue = Queue(maxsize=1)
command_queue = Queue(maxsize=10)  # Commands from GUI (e.g., grid toggle)

connected_clients = set()
mask_clients = set()
telemetry_clients = set()

FRAME_HOST = "localhost"
FRAME_PORT = 6767
MASK_HOST = "localhost"
MASK_PORT = 6771
TELEMETRY_HOST = "localhost"
TELEMETRY_PORT = 6770

# Commands the GUI may send over the telemetry socket. Anything else is ignored
# so a stray message can't reach the processing thread.
COMMAND_ACTIONS = ("toggle_grid", "set_tuning")

key = "perception"

async def broadcast_queue(queue, clients):
    """Encode whatever lands in `queue` and push it to every client in `clients`."""
    while True:
        try:
            frame, _ = queue.get_nowait()
        except Empty:
            await asyncio.sleep(0.01)
            continue

        _, buffer = cv2.imencode('.jpg', frame)
        jpg_bytes = buffer.tobytes()
        b64_str = base64.b64encode(jpg_bytes).decode('utf-8')

        if clients:
            await asyncio.gather(
                *(client.send(b64_str) for client in clients),
                return_exceptions=True
            )

        await asyncio.sleep(0.03)

async def broadcast_telemetry():
    while True:
        try:
            msg = status_queue.get_nowait()
        except Empty:
            await asyncio.sleep(0.01)
            continue

        if telemetry_clients:
            await asyncio.gather(
                *(client.send(msg) for client in telemetry_clients),
                return_exceptions=True
            )

        await asyncio.sleep(0.03)

async def handler(websocket):
    """Register frame stream clients."""
    connected_clients.add(websocket)
    print(f"Frame client connected: {websocket.remote_address}")
    try:
        async for _ in websocket:
            pass
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        connected_clients.discard(websocket)
        print(f"Frame client disconnected: {websocket.remote_address}")

async def mask_handler(websocket):
    """Register filter-mask stream clients.

    Nobody connected here means the GUI isn't showing the mask, and
    sphero_spotter skips drawing it (see mask_view_wanted).
    """
    mask_clients.add(websocket)
    print(f"Mask client connected: {websocket.remote_address}")
    try:
        async for _ in websocket:
            pass
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        mask_clients.discard(websocket)
        print(f"Mask client disconnected: {websocket.remote_address}")

async def telemetry_handler(websocket):
    """Register telemetry clients and receive commands from GUI."""
    telemetry_clients.add(websocket)
    print(f"Telemetry client connected: {websocket.remote_address}")
    try:
        async for msg in websocket:
            try:
                cmd = json.loads(msg)
                print(f"[Telemetry] Received message from GUI: {cmd}")
                if cmd.get("action") in COMMAND_ACTIONS:
                    command_queue.put_nowait(cmd)
                    print(f"[Telemetry] Queued {cmd.get('action')} for sphero_spotter")
            except json.JSONDecodeError as e:
                print(f"[Telemetry] JSON decode error: {e}")
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        telemetry_clients.discard(websocket)
        print(f"Telemetry client disconnected: {websocket.remote_address}")

async def run_server():
    async with websockets.serve(handler, FRAME_HOST, FRAME_PORT):
        async with websockets.serve(mask_handler, MASK_HOST, MASK_PORT):
            async with websockets.serve(telemetry_handler, TELEMETRY_HOST, TELEMETRY_PORT):
                await asyncio.gather(
                    broadcast_queue(frame_queue, connected_clients),
                    broadcast_queue(mask_queue, mask_clients),
                    broadcast_telemetry(),
                )

def start_server():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(run_server())
    except OSError as exc:
        # Prevent noisy thread tracebacks when another process already owns the port.
        if exc.errno == errno.EADDRINUSE:
            print(
                f"Perception WebSocket server not started: one of the ports is already in use "
                f"(frames: ws://{FRAME_HOST}:{FRAME_PORT}, mask: ws://{MASK_HOST}:{MASK_PORT}, "
                f"telemetry: ws://{TELEMETRY_HOST}:{TELEMETRY_PORT})."
            )
        else:
            raise
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()

server_thread = threading.Thread(target=start_server, daemon=True)
server_thread.start()
print(
    f"WebSocket server started — frames: ws://{FRAME_HOST}:{FRAME_PORT} "
    f"mask: ws://{MASK_HOST}:{MASK_PORT} "
    f"telemetry: ws://{TELEMETRY_HOST}:{TELEMETRY_PORT}"
)

def _feed(queue, frame, timestamp):
    try:
        if queue.full():
            try:
                queue.get_nowait()
            except Empty:
                pass
        queue.put_nowait((frame.copy(), timestamp if timestamp else time.time()))
    except Exception:
        pass

def feed_frames_from_calculateFrame(frame, timestamp=None):
    """Call this from calculateFrame after processing a frame."""
    _feed(frame_queue, frame, timestamp)

def feed_mask_frame(frame, timestamp=None):
    """Call this with the filtered (mask) view, for the GUI's filter stream."""
    _feed(mask_queue, frame, timestamp)

def mask_view_wanted():
    """True while the GUI has the filter view open, so it's worth rendering."""
    return bool(mask_clients)

def feed_status(data: dict):
    """Call this from sphero_spotter after each processed frame to push telemetry to the GUI."""
    try:
        msg = json.dumps(data)
        if status_queue.full():
            try:
                status_queue.get_nowait()
            except Empty:
                pass
        status_queue.put_nowait(msg)
    except Exception:
        pass

def get_command():
    """Check for pending commands from the GUI (non-blocking)."""
    try:
        return command_queue.get_nowait()
    except Empty:
        return None
