import cv2
import os

# Ask user for input video and output folder
video_path = input("Enter the path to your video file: ")
output_folder = input("Enter the folder to save frames: ")

# Create the output folder if it doesn't exist
os.makedirs(output_folder, exist_ok=True)

# Open the video
cap = cv2.VideoCapture(video_path)

frame_count = 0
while True:
    ret, frame = cap.read()
    if not ret:
        break  # end of video

    # Save frame as image
    frame_filename = os.path.join(output_folder, f"frame_{frame_count:04d}.jpg")
    cv2.imwrite(frame_filename, frame)

    frame_count += 1

cap.release()

