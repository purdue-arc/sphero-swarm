### Perceptions Subteam

## Running Camera Detection

# In Terminal 

```python sphero_spotter.py```

| Flag | Long Flag | Description |
|------|-----------|-------------|
| `-n` | `--nogui` | Run the Sphero Spotter without opening any GUI windows. |
| `-l` | `--locked` | Freeze the initial Sphero ID assignments. No new IDs will be assigned after the first frame. |
| `-m PATH` | `--model PATH` | Path to the YOLO model file to use for object detection (default: `./models/bestv3.pt`). |
| `-d` | `--debug` | Activates debug mode (prints out all the spheres) |
| `-v PATH` | `--video PATH` | Use provided video path as input stream |
| `-w` | `--webcam` | Use webcam as input stream |
| `-t` | `--latency` | Measure the latency in the camera ⏱️ |


# If Libaries are not installed
Run from the perceptions folder:
pip install -r requirements.txt

**Important: use Python 3.9+.**

### Perceptions folder — file overview

This section summarizes the purpose, key components, and connections between the Python files in the `perceptions` folder.

- [sphero_spotter.py](sphero_spotter.py)
  - Purpose: Central Sphero detection and tracking module. Reads frames from a camera or video, detects Spheros and AprilTags, maintains consistent IDs for swarm coordination, and exposes a ZeroMQ interface for Algorithms to request coordinates.
  - Key components:
      - Camera / video input abstraction using `input_streams.py` (WebcamStream, VideoFileStream)
      - AprilTag detection and optional perspective correction
      - YOLOv8 + BotSort tracking for Spheros
      - ID mapping logic (frozen first-frame IDs with optional dynamic assignment)
      - Real-time visualization (optional GUI)
      - ZeroMQ REP listener thread exposing:
          - `'init'` → number of spheros detected
          - `'coords'` → JSON of Sphero positions
          - `'exit'` → terminates listener
  - Used by: 
      - Algorithms
      - Optional web client / debugging GUI

- [SpheroCoordinate.py](SpheroCoordinate.py)
  - Purpose: Defines a class for storing spheros and their positions
  - Key components: class [`Sphero`](sphero.py) with fields `id`, `x`, `y`
  - Used by: [`Sphero Spotter`](sphero_spotter.py) to store sphero objects

- [input_streams.py](input_streams.py)
  - Purpose: Provides a unified abstract interface for all frame sources (webcam, OAK-D, video files, simulation)
  - Key components:
      - class `InputStream` base abstract class (common API used everywhere)
      - `WebcamStream` — live camera frames
      - `VideoFileStream` — frame timed reads from video (real-time rate aware / doesn't overrun / matches real playback FPS)
  - Used by: [`Sphero Spotter`](sphero_spotter.py) to handle different input streams

- [test_client.py](test_client.py)
  - Purpose: Human operator web client / inspector UI. HTTP based. Allows manual verification, debugging and inspection of sphero_spotter output without needing to run full swarm control. **Must have sphero_spotter.py running**
  - Key components:
      - Flask web server
      - ZeroMQ REQ client connection to sphero_spotter (same REQ/REP protocol as Algorithm)
      - HTML/JS table renderer for returning Sphero list in realtime
  - Used by: N/A. Used during calibration, testing, research iteration, visual sanity checking. Does **not** participate in algorithm. Pure debug/visibility layer.

- [yolo_test_v2.py](yolo_test_v2.py)
  - Purpose: Detects and tracks Spheros using YOLOv8 with a BotSort tracker, assigning consistent display IDs to objects for downstream logic. Supports freezing initial IDs to avoid reassigning labels every frame. **Manually Testing Model**
  - Key components:
      - YOLOv8 model loading and tracking
      - BotSort tracker integration
      - ID mapping logic: frozen first-frame IDs, optional assignment for newcomers
      - Real-time visualization with OpenCV
  - Used by: N/A

- [models/*.pt](models/*.pt)
  - Purpose: Hosts models for running sphero_swarm

## Roll accuracy evaluation

Start perception and detect all four AprilTags to calibrate the arena. Confirm
the grid aligns with physical grid nodes and the detection IDs match the Sphero
tags in the GUI. Algorithm ID 1 maps to perception ID 0, and so on. Enable
controls and step the algorithm to run a trial. Use one robot at a time initially,
then repeat distances and directions for each robot at the regression's speed.

The camera feed draws a labeled crosshair and tolerance ring at each commanded
target. After controls finishes the roll batch, fresh detections must stay within
0.03 grid steps for at least 0.75 seconds and five frames. The mean of those
positions becomes the endpoint circle. A line joins it to the target. The GUI's
Roll accuracy table shows the predicted time, measured error, and pass/fail
(default tolerance: 0.1 grid steps). These overlays are drawn after detection;
they are not drawn into the detection image or pixel mask.

The driver waits for endpoint measurements before issuing the next move.
Trials time out after 10 seconds of waiting for a stable endpoint. Missing/stale
detections cannot become endpoints. Disconnected robots, failed turns/rolls,
identity edits, missing start positions, and timeouts receive explicit statuses.
Zero-distance moves do not roll. Start/end positions are camera measurements;
algorithm simulation coordinates are not measured endpoints. Targets remain
visible until that robot's next trial or perception restarts.

Results append to `controls/Data_Collection/roll_evaluation.csv`. Coordinates
and signed along/perpendicular errors use grid units; endpoint distance is also
reported in inches using the driver's `ROLL_STRAIGHT_INCH` scale (12.67 by
default). Check that scale against your arena before interpreting inch errors.
Along error is positive for overshoot; perpendicular error reports heading drift.
Use the CSV to compare mean/worst endpoint error and pass percentage per robot.

Optional `ROLL_EVALUATION` settings in `gui/constants.json` are read at perception
startup: `SETTLE_SECONDS`, `JITTER_GRID`, `TOLERANCE_GRID`, and `TIMEOUT_SECONDS`.
All must be positive. Keep timeout below the driver's 12-second evaluation wait.
Restart both the driver and controls server after updating: the driver uses
framed batches with completion replies. Legacy controls clients still receive
the existing queue acknowledgement. If calibrated perception is unavailable,
the driver reports that evaluation is unavailable and still executes movement.
