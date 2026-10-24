"""HTTP/JSON client for one Pi's controls/pi_agent.py Controls Service.

One instance per Pi — the registry below creates and reuses these rather
than opening a fresh client per call. Synchronous (requests), matching the
rest of this codebase rather than mixing async and sync HTTP for no reason
yet.

Network failures (Pi offline, unreachable, timed out) are caught here and
normalized into the same {"ok": false, "error": ...} shape pi_agent.py
itself returns for application-level errors — callers only need to handle
one shape, not "the Pi said no" vs. "the Pi never answered" separately.
"""
import requests

DEFAULT_PORT = 5000
DEFAULT_TIMEOUT_SECONDS = 10


class PiClient:
    def __init__(self, host: str, port: int = DEFAULT_PORT, timeout: float = DEFAULT_TIMEOUT_SECONDS):
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
        self.timeout = timeout
        self._session = requests.Session()

    def _request(self, method: str, path: str, json_body: dict = None, headers: dict = None) -> dict:
        try:
            resp = self._session.request(
                method, self.base_url + path,
                json=json_body, headers=headers, timeout=self.timeout,
            )
        except requests.exceptions.RequestException as e:
            return {"ok": False, "error": f"{type(e).__name__}: {e}"}

        try:
            return resp.json()
        except ValueError:
            return {"ok": False, "error": f"non-JSON response (status {resp.status_code})"}

    def health(self) -> dict:
        return self._request("GET", "/health")

    def list_robots(self) -> dict:
        return self._request("GET", "/robots")

    def drive(self, robot_id: str, speed: int, heading: int, duration_ms: int) -> dict:
        return self._request("POST", f"/robots/{robot_id}/drive",
                              {"speed": speed, "heading": heading, "duration_ms": duration_ms})

    def stop(self, robot_id: str) -> dict:
        return self._request("POST", f"/robots/{robot_id}/stop")

    def set_led(self, robot_id: str, r: int, g: int, b: int) -> dict:
        return self._request("POST", f"/robots/{robot_id}/led", {"r": r, "g": g, "b": b})

    def battery(self, robot_id: str) -> dict:
        return self._request("GET", f"/robots/{robot_id}/battery")
