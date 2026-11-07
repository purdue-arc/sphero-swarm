"""Discovers which Pi currently owns which Sphero.

Deliberately does NOT keep its own static robot->Pi mapping. Each Pi
already knows which balls it owns (controls/pi_agent_config.json on that
Pi) — keeping a second copy of that here would just be two sources of
truth that can drift out of sync. Instead this asks every known Pi
directly (GET /robots) and rebuilds the mapping from what they report.

The only thing this needs to be told is the small, stable list of which
Pis exist — not which balls each one has, which changes more often and is
each Pi's own business.
"""
import time

from pi_client import PiClient, DEFAULT_PORT


class RegistryConflictError(Exception):
    """Two Pis both claim the same robot_id — a configuration mistake.
    Must surface loudly; resolving it silently by picking one would hide
    a real problem (e.g. the same ball physically in range of two Pis,
    or a copy-paste error in two pi_agent_config.json files)."""


class RobotRegistry:
    def __init__(self, pi_hosts: list[str], default_port: int = DEFAULT_PORT):
        """pi_hosts entries are either a bare hostname ("sphero-pi-01.local",
        uses default_port) or "host:port" (useful for local testing with
        multiple agents on one machine, or a non-default port)."""
        self._clients: dict[str, PiClient] = {}
        for entry in pi_hosts:
            if ":" in entry:
                host, port_str = entry.rsplit(":", 1)
                port = int(port_str)
            else:
                host, port = entry, default_port
            self._clients[entry] = PiClient(host, port)

        self._robot_to_pi: dict[str, str] = {}
        self._pi_reachable: dict[str, bool] = {entry: False for entry in pi_hosts}
        self._last_refresh = 0.0

    def refresh(self) -> None:
        """Ask every known Pi what it currently owns and rebuild the
        mapping from scratch. Rebuilding (not merging) matters: a ball
        that stops being reported by its Pi should disappear from the
        registry, not linger as a stale entry."""
        new_mapping: dict[str, str] = {}
        for pi_entry, client in self._clients.items():
            result = client.list_robots()
            self._pi_reachable[pi_entry] = bool(result.get("ok"))
            if not result.get("ok"):
                continue
            for robot in result["data"]["robots"]:
                if not robot["connected"]:
                    continue
                robot_id = robot["robot_id"]
                if robot_id in new_mapping and new_mapping[robot_id] != pi_entry:
                    raise RegistryConflictError(
                        f"{robot_id} is claimed by both {new_mapping[robot_id]} and {pi_entry}"
                    )
                new_mapping[robot_id] = pi_entry
        self._robot_to_pi = new_mapping
        self._last_refresh = time.time()

    def pi_for(self, robot_id: str) -> str:
        """Raises KeyError if no Pi currently claims this robot_id —
        correct behavior, not a bug to swallow: a command for a ball
        nobody owns should fail loudly."""
        return self._robot_to_pi[robot_id]

    def client_for(self, robot_id: str) -> PiClient:
        return self._clients[self.pi_for(robot_id)]

    def all_robots(self) -> dict:
        return dict(self._robot_to_pi)

    def pi_status(self) -> dict:
        return dict(self._pi_reachable)

    def last_refresh(self) -> float:
        return self._last_refresh
