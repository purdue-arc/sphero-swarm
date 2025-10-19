import threading                
import zmq                      # for socket to connect to algs
import depthai as dai           # for camera connection

from ultralytics import YOLO    # computer vision imports
import cv2

from SpheroCoordinate import SpheroCoordinate

# CONSTANTS
GRID_DIM_X = 12 # TODO actually like make these real. right now they are all made up 
GRID_DIM_Y = 10
frame_dim_x = 1080
frame_dim_y = 1440

# Global array of SpheroCoordinates
spheros = []

def pixel_to_grid_coords(pixel_x, pixel_y):
    '''
    TODO 
    @Prithika - create function that takes pixel coords and spits out grid coords based off of our grid size.
    '''
    pass
    return None
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
            socket.send_string(f"{num_found}")

        elif msg == 'coords':
            #reply = pickle.dump(get_sphero_coords())    # byte dump list of spheros. Algorithms gets to unpack it
            #reply = pickle.dump('hi')
            #socket.send(reply)                   # send bytedump of sphero coord objects back
            socket.send_string('[pickled SpheroCoordinate objects]')
            print('sphero_spotter: sending coords')

        elif msg == 'exit':
            break

        else:
            socket.send_string("error - command doesn\'t match one of ['init', 'coords', 'exit']")
    print('listener stopped')




if __name__ == '__main__':

    # start the listening thread
    thread = threading.Thread(target=listener, daemon=False) # start a listening thread
    # we do daemon=False because if the listener is shut down then we want the 
    # spotter to close.
    thread.start()

    # TODO start the camera feed, object tracking and updating, all that stuff
    model = YOLO("./model/bestv2.pt")

    # --- CONFIG ---
    ASSIGN_NEW_IDS_AFTER_FIRST_FRAME = True  # set True if you want to label newcomers too

    id_map = {}            # tracker_id -> frozen display_id (1..N from first frame)
    frozen = False         # whether we've frozen the initial mapping
    next_display_id = 1    # next label to hand out (if allowing newcomers)
    initial_n = 0          # how many IDs were frozen on the first frame

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

            # Run YOLOv8 tracking (same as `model.track(source=..., stream=True)`)
            results = model.track(frame, tracker="botsort.yaml", persist=True, verbose=False)

            if not results or results[0].boxes is None or len(results[0].boxes) == 0:
                cv2.imshow("Sphero IDs (frozen from first frame)", frame)
                if cv2.waitKey(1) == 27:  # ESC to quit
                    break
                continue

            dets = []  # (cx, cy, cls_id, x1, y1, x2, y2, tracker_id)
            for b in results[0].boxes:
                if b.id is None:
                    continue  # rely only on tracker IDs
                tid = int(b.id.item())
                x1, y1, x2, y2 = map(float, b.xyxy[0])
                cx = 0.5 * (x1 + x2)
                cy = 0.5 * (y1 + y2)
                cls_id = int(b.cls[0])
                dets.append((cx, cy, cls_id, x1, y1, x2, y2, tid))

            # Freeze ID mapping on first frame
            if not frozen and dets:
                dets_sorted = sorted(dets, key=lambda t: (t[0], t[1]))  # sort by cx then cy
                for (cx, cy, cls_id, x1, y1, x2, y2, tid) in dets_sorted:
                    if tid not in id_map:
                        id_map[tid] = next_display_id
                        next_display_id += 1
                initial_n = len(id_map)
                frozen = True
                print(f"Frozen {initial_n} initial IDs (L→R, T→B):", id_map)

            # Draw all tracked objects
            for (cx, cy, cls_id, x1, y1, x2, y2, tid) in dets:
                if tid in id_map:
                    disp_id = id_map[tid]
                else:
                    if ASSIGN_NEW_IDS_AFTER_FIRST_FRAME:
                        id_map[tid] = next_display_id
                        disp_id = next_display_id
                        next_display_id += 1
                    else:
                        disp_id = None

                class_name = model.names[cls_id]
                cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                cv2.circle(frame, (int(cx), int(cy)), 3, (0, 255, 0), -1)
                if disp_id is not None:
                    label = f"{disp_id} {class_name}"
                    cv2.putText(frame, label, (int(x1), int(y1) - 6),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2, cv2.LINE_AA)
                    print(f"ID {disp_id} | {class_name} | Center: ({int(cx)}, {int(cy)})")

            cv2.imshow("Sphero IDs (frozen from first frame)", frame)
            if cv2.waitKey(1) == 27:  # ESC
                 # send the "exit" command to the listener.
                context = zmq.Context()
                client = context.socket(zmq.REQ)
                client.connect("tcp://localhost:5555")
                client.send_string("exit")
                break

    thread.join()
    cv2.destroyAllWindows()
    print("ENDED")
