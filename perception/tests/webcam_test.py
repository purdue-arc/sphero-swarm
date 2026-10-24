import cv2
import numpy as np
import math

# =============================
# Camera
# =============================
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_AUTO_WB, 0)
cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
cap.set(cv2.CAP_PROP_EXPOSURE, -6)

# =============================
# Windows
# =============================
cv2.namedWindow("Color Only View")
cv2.namedWindow("HSV Tuning")

# =============================
# HSV sliders (tune live)
# =============================
def nothing(x): pass

cv2.createTrackbar("H min", "HSV Tuning", 0, 180, nothing)
cv2.createTrackbar("H max", "HSV Tuning", 180, 180, nothing)
cv2.createTrackbar("S min", "HSV Tuning", 150, 255, nothing)
cv2.createTrackbar("V min", "HSV Tuning", 80, 255, nothing)

# =============================
# Color definitions
# =============================
COLORS = {
    "red":   {"ranges": [((0,0,0),(0,0,0))], "enabled": True},
    "green": {"ranges": [((0,0,0),(0,0,0))], "enabled": True},
    "blue":  {"ranges": [((0,0,0),(0,0,0))], "enabled": True},
}

MIN_AREA = 500
MAX_DIST = 60

# =============================
# Tracking
# =============================
tracks = {}
next_id = 0

def dist(a,b):
    return math.hypot(a[0]-b[0], a[1]-b[1])

# =============================
# Main loop
# =============================
while True:
    ret, frame = cap.read()
    if not ret:
        break

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    hmin = cv2.getTrackbarPos("H min", "HSV Tuning")
    hmax = cv2.getTrackbarPos("H max", "HSV Tuning")
    smin = cv2.getTrackbarPos("S min", "HSV Tuning")
    vmin = cv2.getTrackbarPos("V min", "HSV Tuning")

    # Define ranges dynamically
    COLORS["red"]["ranges"] = [
        ((0, smin, vmin), (hmin, 255, 255)),
        ((hmax, smin, vmin), (180, 255, 255))
    ]
    COLORS["green"]["ranges"] = [((hmin, smin, vmin), (hmax, 255, 255))]
    COLORS["blue"]["ranges"]  = [((hmin, smin, vmin), (hmax, 255, 255))]

    detections = []
    color_masks = {}

    # =============================
    # Detection
    # =============================
    for cname, cinfo in COLORS.items():
        if not cinfo["enabled"]:
            continue

        mask = None
        for lo, hi in cinfo["ranges"]:
            part = cv2.inRange(hsv, lo, hi)
            mask = part if mask is None else cv2.bitwise_or(mask, part)

        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5,5),np.uint8))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((7,7),np.uint8))

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for c in contours:
            if cv2.contourArea(c) < MIN_AREA:
                continue
            x,y,w,h = cv2.boundingRect(c)
            detections.append((x+w//2, y+h//2, cname))

        color_masks[cname] = mask

    # =============================
    # Tracking
    # =============================
    new_tracks = {}

    for cx, cy, cname in detections:
        best = None
        best_d = MAX_DIST
        for tid, (tx, ty) in tracks.items():
            d = dist((cx,cy),(tx,ty))
            if d < best_d:
                best_d = d
                best = tid

        if best is not None:
            new_tracks[best] = (cx,cy)
        else:
            new_tracks[next_id] = (cx,cy)
            next_id += 1

    tracks = new_tracks

    # =============================
    # Black display + color only
    # =============================
    display = np.zeros_like(frame)

    for cname, mask in color_masks.items():
        display[mask > 0] = frame[mask > 0]

    for tid,(x,y) in tracks.items():
        cv2.circle(display,(x,y),10,(255,255,255),2)
        cv2.putText(display,f"ID {tid}",(x+8,y),
                    cv2.FONT_HERSHEY_SIMPLEX,0.5,(255,255,255),1)

    cv2.imshow("Color Only View", display)

    # =============================
    # Controls
    # =============================
    key = cv2.waitKey(1) & 0xFF
    if key == 27:
        break
    if key == ord('r'): COLORS["red"]["enabled"] ^= True
    if key == ord('g'): COLORS["green"]["enabled"] ^= True
    if key == ord('b'): COLORS["blue"]["enabled"] ^= True

cap.release()
cv2.destroyAllWindows()
