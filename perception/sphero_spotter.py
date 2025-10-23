import os
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

import threading                
import zmq                      # for socket to connect to algs
import depthai as dai           # for camera connection

from ultralytics import YOLO    # computer vision imports
import cv2
import argparse
import json

from SpheroCoordinate import SpheroCoordinate
from input_streams import WebcamStream, VideoFileStream

parser = argparse.ArgumentParser(description="Sphero Spotter")
parser.add_argument('--nogui', '-n', action='store_true', help="Run the Sphero Spotter without opening any GUI windows.")
parser.add_argument('--locked', '-l', action='store_true', help="Freeze the initial Sphero ID assignments. No new IDs will be assigned after the first frame.")
parser.add_argument('--model', '-m', type=str, default="./models/bestv2.pt", help="Path to the YOLO model file to use for object detection (default: %(default)s).")
parser.add_argument('--debug', '-d', action='store_true', help="Activates debug mode (aka prints out all the spheres)")

group = parser.add_mutually_exclusive_group()
group.add_argument('--video', '-v', type=str, help="Use provided video path as input stream")
group.add_argument('--webcam', '-w', action='store_true', help="Use webcam as input stream")

args = parser.parse_args()

# CONSTANTS
GRID_DIM_X = 12 # TODO actually like make these real. right now they are all made up 
GRID_DIM_Y = 10
frame_dim_x = 1080
frame_dim_y = 1440

# Global array of SpheroCoordinates
spheros = {}

def format_sphero_json(spheroCoord):
    x,y = pixel_to_grid_coords(spheroCoord.x_coordinate, spheroCoord.y_coordinate)
    return {"ID": spheroCoord.ID, "X": x, "Y": y}

def pixel_to_grid_coords(pixel_x, pixel_y):
    '''
    TODO 
    @Prithika - create function that takes pixel coords and spits out grid coords based off of our grid size.
    '''
    pass
    return (pixel_x, pixel_y)
# 

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
    'coords'                | json of {sphero IDs, x, y}
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
current_id = 0

def calculateFrame(frame):
    global frozen
    # Run YOLOv8 tracking
    results = model.track(frame, tracker="botsort.yaml", persist=True, verbose=False)

    if not results or results[0].boxes is None or len(results[0].boxes) == 0:
        if not args.nogui:
            cv2.imshow("Sphero IDs", frame)
            if cv2.waitKey(1) == 27:  # ESC to quit
                raise SystemExit("Key input clicks")
            if cv2.getWindowProperty("Sphero IDs", cv2.WND_PROP_VISIBLE) < 1:
                raise SystemExit("Window closed")

    dets = []  # (cx, cy, cls_id, x1, y1, x2, y2, tracker_id)
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
                spheros[tid] = len(id_map)
        frozen = True

    # Draw all tracked objects
    for (cx, cy, cls_id, x1, y1, x2, y2, tid) in dets:
        if tid in id_map:
            disp_id = id_map[tid]
        else:
            if ASSIGN_NEW_IDS_AFTER_FIRST_FRAME:
                id_map[tid] = len(id_map)
                disp_id = len(id_map)
            else:
                disp_id = None

        class_name = model.names[cls_id]
        cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
        cv2.circle(frame, (int(cx), int(cy)), 3, (0, 255, 0), -1)
        if disp_id is not None:
            spheros[disp_id] = SpheroCoordinate(disp_id, int(cx), int(cy))
            label = f"{disp_id} {class_name} | Center: ({int(cx)}, {int(cy)})"
            cv2.putText(frame, label, (int(x1), int(y1) - 6),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2, cv2.LINE_AA)
            if args.debug:
                print(f"ID {disp_id} | {class_name} | Center: ({int(cx)}, {int(cy)})")

    if not args.nogui:
        cv2.imshow("Sphero IDs", frame)
        key = cv2.waitKey(1)
        if key == 27:  # ESC
            raise SystemExit("Key input clicks")
        # Check if window was closed with X button
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
    thread = threading.Thread(target=listener, daemon=True)
    thread.start()

    # TODO start the camera feed, object tracking and updating, all that stuff

    try:
        if stream is not None:
            while True:
                frame = stream.read()
                if frame is None:
                    continue

                calculateFrame(frame)
        else:
            device = dai.Device()
            with dai.Pipeline(device) as pipeline:
                outputQueues = {}

                cam = pipeline.create(dai.node.Camera).build()
                rgb_output = cam.requestOutput((1920, 1080), type=dai.ImgFrame.Type.RGB888p)
                outputQueues["RGB"] = rgb_output.createOutputQueue()

                pipeline.start()

                while pipeline.isRunning():
                    queue = outputQueues["RGB"]
                    videoIn = queue.get()
                    assert isinstance(videoIn, dai.ImgFrame)
                    frame = videoIn.getCvFrame()
                    calculateFrame(frame)

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