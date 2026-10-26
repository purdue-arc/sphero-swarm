import pickle
import socket
import struct
import sys

import pytest

from controls import protocol
from controls.Instruction import Instruction
from controls_bridge import ControlsBridge, configure_listener


class RecordingExecutor:
    def __init__(self):
        self.batches = []

    def run_batch(self, instructions):
        self.batches.append(list(instructions))
        return {str(instruction.spheroID): "complete" for instruction in instructions}


@pytest.fixture
def bridge():
    executor = RecordingExecutor()
    server = ControlsBridge(executor, ["SB-1", "SB-2"], port=0, host="127.0.0.1")
    server.start()
    yield server, executor
    server.stop()


def _connect(port):
    sock = socket.create_connection(("127.0.0.1", port), timeout=5)
    return sock


def test_handshake_sends_ordered_robot_ids_then_batch_round_trips_outcomes(bridge):
    server, executor = bridge
    sock = _connect(server.port)
    try:
        assert pickle.loads(sock.recv(4096)) == ["SB-1", "SB-2"]

        outcomes = protocol.send_batch(sock, [Instruction(1, 0, 255, 0, 0), Instruction(2, 1, 60, 1.0)])

        assert outcomes == {"1": "complete", "2": "complete"}
        assert [i.spheroID for i in executor.batches[0]] == [1, 2]
    finally:
        sock.close()


def test_empty_batch_round_trips_as_empty_outcomes(bridge):
    server, _ = bridge
    sock = _connect(server.port)
    try:
        sock.recv(4096)

        assert protocol.send_batch(sock, []) == {}
    finally:
        sock.close()


def test_batch_without_wait_for_completion_is_acknowledged_with_done(bridge):
    server, executor = bridge
    sock = _connect(server.port)
    try:
        sock.recv(4096)
        payload = pickle.dumps({"instructions": [Instruction(1, 3, 0.1)], "wait_for_completion": False})
        sock.sendall(protocol.MAGIC + struct.pack("!I", len(payload)) + payload)

        assert sock.recv(4) == b"Done"
        assert len(executor.batches) == 1
    finally:
        sock.close()


def test_bridge_accepts_a_new_client_after_the_old_one_disconnects(bridge):
    server, _ = bridge
    first = _connect(server.port)
    first.recv(4096)
    first.close()

    second = _connect(server.port)
    try:
        assert pickle.loads(second.recv(4096)) == ["SB-1", "SB-2"]
    finally:
        second.close()


def test_stop_releases_the_port_and_marks_bridge_not_running():
    server = ControlsBridge(RecordingExecutor(), ["SB-1"], port=0, host="127.0.0.1")
    server.start()
    port = server.port

    server.stop()

    assert server.running is False
    rebound = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        rebound.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        rebound.bind(("127.0.0.1", port))
    finally:
        rebound.close()


def test_stop_then_start_again_serves_a_new_client_and_the_old_thread_exits():
    server = ControlsBridge(RecordingExecutor(), ["SB-1"], port=0, host="127.0.0.1")
    server.start()
    first_thread = server._thread
    server.stop()
    assert first_thread.is_alive() is False

    server.start()
    sock = _connect(server.port)
    try:
        assert pickle.loads(sock.recv(4096)) == ["SB-1"]
    finally:
        sock.close()
        server.stop()


class _RecordingSocket:
    def __init__(self):
        self.options = []

    def setsockopt(self, level, option, value):
        self.options.append((level, option, value))


def test_posix_listener_sets_reuseaddr(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    listener = _RecordingSocket()

    configure_listener(listener)

    assert listener.options == [(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)]


def test_windows_listener_never_sets_reuseaddr(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(socket, "SO_EXCLUSIVEADDRUSE", 0x0800, raising=False)
    listener = _RecordingSocket()

    configure_listener(listener)

    assert listener.options == [(socket.SOL_SOCKET, 0x0800, 1)]
    assert all(option != socket.SO_REUSEADDR for _, option, _ in listener.options)


def test_windows_listener_without_exclusive_option_sets_nothing(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.delattr(socket, "SO_EXCLUSIVEADDRUSE", raising=False)
    listener = _RecordingSocket()

    configure_listener(listener)

    assert listener.options == []
