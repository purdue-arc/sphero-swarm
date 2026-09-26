import os
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

import threading
import zmq                      # for socket to connect to algs
from queue import Queue, Empty
from collections import deque
from types import SimpleNamespace

import server
from ultralytics import YOLO    # computer vision imports
import cv2
import argparse
import json
import torch

from pupil_apriltags import Detector # for april tag detection
import numpy as np
import time
detector = Detector()

from SpheroCoordinate import SpheroCoordinate
from input_streams import WebcamStream, VideoFileStream
import blob_merge

# Brightness-mode tuning. Lives in constants.json under "PERCEPTION" so it can
# be changed without editing code or passing a wall of flags; the values below
# are the fallbacks when the file or a key is missing. The mask-window sliders
# write straight into this at runtime.
PERCEPTION_DEFAULTS = {
    "BRIGHT_THRESH": 200,        # brightness cutoff 0-255, at or below = background
    "BRIGHT_MIN_AREA": 50.0,     # smallest blob accepted as a sphero, in pixels
    "BRIGHT_MAX_AREA": 0.0,      # largest blob accepted, 0 = no upper limit
    "BRIGHT_BLUR": 5,            # gaussian blur kernel before thresholding, 0 = off
    "BRIGHT_MATCH_DIST": 80.0,   # max px a blob may move and keep its track id
    "BRIGHT_MAX_BLOBS": 0,       # blobs kept, largest first; 0 = use N_SPHEROS
    "MERGE_SPLIT": True,         # split blobs holding two touching spheros
    "MERGE_AREA_RATIO": 1.5,     # blob this many x one sphero = a merge
    "MERGE_PEAK_SEP": 6,         # min px between the two peaks used to split
}

# Load N_SPHEROS and the perception tuning from the shared constants file
_constants_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'gui', 'constants.json')
try:
    with open(_constants_path) as _f:
        _constants = json.load(_f)
    N_SPHEROS = _constants.get('N_SPHEROS', 3)
    print(f"sphero_spotter: N_SPHEROS={N_SPHEROS} (from constants.json)")
except Exception as _e:
    _constants = {}
    N_SPHEROS = 3
    print(f"sphero_spotter: could not read constants.json ({_e}), defaulting N_SPHEROS={N_SPHEROS}")

_perception = _constants.get('PERCEPTION', {})
tune = SimpleNamespace(**{k: _perception.get(k, v) for k, v in PERCEPTION_DEFAULTS.items()})
if _perception:
    _overrides = [k for k in PERCEPTION_DEFAULTS if k in _perception]
    print(f"sphero_spotter: PERCEPTION settings from constants.json: {', '.join(_overrides)}")

parser = argparse.ArgumentParser(description="Sphero Spotter")
parser.add_argument('--nogui', '-n', action='store_true', help="Run the Sphero Spotter without opening any GUI windows.")
parser.add_argument('--locked', '-l', action='store_true', help="Freeze the initial Sphero ID assignments. No new IDs will be assigned after the first frame.")
parser.add_argument('--model', '-m', type=str, default="./models/bestv3.pt", help="Path to the YOLO model file to use for object detection (default: %(default)s).")
parser.add_argument('--debug', '-d', action='store_true', help="Activates debug mode (aka prints out all the spheres)")
parser.add_argument('--latency', '-t', action='store_true', help="Prints the latency in the camera as well as processing time")
parser.add_argument('--imgsz', type=int, default=640, help="YOLO inference image size (smaller = faster, default: 640)")
parser.add_argument('--conf', type=float, default=0.25, help="YOLO confidence threshold (default: 0.25)")
parser.add_argument('--device', type=str, default=None, help="Device for YOLO inference (cuda, mps, cpu, or None for auto)")
parser.add_argument('--server', '-s', action='store_true', help="Streams video to server")
parser.add_argument('--grid', '-g', action='store_true', help="Shows the grid overlay")
parser.add_argument('--brightness', '-b', action='store_true', help="Detect spheros by pixel brightness instead of YOLO: dark background is thresholded away and each blob of bright pixels is reported as a sphero.")
parser.add_argument('--hide-mask', action='store_true', help="In --brightness mode, don't show the filtered (thresholded) view. By default it is shown alongside the camera image with live tuning sliders.")
parser.add_argument('--bright-thresh', type=int, default=None, help="Brightness cutoff 0-255 for --brightness mode; at or below this is background (default: from constants.json).")
parser.add_argument('--bright-min-area', type=float, default=None, help="Smallest blob accepted as a sphero, in pixels (default: from constants.json).")
parser.add_argument('--bright-blur', type=int, default=None, help="Gaussian blur kernel applied before thresholding, 0 = off (default: from constants.json).")
parser.add_argument('--bright-match-dist', type=float, default=None, help="Max pixels a blob may move between frames and keep its track id (default: from constants.json).")


group = parser.add_mutually_exclusive_group()
group.add_argument('--video', '-v', type=str, help="Use provided video path as input stream")
group.add_argument('--webcam', '-w', action='store_true', help="Use webcam as input stream")

args = parser.parse_args()

def apply_tuning(values):
    """Write tuning values into `tune`, coerced to the type of each default.

    Used by the command line flags and by the GUI's live sliders, which send
    {"action": "set_tuning", "values": {...}} over the telemetry socket.
    Unknown keys are ignored so a stale GUI can't set arbitrary attributes.
    """
    applied = {}
    for key, value in (values or {}).items():
        default = PERCEPTION_DEFAULTS.get(key)
        if default is None and key not in PERCEPTION_DEFAULTS:
            continue
        try:
            cast = type(default)(value) if not isinstance(default, bool) else bool(value)
        except (TypeError, ValueError):
            continue
        setattr(tune, key, cast)
        applied[key] = cast
    return applied

# Command line beats constants.json for the brightness settings, so the GUI can
# launch with whatever the user last had on the sliders.
_cli_tuning = {
    "BRIGHT_THRESH": args.bright_thresh,
    "BRIGHT_MIN_AREA": args.bright_min_area,
    "BRIGHT_BLUR": args.bright_blur,
    "BRIGHT_MATCH_DIST": args.bright_match_dist,
}
_cli_tuning = {k: v for k, v in _cli_tuning.items() if v is not None}
if _cli_tuning:
    print(f"sphero_spotter: tuning from command line: {apply_tuning(_cli_tuning)}")

# CONSTANTS
GRID_DIM_X = 12 # TODO finalize dimensions
GRID_DIM_Y = 10
frame_dim_x = 100000
frame_dim_y = 100000

# Global array of SpheroCoordinates
spheros = {}

def format_sphero_json(spheroCoord):
    x,y = pixel_to_grid_coords(spheroCoord.x_coordinate, spheroCoord.y_coordinate)
    return {"ID": spheroCoord.ID, "X": x, "Y": y}

def pixel_to_grid_coords(pixel_x, pixel_y):
    pixels_per_inch_x = arena_w_px / ARENA_WIDTH_INCH
    pixels_per_inch_y = arena_h_px / ARENA_HEIGHT_INCH

    cell_w = ROLL_STRAIGHT_INCH * pixels_per_inch_x
    cell_h = ROLL_STRAIGHT_INCH * pixels_per_inch_y

    grid_x = float(pixel_x / cell_w)
    grid_y = float(pixel_y / cell_h)

    grid_x = min(grid_x, GRID_WIDTH - 1)
    grid_y = min(grid_y, GRID_HEIGHT - 1)

    return (grid_x, grid_y)
# 

ARENA_WIDTH_INCH = 59
ARENA_HEIGHT_INCH = 49
ROLL_STRAIGHT_INCH = 12.67
GRID_WIDTH = GRID_HEIGHT = 7
arena_w_px = 500
arena_h_px = 500

last_valid_frame = None

# Status tracking for GUI telemetry
last_apriltag_count = 0
zmq_bound = False
last_latency = None

def draw_grid(frame, top_left, bottom_right):
    global arena_h_px, arena_w_px

    if not args.grid:
        return frame

    x0, y0 = top_left
    x1, y1 = bottom_right

    # Arena pixel size
    arena_w_px = x1 - x0
    arena_h_px = y1 - y0

    # Convert inches → pixels
    pixels_per_inch_x = arena_w_px / ARENA_WIDTH_INCH
    pixels_per_inch_y = arena_h_px / ARENA_HEIGHT_INCH

    # Grid cell size in pixels
    cell_w = ROLL_STRAIGHT_INCH * pixels_per_inch_x
    cell_h = ROLL_STRAIGHT_INCH * pixels_per_inch_y

    # Determine number of lines (still clamped)
    num_lines_x = min(int(ARENA_WIDTH_INCH / ROLL_STRAIGHT_INCH), GRID_WIDTH)
    num_lines_y = min(int(ARENA_HEIGHT_INCH / ROLL_STRAIGHT_INCH), GRID_HEIGHT)

    # Vertical lines
    for i in range(num_lines_x + 1):
        x = int(x0 + i * cell_w)
        cv2.line(frame, (x, y0), (x, y1), (0, 255, 0), 1)
    
    # Horizontal lines
    for j in range(num_lines_y + 1):
        y = int(y0 + j * cell_h)
        cv2.line(frame, (x0, y), (x1, y),  (0, 255, 0), 1)

    # Diagonals
    for i in range(num_lines_x):
        for j in range(num_lines_y):
            x_start = int(x0 + i * cell_w)
            y_start = int(y0 + j * cell_h)
            x_end   = int(x0 + (i+1) * cell_w)
            y_end   = int(y0 + (j+1) * cell_h)

            # First diagonal: top-left → bottom-right
            cv2.line(frame, (x_start, y_start), (x_end, y_end), (0, 255, 0), 1)

            # Second diagonal: bottom-left → top-right
            cv2.line(frame, (x_start, y_end), (x_end, y_start), (0, 255, 0), 1)

    return frame

def process_apriltags(frame, force_process=False):
    global april_tag_frame_counter, last_warped_frame, last_warp_matrix, last_apriltag_count
    
    # Only process April tags periodically to reduce latency
    if not force_process:
        april_tag_frame_counter += 1
        if april_tag_frame_counter % APRIL_TAG_PROCESS_INTERVAL != 0:
            # Reuse last warped frame if available
            if last_warped_frame is not None and last_warp_matrix is not None:
                warped = cv2.warpPerspective(frame, last_warp_matrix, (500, 500))
                top_left = (0, 0)
                bottom_right = (warped.shape[1] - 1, warped.shape[0] - 1)
                grid = draw_grid(warped, top_left, bottom_right)
                return grid
            # No warped frame available, draw grid on full frame if enabled
            if args.grid:
                top_left = (0, 0)
                bottom_right = (frame.shape[1] - 1, frame.shape[0] - 1)
                return draw_grid(frame, top_left, bottom_right)
            return frame
    
    # Process April tags (full detection)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    results = detector.detect(gray)
    last_apriltag_count = len(results) # type: ignore
    tag_points = {}

    for r in results: # type: ignore
        corners = r.corners.astype(int)
        tag_id = r.tag_id
        cX, cY = int(r.center[0]), int(r.center[1])

        # Draw tag outline and ID
        for j in range(4):
            cv2.line(frame, tuple(corners[j]), tuple(corners[(j + 1) % 4]), (0, 255, 0), 2)
        cv2.circle(frame, (cX, cY), 4, (0, 0, 255), -1)
        cv2.putText(frame, f"ID: {tag_id}", (cX - 20, cY - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
        tag_points[tag_id] = corners

    # Optional perspective correction if 4 tags detected
    warped = None
    if len(tag_points) == 4:
        ids = sorted(tag_points.keys())
        custom_points = []
        for i, tid in enumerate(ids):
            corners = tag_points[tid]
            if i == 0: custom_points.append(tuple(corners[1]))
            elif i == 1: custom_points.append(tuple(corners[0]))
            elif i == 2: custom_points.append(tuple(corners[2]))
            elif i == 3: custom_points.append(tuple(corners[3]))

        custom_points = np.array(custom_points, dtype=np.float32)
        size = 500
        dst_pts = np.array([[0,0],[size,0],[0,size],[size,size]], dtype=np.float32)
        M = cv2.getPerspectiveTransform(custom_points, dst_pts)
        last_warp_matrix = M  # Cache the transformation matrix
        warped = cv2.warpPerspective(frame, M, (size, size))
        last_warped_frame = warped.copy()  # Cache the warped frame
        top_left = (0, 0)
        bottom_right = (warped.shape[1] - 1, warped.shape[0] - 1)

        grid = draw_grid(warped, top_left, bottom_right)
        return grid
    
    # No perspective correction available, draw grid on full frame if enabled
    if args.grid:
        top_left = (0, 0)
        bottom_right = (frame.shape[1] - 1, frame.shape[0] - 1)
        return draw_grid(frame, top_left, bottom_right)
    
    return warped if warped is not None else frame

def initialize_spheros():
    return N_SPHEROS

def listener():
    '''
    This function is started in a thread and concurrently listens for requests from Algorithm team's side.

    Algorithm team will send a request containing "init" and we will wait for that. we will send back a message saying
    "connected" and then start listening for strings saying "coords". When we receive a string
    containing "exit", the listener will stop.

    We receive:             | We send back:
    ------------------------|-------------------------------------------
    'init'                  | number of spheros we detected, as a string.
    'coords'                | json of format {"numSpheros": __, "spheros": [{"id": __ , "x":__, "y":__ }]
    'exit'                  | nothing


    '''
    global zmq_bound
    # connect to the socket
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind("tcp://*:5555")
    zmq_bound = True
    print('sphero_spotter: socket bind success')


    # start listening for 'init', 'coords' requests or 'exit'.
    while True:
        print('sphero_spotter: listening...')

        msg = socket.recv_string()
        print(f"Received request '{msg}' from algorithms!")

        if msg == 'init':
            num_found = initialize_spheros() # get their positions and assign IDs.
            socket.send_string(f"connected - {num_found}")

        elif msg == 'coords':
            json_val = {"numSpheros":len(spheros), "spheros":[format_sphero_json(x) for x in spheros.values()]}

            socket.send_json(json_val)

        elif msg == 'exit':
            break

        else:
            socket.send_string("error - command doesn\'t match one of ['init', 'coords', 'exit']")
    print('listener stopped')


ASSIGN_NEW_IDS_AFTER_FIRST_FRAME = not args.locked
frozen = False
id_map = {}
model = YOLO(args.model) if not args.brightness else None

# Optimize model device
if args.device is None:
    if torch.cuda.is_available():
        device = 'cuda'
    elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
        device = 'mps'
    else:
        device = 'cpu'
else:
    device = args.device

# Move model to device (YOLO handles device placement automatically, but we can optimize)
if device != 'cpu':
    try:
        # YOLO will automatically use the device when inference is called
        print(f"Using device: {device} for YOLO inference")
    except Exception as e:
        print(f"Warning: Could not optimize model for {device}: {e}")

next_display_id = 0
lost_spheros = {}  # disp_id -> (last_cx, last_cy)

# Threading for async processing
frame_queue = Queue(maxsize=2)  # Only keep latest 2 frames
result_queue = Queue(maxsize=1)
processing_thread = None
stop_processing = threading.Event()

# April tag processing optimization
april_tag_frame_counter = 0
APRIL_TAG_PROCESS_INTERVAL = 5  # Process April tags every N frames
last_warped_frame = None
last_warp_matrix = None

# --- Brightness-threshold detection ------------------------------------------
# Treats the scene as bright spheros on a dark background: everything at or
# below --bright-thresh is dropped, the mask is cleaned up with morphology, and
# each surviving blob inside the area limits becomes one detection.
bright_tracks = {}   # tracker_id -> (cx, cy) from the previous frame
bright_vels = {}     # tracker_id -> (vx, vy), smoothed, for merge predictions
next_bright_tid = 0
single_area = blob_merge.SingleAreaEstimator()   # running size of one sphero
_merge_state = {}    # frozenset of merged tracker ids -> how it was last split

def class_name_for(cls_id):
    if cls_id < 0 or model is None:
        return "bright"
    return model.names[cls_id]

# Predicted track positions inside this many pixels of a blob's box count as
# "this track is in that blob" when deciding whether the blob is a merge.
MERGE_NEAR_MARGIN = 8

def resolve_merged_blobs(mask, blobs):
    """Split blobs that hold two spheros, between blob extraction and matching.

    Returns (entries, vis): entries are blob tuples with a forced tracker id
    appended (None = let the normal matching decide), vis is what the mask
    window should draw for each merge being resolved.
    """
    global _merge_state

    est = single_area.estimate
    preds = {tid: blob_merge.predict(pos, bright_vels.get(tid, (0.0, 0.0)))
             for tid, pos in bright_tracks.items()}

    entries = []
    vis = []
    seen = {}
    claimed = set()
    coasting = {}   # tracker_id -> dead-reckoned position, while fully occluded
    for area, cx, cy, x1, y1, x2, y2 in blobs:
        near = [t for t, p in preds.items()
                if t not in claimed
                and x1 - MERGE_NEAR_MARGIN <= p[0] <= x2 + MERGE_NEAR_MARGIN
                and y1 - MERGE_NEAR_MARGIN <= p[1] <= y2 + MERGE_NEAR_MARGIN]

        if not (tune.MERGE_SPLIT and blob_merge.is_merged(area, est, tune.MERGE_AREA_RATIO, len(near))):
            single_area.update(area)   # unambiguously one sphero: size reference
            entries.append((area, cx, cy, x1, y1, x2, y2, None))
            continue

        # The two tracks this blob is holding: nearest predictions to its centre
        pair = sorted(near, key=lambda t: (preds[t][0] - cx)**2 + (preds[t][1] - cy)**2)[:2]

        pieces, peaks = blob_merge.split_blob(mask, (x1, y1, x2, y2), tune.MERGE_PEAK_SEP)
        mode = "watershed"
        if not blob_merge.pieces_plausible(pieces, est):
            # Peaks were wrong or the halves were lopsided: fall back to where
            # each track was heading and cut the pixels by nearest prediction.
            pieces = blob_merge.split_by_prediction(mask, (x1, y1, x2, y2),
                                                    [preds[t] for t in pair]) if len(pair) == 2 else None
            mode = "predicted"
        if pieces is None:
            mode = "unsplit"
            entries.append((area, cx, cy, x1, y1, x2, y2, None))
        elif len(pair) == 2:
            order = blob_merge.assign_pieces(pieces, [preds[t] for t in pair])
            for tid, piece in zip(pair, (pieces[order[0]], pieces[order[1]])):
                entries.append(piece + (tid,))
                claimed.add(tid)
                if mode == "predicted":
                    # One peak for two spheros means they are on top of each
                    # other. The half each track gets is always the side it is
                    # already on, so feeding those centroids back in would stall
                    # the crossing: carry the track on dead reckoning instead,
                    # clamped to the blob, and still report the measured half.
                    coasting[tid] = blob_merge.clamp_to_box(preds[tid], (x1, y1, x2, y2))
            vis.append((pieces[order[0]], pieces[order[1]], (x1, y1, x2, y2), mode, tuple(pair)))
        else:
            # Split worked but we don't know whose halves these are (e.g. first
            # frame) - let the normal matching hand out ids.
            for piece in pieces:
                entries.append(piece + (None,))
            vis.append((pieces[0], pieces[1], (x1, y1, x2, y2), mode, tuple(pair)))

        key = frozenset(pair) if pair else frozenset()
        seen[key] = mode
        if _merge_state.get(key) != mode or args.debug:
            ratio = f"{area / est:.2f}x" if est else "no size estimate yet"
            ids = ",".join(str(t) for t in pair) if pair else "unassigned"
            print(f"[merge] blob area={int(area)} ({ratio}) peaks={peaks} -> {mode}, ids {ids}")
    _merge_state = seen

    # Forced ids first, so a neighbouring blob can't take one by proximity
    entries.sort(key=lambda e: e[7] is None)
    return entries, vis, claimed, coasting

MERGE_COLOURS = ((255, 0, 255), (255, 255, 0))   # magenta / cyan, one per half
MERGE_BOX_COLOUR = (0, 165, 255)                 # orange, the blob they came from

def draw_merge_overlay(mask_view, merge_vis):
    """Mark every merge being resolved on the filtered view."""
    for piece_a, piece_b, (mx1, my1, mx2, my2), mode, pair in merge_vis:
        cv2.rectangle(mask_view, (int(mx1), int(my1)), (int(mx2), int(my2)),
                      MERGE_BOX_COLOUR, 1)
        for piece, colour in zip((piece_a, piece_b), MERGE_COLOURS):
            cv2.circle(mask_view, (int(piece[1]), int(piece[2])), 4, colour, -1)
        label = "MERGED (" + mode + ")" + (f" {pair[0]}/{pair[1]}" if len(pair) == 2 else "")
        cv2.putText(mask_view, label, (int(mx1), max(12, int(my1) - 5)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, MERGE_BOX_COLOUR, 1, cv2.LINE_AA)

def detect_bright_blobs(frame):
    """Return (dets, mask, merge_vis) where dets matches the YOLO tuple layout."""
    global bright_tracks, bright_vels, next_bright_tid

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    k = tune.BRIGHT_BLUR
    if k > 0:
        k = k if k % 2 == 1 else k + 1   # GaussianBlur needs an odd kernel
        gray = cv2.GaussianBlur(gray, (k, k), 0)

    _, mask = cv2.threshold(gray, tune.BRIGHT_THRESH, 255, cv2.THRESH_BINARY)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)    # kill speckle
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)   # fill holes

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    blobs = []  # (area, cx, cy, x1, y1, x2, y2)
    for c in contours:
        area = cv2.contourArea(c)
        if area < tune.BRIGHT_MIN_AREA:
            continue
        if tune.BRIGHT_MAX_AREA > 0 and area > tune.BRIGHT_MAX_AREA:
            continue
        x, y, w, h = cv2.boundingRect(c)
        m = cv2.moments(c)
        if m["m00"] > 0:
            cx = m["m10"] / m["m00"]
            cy = m["m01"] / m["m00"]
        else:
            cx, cy = x + w / 2.0, y + h / 2.0
        blobs.append((area, cx, cy, float(x), float(y), float(x + w), float(y + h)))

    # Largest first, so leftover glare loses to the actual spheros
    blobs.sort(key=lambda b: b[0], reverse=True)
    limit = tune.BRIGHT_MAX_BLOBS if tune.BRIGHT_MAX_BLOBS > 0 else N_SPHEROS
    blobs = blobs[:limit]

    # A merged blob is two spheros in one contour: split it and pin each half
    # to its own track before the ordinary matching runs.
    blobs, merge_vis, merged_tids, coasting = resolve_merged_blobs(mask, blobs)

    # Greedy nearest-neighbour association with the previous frame, so the
    # downstream ID logic sees stable tracker IDs like YOLO's tracker provides.
    new_tracks = {}
    new_vels = {}
    available = dict(bright_tracks)
    dets = []
    for area, cx, cy, x1, y1, x2, y2, forced_tid in blobs:
        tid = None
        if forced_tid is not None and forced_tid in available:
            tid = forced_tid
            del available[tid]
        elif available:
            cand = min(available,
                       key=lambda t: (cx - available[t][0])**2 + (cy - available[t][1])**2)
            px, py = available[cand]
            if (cx - px)**2 + (cy - py)**2 <= tune.BRIGHT_MATCH_DIST**2:
                tid = cand
                del available[cand]
        if tid is None:
            tid = next_bright_tid
            next_bright_tid += 1
        if tid in merged_tids:
            # Split centroids sit outside the true ones and converge as the
            # spheros touch, so re-estimating velocity here bleeds away the
            # momentum that carries them past each other. Hold it instead.
            new_vels[tid] = bright_vels.get(tid, (0.0, 0.0))
        elif tid in bright_tracks:
            new_vels[tid] = blob_merge.update_velocity(bright_vels.get(tid, (0.0, 0.0)),
                                                       bright_tracks[tid], (cx, cy))
        else:
            new_vels[tid] = (0.0, 0.0)
        new_tracks[tid] = coasting.get(tid, (cx, cy))
        dets.append((cx, cy, -1, x1, y1, x2, y2, tid))

    bright_tracks = new_tracks
    bright_vels = new_vels
    return dets, mask, merge_vis

def process_frame_async():
    """Background thread for YOLO inference"""
    global frozen
    while not stop_processing.is_set():
        try:
            # Check for commands from GUI (e.g., grid toggle)
            cmd = server.get_command()
            if cmd:
                print(f"[sphero_spotter] Received command: {cmd}")
                if cmd.get("action") == "toggle_grid":
                    args.grid = not args.grid
                    print(f"[sphero_spotter] Grid toggled to: {args.grid}")
                    if args.debug:
                        print(f"Grid toggled: {args.grid}")
                elif cmd.get("action") == "set_tuning":
                    # Live slider moves from the GUI; picked up on the next frame
                    applied = apply_tuning(cmd.get("values"))
                    print(f"[sphero_spotter] Tuning updated: {applied}")
            
            # Get latest frame (non-blocking, skip stale frames)
            try:
                frame_data = frame_queue.get(timeout=0.1)
                frame, frame_timestamp = frame_data
            except Empty:
                continue
            
            # Skip if queue has newer frames (drop stale frames)
            while not frame_queue.empty():
                try:
                    frame_data = frame_queue.get_nowait()
                    frame, frame_timestamp = frame_data
                except Empty:
                    break
            
            # Process April tags
            frame = process_apriltags(frame)
            
            dets = []  # (cx, cy, cls_id, x1, y1, x2, y2, tracker_id)

            mask_view = None

            if args.brightness:
                # Brightness thresholding instead of YOLO
                dets, bright_mask, merge_vis = detect_bright_blobs(frame)
                if show_mask_view():
                    # Colour copy of the mask with every accepted blob outlined,
                    # so the sliders show what each setting is actually keeping.
                    mask_view = cv2.cvtColor(bright_mask, cv2.COLOR_GRAY2BGR)
                    for (bcx, bcy, _bc, bx1, by1, bx2, by2, _bt) in dets:
                        cv2.rectangle(mask_view, (int(bx1), int(by1)), (int(bx2), int(by2)),
                                      (0, 255, 0), 1)
                        cv2.circle(mask_view, (int(bcx), int(bcy)), 3, (0, 0, 255), -1)
                    draw_merge_overlay(mask_view, merge_vis)
                    cv2.putText(mask_view,
                                f"thresh={tune.BRIGHT_THRESH} min_area={int(tune.BRIGHT_MIN_AREA)}"
                                f" blur={tune.BRIGHT_BLUR} blobs={len(dets)}",
                                (8, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1,
                                cv2.LINE_AA)
            else:
                # Run YOLOv8 tracking with optimized settings
                results = model.track(
                    frame, 
                    tracker="botsort.yaml", 
                    persist=True, 
                    verbose=False,
                    imgsz=args.imgsz,
                    conf=args.conf,
                    device=device
                )

                # Process results
                if results and results[0].boxes is not None:
                    for b in results[0].boxes:
                        if b.id is None:
                            continue
                        tid = int(b.id.item())
                        x1, y1, x2, y2 = map(float, b.xyxy[0])
                        cx = 0.5 * (x1 + x2)
                        cy = 0.5 * (y1 + y2)
                        cls_id = int(b.cls[0])
                        dets.append((cx, cy, cls_id, x1, y1, x2, y2, tid))
            

            global next_display_id, lost_spheros

            if not frozen and dets:
                # First frame: assign IDs sorted by position for deterministic ordering
                for (cx, cy, cls_id, x1, y1, x2, y2, tid) in sorted(dets, key=lambda t: (t[0], t[1])):
                    if tid not in id_map and next_display_id < N_SPHEROS:
                        id_map[tid] = next_display_id
                        next_display_id += 1
                frozen = True

            # Assign IDs to new tracker IDs: prefer recovering a lost sphero by
            # nearest distance, then create a fresh ID if under cap and not locked.
            for (cx, cy, cls_id, x1, y1, x2, y2, tid) in dets:
                if tid not in id_map:
                    if lost_spheros:
                        nearest = min(
                            lost_spheros,
                            key=lambda did: (cx - lost_spheros[did][0])**2 + (cy - lost_spheros[did][1])**2
                        )
                        id_map[tid] = nearest
                        del lost_spheros[nearest]
                    elif ASSIGN_NEW_IDS_AFTER_FIRST_FRAME and next_display_id < N_SPHEROS:
                        id_map[tid] = next_display_id
                        next_display_id += 1

            # Update spheros dictionary and draw detections on frame
            detected_disp_ids = set()
            for (cx, cy, cls_id, x1, y1, x2, y2, tid) in dets:
                if tid not in id_map:
                    continue
                disp_id = id_map[tid]
                detected_disp_ids.add(disp_id)
                spheros[disp_id] = SpheroCoordinate(disp_id, int(cx), int(cy))
                lost_spheros.pop(disp_id, None)

                class_name = class_name_for(cls_id)
                cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                cv2.circle(frame, (int(cx), int(cy)), 3, (0, 255, 0), -1)
                label = f"{disp_id} {class_name} | Center: ({int(cx)}, {int(cy)})"
                cv2.putText(frame, label, (int(x1), int(y1) - 6),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2, cv2.LINE_AA)
                if args.debug:
                    print(f"ID {disp_id} | {class_name} | Center: ({int(cx)}, {int(cy)})")

            # Record last known position of any sphero not seen this frame
            for disp_id, coord in spheros.items():
                if disp_id not in detected_disp_ids and disp_id not in lost_spheros:
                    lost_spheros[disp_id] = (coord.x_coordinate, coord.y_coordinate)
            
            # Push telemetry to GUI via server
            if args.server:
                status_spheros = []
                for (cx, cy, cls_id, x1, y1, x2, y2, tid) in dets:
                    if tid in id_map:
                        disp_id = id_map[tid]
                        gx, gy = pixel_to_grid_coords(cx, cy)
                        status_spheros.append({
                            "id": disp_id,
                            "px": int(cx), "py": int(cy),
                            "gx": round(gx, 2), "gy": round(gy, 2),
                        })
                server.feed_status({
                    "type": "status",
                    "ts": time.time(),
                    "input_source": _input_source,
                    "device": device,
                    "model": "color filter" if args.brightness else os.path.basename(args.model),
                    "id_mode": "locked" if args.locked else "dynamic",
                    "apriltag_count": last_apriltag_count,
                    "perspective_calibrated": last_warp_matrix is not None,
                    "zmq_bound": zmq_bound,
                    "spheros": status_spheros,
                    "latency": last_latency,
                    # Lets the GUI show what the filter is actually running with
                    "tuning": {k: getattr(tune, k) for k in PERCEPTION_DEFAULTS},
                    "mask_streaming": mask_view is not None,
                })

            # Put result in queue (replace if queue is full)
            result_data = (frame, dets, frame_timestamp, mask_view)
            if result_queue.full():
                try:
                    result_queue.get_nowait()
                except Empty:
                    pass
            result_queue.put(result_data)
            
        except Exception as e:
            import traceback
            print(f"Error in processing thread: {e}")
            traceback.print_exc()

# --- Display: main view, filtered (mask) view, and the tuning sliders --------
MAIN_WINDOW = "Sphero IDs"
MASK_WINDOW = "Sphero Filter (brightness mask)"
last_valid_mask = None
_mask_window_ready = False

def show_mask_view():
    """True when the filtered view should be produced and displayed.

    Under --server there is no local window: the mask goes out on its own
    stream, and it is only worth drawing while the GUI has that view open.
    """
    if not args.brightness or args.hide_mask:
        return False
    if args.server:
        return server.mask_view_wanted()
    return not args.nogui

def _set_thresh(v):
    tune.BRIGHT_THRESH = int(v)

def _set_min_area(v):
    tune.BRIGHT_MIN_AREA = float(v)

def _set_blur(v):
    tune.BRIGHT_BLUR = int(v)

def _set_match_dist(v):
    tune.BRIGHT_MATCH_DIST = float(max(v, 1))

def _set_merge_ratio(v):
    tune.MERGE_AREA_RATIO = max(v, 10) / 10.0   # slider is in tenths

def _set_merge_peak_sep(v):
    tune.MERGE_PEAK_SEP = int(max(v, 1))

def ensure_mask_window():
    """Create the mask window and its sliders once, on the display thread."""
    global _mask_window_ready
    if _mask_window_ready:
        return
    cv2.namedWindow(MASK_WINDOW, cv2.WINDOW_NORMAL)
    # Sliders write straight into args, which the worker thread re-reads each frame
    cv2.createTrackbar("Brightness cutoff", MASK_WINDOW, int(tune.BRIGHT_THRESH), 255, _set_thresh)
    cv2.createTrackbar("Min blob area", MASK_WINDOW, int(tune.BRIGHT_MIN_AREA), 2000, _set_min_area)
    cv2.createTrackbar("Blur kernel", MASK_WINDOW, int(tune.BRIGHT_BLUR), 31, _set_blur)
    cv2.createTrackbar("Track match dist", MASK_WINDOW, int(tune.BRIGHT_MATCH_DIST), 300, _set_match_dist)
    cv2.createTrackbar("Merge area ratio x10", MASK_WINDOW, int(tune.MERGE_AREA_RATIO * 10), 30, _set_merge_ratio)
    cv2.createTrackbar("Min peak separation", MASK_WINDOW, int(tune.MERGE_PEAK_SEP), 40, _set_merge_peak_sep)
    _mask_window_ready = True

def display_frames(frame, mask_view, timestamp):
    """Show/stream the camera view, plus the filtered view in brightness mode."""
    if args.nogui:
        return

    if args.server:
        # The GUI has a stream per view: camera on 6767, filter mask on 6771
        server.feed_frames_from_calculateFrame(frame, timestamp)
        if mask_view is not None:
            server.feed_mask_frame(mask_view, timestamp)
        return

    cv2.imshow(MAIN_WINDOW, frame)
    if show_mask_view() and mask_view is not None:
        ensure_mask_window()
        cv2.imshow(MASK_WINDOW, mask_view)

    key = cv2.waitKey(1) & 0xFF
    if key == 27:  # ESC
        raise SystemExit("Key input clicks")
    if cv2.getWindowProperty(MAIN_WINDOW, cv2.WND_PROP_VISIBLE) < 1:
        raise SystemExit("Window closed")

def calculateFrame(frame, frame_timestamp=None):
    """Main frame processing function - now uses async processing"""
    global last_valid_frame, last_valid_mask

    if not show_mask_view():
        # Filter view was turned off (or the GUI closed it): drop the last one
        # so a stale mask can't be re-sent while waiting on the next result.
        last_valid_mask = None

    # Add frame to processing queue (drop if queue is full = we're behind)
    frame_data = (frame.copy(), frame_timestamp if frame_timestamp else time.time())
    if frame_queue.full():
        try:
            frame_queue.get_nowait()  # Remove oldest frame
        except Empty:
            pass
    try:
        frame_queue.put_nowait(frame_data)
    except:
        pass  # Queue full, skip this frame

    # Try to get latest result (non-blocking)
    try:
        result_frame, dets, result_timestamp, mask_view = result_queue.get_nowait()
        last_valid_frame = result_frame  # Store the last valid processed frame
        if mask_view is not None:
            last_valid_mask = mask_view
        display_frames(result_frame, mask_view, result_timestamp)
    except Empty:
        # No YOLO result yet — stream the raw frame so the GUI shows the feed immediately
        display = last_valid_frame if last_valid_frame is not None else frame
        display_frames(display, last_valid_mask, frame_timestamp)

if __name__ == '__main__':

    _input_source = "webcam" if args.webcam else ("video" if args.video else "oakd")

    if args.webcam:
        stream = WebcamStream(args.webcam)
    elif args.video:
        stream = VideoFileStream(args.video)
    else:
        stream = None

    # start the listening thread
    listener_thread = threading.Thread(target=listener, daemon=True)
    listener_thread.start()

    # Start async processing thread
    processing_thread = threading.Thread(target=process_frame_async, daemon=True)
    processing_thread.start()

    pipeline_latency_ms = 0
    processing_start_time = 0
    
    try:
        if stream is not None:
            while True:
                frame = stream.read()
                if frame is None:
                    continue
                calculateFrame(frame)
        else:
            import depthai as dai
            dai_device = dai.Device()
            with dai.Pipeline(dai_device) as pipeline:
                outputQueues = {}

                cam = pipeline.create(dai.node.Camera).build()
                rgb_output = cam.requestOutput((600, 500), type=dai.ImgFrame.Type.RGB888p)
                outputQueues["RGB"] = rgb_output.createOutputQueue()

                pipeline.start()

                while pipeline.isRunning():
                    queue = outputQueues["RGB"]
                    videoIn = queue.get()
                    assert isinstance(videoIn, dai.ImgFrame)

                    # --- LATENCY: Start Measurements (OAK-D) ---
                    capture_timestamp = None
                    if args.latency:
                        # 1. Get device capture timestamp (when the image was taken)
                        capture_timestamp = videoIn.getTimestamp()
                        
                        # 2. Get host time *now* (when frame arrived)
                        host_receive_time = dai.Clock.now() # type: ignore
                        
                        # 3. Calculate pipeline latency (device capture -> host receive)
                        pipeline_latency_ms = (host_receive_time - capture_timestamp).total_seconds() * 1000
                        
                        # 4. Start processing timer on host
                        processing_start_time = time.perf_counter()

                    frame = videoIn.getCvFrame()
                    calculateFrame(frame, capture_timestamp)

                    # --- LATENCY: Stop Measurements (OAK-D) ---
                    if args.latency and capture_timestamp:
                    # 5. End processing timer (this is just the time to queue the frame)
                        processing_end_time = time.perf_counter()
                        queue_time_ms = (processing_end_time - processing_start_time) * 1000

                        # 6. Get host time *after queuing*
                        host_queued_time = dai.Clock.now()
                        
                        # 7. Calculate total end-to-end latency (device capture -> host queued)
                        total_e2e_latency_ms = (host_queued_time - capture_timestamp).total_seconds() * 1000
                    
                        # --- Print diagnostics ---
                        print(f"Pipeline Latency: {pipeline_latency_ms:.2f} ms | Queue Time: {queue_time_ms:.2f} ms | Total E2E Latency (to queue): {total_e2e_latency_ms:.2f} ms")
                        last_latency = {
                            "pipeline_ms": round(pipeline_latency_ms, 2),
                            "queue_ms": round(queue_time_ms, 2),
                            "e2e_ms": round(total_e2e_latency_ms, 2),
                        }


    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Stop processing thread
        stop_processing.set()
        if processing_thread is not None:
            processing_thread.join(timeout=2.0)
        
        if stream is not None:
            stream.release()
        cv2.destroyAllWindows()
        
        listener_thread.join(timeout=2.0)
        
        print("Shutdown complete")