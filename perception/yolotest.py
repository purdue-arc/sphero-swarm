from ultralytics import YOLO

# Load a pretrained YOLO model
model = YOLO("yolov8s.pt")# Perform object detection on an image
results = model(source="perception/TestVideos/SS_edited_demo25.mp4", show=True, save=True)# Visualize the results
results.show()# Export the model to ONNX format
success = model.export(format="onnx")
