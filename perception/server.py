import asyncio
import base64
import threading
import time
import json
import cv2
from queue import Queue, Empty
import websockets

frame_queue = Queue(maxsize=1)
status_queue = Queue(maxsize=1)

connected_clients = set()
telemetry_clients = set()

key = "perception"

async def broadcast_frames():
    while True:
        try:
            frame, _ = frame_queue.get_nowait()
        except Empty:
            await asyncio.sleep(0.01)
            continue

        _, buffer = cv2.imencode('.jpg', frame)
        jpg_bytes = buffer.tobytes()
        b64_str = base64.b64encode(jpg_bytes).decode('utf-8')

        if connected_clients:
            await asyncio.gather(
                *(client.send(b64_str) for client in connected_clients),
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

async def telemetry_handler(websocket):
    """Register telemetry clients."""
    telemetry_clients.add(websocket)
    print(f"Telemetry client connected: {websocket.remote_address}")
    try:
        async for _ in websocket:
            pass
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        telemetry_clients.discard(websocket)
        print(f"Telemetry client disconnected: {websocket.remote_address}")

async def run_server():
    async with websockets.serve(handler, "localhost", 6767):
        async with websockets.serve(telemetry_handler, "localhost", 6768):
            await asyncio.gather(broadcast_frames(), broadcast_telemetry())

def start_server():
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
print("WebSocket server started — frames: ws://localhost:6767  telemetry: ws://localhost:6768")

def feed_frames_from_calculateFrame(frame, timestamp=None):
    """Call this from calculateFrame after processing a frame."""
    try:
        if frame_queue.full():
            try:
                frame_queue.get_nowait()
            except Empty:
                pass
        frame_queue.put_nowait((frame.copy(), timestamp if timestamp else time.time()))
    except Exception:
        pass

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
