import cv2
import numpy as np

cap = cv2.VideoCapture('perception/TestVideos/Vid5.mp4')

if not cap.isOpened():
    print("Error: Failed to open the video file.")
    exit()

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    cv2.imshow("Processing Step", gray)
    cv2.waitKey(2000)

    #Treshholding to detect LEDs
    _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)

    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    for contour in contours:
        (x, y), radius = cv2.minEnclosingCircle(contour)
        center = (int(x), int(y))
        radius = int(radius)


        if radius > 10:
            cv2.circle(frame, center, radius, (0, 255, 0), 2) 
            cv2.circle(frame, center, 1, (0, 0, 255), 3)       
    cv2.imshow("LED Detection", frame)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
