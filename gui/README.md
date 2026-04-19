# GUI Usage Guide

## First-Time Setup

From the project root:

```bash
uv sync
cd gui
npm install
```

## Running the GUI

From `gui/`:

```bash
npm run start
```

## Configure Before Any Run

In the Config tab, verify and save:

- Grid size
- Sphero IDs and mapped locations
- Any other run-specific constants

Always save config changes before starting a test.

## Running a Full Hardware Test

1. Place all Spheros on the grid in the correct orientation.
2. If AprilTags are set up:
	- Start the perception server.
	- Toggle/show the grid and verify all balls are in correct positions.
	- Stop the perception server after positioning
3. In the Controls tab, attempt to connect all robots.
4. If not all connect:
	- Disconnect the ones that did connect.
	- Click Refresh Controls Script.
	- Retry connection.
5. Once all are connected, open Perception, choose OAK-D, and click Start.
6. In a separate terminal (from project root), start the algorithm/driver process:

```bash
uv run python -m gui_driver
```

If needed for your environment:

```bash
uv run python3 -m gui_driver
```

7. In the GUI, enable controls.
8. Click Start.

## Resetting After a Test

1. Disconnect all Spheros.
2. Stop the algorithm server (`Ctrl+C` in its terminal).
3. Click Reset Controls Script.
4. Update config values if needed.
5. Reconnect from the Controls tab (Connect All).
6. Restart the perception server.
7. Restart the algorithm server and verify Enable Controls is on.

## Running Simulation Only

1. Configure values in the Config tab.
2. Between algorithm tests, click Reset.

## Important Notes

- Keep GUI and Python backend logs visible in separate terminals while testing.
- If controls become unresponsive, disconnect all robots, refresh/reset controls script, and reconnect.
- If tracking looks wrong, re-check grid config and robot starting positions before rerunning.