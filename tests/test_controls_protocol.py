import pickle
import socket
import struct
import threading
import unittest

from controls.protocol import MAGIC, receive_batch, send_batch, send_result


class ControlsProtocolTests(unittest.TestCase):
    def sockets(self):
        left, right = socket.socketpair()
        self.addCleanup(left.close)
        self.addCleanup(right.close)
        left.settimeout(2)
        right.settimeout(2)
        return left, right

    def test_complete_roundtrip_with_large_instruction_batch(self):
        client, server = self.sockets()
        instructions = list(range(5000))
        errors = []
        def respond():
            try:
                batch = receive_batch(server)
                self.assertTrue(batch["wait_for_completion"])
                self.assertEqual(batch["instructions"], instructions)
                send_result(server, {"1": "complete", "2": "disconnected"})
            except Exception as error:
                errors.append(error)
        thread = threading.Thread(target=respond)
        thread.start()
        self.assertEqual(send_batch(client, instructions), {"1": "complete", "2": "disconnected"})
        thread.join(2)
        self.assertFalse(errors)

    def test_fragmented_packets_are_reassembled(self):
        client, server = self.sockets()
        payload = pickle.dumps({"instructions": [1, 2, 3]})
        wire = MAGIC + struct.pack("!I", len(payload)) + payload
        thread = threading.Thread(target=lambda: [client.sendall(bytes([byte])) for byte in wire])
        thread.start()
        self.assertEqual(receive_batch(server), {"instructions": [1, 2, 3]})
        thread.join(2)

    def test_legacy_instruction_lists_still_work(self):
        client, server = self.sockets()
        client.sendall(pickle.dumps([1, 2, 3]))
        self.assertEqual(receive_batch(server), [1, 2, 3])


if __name__ == "__main__":
    unittest.main()
