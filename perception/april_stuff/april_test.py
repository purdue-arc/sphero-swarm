from typing import Any


import cv2
import numpy as np
from pupil_apriltags import Detector

cap = cv2.VideoCapture(0)
detector = Detector()

while True:
    ret, frame = cap.read()
    if not ret:
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    results = detector.detect(gray)

    tag_points = {}

    for r in results:
        corners = r.corners.astype(int)
        tag_id = r.tag_id
        cX, cY = int(r.center[0]), int(r.center[1])

        # Draw tag outline
        for j in range(4):
            cv2.line(frame, tuple(corners[j]), tuple(corners[(j + 1) % 4]), (0, 255, 0), 2)

        # Draw center and ID
        cv2.circle(frame, (cX, cY), 4, (0, 0, 255), -1)
        cv2.putText(frame, f"ID: {tag_id}", (cX - 20, cY - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

        # Save center and corners for later
        tag_points[tag_id] = corners

    # If all 4 tags are found
    if len(tag_points) == 4:
        # Sort tags by ID (adjust order if you want)
        ids = sorted(tag_points.keys())
        # Extract opposite corners depending on locationq
        custom_points = []
        for i, tid in enumerate(ids):  # fix enumerate
            corners = tag_points[tid]
            if i == 0:  # top-left tag → use bottom-right corner (corner[2])
                custom_points.append(tuple(corners[1]))
            elif i == 1:  # top-right tag → bottom-left corner (corner[3])
                custom_points.append(tuple(corners[0]))
            elif i == 2:  # bottom-right tag → top-left corner (corner[0])
                custom_points.append(tuple(corners[2]))
            elif i == 3:  # bottom-left tag → top-right corner (corner[1])
                custom_points.append(tuple(corners[3]))

        custom_points = np.array(custom_points, dtype=np.float32)

        # Draw custom square
        connections = [(0, 1), (1, 3), (2, 3), (2, 0)]
        for a, b in connections:
            cv2.line(frame, tuple(custom_points[a].astype(int)), tuple(custom_points[b].astype(int)), (0, 255, 255), 2)

        # Destination square
        size = 500
        dst_pts = np.array([
            [0, 0],
            [size, 0],
            [0, size],
            [size, size]
        ], dtype=np.float32)

        # Perspective transform
        M = cv2.getPerspectiveTransform(custom_points, dst_pts)
        warped = cv2.warpPerspective(frame, M, (size, size))

        cv2.imshow("Warped Square", warped)

    cv2.imshow("AprilTag Detection", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
