from ultralytics import YOLO
import cv2

# Load YOLOv8 model
model = YOLO("runs/detect/train3/weights/best.pt")

vid_source = input("Video Source: ")

if vid_source == "0":
    vid_source = int(vid_source)
    
# Run detection with tracking
for result in model.track(source=vid_source, tracker="botsort.yaml", show=True, stream=True):
    for box in result.boxes:
        # Get bounding box coordinates
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        cx = int((x1 + x2) / 2)
        cy = int((y1 + y2) / 2)

        cls_id = int(box.cls[0])
        class_name = model.names[cls_id]
       
        if box.id is not None:
            track_id = int(box.id.item())
        else:
            track_id = -1  # or skip ID

        # Print center in terminal
        print(f"ID {track_id} | {class_name} | Center: ({cx}, {cy})")
