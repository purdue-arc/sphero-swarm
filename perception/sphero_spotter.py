import os
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

import threading                
import zmq                      # for socket to connect to algs
import depthai as dai           # for camera connection
from queue import Queue, Empty
from collections import deque

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

parser = argparse.ArgumentParser(description="Sphero Spotter")
parser.add_argument('--nogui', '-n', action='store_true', help="Run the Sphero Spotter without opening any GUI windows.")
parser.add_argument('--locked', '-l', action='store_true', help="Freeze the initial Sphero ID assignments. No new IDs will be assigned after the first frame.")
parser.add_argument('--model', '-m', type=str, default="./models/TopDownModel.pt", help="Path to the YOLO model file to use for object detection (default: %(default)s).")
parser.add_argument('--debug', '-d', action='store_true', help="Activates debug mode (aka prints out all the spheres)")
parser.add_argument('--latency', '-t', action='store_true', help="Prints the latency in the camera as well as processing time")
parser.add_argument('--imgsz', type=int, default=640, help="YOLO inference image size (smaller = faster, default: 640)")
parser.add_argument('--conf', type=float, default=0.25, help="YOLO confidence threshold (default: 0.25)")
parser.add_argument('--device', type=str, default=None, help="Device for YOLO inference (cuda, mps, cpu, or None for auto)")

group = parser.add_mutually_exclusive_group()
group.add_argument('--video', '-v', type=str, help="Use provided video path as input stream")
group.add_argument('--webcam', '-w', action='store_true', help="Use webcam as input stream")
group.add_argument('--grid', '-g', action='store_true', help="Shows the grid overlay")

args = parser.parse_args()

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
    global april_tag_frame_counter, last_warped_frame, last_warp_matrix
    
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
            return frame
    
    # Process April tags (full detection)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    results = detector.detect(gray)
    tag_points = {}

    for r in results:
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
    return warped if warped is not None else frame

def initialize_spheros():
    '''
    TODO @anthony
    initializes global sphero object array.
    Returns number of spheros found.
    '''
    n_found = 0
    return n_found

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
    # connect to the socket
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind("tcp://*:5555")
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
model = YOLO(args.model)

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

current_id = 0

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

def process_frame_async():
    """Background thread for YOLO inference"""
    global frozen
    while not stop_processing.is_set():
        try:
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
            dets = []  # (cx, cy, cls_id, x1, y1, x2, y2, tracker_id)
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
            

            if not frozen and dets:
                dets_sorted = sorted(dets, key=lambda t: (t[0], t[1]))
                for (cx, cy, cls_id, x1, y1, x2, y2, tid) in dets_sorted:
                    if tid not in id_map:
                        id_map[tid] = len(id_map)
                frozen = True

            # Update spheros dictionary and draw detections on frame
            for (cx, cy, cls_id, x1, y1, x2, y2, tid) in dets:
                if tid in id_map:
                    disp_id = id_map[tid]
                else:
                    if ASSIGN_NEW_IDS_AFTER_FIRST_FRAME:
                        id_map[tid] = len(id_map)
                        disp_id = len(id_map)
                    else:
                        disp_id = None

                if disp_id is not None:
                    spheros[disp_id] = SpheroCoordinate(disp_id, int(cx), int(cy))
                    
                    # Draw detection boxes and labels on frame
                    class_name = model.names[cls_id]
                    cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                    cv2.circle(frame, (int(cx), int(cy)), 3, (0, 255, 0), -1)
                    label = f"{disp_id} {class_name} | Center: ({int(cx)}, {int(cy)})"
                    cv2.putText(frame, label, (int(x1), int(y1) - 6),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2, cv2.LINE_AA)
                    if args.debug:
                        print(f"ID {disp_id} | {class_name} | Center: ({int(cx)}, {int(cy)})")
            
            # Put result in queue (replace if queue is full)
            result_data = (frame, dets, frame_timestamp)
            if result_queue.full():
                try:
                    result_queue.get_nowait()
                except Empty:
                    pass
            result_queue.put(result_data)
            
        except Exception as e:
            if args.debug:
                print(f"Error in processing thread: {e}")

def calculateFrame(frame, frame_timestamp=None):
    """Main frame processing function - now uses async processing"""
    global last_valid_frame
    
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
        result_frame, dets, result_timestamp = result_queue.get_nowait()
        last_valid_frame = result_frame  # Store the last valid processed frame
        
        # Display frame
        if not args.nogui:
            cv2.imshow("Sphero IDs", result_frame)
            key = cv2.waitKey(1) & 0xFF
            if key == 27:  # ESC
                raise SystemExit("Key input clicks")
            if cv2.getWindowProperty("Sphero IDs", cv2.WND_PROP_VISIBLE) < 1:
                raise SystemExit("Window closed")
    except Empty:
        # No result yet, show last valid frame if available
        if not args.nogui and last_valid_frame is not None:
            cv2.imshow("Sphero IDs", last_valid_frame)
            key = cv2.waitKey(1) & 0xFF
            if key == 27:  # ESC
                raise SystemExit("Key input clicks")
            if cv2.getWindowProperty("Sphero IDs", cv2.WND_PROP_VISIBLE) < 1:
                raise SystemExit("Window closed")

if __name__ == '__main__':

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
    
    try:
        if stream is not None:
            while True:
                frame = stream.read()
                if frame is None:
                    continue
                calculateFrame(frame)
        else:
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
                        host_receive_time = dai.Clock.now()
                        
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