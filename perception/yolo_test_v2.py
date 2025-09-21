from ultralytics import YOLO
import cv2

# Load model with verbose off
model = YOLO("runs/detect/train2/weights/best.pt", verbose=False)

cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    results = model(frame, verbose=False)  # also set here to be safe

    for result in results:
        for box in result.boxes:
            x1, y1, x2, y2 =  map(int, box.xyxy[0])
            cx = int((x1 + x2) / 2)
            cy = int((y1 + y2) / 2)
            print(f"Center: ({cx:.1f}, {cy:.1f})")
            # Draw rectangle
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

            # Draw center point
            cv2.circle(frame, (cx, cy), 4, (0, 0, 255), -1)
            
    cv2.imshow("YOLO", frame)
    print()
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
