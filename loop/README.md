# RFC phase loop

Drives implementation of a `controls/rfcs/<slug>.md` RFC one phase at a time:
for each `## Phase N: Title` heading, spawns a `controls-phase-worker`
subagent to implement it, then a `controls-phase-reviewer` subagent to check
it. Retries a failed phase (worker gets the reviewer's findings) up to
`LOOP_MAX_RETRIES` (default 3) times, then stops for manual intervention.
**Never commits on your behalf** — review `git diff` and commit yourself once
a run finishes.

## Requirements

- `claude` CLI on `PATH`
- `jq`
- bash (works with macOS's default bash 3.2 — no `mapfile`/associative arrays used)

## Usage

Normally you don't call `_engine.sh` directly — the `controls-rfc` skill
writes an RFC and then runs `loop/new-project.sh <slug>` for you, which
creates an executable launcher:

```
./loop/<slug>              # run/resume
./loop/<slug> --reset      # clear progress and start over from phase 1
```

If you already have an RFC but no launcher (e.g. you wrote it by hand):

```
loop/new-project.sh <slug>
```

## What "autonomous" means here

Each phase step runs two headless `claude -p` invocations:

- **Worker** — `--agent controls-phase-worker --permission-mode acceptEdits
  --allowedTools "Read Edit Write Grep Glob Bash(git*) Bash(python*)
  Bash(python3*) Bash(uv*) Bash(pytest*)"`. It can edit files and run
  git/python/uv/pytest commands with no approval prompt (headless mode has no
  terminal to prompt from — this is what makes an unattended loop possible
  at all), but it cannot run arbitrary shell commands outside that allowlist.
- **Reviewer** — same allowlist minus `Edit`/`Write` (read-only + test
  execution), forced into a strict `{"verdict": "pass"|"fail", ...}` JSON
  response via `--json-schema`, checked only *after* the worker's turn
  finishes — it does not gate actions while the worker runs.

If you need the worker to use something outside that allowlist, add it
explicitly to `WORKER_TOOLS`/`REVIEWER_TOOLS` in `_engine.sh`. Don't reach for
`--dangerously-skip-permissions` — that removes all gating, not just widens
the allowlist.

## State and logs

- `loop/.state/<slug>.json` — which phases have passed (makes reruns
  resumable; delete or use `--reset` to start over)
- `loop/.logs/<slug>/phase-N-{worker,review}-ATTEMPT.json` — full transcript
  of every attempt, for when a phase fails and you want to see why

Both are gitignored — they're local run state, not part of the RFC.

## Model / cost policy

Worker and reviewer both default to Haiku (`claude-haiku-4-5-20251001`) —
grunt work that executes an already-written spec, not open-ended judgment.
The RFC itself (built interactively via the `controls-rfc` skill, in your
normal Sonnet/Opus session) is where the actual thinking happens; the loop
just executes and checks it cheaply.

Override per run without editing any file:

```
LOOP_WORKER_MODEL=claude-sonnet-5 ./loop/<slug>     # smarter implementation
LOOP_REVIEWER_MODEL=claude-sonnet-5 ./loop/<slug>   # smarter review gate
```

Bump `LOOP_REVIEWER_MODEL` at minimum for any phase touching threading,
`run_server_lock`/`KILL_FLAG`, or the `Instruction` protocol — Haiku follows
the `controls:controls-conventions` checklist mechanically but is more
likely to miss a subtle invariant violation than to flag one it wasn't told
to look for.

Each `claude -p` call still pays a real (if much smaller, on Haiku) API cost
— context caching means the first call in a fresh cache is the priciest.
A 5-phase RFC with no retries is ~10 invocations. Not free — factor that in
before kicking off a big RFC unattended.

## Reality check this loop cannot replace

Nothing here can exercise real Bluetooth hardware. Both subagents load the
`controls:controls-conventions` skill, which tells them to flag
BLE/hardware-dependent behavior as "needs manual verification" rather than
claim it works. Always do a real run against physical Spheros before trusting
a phase that touches connect/roll/turn behavior.
