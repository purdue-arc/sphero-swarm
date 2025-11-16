import os
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

import threading
import zmq                      # for socket to connect to algs
import depthai as dai           # for camera connection
import cv2
import argparse
import json
from pupil_apriltags import Detector # for april tag detection
import numpy as np
import time
from SpheroCoordinate import SpheroCoordinate
from input_streams import WebcamStream, VideoFileStream

# -------------------------------
# ARG PARSER
# -------------------------------
parser = argparse.ArgumentParser(description="Sphero Spotter (OAK-D blob YOLO)")
parser.add_argument('--nogui', '-n', action='store_true', help="Run the Sphero Spotter without opening any GUI windows.")
parser.add_argument('--locked', '-l', action='store_true', help="Freeze the initial Sphero ID assignments. No new IDs will be assigned after the first frame.")
parser.add_argument('--debug', '-d', action='store_true', help="Activates debug mode (aka prints out all the spheres)")
parser.add_argument('--latency', '-t', action='store_true', help="Prints the latency in the camera as well as processing time")
parser.add_argument('--video', '-v', type=str, help="Use provided video path as input stream")
parser.add_argument('--webcam', '-w', action='store_true', help="Use webcam as input stream")
parser.add_argument('--grid', '-g', action='store_true', help="Shows the grid overlay")
parser.add_argument('--blob', type=str, default="TopDownModel_openvino.blob", help="Path to the OpenVINO .blob file (OAK-D)")
parser.add_argument('--conf', type=float, default=0.4, help="Confidence threshold for detections")
parser.add_argument('--max_dist', type=float, default=80.0, help="Max pixel distance to associate detection to existing track")

args = parser.parse_args()

detector = Detector()

# -------------------------------
# MODEL / BLOB CONFIG (adjust if needed)
# -------------------------------
BLOB_PATH = args.blob

# Typical YOLO anchors and strides (adjust to your exported model if necessary).
# If your blob is from a different variant, update these values accordingly.
NUM_CLASSES = 1
CLASS_NAMES = ["sphero"]  # adjust if your model has different class names

# YOLOv5-like anchors/strides (common defaults). Replace if your model uses different anchors.
ANCHORS = [10,13, 16,30, 33,23, 30,61, 62,45, 59,119, 116,90, 156,198, 373,326]
ANCHOR_MASKS = [[0,1,2], [3,4,5], [6,7,8]]
STRIDES = [8, 16, 32]  # typical strides
CONF_THRESHOLD = float(args.conf)
IOU_THRESHOLD = 0.5

# -------------------------------
# GRID / ARENA SETTINGS
# -------------------------------
GRID_DIM_X = 12
GRID_DIM_Y = 10
ARENA_WIDTH_INCH = 59
ARENA_HEIGHT_INCH = 49
ROLL_STRAIGHT_INCH = 12.67
GRID_WIDTH = GRID_HEIGHT = 7
arena_w_px = 500
arena_h_px = 500

# Global array of SpheroCoordinates
spheros = {}

# ID assignment / mapping
ASSIGN_NEW_IDS_AFTER_FIRST_FRAME = not args.locked
frozen = False
id_map = {}   # mapping from internal tracker id -> display id

# -------------------------------
# Utility functions
# -------------------------------
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

def process_apriltags(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    results = detector.detect(gray)
    tag_points = {}

    for r in results:
        corners = r.corners.astype(int)
        tag_id = r.tag_id
        cX, cY = int(r.center[0]), int(r.center[1])
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
        warped = cv2.warpPerspective(frame, M, (size, size))
        top_left = (0, 0)
        bottom_right = (warped.shape[1] - 1, warped.shape[0] - 1)

        grid = draw_grid(warped, top_left, bottom_right)
        return grid
    return warped if warped is not None else frame

# -------------------------------
# SIMPLE FAST TRACKER (greedy centroid matching)
# -------------------------------
class Track:
    def __init__(self, track_id, bbox, cls_id):
        # bbox: (x1,y1,x2,y2)
        self.track_id = track_id
        self.bbox = bbox
        self.cls_id = cls_id
        self.last_seen = time.time()
        self.hits = 1

    def center(self):
        x1,y1,x2,y2 = self.bbox
        return ((x1+x2)/2.0, (y1+y2)/2.0)

    def update(self, bbox):
        self.bbox = bbox
        self.last_seen = time.time()
        self.hits += 1

class SimpleTracker:
    def __init__(self, max_age=0.8, max_dist=args.max_dist):
        self.max_age = max_age            # seconds to keep a lost track
        self.max_dist = max_dist          # max pixel distance to match centers
        self.tracks = {}
        self.next_id = 0

    def _match_and_update(self, detections):
        # detections: list of (x1,y1,x2,y2,conf,cls_id)
        assigned = set()
        # Build lists
        det_centers = [((d[0]+d[2])/2.0, (d[1]+d[3])/2.0) for d in detections]
        track_items = list(self.tracks.items())  # (tid, Track)
        track_centers = [t.center() for _, t in track_items]

        # Greedy: for each detection find nearest track within max_dist
        for di, d in enumerate(detections):
            best_tid = None
            best_dist = None
            dcx, dcy = det_centers[di]
            for ti, (tid, track) in enumerate(track_items):
                if tid in assigned:
                    continue
                t_cx, t_cy = track_centers[ti]
                dist = np.hypot(t_cx - dcx, t_cy - dcy)
                if dist <= self.max_dist and (best_dist is None or dist < best_dist):
                    best_dist = dist
                    best_tid = tid

            if best_tid is not None:
                # update matched track
                x1,y1,x2,y2,conf,cls_id = d
                self.tracks[best_tid].update((x1,y1,x2,y2))
                assigned.add(best_tid)
            else:
                # create new track
                x1,y1,x2,y2,conf,cls_id = d
                t = Track(self.next_id, (x1,y1,x2,y2), cls_id)
                self.tracks[self.next_id] = t
                assigned.add(self.next_id)
                self.next_id += 1

        # Remove stale tracks
        now = time.time()
        to_delete = []
        for tid, track in self.tracks.items():
            if (now - track.last_seen) > self.max_age:
                to_delete.append(tid)

        for tid in to_delete:
            del self.tracks[tid]

    def update(self, detections):
        """
        Input:
            detections: list of (x1,y1,x2,y2,conf,cls_id)
        Output:
            list of (track_id, bbox, cls_id)
        """
        self._match_and_update(detections)
        out = []
        for tid, tr in self.tracks.items():
            out.append((tid, tr.bbox, tr.cls_id))
        return out

# initialize tracker
tracker = SimpleTracker(max_age=0.8, max_dist=args.max_dist)

# -------------------------------
# ZMQ listener thread (unchanged)
# -------------------------------
def initialize_spheros():
    # Optionally implement detection to seed spheros global at start.
    # For now returns current count
    return len(spheros)

def listener():
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind("tcp://*:5555")
    print('sphero_spotter: socket bind success')

    while True:
        print('sphero_spotter: listening...')
        msg = socket.recv_string()
        print(f"Received request '{msg}' from algorithms!")

        if msg == 'init':
            num_found = initialize_spheros()
            socket.send_string(f"connected - {num_found}")
        elif msg == 'coords':
            json_val = {"numSpheros":len(spheros), "spheros":[format_sphero_json(x) for x in spheros.values()]}
            socket.send_json(json_val)
        elif msg == 'exit':
            break
        else:
            socket.send_string("error - command doesn't match one of ['init', 'coords', 'exit']")
    print('listener stopped')

# -------------------------------
# Helper: convert DepthAI YoloDetection to pixel bbox
# -------------------------------
def dai_detection_to_bbox(d):
    # d is depthai.Detection
    # d.xmin, d.ymin, d.xmax, d.ymax are normalized (0..1) in some pipelines or already absolute depending on config.
    # In DepthAI YoloDetectionNetwork, values are relative to frame size; use detection.xmin etc.
    # We'll map them to pixel coords given frame width/height when using.
    return (d.xmin, d.ymin, d.xmax, d.ymax, d.confidence, int(d.label))

# -------------------------------
# Main frame processing (given Python detections)
# -------------------------------
def calculateFrame(frame, detections_list=None):
    """
    frame: BGR image
    detections_list: optional list of detections in pixel coords [(x1,y1,x2,y2,conf,cls), ...]
                     if None, we assume detections are already performed elsewhere (used for file/webcam pipeline)
    """
    global frozen, id_map, spheros

    # First process apriltags / perspective / grid
    frame_proc = process_apriltags(frame)

    dets = []
    if detections_list:
        # detections_list uses pixel coordinates already
        for (x1,y1,x2,y2,conf,cls_id) in detections_list:
            cx = 0.5*(x1+x2)
            cy = 0.5*(y1+y2)
            dets.append((x1,y1,x2,y2,conf,cls_id))

    # Update tracker (this returns list of current tracks)
    tracks = tracker.update(dets)

    # Assign stable display IDs (id_map maps track_id -> display_id)
    if not frozen and tracks:
        # Freeze assignment after the first frame if required
        # sort by center to produce deterministic ids
        sorted_tracks = sorted(tracks, key=lambda t: ((t[1][0]+t[1][2])/2.0, (t[1][1]+t[1][3])/2.0))
        for (tid, bbox, cls_id) in sorted_tracks:
            if tid not in id_map:
                id_map[tid] = len(id_map)
        frozen = True

    # Draw & update spheros dictionary
    for (tid, bbox, cls_id) in tracks:
        x1,y1,x2,y2 = map(int, bbox)
        cx = int(0.5*(x1+x2))
        cy = int(0.5*(y1+y2))

        if tid in id_map:
            disp_id = id_map[tid]
        else:
            if ASSIGN_NEW_IDS_AFTER_FIRST_FRAME:
                id_map[tid] = len(id_map)
                disp_id = id_map[tid]
            else:
                disp_id = None

        class_name = CLASS_NAMES[cls_id] if cls_id < len(CLASS_NAMES) else str(cls_id)

        # Save to global spheros by display id
        if disp_id is not None:
            spheros[disp_id] = SpheroCoordinate(disp_id, cx, cy)

        # Draw bounding box and label
        cv2.rectangle(frame_proc, (x1,y1), (x2,y2), (0,255,0), 2)
        label = f"{disp_id if disp_id is not None else '??'} {class_name} ({int(100*0):d}%)"  # confidence omitted here
        cv2.putText(frame_proc, label, (x1, max(10,y1-6)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2, cv2.LINE_AA)

        if args.debug:
            print(f"TRACK {tid} -> DISP {disp_id} | {class_name} | Center: ({cx},{cy})")

    if not args.nogui:
        cv2.imshow("Sphero IDs", frame_proc)
        key = cv2.waitKey(1)
        if key == 27:
            raise SystemExit("Key input clicks")
        if cv2.getWindowProperty("Sphero IDs", cv2.WND_PROP_VISIBLE) < 1:
            raise SystemExit("Window closed")

# -------------------------------
# Build DepthAI pipeline with YOLO blob on device
# -------------------------------
def build_oak_pipeline(blob_path, conf_threshold=CONF_THRESHOLD):
    pipeline = dai.Pipeline()

    # Color camera
    cam = pipeline.create(dai.node.ColorCamera)
    cam.setPreviewSize(640, 480)
    cam.setInterleaved(False)
    cam.setFps(30)

    # Yolo detection network node
    yolo = pipeline.create(dai.node.YoloDetectionNetwork)
    yolo.setBlobPath(blob_path)
    yolo.setConfidenceThreshold(conf_threshold)
    yolo.setNumClasses(NUM_CLASSES)
    yolo.setCoordinateSize(4)  # x,y,w,h
    yolo.setAnchors(ANCHORS)
    yolo.setAnchorMasks(ANCHOR_MASKS)
    yolo.setIouThreshold(IOU_THRESHOLD)
    yolo.setNumInferenceThreads(2)
    yolo.setBlobPath(blob_path)
    # set size to match how model expects input:
    # many YOLO blobs expect 640x640 or 320x320 etc.; set preview as required or change cam frame size
    yolo.input.setBlocking(False)

    # Link camera preview to yolo input
    cam.preview.link(yolo.input)

    # Outputs
    xout_rgb = pipeline.create(dai.node.XLinkOut)
    xout_det = pipeline.create(dai.node.XLinkOut)
    xout_rgb.setStreamName("rgb")
    xout_det.setStreamName("detections")

    yolo.passthrough.link(xout_rgb.input)
    yolo.out.link(xout_det.input)

    return pipeline

# -------------------------------
# Main run
# -------------------------------
if __name__ == '__main__':
    # start listener thread
    thread = threading.Thread(target=listener, daemon=True)
    thread.start()

    stream = None
    if args.webcam:
        stream = WebcamStream(args.webcam)
    elif args.video:
        stream = VideoFileStream(args.video)
    else:
        stream = None

    try:
        if stream is not None:
            # Use purely CPU-based detection or some other precomputed detections if provided.
            # Here, we assume detections_list is None and calculateFrame will be called with no detections.
            while True:
                frame = stream.read()
                if frame is None:
                    continue
                calculateFrame(frame)
        else:
            # Start OAK-D device pipeline
            if not os.path.exists(BLOB_PATH):
                raise FileNotFoundError(f"Blob not found at {BLOB_PATH}. Please provide a compatible YOLO blob.")

            pipeline = build_oak_pipeline(BLOB_PATH, conf_threshold=CONF_THRESHOLD)
            with dai.Device(pipeline) as device:
                rgb_queue = device.getOutputQueue(name="rgb", maxSize=4, blocking=False)
                det_queue = device.getOutputQueue(name="detections", maxSize=4, blocking=False)

                print("OAK-D pipeline started. Waiting for frames...")

                while True:
                    # get frames and detections
                    in_rgb = rgb_queue.tryGet()
                    in_det = det_queue.tryGet()

                    # LATENCY measurement
                    if args.latency and in_rgb is not None:
                        capture_timestamp = in_rgb.getTimestamp()
                        host_receive_time = dai.Clock.now()
                        pipeline_latency_ms = (host_receive_time - capture_timestamp).total_seconds() * 1000
                        processing_start_time = time.perf_counter()
                    else:
                        processing_start_time = None

                    if in_rgb is None:
                        # small sleep to avoid busy loop
                        time.sleep(0.001)
                        continue

                    frame = in_rgb.getCvFrame()

                    # Parse Detections from device
                    detections_list = []
                    if in_det is not None:
                        dets = in_det.detections
                        h,w = frame.shape[:2]
                        for d in dets:
                            # d.xmin etc are normalized floats (0..1) for yolo nodes
                            x1 = int(max(0, d.xmin * w))
                            y1 = int(max(0, d.ymin * h))
                            x2 = int(min(w, d.xmax * w))
                            y2 = int(min(h, d.ymax * h))
                            conf = float(d.confidence)
                            cls_id = int(d.label)
                            # Only keep if above threshold (device also filters, but double-check)
                            if conf >= CONF_THRESHOLD:
                                detections_list.append((x1,y1,x2,y2,conf,cls_id))

                    # Call frame processing with detections
                    calculateFrame(frame, detections_list=detections_list)

                    # LATENCY measurement end
                    if args.latency and processing_start_time is not None:
                        processing_end_time = time.perf_counter()
                        processing_time_ms = (processing_end_time - processing_start_time) * 1000
                        host_processed_time = dai.Clock.now()
                        total_e2e_latency_ms = (host_processed_time - capture_timestamp).total_seconds() * 1000
                        print(f"Pipeline Latency: {pipeline_latency_ms:.2f} ms | Processing Time: {processing_time_ms:.2f} ms | Total E2E Latency: {total_e2e_latency_ms:.2f} ms")

    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if stream is not None:
            stream.release()
        cv2.destroyAllWindows()
        thread.join(timeout=2.0)
        print("Shutdown complete")