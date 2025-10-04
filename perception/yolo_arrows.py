from ultralytics import YOLO
import cv2
from math import atan2, hypot, cos, sin

# Load YOLOv8 model
model = YOLO("bestv2.pt")

vid_source = input("Video Source: ")
if vid_source == "0":
    vid_source = 0

# --- CONFIG ---
ASSIGN_NEW_IDS_AFTER_FIRST_FRAME = False  # set True if you want to label newcomers too

# Arrow display configuration
ARROW_SCALE = 30.0      # pixels per unit of measured motion (tweak as desired)
MIN_ARROW_LEN = 8       # minimum arrow length in pixels for visibility
ARROW_COLOR = (0, 0, 255)  # BGR color for arrow (red)
ARROW_THICKNESS = 2
ARROW_TIP_LENGTH = 0.25  # relative size of the arrow tip

# tracker state
id_map = {}            # tracker_id -> frozen display_id (1..N from first frame)
frozen = False         # whether we've frozen the initial mapping
next_display_id = 1    # next label to hand out (if allowing newcomers)
initial_n = 0          # how many IDs were frozen on the first frame

# dets will be a list of detection records: [cx, cy, cls_id, x1, y1, x2, y2, tid, dx, dy]
detsprev = {}  # mapping tid -> (cx, cy) from previous frame

for result in model.track(source=vid_source, tracker="botsort.yaml", show=False, stream=True):
    frame = result.orig_img.copy()

    # No detections this frame
    if result.boxes is None or len(result.boxes) == 0:
        cv2.imshow("Sphero IDs (frozen from first frame)", frame)
        if cv2.waitKey(1) == 27:
            break
        continue

    # Gather dets with tracker IDs
    dets = []
    for b in result.boxes:
        if b.id is None:
            continue  # we rely on tracker IDs
        tid = int(b.id.item())
        x1, y1, x2, y2 = map(float, b.xyxy[0])
        cx = 0.5 * (x1 + x2)
        cy = 0.5 * (y1 + y2)
        cls_id = int(b.cls[0])
        # compute delta from previous frame for this tracker id (if available)
        prev = detsprev.get(tid, (cx, cy))
        dx = cx - prev[0]
        dy = cy - prev[1]
        dets.append([cx, cy, cls_id, x1, y1, x2, y2, tid, dx, dy])

    # If first usable frame: freeze mapping by spatial order (L→R, then T→B)
    if not frozen and dets:
        dets_sorted = sorted(dets, key=lambda t: (t[0], t[1]))  # sort by cx then cy
        for det in dets_sorted:
            cx, cy, cls_id, x1, y1, x2, y2, tid = det[:8]
            if tid not in id_map:
                id_map[tid] = next_display_id
                next_display_id += 1
        initial_n = len(id_map)
        frozen = True
        # Optionally print what was frozen
        print(f"Frozen {initial_n} initial IDs (L\u2192R, T\u2192B):", id_map)

    # Draw all tracked objects, but only show IDs for the frozen set (or also for newcomers if allowed)
    for (cx, cy, cls_id, x1, y1, x2, y2, tid, dx, dy) in dets:
        # Assign ID if known
        if tid in id_map:
            disp_id = id_map[tid]
        else:
            if ASSIGN_NEW_IDS_AFTER_FIRST_FRAME:
                id_map[tid] = next_display_id
                disp_id = next_display_id
                next_display_id += 1
            else:
                # Skip labeling newcomers; still draw box if you want
                disp_id = None

        class_name = model.names[cls_id]
        # Draw bounding box and center
        cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
        cv2.circle(frame, (int(cx), int(cy)), 3, (0, 255, 0), -1)

        # Draw arrow indicating velocity direction (angle) and magnitude (scaled)
        # angle from atan2(dy, dx); note image y axis points downwards which matches dy computation
        angle = atan2(dy, dx)
        mag = hypot(dx, dy)
        # scale measured motion to pixels for display
        arrow_len = mag * ARROW_SCALE
        if arrow_len < MIN_ARROW_LEN:
            arrow_len = MIN_ARROW_LEN
        end_x = int(cx + arrow_len * cos(angle))
        end_y = int(cy + arrow_len * sin(angle))
        # draw arrowed line from center to end point
        cv2.arrowedLine(frame, (int(cx), int(cy)), (end_x, end_y), ARROW_COLOR, ARROW_THICKNESS, tipLength=ARROW_TIP_LENGTH)
        if disp_id is not None:
            label = f"{disp_id} {class_name}"
            cv2.putText(frame, label, (int(x1), int(y1) - 6),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2, cv2.LINE_AA)
            print(f"ID {disp_id} | {class_name} | Center: ({int(cx)}, {int(cy)}) | Velocity: ({atan2(dy, dx):.2}, {hypot(dx, dy):.2})")

    cv2.imshow("Sphero IDs (frozen from first frame)", frame)
    if cv2.waitKey(1) == 27:
        break

    # update detsprev mapping for next frame
    detsprev = {int(det[7]): (det[0], det[1]) for det in dets}

cv2.destroyAllWindows()
