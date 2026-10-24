import asyncio
import json
import logging
import unittest

import websockets

from websocket_logging import IgnoreEmptyHandshakes


class RecordingHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        self.records.append(record)


class HandshakeTests(unittest.IsolatedAsyncioTestCase):
    async def test_empty_connection_is_quiet_but_invalid_request_is_logged(self):
        logger = logging.Logger("handshake-test")
        records = RecordingHandler()
        logger.addHandler(records)
        logger.addFilter(IgnoreEmptyHandshakes())

        async def echo(socket):
            async for message in socket:
                await socket.send(message)

        async with websockets.serve(echo, "127.0.0.1", 0, logger=logger) as server:
            port = server.sockets[0].getsockname()[1]

            async def request(data):
                reader, writer = await asyncio.open_connection("127.0.0.1", port)
                writer.write(data)
                await writer.drain()
                writer.write_eof()
                await reader.read()
                writer.close()
                await writer.wait_closed()

            await request(b"")
            failures = lambda: [r for r in records.records
                                if r.getMessage() == "opening handshake failed"]
            self.assertEqual(failures(), [])

            for data in [b"GET /", b"GET / HTTP/1.1\r\n", b"invalid\r\n\r\n"]:
                with self.subTest(data=data):
                    before = len(failures())
                    await request(data)
                    self.assertEqual(len(failures()), before + 1)

            # Failed handshakes must not affect valid commands or state traffic.
            async with websockets.connect(f"ws://127.0.0.1:{port}") as socket:
                command = json.dumps({"type": "step_seconds", "value": 0.5})
                await socket.send(command)
                self.assertEqual(await socket.recv(), command)


if __name__ == "__main__":
    unittest.main()
