#!/usr/bin/env bash
# Scaffolds an executable ./loop/<slug> launcher for an existing RFC at
# controls/rfcs/<slug>.md. The controls-rfc skill calls this automatically
# when it finishes writing a new RFC; run it by hand if you wrote/updated an
# RFC without going through that skill.
set -euo pipefail

SLUG="${1:-}"
if [ -z "$SLUG" ]; then
  echo "Usage: loop/new-project.sh <slug>" >&2
  exit 1
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RFC="$REPO_ROOT/controls/rfcs/$SLUG.md"
LAUNCHER="$REPO_ROOT/loop/$SLUG"

if [ ! -f "$RFC" ]; then
  echo "No RFC found at controls/rfcs/$SLUG.md — write one first (see the controls-rfc skill)." >&2
  exit 1
fi

cat > "$LAUNCHER" <<EOF
#!/usr/bin/env bash
# Auto-generated launcher for the "$SLUG" RFC.
# Do not edit by hand — rerun 'loop/new-project.sh $SLUG' to regenerate.
exec "\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)/_engine.sh" "$SLUG" "\$@"
EOF
chmod +x "$LAUNCHER"

echo "Created $LAUNCHER"
echo "Run it with: ./loop/$SLUG"
echo "Restart a phase loop from scratch with: ./loop/$SLUG --reset"
