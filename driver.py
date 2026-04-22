import asyncio
import json
import threading

import websockets

from gui_driver import main_server

WS_URL = "ws://localhost:6769"

async def send_start_when_ready() -> None:
    while True:
        try:
            async with websockets.connect(WS_URL) as ws:
                await ws.send(json.dumps({"type": "use_controls", "value": True}))
                await ws.send(json.dumps({"type": "start"}))
                print("[driver] connected, enabled controls, and sent start command")
                async for _message in ws:
                    pass
        except OSError:
            await asyncio.sleep(0.25)

def start_main_server_thread() -> threading.Thread:
    thread = threading.Thread(target=main_server, daemon=True)
    thread.start()
    return thread

if __name__ == "__main__":
    start_main_server_thread()
    asyncio.run(send_start_when_ready())