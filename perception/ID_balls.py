import cv2
import numpy as np
from scipy.spatial import distance

cap = cv2.VideoCapture('perception/TestVideos/Vid9.mov')

if not cap.isOpened():
    print("Error: Failed to open the video file.")
    exit()

tracked_balls = {}
ball_id = 0 

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    cv2.imshow("Processing Step", gray)
    cv2.waitKey(2000) 

    _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)

    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    detected_balls = [] 

    for contour in contours:
        (x, y), radius = cv2.minEnclosingCircle(contour)
        center = (int(x), int(y))
        radius = int(radius)

        if radius > 10:
            detected_balls.append((center, radius))

    # Match detected balls with tracked balls using Euclidean distance
    updated_balls = {}
    for center, radius in detected_balls:
        min_dist = float("inf")
        closest_id = None

        # Compare with existing tracked balls
        for id, prev_center in tracked_balls.items():
            dist = distance.euclidean(center, prev_center)
            if dist < min_dist and dist < 50: 
                min_dist = dist
                closest_id = id

        # Assign an ID
        if closest_id is not None:
            updated_balls[closest_id] = center
        else:
            ball_id += 1
            updated_balls[ball_id] = center

    for id, center in updated_balls.items():
        cv2.circle(frame, center, radius, (0, 255, 0), 2)  
        cv2.circle(frame, center, 3, (0, 0, 255), -1)
        cv2.putText(frame, f"Ball {id}", (center[0] + 10, center[1] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

    tracked_balls = updated_balls.copy() 

    cv2.imshow("Ball Tracking", frame)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
