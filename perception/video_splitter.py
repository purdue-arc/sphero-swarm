import cv2
import os

# Ask user for input video and output folder
video_path = input("Enter the path to your video file: ")
output_folder = "annotated_test_frames"
frame_skip = 18

os.makedirs(output_folder, exist_ok=True)

cap = cv2.VideoCapture(video_path)
frame_count = 0
saved_count = 0

while True:
    ret, frame = cap.read()
    if not ret:
        break  # end of video

    # Only save every Nth frame
    if frame_count % frame_skip == 0:
        frame_filename = os.path.join(output_folder, f"frame_{saved_count:05d}.jpg")
        cv2.imwrite(frame_filename, frame)
        saved_count += 1

    frame_count += 1

cap.release()
print(f"Saved {saved_count} frames to {output_folder}")
