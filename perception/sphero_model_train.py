from ultralytics import YOLO

# Load model
model = YOLO("yolov8n.pt")  # can also use yolov8s.pt

# Train
model.train(
    data="sphero_training_v1/data.yaml",
    epochs=50,
    imgsz=640
)