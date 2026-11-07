#!/usr/bin/env bash
# Installs controls/pi_node.py as the sphero-node systemd service on a Raspberry Pi.
# Run as the normal user (not root); the privileged steps call sudo.
#
#   bash scripts/install_pi_node.sh            # first Pi: generates a token
#   bash scripts/install_pi_node.sh <token>    # other Pis: reuse that token
#
# Every Pi must share one token, because coordinator/pis.json holds a single
# token that the dashboard sends to all of them.
set -euo pipefail
SHARED_TOKEN="${1:-}"
if [ -n "$SHARED_TOKEN" ] && ! [[ "$SHARED_TOKEN" =~ ^[A-Za-z0-9_-]+$ ]]; then
    echo "Token may only contain letters, digits, '-' and '_'." >&2
    exit 1
fi

if [ "$(id -u)" -eq 0 ] && [ -z "${SUDO_USER:-}" ]; then
    echo "Run this as the normal user, not as root." >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TARGET_USER="${SUDO_USER:-$(id -un)}"
TARGET_HOME="$(getent passwd "$TARGET_USER" | cut -d: -f6)"
TEMPLATE="$REPO_ROOT/controls/pi_node.service"
UNIT_PATH="/etc/systemd/system/sphero-node.service"
SUDOERS_PATH="/etc/sudoers.d/sphero-node"
CONFIG_DIR="$TARGET_HOME/.config"
CONFIG_PATH="$CONFIG_DIR/sphero-node.json"

if command -v uv >/dev/null 2>&1; then
    UV_BIN="$(command -v uv)"
elif [ -x "$HOME/.local/bin/uv" ]; then
    UV_BIN="$HOME/.local/bin/uv"
else
    echo "uv not found. Install it first: curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
    exit 1
fi

# Run a command as the target user (directly if we already are that user).
as_target() {
    if [ "$(id -un)" = "$TARGET_USER" ]; then
        "$@"
    else
        sudo -u "$TARGET_USER" "$@"
    fi
}

echo "Repo: $REPO_ROOT"
echo "User: $TARGET_USER"
echo "uv:   $UV_BIN"

# Install only what the node needs into the repo's .venv. A full `uv sync` would
# pull the camera/ML stack (depthai, ultralytics, ...), which the Pi doesn't use
# and may not build on arm64. The service runs .venv/bin/python directly.
if [ ! -d "$REPO_ROOT/.venv" ]; then
    (cd "$REPO_ROOT" && "$UV_BIN" venv)
fi
(cd "$REPO_ROOT" && "$UV_BIN" pip install flask spherov2 bleak)
if ! "$REPO_ROOT/.venv/bin/python" -c "import flask, spherov2, bleak"; then
    echo "The node's dependencies don't import from $REPO_ROOT/.venv; fix that and re-run." >&2
    exit 1
fi

# The node and the old controls/pi_agent.py both use port 5000. If pi_agent.py (or
# anything else) is still running, the service would crash-loop on "address in use".
sudo systemctl stop sphero-node 2>/dev/null || true
if ss -ltn 'sport = :5000' | grep -q LISTEN; then
    echo "Something is already listening on port 5000 - probably controls/pi_agent.py." >&2
    echo "Stop it first (e.g. pkill -f pi_agent.py), then re-run this script." >&2
    exit 1
fi

echo "Writing $UNIT_PATH"
sed -e "s|__USER__|$TARGET_USER|g" -e "s|__REPO__|$REPO_ROOT|g" -e "s|__UV__|$UV_BIN|g" "$TEMPLATE" \
    | sudo tee "$UNIT_PATH" >/dev/null

echo "Writing $SUDOERS_PATH"
SUDOERS_TMP="$(mktemp)"
cat > "$SUDOERS_TMP" <<EOF
$TARGET_USER ALL=(root) NOPASSWD: /sbin/shutdown, /usr/sbin/shutdown
EOF
sudo visudo -cf "$SUDOERS_TMP"
sudo install -m 440 "$SUDOERS_TMP" "$SUDOERS_PATH"
rm -f "$SUDOERS_TMP"

# Operator override for the node config (merged over controls/pi_node_config.json).
# Holds the token that coordinator/pis.json must match. Created once; afterwards only
# the "token" key changes, and only when a token is passed in (other keys are kept).
if [ -f "$CONFIG_PATH" ] && [ -z "$SHARED_TOKEN" ]; then
    echo "Keeping existing $CONFIG_PATH"
else
    if [ -n "$SHARED_TOKEN" ]; then
        echo "Setting the token in $CONFIG_PATH to the one you passed in"
        NEW_TOKEN="$SHARED_TOKEN"
    else
        echo "Creating $CONFIG_PATH with a new random token"
        NEW_TOKEN="$(python3 -c 'import secrets;print(secrets.token_hex(16))')"
    fi
    as_target mkdir -p "$CONFIG_DIR"
    # umask 077 so the token is never readable by others, even for a moment.
    as_target sh -c 'umask 077; python3 - "$1" "$2"' _ "$CONFIG_PATH" "$NEW_TOKEN" <<'PY'
import json, os, sys
path, token = sys.argv[1], sys.argv[2]
config = {}
if os.path.exists(path):
    with open(path) as f:
        config = json.load(f)
config["token"] = token
# Lock the mode down before writing, in case the file was hand-made with 0644.
fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
os.fchmod(fd, 0o600)
with os.fdopen(fd, "w") as f:
    json.dump(config, f, indent=2)
    f.write("\n")
PY
fi
TOKEN="$(as_target python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("token", ""))' "$CONFIG_PATH")"

if ! getent group bluetooth >/dev/null; then
    echo "Group 'bluetooth' does not exist. Install bluez first." >&2
    exit 1
fi
sudo usermod -aG bluetooth "$TARGET_USER"

sudo systemctl daemon-reload
# restart, not `enable --now`: on a re-install the node is already running and
# --now would leave the old code and old token in place.
sudo systemctl enable sphero-node
sudo systemctl restart sphero-node

echo
echo "Waiting for the node to answer on port 5000..."
HEALTHY=""
for _ in $(seq 1 20); do
    if curl -fsS http://localhost:5000/health >/dev/null 2>&1; then
        HEALTHY="yes"
        break
    fi
    sleep 1
done
if [ -n "$HEALTHY" ]; then
    echo "OK: sphero-node is running and answering /health. It will start on every boot."
else
    echo "WARNING: sphero-node did not answer within 20 s. Recent log:" >&2
    sudo journalctl -u sphero-node -n 30 --no-pager >&2 || true
fi

echo
echo "Network interfaces (MAC addresses):"
for f in /sys/class/net/*/address; do
    echo "  $(basename "$(dirname "$f")"): $(cat "$f")"
done
echo
echo "Logs: journalctl -u sphero-node -f"
echo
if [ -n "$TOKEN" ]; then
    echo "Node token (from $CONFIG_PATH):"
    echo "  $TOKEN"
    echo "Copy this into the \"token\" field of coordinator/pis.json on the mini-PC,"
    echo "and install the other Pis with: bash scripts/install_pi_node.sh $TOKEN"
else
    echo "WARNING: $CONFIG_PATH has no \"token\"; the node falls back to the default. Add one and restart." >&2
fi
