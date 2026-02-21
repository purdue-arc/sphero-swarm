import asyncio
import base64
import threading
import time
import cv2
from queue import Queue, Empty
import numpy as np
import websockets

frame_queue = Queue(maxsize=1)

connected_clients = set()
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
        b64_bytes = base64.b64encode(jpg_bytes)
        b64_str = b64_bytes.decode('utf-8')

        if connected_clients:
            await asyncio.gather(*(client.send(b64_str) for client in connected_clients))

        await asyncio.sleep(0.03)

async def handler(websocket):
    """Register clients and keep connection alive."""
    connected_clients.add(websocket)
    print(f"Client connected: {websocket.remote_address}")
    try:
        async for _ in websocket:
            pass  # Ignore incoming messages
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        connected_clients.remove(websocket)
        print(f"Client disconnected: {websocket.remote_address}")

async def run_server():
    """Run both the WebSocket server and frame broadcaster."""
    async with websockets.serve(handler, "localhost", 6767):
        await broadcast_frames()

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
print("WebSocket server started on ws://localhost:6767")

def feed_frames_from_calculateFrame(frame, timestamp=None):
    """Call this from calculateFrame after processing frame"""
    try:
        if frame_queue.full():
            try:
                frame_queue.get_nowait()
            except Empty:
                pass
        frame_queue.put_nowait((frame.copy(), timestamp if timestamp else time.time()))
    except:
        pass