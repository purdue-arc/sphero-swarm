# Onboarding curriculum

Sessions are surged — anyone who finishes a session's goals early moves on to
the next session's material instead of waiting.

There is no single script that "generates" these sessions. Each one maps onto
real code already in this repo — some of it archived (moved into
`controls/Old_code/` since it's no longer part of the live pipeline, but it's
still exactly what these exercises are teaching). Pointers are below each
bullet.

## Session 1 — Basic setup

- Install Python (python.org), then install deps: `spherov2`, and stdlib
  modules `socket`, `pickle`, `threading`, `subprocess` need no install;
  `keyboard` does (`pip install keyboard`).
- Set up Git/GitHub, clone the repo.
- Just run the code — no explanation yet. Use `controls/Controls_Test_Server.py`
  (LED-only, safest first run — connects and sets colors, never moves).
  - Functions it calls: `scanner.find_toys()`, `SpheroEduAPI(toy).__enter__()`,
    `sb.set_main_led(Color(r,g,b))`.
- Point to docs: https://spherov2.readthedocs.io/en/latest/sphero_edu.html

## Session 2 — Single Sphero control

- **Hardcoded turn / roll / color change.**
  Functions actually used here: `api.set_main_led(Color(r,g,b))`,
  `api.set_heading(degrees)`, `api.set_speed(speed)` for straight-line
  movement.
  Reference: `controls/Old_code/Demo/functionalities.py` (`bolt.set_speed()` /
  `bolt.set_heading()`).

- **WASD-responsive, with a color change command.**
  Functions: `keyboard.is_pressed('w'/'a'/'s'/'d')` polled in a loop, driving
  `api.set_heading()` + `api.set_speed()`.
  Reference: `controls/Old_code/Demo/wasd-control.py` (absolute cardinal
  headings) and `qweasd-control.py` (relative-turn headings) — two different
  conventions, worth comparing.

## Session 3 — Multi-Sphero and advanced functions

- **Variable number of Spheros, synchronous execution.**
  Functions: `threading.Thread` — one thread per ball for connect and for
  command execution, then `.join()` on all of them before moving to the next
  command batch.
  Reference: `controls/Controls_Server.py::connect_multi_ball()` and
  `run_multi_command()`.

- **Curved movement (iterative angle change — doesn't need precision).**
  Pattern: don't issue one big turn command — step the heading in small
  increments across elapsed time, recomputing the target delta from the
  elapsed-time fraction each iteration.
  Reference: `controls/Controls_Server.py::run_command()`, case `2` (turn) —
  this exact pattern; spherov2's own `SpheroEduAPI.spin()`
  (`sphero_edu.py` ~line 204) is the same algorithm internally.

## Session 4 — Full introduction

- **Walk through `controls/Controls_Server.py` in detail**: scan → connect →
  queue → execute → teardown. Explain why it's threaded (one BLE session per
  ball), why there's a `KILL_FLAG` (cooperative shutdown other threads check
  on every loop iteration), and why there's a `run_server_lock` (only one
  session active at a time).

- **New members build a basic server-client multifile system.**
  Server-side pattern: `socket.socket()`, `.bind()`, `.listen()`, `.accept()`,
  `conn.recv()`/`conn.send()`, `pickle.loads()`/`pickle.dumps()`.
  Client-side pattern: `socket.socket()`, `.connect()`, send a pickled list of
  `Instruction` objects, wait for the ack.
  Reference: `controls/Controls_Server.py::command_gathering()` (server) +
  `gui_driver.py::_send_controls_update()` (repo root — client) — this is the
  actual current two-file client/server split, not an archived demo. (Note:
  `controls/Old_code/Experiments/producer_script.py` /
  `consumer_script.py` / `controlCenter.py` look similar by name but use
  `multiprocessing`/`subprocess`, not sockets — don't point new members at
  those for this exercise.)

- **Active problems to introduce:**
  - *Curved movement fine-tuning (radius/timing)* — same iterative-angle code
    as Session 3; tune the `time_pre_rev` / duration constants in
    `Controls_Server.py::run_command()` case `2`.
  - *Reply to messages* — extend the `conn.send(...)` ack in
    `command_gathering()` to carry real status instead of just `b"Done"`.
  - *Safe termination across multiple files* — the `KILL_FLAG` +
    `try/finally` pattern has to propagate across the socket boundary too;
    the client must catch `EOFError` when the server closes (see
    `command_gathering()`'s own `except EOFError` handling for the mirror
    case).
  - *Expanding beyond one Bluetooth adapter's limit* — a genuinely open
    problem in this codebase, not solved yet. Worth investigating whether
    multiple `BleakAdapter` connections sharing one machine's radio is the
    actual ceiling, and whether multiple machines/adapters is the fix.
