#!/usr/bin/env bash
# Opens the mini-PC's dashboard on this Mac. Everything runs on the mini-PC; the Mac
# only shows the page, through an SSH tunnel (the dashboard only accepts local
# connections, and the tunnel makes the Mac count as local). It forwards to 127.0.0.1,
# not localhost, because Windows resolves localhost to IPv6 first and the server is IPv4-only.
#
#   bash scripts/open_dashboard.sh <windows-user>@<mini-pc-ip>
#
# Leave the window open while you use the dashboard; Ctrl+C closes the tunnel.
set -euo pipefail

TARGET="${1:?usage: bash scripts/open_dashboard.sh <windows-user>@<mini-pc-ip>}"
PORT=8000
URL="http://localhost:$PORT"

if curl -fsS "$URL/favicon.ico" >/dev/null 2>&1; then
    echo "Something on this Mac already answers on port $PORT (a local dashboard?). Stop it first." >&2
    exit 1
fi

# -f asks for the password in the foreground, then moves the tunnel to the background.
ssh -f -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=15 -L "$PORT:127.0.0.1:$PORT" "$TARGET"
SSH_PID="$(pgrep -f -- "-L $PORT:127.0.0.1:$PORT $TARGET" | head -n 1)"
trap '[ -n "$SSH_PID" ] && kill "$SSH_PID" 2>/dev/null; echo; echo "Tunnel closed."' EXIT

for _ in $(seq 1 20); do
    if curl -fsS "$URL/favicon.ico" >/dev/null 2>&1; then
        open "$URL/"
        echo "Dashboard open at $URL (running on the mini-PC). Ctrl+C here closes it."
        while kill -0 "$SSH_PID" 2>/dev/null; do sleep 2; done
        echo "The SSH connection dropped." >&2
        exit 1
    fi
    sleep 1
done
echo "Connected, but the dashboard didn't answer. Is the SpheroCoordinator task running on the mini-PC?" >&2
exit 1
