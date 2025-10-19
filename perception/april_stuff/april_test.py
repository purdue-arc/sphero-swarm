import cv2
import numpy as np
from pupil_apriltags import Detector

# --- Initialize webcam (0 = default camera) ---
cap = cv2.VideoCapture(0)

detector = Detector()

while True:
    ret, frame = cap.read()
    if not ret:
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    results = detector.detect(gray)

    centers = []

    for r in results:
        corners = r.corners.astype(int)
        tag_id = r.tag_id
        cX, cY = int(r.center[0]), int(r.center[1])
        centers.append((tag_id, (cX, cY)))

        # Draw each tag outline
        for j in range(4):
            cv2.line(frame, tuple(corners[j]), tuple(corners[(j + 1) % 4]), (0, 255, 0), 2)

        # Draw center point
        cv2.circle(frame, (cX, cY), 4, (0, 0, 255), -1)

        # Label tag ID
        cv2.putText(frame, f"ID: {tag_id}", (cX - 20, cY - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

    # --- If all 4 tags are detected, draw square between their centers ---
    if len(centers) == 4:
        # Sort by ID for consistency
        centers.sort(key=lambda x: x[0])
        points = [c[1] for c in centers]

        # Draw lines connecting the four centers in order and back to the first
        for i in range(4):
            cv2.line(frame, points[i], points[(i + 1) % 4], (0, 255, 255), 2)

    cv2.imshow("AprilTag Detection", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
