import cv2
import numpy as np

cap = cv2.VideoCapture('perception/TestVideos/Vid9.mov')

if not cap.isOpened():
    print("Error: Failed to open the video file.")
    exit()

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    # Convert image to HSV color space
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # Define range of red color in HSV
    lower_red1 = np.array([0, 120, 70])   # Lower bound of red
    upper_red1 = np.array([10, 255, 255]) # Upper bound of red

    lower_red2 = np.array([170, 120, 70])  # Second lower bound (for wrapping red in HSV)
    upper_red2 = np.array([180, 255, 255]) # Second upper bound

    # Create masks to detect red color
    mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
    mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
    
    mask = mask1 + mask2  # Combine both masks

    cv2.imshow("Processing Step", mask)
    cv2.waitKey(2000)

    # Find contours from the red-colored regions
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    for contour in contours:
        (x, y), radius = cv2.minEnclosingCircle(contour)
        center = (int(x), int(y))
        radius = int(radius)

        if radius > 5:  # Filter small detections (noise)
            cv2.circle(frame, center, radius, (0, 255, 0), 2)  # Green circle around red object
            cv2.circle(frame, center, 1, (0, 0, 255), 3)        # Red dot at center

    cv2.imshow("Red Color Detection", frame)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
