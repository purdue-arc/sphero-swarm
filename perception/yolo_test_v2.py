from ultralytics import YOLO

# Load your trained model
model = YOLO("yolov8s.pt")

# Run live detection on your webcam
#Camera Size, Number of Detections, how long YOLO took to process it)
results = model.predict(source=0, show=True, conf=0.5)  # source=0 is default webcam
