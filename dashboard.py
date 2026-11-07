"""Open the swarm dashboard from any computer on the lab Wi-Fi.

The coordinator runs on the mini-PC (it starts at boot) and the Pis run their nodes
(they start at boot), so this only has to connect you to it:

    python3 dashboard.py          # Mac / Linux
    py dashboard.py               # Windows

It opens an SSH tunnel to the mini-PC (asks for the mini-PC's Windows password), checks
the coordinator and the Pis, and opens the dashboard in your browser. Ctrl+C closes it.

Standard library only, so it needs nothing installed beyond Python 3.8+ and the `ssh`
command (built into macOS, Linux and Windows 10+). Mini-PC address and login live in
coordinator/minipc.json; override with --host / --user.
"""
import argparse
import json
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parent / "coordinator" / "minipc.json"
SSH_PORT = 22
REACH_TIMEOUT_SECONDS = 3
STARTUP_TIMEOUT_SECONDS = 90


def load_config(args: argparse.Namespace) -> dict:
    config = json.loads(CONFIG_PATH.read_text()) if CONFIG_PATH.is_file() else {}
    host = args.host or config.get("host")
    user = args.user or config.get("user")
    if not host or not user:
        sys.exit(f"Set the mini-PC's \"host\" and \"user\" in {CONFIG_PATH}, or pass --host and --user.")
    return {"host": host, "user": user, "port": int(config.get("dashboard_port", 8000))}


def can_connect(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=REACH_TIMEOUT_SECONDS):
            return True
    except OSError:
        return False


def get(url: str, timeout: float) -> bytes:
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return resp.read()


def preflight(cfg: dict) -> None:
    if not shutil.which("ssh"):
        sys.exit("The `ssh` command isn't available. On Windows: Settings > System > Optional features > "
                 "OpenSSH Client.")
    if can_connect("127.0.0.1", cfg["port"]):
        sys.exit(f"Something on this computer already uses port {cfg['port']} (another dashboard window?). "
                 "Close it and try again.")
    print(f"Checking the mini-PC at {cfg['host']} ...")
    if not can_connect(cfg["host"], SSH_PORT):
        sys.exit(f"Can't reach the mini-PC at {cfg['host']}.\n"
                 "  - Is this computer on the lab Wi-Fi (192.168.11.x), not campus Wi-Fi?\n"
                 "  - Is the mini-PC powered on? Give it ~2 minutes after boot.\n"
                 f"  - If its IP changed, update \"host\" in {CONFIG_PATH} (or pass --host).")


def open_tunnel(cfg: dict) -> subprocess.Popen:
    """ssh runs in the foreground of this terminal so it can ask for the password itself.
    127.0.0.1 on the far side, not localhost: Windows resolves localhost to IPv6 first and
    the coordinator only listens on IPv4."""
    print(f"Connecting as \"{cfg['user']}\" - enter the mini-PC's Windows password when asked.")
    return subprocess.Popen([
        "ssh", "-N",
        "-o", "ExitOnForwardFailure=yes",
        "-o", "ServerAliveInterval=15",
        "-L", f"{cfg['port']}:127.0.0.1:{cfg['port']}",
        "-l", cfg["user"], cfg["host"],
    ])


def wait_for_dashboard(tunnel: subprocess.Popen, base: str) -> None:
    deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if tunnel.poll() is not None:
            sys.exit("The SSH connection closed (wrong password, or SSH is off on the mini-PC).")
        try:
            get(f"{base}/favicon.ico", timeout=2)
            return
        except OSError:
            time.sleep(1)
    tunnel.terminate()
    sys.exit("Connected to the mini-PC, but the coordinator didn't answer. On the mini-PC, check the "
             "SpheroCoordinator task (schtasks /query /tn SpheroCoordinator) and coordinator\\coordinator.log.")


def print_pis(base: str) -> None:
    try:
        pis = json.loads(get(f"{base}/api/pis?refresh=1", timeout=30))["data"]["pis"]
    except (OSError, ValueError, KeyError):
        print("Couldn't read the Pi list yet; the dashboard will show it.")
        return
    for pi in pis:
        state = f"online  {pi['ip']}  ({pi.get('hostname') or '?'})" if pi["online"] else "offline"
        print(f"  Pi {pi['number']}: {state}")
    online = sum(1 for pi in pis if pi["online"])
    print(f"{online} of {len(pis)} Pis online - all online Pis are selected; untick any you don't want.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Open the swarm dashboard running on the mini-PC")
    parser.add_argument("--host", help="mini-PC IP address (default: coordinator/minipc.json)")
    parser.add_argument("--user", help="mini-PC Windows username (default: coordinator/minipc.json)")
    parser.add_argument("--no-browser", action="store_true", help="don't open the browser")
    args = parser.parse_args()
    cfg = load_config(args)
    preflight(cfg)
    tunnel = open_tunnel(cfg)
    base = f"http://localhost:{cfg['port']}"
    try:
        wait_for_dashboard(tunnel, base)
        print("Coordinator is up. Looking for Pis ...")
        print_pis(base)
        if not args.no_browser:
            webbrowser.open(f"{base}/")
        print(f"\nDashboard: {base}  (running on the mini-PC). Leave this window open; Ctrl+C to close.")
        tunnel.wait()
        print("The SSH connection dropped.")
    except KeyboardInterrupt:
        print("\nClosing.")
    finally:
        if tunnel.poll() is None:
            tunnel.terminate()


if __name__ == "__main__":
    main()
