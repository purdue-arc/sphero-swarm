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