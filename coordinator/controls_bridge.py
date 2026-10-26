"""Serves controls/protocol.py on the Controls_Server port so gui_driver.py can run unchanged.

To hook up gui_driver.py: run the dashboard, connect the balls, start the bridge
(dashboard endpoint POST /api/bridge/start, stop with POST /api/bridge/stop),
then run gui_driver.py instead of starting Controls_Server.py. The algorithm
code does not change; only the thing on port 1235 does.

Per connection: send the ordered robot ids (gui_driver reads them as the
handshake), then loop receive batch -> BatchExecutor.run_batch -> reply. The
socket framing is the same protocol gui_driver already speaks. A dropped
client just waits for a reconnection, like Controls_Server does.
"""
import logging
import pickle
import socket
import sys
import threading
from pathlib import Path
from typing import Any, Sequence

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from controls import protocol  # noqa: E402  (needs the repo root on sys.path)

logger = logging.getLogger(__name__)

DEFAULT_PORT = 1235
ACCEPT_TIMEOUT_SECONDS = 0.5
JOIN_TIMEOUT_SECONDS = 5


def configure_listener(listener: socket.socket) -> None:
    """Make a busy port fail to bind.

    On Linux/macOS SO_REUSEADDR only lets a restart reuse TIME_WAIT sockets. On
    Windows the same option lets a second process bind a port that is already
    listening, which would split commands with a running Controls_Server.py.
    There, SO_EXCLUSIVEADDRUSE is the correct option.
    """
    if sys.platform == "win32":
        exclusive = getattr(socket, "SO_EXCLUSIVEADDRUSE", None)
        if exclusive is not None:
            listener.setsockopt(socket.SOL_SOCKET, exclusive, 1)
        return
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)


class ControlsBridge:
    def __init__(self, executor: Any, ordered_robot_ids: Sequence[str],
                 port: int = DEFAULT_PORT, host: str = "localhost"):
        self._executor = executor
        self._robot_ids = list(ordered_robot_ids)
        self._host = host
        self._requested_port = port
        self._port = port
        self._listener: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._stop: threading.Event = threading.Event()

    @property
    def port(self) -> int:
        return self._port

    @property
    def robot_ids(self) -> list[str]:
        return list(self._robot_ids)

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        """Bind synchronously so a busy port raises here, not inside a thread."""
        if self.running:
            raise RuntimeError("controls bridge already running")
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            configure_listener(listener)
            listener.bind((self._host, self._requested_port))
            listener.listen(5)
        except OSError:
            listener.close()
            raise
        listener.settimeout(ACCEPT_TIMEOUT_SECONDS)
        self._port = listener.getsockname()[1]
        self._listener = listener
        # A fresh Event per start: a serve thread left over from a previous start
        # keeps the Event it was given and cannot be revived by this one.
        stop = threading.Event()
        self._stop = stop
        self._thread = threading.Thread(target=self._serve, args=(listener, stop),
                                        name="controls-bridge", daemon=True)
        self._thread.start()
        logger.info("controls bridge listening on %s:%s", self._host, self._port)

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=JOIN_TIMEOUT_SECONDS)
            self._thread = None
        if self._listener is not None:
            self._listener.close()
            self._listener = None

    def _serve(self, listener: socket.socket, stop: threading.Event) -> None:
        # The listener and stop Event are passed in, not read from self, so a stop()
        # that clears self._listener cannot turn accept() into an AttributeError here.
        while not stop.is_set():
            try:
                conn, _ = listener.accept()
            except socket.timeout:
                continue
            except (OSError, AttributeError):
                return  # listener closed: stop() is tearing us down
            try:
                self._handle(conn, stop)
            finally:
                conn.close()

    def _handle(self, conn: socket.socket, stop: threading.Event) -> None:
        conn.settimeout(ACCEPT_TIMEOUT_SECONDS)
        try:
            conn.sendall(pickle.dumps(self._robot_ids))
            while not stop.is_set():
                try:
                    payload = protocol.receive_batch(conn)
                except socket.timeout:
                    continue
                self._answer(conn, payload)
        except (EOFError, ConnectionResetError, BrokenPipeError, OSError) as error:
            logger.info("controls client disconnected (%s); waiting for reconnection", error)

    def _answer(self, conn: socket.socket, payload: Any) -> None:
        if isinstance(payload, dict):
            instructions = payload.get("instructions", [])
            wait_for_completion = bool(payload.get("wait_for_completion"))
        else:
            instructions = payload
            wait_for_completion = False
        outcomes = self._run(instructions)
        if wait_for_completion:
            protocol.send_result(conn, outcomes)
        else:
            conn.sendall(b"Done")

    def _run(self, instructions: Any) -> dict:
        try:
            return self._executor.run_batch(list(instructions))
        except Exception:
            logger.exception("batch failed; replying with no outcomes")
            return {}
