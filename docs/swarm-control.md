# Swarm control: Pi nodes + mini-PC dashboard

How the lab runs a multi-Pi Sphero session from one browser tab on the mini-PC.

```
 browser (mini-PC)                 mini-PC                         each Raspberry Pi
 dashboard.html  ── HTTP ──▶  coordinator/server.py  ── HTTP ──▶  controls/pi_node.py ── BLE ──▶ Spheros
                              coordinator/controls_bridge.py ◀── TCP (controls/protocol.py) ── gui_driver.py (future)
```

## Operator workflow

1. Plug in the Pis. `pi_node.py` starts at boot (systemd), idle, connected to nothing.
2. On the mini-PC double-click `start_dashboard.bat` → opens `http://localhost:8000`.
3. **Pis** — cards for Pi 1–4 go green as they're found. Tick the ones to use.
4. **Scan** — every selected Pi listens for Spheros over BLE (no connecting) and reports signal strength.
5. **Assign** — auto (even split, best signal) / shuffle (random even split) / drag-and-drop / per-card dropdown / "use last layout".
6. **Connect** — each Pi connects its balls one at a time. A ball that fails is marked red and skipped.
7. **Run** — live board + manual controls + routines (square, circle) with a placement guide.
8. **Disconnect all** — stop, LED off, close each BLE link cleanly. Optional **Shut down Pis**.

## One-time Pi setup

```
ssh sphero@<pi-ip>
cd ~/sphero-swarm && git pull
bash scripts/install_pi_node.sh            # first Pi: generates a token and prints it
bash scripts/install_pi_node.sh <token>    # every other Pi: reuse that same token
cat /sys/class/net/wlan0/address           # put this MAC in coordinator/pis.json
```

The install script writes `/etc/systemd/system/sphero-node.service` (`Restart=always`,
starts after bluetooth + network) and a sudoers rule so the node can run `shutdown`
without a password. It installs only flask/spherov2/bleak into the repo's `.venv` (the
service runs `uv run --no-sync`, so the camera/ML stack is never pulled onto the Pi).
The token lives in `~/.config/sphero-node.json` (outside the repo, so `/system/update`
can't stash it away). All Pis must share one token because `coordinator/pis.json` holds
a single `"token"` — copy it there. Re-running the script is safe and restarts the node
with the current code. After that the Pi never needs SSH or HDMI:
plugging it in starts the node; the dashboard's restart/update buttons exit the process
and systemd starts it again.

Logs: `journalctl -u sphero-node -f`. Stop: `sudo systemctl stop sphero-node` (graceful).

---

## Contract 1 — Pi node HTTP API (`controls/pi_node.py`, port 5000)

Every response: `{"ok": true, "data": ...}` or `{"ok": false, "error": "..."}`. CORS open
(same headers + OPTIONS preflight as `pi_agent.py`). `*` = requires header `X-Agent-Token`.

| Method | Path | Body | Data returned |
|---|---|---|---|
| GET | `/health` | | `{status:"alive", hostname, macs:{iface: "aa:bb:.."}, version:{branch, commit}, state:"idle"\|"scanning"\|"connecting"\|"ready", connected_count}` |
| POST | `/scan` | `{seconds?: 8}` | `{robots:[{robot_id:"SB-8262", address, rssi:-61}]}` sorted strongest first. 409 if connecting. |
| GET | `/robots` | | `{state, robots:[{robot_id, status, connected:bool, error, address}]}` |
| POST | `/robots/assign` | `{robots:["SB-1",...]}` | `{accepted:[...], released:[...]}` — makes this Pi's set **exactly** the list. Removed balls are released **synchronously** before the response (cancel, stop, close; a busy ball is cancelled within ~10 ms, a hung close costs up to `release_timeout_seconds` per ball), so `released` is accurate. New balls connect in a background thread; the response does not wait for connects, so poll `/robots`. |
| POST | `/robots/release` | `{robots?:[...]}` (omit = all) | `{released:[...], forced:[...]}` — cancels in-flight commands and drives on those balls, then graceful disconnect. Blocks until done, bounded by `release_timeout_seconds`. A connecting ball is marked released and not waited for. |
| POST | `/robots/stop-all` | | `{stopped:[...]}` — cancels running and queued commands, stop_roll every ball |
| POST | `/robots/<id>/command` | Instruction fields, see below | `{robot_id, outcome}` — blocks until the command finishes |
| POST | `/robots/<id>/drive` | `{speed, heading, duration_ms}` | as `pi_agent.py` |
| POST | `/robots/<id>/stop` | | as `pi_agent.py` |
| POST | `/robots/<id>/led` | `{r,g,b}` | as `pi_agent.py` |
| POST | `/robots/<id>/aim` | `{on: bool}` | on: back LED full; off: `reset_aim()` then back LED off |
| GET | `/robots/<id>/battery` | | `{robot_id, voltage}` |
| GET | `/system/version` | | `{branch, commit}` |
| POST | `/system/restart` * | | responds, then releases all balls and exits (systemd restarts it) |
| POST | `/system/update` * | `{branch?: "main"}` | git fetch / auto-stash / checkout / pull, then restart. If checkout or pull fails after the stash, `git stash pop` is attempted and the error says whether it worked |
| POST | `/system/shutdown` * | | releases all, then `sudo -n shutdown -h now` |

Robot `status` values: `queued`, `connecting`, `connected`, `failed`, `released`.
`connected` (bool) is kept so the old `controls/pi_agent_tester.html` still works against a node.

### `/command` body = `controls/Instruction.py` semantics, executed exactly like `Controls_Server.run_command`

```json
{"type": 0, "r": 255, "g": 0, "b": 0}       // LED
{"type": 1, "speed": 80, "duration": 1.5}    // roll at current heading; negative speed = backward; seconds
{"type": 2, "degrees": 90, "duration": 0.5}  // turn RELATIVE to current heading, ramped over duration
{"type": 3, "duration": 1.0}                 // wait
```

`duration` is capped at 60 s and `|degrees|` at 3600; larger values are HTTP 400.

`outcome` ∈ `complete` | `cancelled` (stop-all or a release of that ball hit it, including while it was queued behind another command) | `failed` | `disconnected` (ball not connected — HTTP 200, not 404, so batches keep going).

### Pi node behaviour

- Starts with **no** robots. Config is merged in order: built-in defaults, then `controls/pi_node_config.json`
  (`{"port":5000, "token":"change-me", "connect_timeout_seconds":30, "max_scan_attempts":20, "scan_seconds":8}`),
  then the optional operator override `~/.config/sphero-node.json` (the install script writes the token here).
  The node prints which files it read at startup. The override survives `/system/update` (the git auto-stash
  only touches the repo).
- Connect = same proven pattern as `pi_agent.py`: `scanner.find_toys(toy_names=...)` accumulated across
  attempts, then **sequential** `SpheroEduAPI(toy).__enter__()`. Each ball has a wall-clock budget of
  `connect_timeout_seconds`; `hw.connect` runs in a daemon thread, so a hung BLE connect cannot wedge the node.
  Timing out marks the ball `failed` with `connect timed out after Ns`. A connect that returns after its
  budget is closed by its own thread and never stored. A ball that isn't found or doesn't connect becomes
  `failed` with a reason; the rest continue. `/scan` is 409 only while the connect worker is running.
- Cancellation uses epochs, not flags. Stop-all bumps a node-wide stop epoch. Release bumps that ball's
  release epoch. A command or drive snapshots both on arrival, before it waits for the ball's lock, and ends
  `cancelled` if either moved. Nothing is cleared, so a command that arrives after stop-all runs normally.
- Graceful release per ball: cancel in-flight work and `hw.stop` (best effort, before waiting for the ball's lock),
  then `stop_roll()`, LED off, `__exit__(None, None, None)` in a worker thread with a 10 s limit. If the lock
  stays busy, or the close hangs or raises and the address is known, the node runs `bluetoothctl disconnect <address>`
  (counted in `forced`). SIGTERM / SIGINT / `/system/*` exits all run release-all first.
- Hardware access lives behind a small interface (`controls/sphero_hardware.py` real, `controls/sphero_fake.py`
  simulated) injected into `create_app(config, hardware)`. `python controls/pi_node.py --fake 6 --port 5001`
  runs a node with 6 simulated balls on a laptop — used by tests and for UI work without hardware.
- `pi_agent.py` is untouched; the node is a separate program.

## Contract 2 — coordinator HTTP API (`coordinator/server.py`, `localhost:8000`)

Same `{ok, data|error}` envelope. Browser only ever talks to this server.

Requests must come from the local dashboard: `Host` is `localhost:8000` or `127.0.0.1:8000` (else 403),
any `Origin` header must be `http://localhost:8000` or `http://127.0.0.1:8000` (else 403), and every
POST/PUT/PATCH/DELETE must send `Content-Type: application/json` (else 415). This blocks cross-site form
posts and DNS rebinding. The dashboard always sends JSON, with `{}` when there is no body.

| Method | Path | Body | Data |
|---|---|---|---|
| GET | `/` | | the dashboard |
| GET | `/api/pis` `?refresh=1` | | `{pis:[{number, mac, ip, online, hostname, state, version, connected_count, selected}]}` — refresh re-runs discovery |
| POST | `/api/pis/select` | `{numbers:[1,2]}` | same as GET |
| POST | `/api/scan` | `{seconds?: 8}` | `{robots:[{robot_id, rssi_by_pi:{"1":-60,"2":-75}, best_pi}], errors:{"2":"..."}}` |
| POST | `/api/assign/auto` | `{mode:"signal"\|"shuffle", robots?:[ids]}` | `{assignment:{"1":[ids], "2":[ids]}}` (from last scan if `robots` omitted) |
| GET | `/api/assignment/last` | | `{assignment}` or `{assignment: null}` |
| POST | `/api/connect` | `{assignment:{"1":[...],...}}` | `{per_pi:{"1":{ok, error?}}}` — releases moved balls on their old Pi first (the old Pi may be unselected, as long as it is online), then `/robots/assign` on every selected Pi; saves `coordinator/last_assignment.json` |
| GET | `/api/status` | | `{pis:{"1":{online, state, robots:[...]}}}` — dashboard polls ~1 s |
| POST | `/api/robots/<id>/<action>` | as Pi | routed to the owning Pi (`drive`, `stop`, `led`, `aim`, `battery`) |
| POST | `/api/all/<action>` | as Pi | fan-out to every connected ball, `{results:{id: response}}` |
| POST | `/api/stop-all` | | stop-all on every **online** Pi (selected or not) + cancel any running routine; waits up to 5 s for the routine thread to exit |
| POST | `/api/release` | | graceful release-all on every **online** Pi, `{per_pi:{...}}` |
| GET | `/api/routines` | | `{routines:[{key, name, description, setup_steps:[...], min_robots, max_robots, params:[{name, label, default, min, max}]}]}` |
| POST | `/api/routines/<key>/formation` | `{order:[ids], params?}` | `{slots:[{slot, robot_id, x_ft, y_ft, heading_deg, color:[r,g,b]}]}` |
| POST | `/api/routines/<key>/identify` | `{order:[ids]}` | lights each ball in its slot colour so you can match ball ↔ diagram |
| POST | `/api/aim` | `{on: bool}` | aim on/off for every connected ball |
| POST | `/api/routines/<key>/run` | `{order:[ids], params?}` | starts in background; 409 if one is running |
| GET | `/api/routines/progress` | | `{running, key, batch_index, batch_count, last_outcomes, error}` |
| POST | `/api/system/<restart\|update\|shutdown>` | `{branch?}` | forwarded with the token to every selected Pi |

`coordinator/pis.json`:
```json
{"port": 5000, "token": "change-me", "subnet_sweep": true,
 "pis": [{"number": 1, "mac": "XX:XX:XX:XX:XX:XX", "last_ip": "192.168.11.135"}, ...]}
```
Discovery: probe every `last_ip`; Pis with a real MAC that weren't found → sweep the mini-PC's /24 for
`GET :5000/health` (parallel, ~0.5 s timeout) and match any reported MAC (case-insensitive). The mini-PC's
address is found by routing toward the known Pi IPs first (works on an isolated lab LAN with no gateway),
then 8.8.8.8; if neither routes, the sweep is skipped and a warning is logged. A placeholder MAC
(contains `X`) matches by `last_ip` only. Found IPs are written back to `last_ip`.

## Contract 3 — the algorithm seam (future `gui_driver.py` hookup)

`coordinator/executor.py::BatchExecutor.run_batch(instructions) -> {"<spheroID>": outcome}`

- Takes a list of `controls.Instruction.Instruction` objects (or equivalent dicts) — the **same** type
  `gui_driver.py` already builds — and runs one batch: every instruction in parallel, returns when all finish.
  `spheroID` is 1-based into the session's ordered robot list (exactly like `Controls_Server` indexing
  `constants.SPHERO_TAGS`). Type -1/-2 → stop-all.
- Outcomes use the same strings `Controls_Server` returns, so `gui_driver`'s `turn_outcomes.get(...) == "complete"`
  logic works unchanged.
- `coordinator/controls_bridge.py` serves `controls/protocol.py` on `localhost:1235` (Controls_Server's port):
  on connect it sends `pickle.dumps(ordered_robot_ids)`, then loops `receive_batch` → `run_batch` → `send_result`.
  **Hooking up `gui_driver.py` = run the dashboard, connect balls, start the bridge, run `gui_driver.py` instead of
  starting `Controls_Server.py`.** No algorithm code changes.
- Routines (`coordinator/routines/`) produce lists of batches of the same `Instruction`s and run through the same
  executor. Adding one = one file with `formation(n, params)` + `batches(n, params)`, registered in `routines/__init__.py`.

## Tests

```
uv run --with pytest pytest controls/tests coordinator/tests -q
```
All run on a laptop with no Bluetooth (fake hardware / fake Pi nodes).
