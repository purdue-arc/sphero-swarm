#!/usr/bin/env bash
# Core RFC phase-loop engine. Not meant to be run directly — invoked via a
# generated ./loop/<slug> launcher (see loop/new-project.sh), which is what
# the controls-rfc skill creates once it finishes writing an RFC.
#
# For each "## Phase N: Title" heading in controls/rfcs/<slug>.md, spawns a
# controls-phase-worker subagent to implement it, then a
# controls-phase-reviewer subagent to check it, retrying on failure up to
# LOOP_MAX_RETRIES times before stopping for manual intervention. Never
# commits on its own. Resumable: completed phases are skipped on a re-run
# unless --reset is passed.
set -euo pipefail

SLUG="${1:-}"
if [ -z "$SLUG" ]; then
  echo "Usage: loop/_engine.sh <slug> [--reset]" >&2
  exit 1
fi
shift || true

RESET=false
for arg in "$@"; do
  case "$arg" in
    --reset) RESET=true ;;
    *) echo "Unknown option: $arg" >&2; exit 1 ;;
  esac
done

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RFC="$REPO_ROOT/controls/rfcs/$SLUG.md"
STATE_DIR="$REPO_ROOT/loop/.state"
LOG_DIR="$REPO_ROOT/loop/.logs/$SLUG"
STATE_FILE="$STATE_DIR/$SLUG.json"
PHASE_LINES_FILE="$LOG_DIR/.phase_lines"

command -v claude >/dev/null 2>&1 || { echo "claude CLI not found on PATH" >&2; exit 1; }
command -v jq >/dev/null 2>&1 || { echo "jq is required (brew install jq)" >&2; exit 1; }
[ -f "$RFC" ] || { echo "RFC not found: $RFC (write one with the controls-rfc skill first)" >&2; exit 1; }

mkdir -p "$STATE_DIR" "$LOG_DIR"

if [ "$RESET" = true ] || [ ! -f "$STATE_FILE" ]; then
  echo '{"completed_phases": []}' > "$STATE_FILE"
fi

MAX_RETRIES="${LOOP_MAX_RETRIES:-3}"
# Cost policy: grunt work (implementing a spec someone already wrote) runs on
# the cheapest model. Bump LOOP_REVIEWER_MODEL for phases where a missed bug
# would reach real hardware — see .claude/agents/controls-phase-reviewer.md.
WORKER_MODEL="${LOOP_WORKER_MODEL:-claude-haiku-4-5-20251001}"
REVIEWER_MODEL="${LOOP_REVIEWER_MODEL:-claude-haiku-4-5-20251001}"
WORKER_TOOLS="Read Edit Write Grep Glob Bash(git*) Bash(python*) Bash(python3*) Bash(uv*) Bash(pytest*)"
REVIEWER_TOOLS="Read Grep Glob Bash(git*) Bash(python*) Bash(python3*) Bash(uv*) Bash(pytest*)"
VERDICT_SCHEMA='{"type":"object","properties":{"verdict":{"type":"string","enum":["pass","fail"]},"summary":{"type":"string"},"findings":{"type":"array","items":{"type":"string"}}},"required":["verdict","summary"]}'

grep -n '^## Phase [0-9]\{1,\}:' "$RFC" > "$PHASE_LINES_FILE" || true
TOTAL=$(wc -l < "$PHASE_LINES_FILE" | tr -d ' ')
RFC_LAST_LINE=$(wc -l < "$RFC" | tr -d ' ')

if [ "$TOTAL" -eq 0 ]; then
  echo "No '## Phase N: Title' headings found in $RFC — nothing to run." >&2
  exit 1
fi

echo "RFC: $RFC  ($TOTAL phase(s))"

PHASE_NUM=0
while IFS=: read -r START_LN REST <&3; do
  PHASE_NUM=$((PHASE_NUM + 1))
  TITLE=$(printf '%s' "$REST" | sed -E 's/^## Phase [0-9]+: //')

  ALREADY_DONE=$(jq -r --argjson n "$PHASE_NUM" '(.completed_phases | index($n)) != null' "$STATE_FILE")
  if [ "$ALREADY_DONE" = "true" ]; then
    echo "==> Phase $PHASE_NUM/$TOTAL ($TITLE): already completed, skipping"
    continue
  fi

  NEXT_LINE=$(sed -n "$((PHASE_NUM + 1))p" "$PHASE_LINES_FILE")
  if [ -n "$NEXT_LINE" ]; then
    NEXT_START_LN="${NEXT_LINE%%:*}"
    END_LN=$((NEXT_START_LN - 1))
  else
    END_LN="$RFC_LAST_LINE"
  fi
  PHASE_BODY=$(sed -n "${START_LN},${END_LN}p" "$RFC")

  echo ""
  echo "============================================================"
  echo " Phase $PHASE_NUM/$TOTAL: $TITLE"
  echo "============================================================"

  FEEDBACK=""
  ATTEMPT=1
  PASSED=false

  while [ "$ATTEMPT" -le "$MAX_RETRIES" ]; do
    echo "-- worker attempt $ATTEMPT/$MAX_RETRIES --"

    WORKER_PROMPT="Implement Phase $PHASE_NUM of the RFC at controls/rfcs/$SLUG.md (\"$TITLE\") — nothing more, nothing less.

Phase text:
---
$PHASE_BODY
---
"
    if [ -n "$FEEDBACK" ]; then
      WORKER_PROMPT="$WORKER_PROMPT
The previous attempt was reviewed and FAILED with this feedback — fix exactly these issues, do not introduce unrelated changes:
$FEEDBACK
"
    fi
    WORKER_PROMPT="$WORKER_PROMPT
Follow the controls:controls-conventions skill. Do not commit. Do not touch controls/Old_code/. Summarize what changed and which files you touched."

    WORKER_OUT="$LOG_DIR/phase-$PHASE_NUM-worker-$ATTEMPT.json"
    if ! claude -p "$WORKER_PROMPT" \
        --agent controls-phase-worker \
        --model "$WORKER_MODEL" \
        --permission-mode acceptEdits \
        --allowedTools $WORKER_TOOLS \
        --output-format json \
        > "$WORKER_OUT" 2> "$LOG_DIR/phase-$PHASE_NUM-worker-$ATTEMPT.stderr"; then
      echo "Worker invocation failed (nonzero exit) — see $LOG_DIR/phase-$PHASE_NUM-worker-$ATTEMPT.stderr" >&2
      exit 1
    fi

    WORKER_IS_ERROR=$(jq -r '.is_error // true' "$WORKER_OUT" 2>/dev/null || echo true)
    if [ "$WORKER_IS_ERROR" = "true" ]; then
      echo "Worker session errored — see $WORKER_OUT" >&2
      exit 1
    fi

    echo "-- reviewer attempt $ATTEMPT/$MAX_RETRIES --"

    REVIEWER_PROMPT="Review the current uncommitted changes against Phase $PHASE_NUM of controls/rfcs/$SLUG.md (\"$TITLE\").

Phase text (Definition of Done / Verification):
---
$PHASE_BODY
---

Run 'git diff' and 'git status' yourself to see what actually changed. Follow the controls:controls-conventions skill. Verify: (1) it matches the Definition of Done, (2) it doesn't violate run_server_lock/KILL_FLAG/threading/Instruction-protocol conventions, (3) available tests or import/py_compile checks actually pass, (4) hardware-dependent behavior is explicitly flagged rather than assumed correct. Give a strict pass/fail verdict with specific findings."

    REVIEWER_OUT="$LOG_DIR/phase-$PHASE_NUM-review-$ATTEMPT.json"
    if ! claude -p "$REVIEWER_PROMPT" \
        --agent controls-phase-reviewer \
        --model "$REVIEWER_MODEL" \
        --permission-mode acceptEdits \
        --allowedTools $REVIEWER_TOOLS \
        --output-format json \
        --json-schema "$VERDICT_SCHEMA" \
        > "$REVIEWER_OUT" 2> "$LOG_DIR/phase-$PHASE_NUM-review-$ATTEMPT.stderr"; then
      echo "Reviewer invocation failed (nonzero exit) — see $LOG_DIR/phase-$PHASE_NUM-review-$ATTEMPT.stderr" >&2
      exit 1
    fi

    REVIEWER_IS_ERROR=$(jq -r '.is_error // true' "$REVIEWER_OUT" 2>/dev/null || echo true)
    if [ "$REVIEWER_IS_ERROR" = "true" ]; then
      echo "Reviewer session errored — see $REVIEWER_OUT" >&2
      exit 1
    fi

    VERDICT=$(jq -r '.structured_output.verdict // empty' "$REVIEWER_OUT")
    SUMMARY=$(jq -r '.structured_output.summary // empty' "$REVIEWER_OUT")

    if [ "$VERDICT" = "pass" ]; then
      echo "PASS: $SUMMARY"
      PASSED=true
      break
    fi

    echo "FAIL (attempt $ATTEMPT): $SUMMARY"
    FEEDBACK=$(jq -r '(.structured_output.findings // []) | map("- " + .) | join("\n")' "$REVIEWER_OUT")
    ATTEMPT=$((ATTEMPT + 1))
  done

  if [ "$PASSED" != "true" ]; then
    echo ""
    echo "Phase $PHASE_NUM failed review after $MAX_RETRIES attempt(s). Stopping for manual intervention."
    echo "Logs: $LOG_DIR/phase-$PHASE_NUM-*"
    exit 1
  fi

  jq --argjson n "$PHASE_NUM" '.completed_phases += [$n]' "$STATE_FILE" > "$STATE_FILE.tmp"
  mv "$STATE_FILE.tmp" "$STATE_FILE"
done 3< "$PHASE_LINES_FILE"

echo ""
echo "All $TOTAL phase(s) of '$SLUG' passed review."
echo "Nothing was committed. Review and commit yourself:"
echo "  git status"
echo "  git diff"
