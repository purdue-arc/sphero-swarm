# Sphero Swarm GUI

## Setup

From the repository root:

```bash
uv sync
cd gui
npm install
```

## Run

From `gui/`:

```bash
npm run start
```

This launches the desktop app. Electron manages the algorithm process, controls server, and perception process; a separate `gui_driver` terminal is no longer needed. The algorithm starts with the app. Controls and perception start from Runner.

## Runner

The main workspace keeps four panels on screen:

- **Settings (top left):** Edit the grid, Sphero tags, starting coordinates, and head/tail roles. Changes update the stopped algorithm preview immediately and save to `constants.json` automatically. Select a ball and click a grid node in the preview to place it.
- **Controls (top right):** Connect the fleet, see when each Sphero was found, retry a ball, disconnect it, disconnect all, or restart the controls service. Disconnect All and Restart wait for the controls session to release Sphero connections before starting a fresh server.
- **Algorithms (bottom left):** See starting positions and ball IDs while stopped, then live algorithm positions while running. Start and Stop control the test. Use controls enables hardware movement when Spheros are connected; Step seconds sets the time between algorithm steps. The service restart button relaunches `gui_driver` as a child process.
- **Perception (bottom right):** Choose OAK-D or a webcam, display grid lines, and start, stop, or restart the camera service.

The full Perception page still provides detection telemetry and live Sphero tag reassignment.

The Dashboard, Configuration, Controls, Perception, Algorithms, and Simulation views remain in the sidebar. Algorithms and Simulation share the same run settings.
