"""Coordinator entry point — the registry + routing layer only.

Discovers robot->Pi assignments from pi_hosts.json by asking each Pi
directly, then lets you drive/stop/led a ball by id without knowing which
Pi it's actually on.

This does NOT yet run the algorithm "brain" (gui_driver.py's role) or
serve a websocket to the GUI — those are separate, bigger pieces. This is
just enough to prove routing works: look up the right Pi, send the
command, report the result.

Usage:
    uv run python coordinator/main.py                      # discover + report status
    uv run python coordinator/main.py drive SB-8262         # discover, then drive one ball
"""
import json
import sys
from pathlib import Path

from registry import RobotRegistry, RegistryConflictError

CONFIG_PATH = Path(__file__).with_name("pi_hosts.json")


def load_pi_hosts(path: Path = CONFIG_PATH) -> list[str]:
    with open(path) as f:
        config = json.load(f)
    return config["pi_hosts"]


def discover(pi_hosts: list[str]) -> RobotRegistry:
    registry = RobotRegistry(pi_hosts)
    print(f"Polling {len(pi_hosts)} Pi(s): {pi_hosts}")
    try:
        registry.refresh()
    except RegistryConflictError as e:
        print(f"CONFIG ERROR: {e}")
        sys.exit(1)
    return registry


def main():
    registry = discover(load_pi_hosts())

    print("Pi reachable:", registry.pi_status())
    print("Robot -> Pi assignments discovered:", registry.all_robots())

    if len(sys.argv) < 2:
        return

    command = sys.argv[1]

    if command == "drive":
        robot_id = sys.argv[2]
        try:
            client = registry.client_for(robot_id)
        except KeyError:
            print(f"No Pi currently claims {robot_id} — check it's connected on its Pi "
                  f"(controls/pi_agent_config.json there) and that Pi is reachable.")
            sys.exit(1)
        result = client.drive(robot_id, speed=60, heading=0, duration_ms=1000)
        print(f"drive({robot_id}) via {registry.pi_for(robot_id)}: {result}")

    elif command == "stop":
        robot_id = sys.argv[2]
        client = registry.client_for(robot_id)
        print(client.stop(robot_id))

    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
