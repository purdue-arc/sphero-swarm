# sphero_spotter_fast.py
import os
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

import threading
import zmq
import depthai as dai
from ultralytics import YOLO
import cv2
import argparse
import json
from pupil_apriltags import Detector
import numpy as np
import time
from queue import Queue, Full, Empty
from SpheroCoordinate import SpheroCoordinate
from input_streams import WebcamStream, VideoFileStream

parser = argparse.ArgumentParser(description="Sphero Spotter (fast)")
parser.add_argument('--nogui', '-n', action='store_true')
parser.add_argument('--locked', '-l', action='store_true')
parser.add_argument('--model', '-m', type=str, default="./models/bestv3.pt")
parser.add_argument('--debug', '-d', action='store_true')
parser.add_argument('--latency', '-t', action='store_true')

group = parser.add_mutually_exclusive_group()
group.add_argument('--video', '-v', type=str)
group.add_argument('--webcam', '-w', action='store_true')

args = parser.parse_args()

# Tunables
INFER_SIZE = 640            # run YOLO on this size (lower = faster)
APRILTAG_FREQ = 5          # run april tags every N frames (set to 1 to run every frame)
GUI_FPS = 10               # how often to update imshow (frames per second)
FRAME_QUEUE_MAX = 2        # small queue to avoid backlog; drops oldest frames when full

detector = Detector()

# Globals
spheros = {}
spheros_lock = threading.Lock()
id_map = {}
id_map_lock = threading.Lock()
ASSIGN_NEW_IDS_AFTER_FIRST_FRAME = not args.locked
frozen = False
frozen_lock = threading.Lock()
current_id = 0

# Helper functions
def pixel_to_grid_coords(pixel_x, pixel_y):
    # TODO map to GRID coords — placeholder passthrough
    return (pixel_x, pixel_y)

def format_sphero_json(spheroCoord):
    x, y = pixel_to_grid_coords(spheroCoord.x_coordinate, spheroCoord.y_coordinate)
    return {"ID": spheroCoord.ID, "X": x, "Y": y}

def process_apriltags(frame, downscale=2):
    """
    Run april tags on a smaller grayscale copy to save time.
    Returns (maybe warped frame) - but we avoid full-size warping if not needed.
    """
    # run on a downscaled gray image
    h, w = frame.shape[:2]
    small = cv2.resize(frame, (w // downscale, h // downscale), interpolation=cv2.INTER_LINEAR)
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    results = detector.detect(gray)
    tag_points = {}

    for r in results:
        # scale corners/center back up
        corners = (r.corners * downscale).astype(int)
        tag_id = r.tag_id
        cX, cY = int(r.center[0] * downscale), int(r.center[1] * downscale)

        # draw on the *original* frame (cheap)
        for j in range(4):
            cv2.line(frame, tuple(corners[j]), tuple(corners[(j + 1) % 4]), (0, 255, 0), 2)
        cv2.circle(frame, (cX, cY), 4, (0, 0, 255), -1)
        cv2.putText(frame, f"ID: {tag_id}", (cX - 20, cY - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
        tag_points[tag_id] = corners

    # optional perspective correction if 4 tags detected (we can still warp original frame if you want)
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
        return warped
    return frame

# Listener thread — unchanged except use spheros_lock when reading
def listener():
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind("tcp://*:5555")
    print('sphero_spotter: socket bind success')

    while True:
        try:
            msg = socket.recv_string()
        except Exception as e:
            print("Socket recv error:", e)
            break

        print(f"Received request '{msg}' from algorithms!")

        if msg == 'init':
            # send number found (acquire lock)
            with spheros_lock:
                num_found = len(spheros)
            socket.send_string(f"connected - {num_found}")

        elif msg == 'coords':
            with spheros_lock:
                json_val = {"numSpheros": len(spheros), "spheros": [format_sphero_json(x) for x in spheros.values()]}
            socket.send_json(json_val)

        elif msg == 'exit':
            socket.send_string("exiting")
            break
        else:
            socket.send_string("error - command doesn't match one of ['init', 'coords', 'exit']")
    print('listener stopped')

# Producer (capture) thread — pushes frames into queue
def capture_thread_fn(frame_queue, stop_event, stream):
    if stream is None:
        # OAK-D capture - keep pipeline open here and push frames into queue
        device = dai.Device()
        with dai.Pipeline(device) as pipeline:
            outputQueues = {}
            cam = pipeline.create(dai.node.Camera).build()
            rgb_output = cam.requestOutput((1920, 1080), type=dai.ImgFrame.Type.RGB888p)
            outputQueues["RGB"] = rgb_output.createOutputQueue()
            pipeline.start()
            while pipeline.isRunning() and not stop_event.is_set():
                queue = outputQueues["RGB"]
                videoIn = queue.get()
                frame = videoIn.getCvFrame()
                # drop oldest if full
                try:
                    frame_queue.put_nowait((frame, videoIn.getTimestamp()))
                except Full:
                    try:
                        _ = frame_queue.get_nowait()  # drop oldest
                        frame_queue.put_nowait((frame, videoIn.getTimestamp()))
                    except Exception:
                        pass
    else:
        # Use provided stream object (WebcamStream or VideoFileStream)
        while not stop_event.is_set():
            frame = stream.read()
            if frame is None:
                time.sleep(0.001)
                continue
            try:
                frame_queue.put_nowait((frame, None))
            except Full:
                # drop oldest
                try:
                    _ = frame_queue.get_nowait()
                    frame_queue.put_nowait((frame, None))
                except Exception:
                    pass

# Worker (inference + annot) thread
def worker_thread_fn(frame_queue, display_queue, stop_event, model, device_name):
    global frozen
    frame_count = 0
    last_display_time = 0.0
    while not stop_event.is_set():
        try:
            frame, timestamp = frame_queue.get(timeout=0.1)
        except Empty:
            continue

        frame_count += 1

        # optionally run april tags every APRILTAG_FREQ frames on downscaled frames
        if APRILTAG_FREQ <= 1 or (frame_count % APRILTAG_FREQ == 0):
            frame_for_tags = process_apriltags(frame, downscale=2)
        else:
            frame_for_tags = frame

        # Resize for inference (keep original dims for scaling)
        orig_h, orig_w = frame_for_tags.shape[:2]
        # YOLO expects square imgsz; we'll letterbox-resize manually
        resized = cv2.resize(frame_for_tags, (INFER_SIZE, INFER_SIZE), interpolation=cv2.INTER_LINEAR)

        # Run tracking/inference on the resized image; specify device and imgsz to speed things up
        # Note: ultralytics' .track() typically accepts these args; if your installed version differs adjust accordingly
        try:
            results = model.track(resized, tracker="botsort.yaml", persist=True, verbose=False, device=device_name, imgsz=INFER_SIZE)
        except TypeError:
            # fallback if API doesn't accept device/imgsz here
            results = model.track(resized, tracker="botsort.yaml", persist=True, verbose=False)

        # Results' boxes coordinates are in resized frame space; scale back to orig
        dets = []
        scale_x = orig_w / INFER_SIZE
        scale_y = orig_h / INFER_SIZE

        if results and results[0].boxes is not None and len(results[0].boxes) > 0:
            for b in results[0].boxes:
                if b.id is None:
                    continue
                tid = int(b.id.item())
                x1_r, y1_r, x2_r, y2_r = map(float, b.xyxy[0])
                x1 = x1_r * scale_x
                y1 = y1_r * scale_y
                x2 = x2_r * scale_x
                y2 = y2_r * scale_y
                cx = 0.5 * (x1 + x2)
                cy = 0.5 * (y1 + y2)
                cls_id = int(b.cls[0])
                dets.append((cx, cy, cls_id, x1, y1, x2, y2, tid))

        # ID assignment (first non-empty frame)
        if not frozen and dets:
            dets_sorted = sorted(dets, key=lambda t: (t[0], t[1]))
            with id_map_lock:
                for (cx, cy, cls_id, x1, y1, x2, y2, tid) in dets_sorted:
                    if tid not in id_map:
                        id_map[tid] = len(id_map)
            with frozen_lock:
                frozen = True

        # draw and update spheros
        for (cx, cy, cls_id, x1, y1, x2, y2, tid) in dets:
            with id_map_lock:
                if tid in id_map:
                    disp_id = id_map[tid]
                else:
                    if ASSIGN_NEW_IDS_AFTER_FIRST_FRAME:
                        id_map[tid] = len(id_map)
                        disp_id = id_map[tid]
                    else:
                        disp_id = None

            class_name = model.names.get(cls_id, str(cls_id)) if hasattr(model, 'names') else str(cls_id)
            # Draw on original-sized frame_for_tags
            cv2.rectangle(frame_for_tags, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
            cv2.circle(frame_for_tags, (int(cx), int(cy)), 3, (0, 255, 0), -1)
            if disp_id is not None:
                with spheros_lock:
                    spheros[disp_id] = SpheroCoordinate(disp_id, int(cx), int(cy))
                label = f"{disp_id} {class_name} | Center: ({int(cx)}, {int(cy)})"
                cv2.putText(frame_for_tags, label, (int(x1), int(y1) - 6),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2, cv2.LINE_AA)
                if args.debug:
                    print(f"ID {disp_id} | {class_name} | Center: ({int(cx)}, {int(cy)})")

        # Send to display queue but don't block (drop if too slow)
        try:
            display_queue.put_nowait(frame_for_tags)
        except Full:
            try:
                _ = display_queue.get_nowait()
                display_queue.put_nowait(frame_for_tags)
            except Exception:
                pass

        # latency diagnostics (if OAK timestamp available)
        if args.latency and timestamp is not None:
            host_now = dai.Clock.now()
            pipeline_latency_ms = (host_now - timestamp).total_seconds() * 1000
            # wall-clock processing time not measured here (could add timestamps)
            print(f"Pipeline latency (capture->host recv): {pipeline_latency_ms:.1f} ms")

# GUI thread: display frames at GUI_FPS and poll for keys
def gui_thread_fn(display_queue, stop_event):
    if args.nogui:
        return
    sleep_time = 1.0 / GUI_FPS
    while not stop_event.is_set():
        try:
            frame = display_queue.get(timeout=0.5)
        except Empty:
            continue
        cv2.imshow("Sphero IDs", frame)
        key = cv2.waitKey(1)
        if key == 27:
            stop_event.set()
            break
        # If user closed window:
        if cv2.getWindowProperty("Sphero IDs", cv2.WND_PROP_VISIBLE) < 1:
            stop_event.set()
            break
        time.sleep(sleep_time)
    # cleanup
    cv2.destroyAllWindows()

# Start everything
if __name__ == '__main__':
    # Choose device
    device_name = 'cuda' if (cv2.cuda.getCudaEnabledDeviceCount() > 0) else 'cpu'
    # fallback: if ultralytics uses torch.cuda, we can check torch too:
    try:
        import torch
        if torch.cuda.is_available():
            device_name = 'cuda'
    except Exception:
        pass

    print("Using device:", device_name)
    model = YOLO(args.model)
    # Move model to cuda if available; this can speed up subsequent calls
    try:
        model.to(device_name)
    except Exception:
        # ignore if API doesn't have .to
        pass

    # Prepare capture stream
    if args.webcam:
        stream = WebcamStream(args.webcam)
    elif args.video:
        stream = VideoFileStream(args.video)
    else:
        stream = None  # use OAK-D

    # Threading primitives
    frame_queue = Queue(maxsize=FRAME_QUEUE_MAX)
    display_queue = Queue(maxsize=FRAME_QUEUE_MAX)
    stop_event = threading.Event()

    # Start listener thread
    listener_thread = threading.Thread(target=listener, daemon=True)
    listener_thread.start()

    # Start capture thread
    capture_thread = threading.Thread(target=capture_thread_fn, args=(frame_queue, stop_event, stream), daemon=True)
    capture_thread.start()

    # Start worker (inference) thread
    worker_thread = threading.Thread(target=worker_thread_fn, args=(frame_queue, display_queue, stop_event, model, device_name), daemon=True)
    worker_thread.start()

    # Start GUI thread (not daemon so we can join if needed)
    gui_thread = threading.Thread(target=gui_thread_fn, args=(display_queue, stop_event), daemon=True)
    gui_thread.start()

    try:
        while not stop_event.is_set():
            time.sleep(0.2)
    except KeyboardInterrupt:
        stop_event.set()
    finally:
        stop_event.set()
        capture_thread.join(timeout=1.0)
        worker_thread.join(timeout=1.0)
        gui_thread.join(timeout=1.0)
        listener_thread.join(timeout=1.0)
        if stream is not None:
            stream.release()
        print("Shutdown complete")