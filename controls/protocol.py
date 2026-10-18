"""Framed instruction batches; legacy clients remain supported by the server."""
import pickle
import struct
import socket

MAGIC = b"SW26"


def read_exact(sock, size):
    data = bytearray()
    while len(data) < size:
        try:
            chunk = sock.recv(size - len(data))
        except socket.timeout:
            if data:
                raise EOFError("Timed out inside a controls message")
            raise
        if not chunk:
            raise EOFError("Controls connection closed")
        data.extend(chunk)
    return bytes(data)


def send_batch(sock, instructions):
    payload = pickle.dumps({"instructions": instructions, "wait_for_completion": True})
    sock.sendall(MAGIC + struct.pack("!I", len(payload)) + payload)
    size = struct.unpack("!I", read_exact(sock, 4))[0]
    return pickle.loads(read_exact(sock, size))


def receive_batch(sock):
    prefix = read_exact(sock, 4)
    if prefix == MAGIC:
        try:
            size = struct.unpack("!I", read_exact(sock, 4))[0]
            if size > 1024 * 1024:
                raise EOFError("Instruction batch too large")
            return pickle.loads(read_exact(sock, size))
        except socket.timeout as error:
            raise EOFError("Timed out inside a controls message") from error
    return pickle.loads(prefix + sock.recv(65536))


def send_result(sock, result):
    payload = pickle.dumps(result)
    sock.sendall(struct.pack("!I", len(payload)) + payload)
