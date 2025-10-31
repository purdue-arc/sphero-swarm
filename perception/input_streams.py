import cv2
import depthai as dai
import time

class InputStream:
    def read(self):
        raise NotImplementedError

    def release(self):
        pass


class WebcamStream(InputStream):
    def __init__(self, cam_index=0):
        self.cap = cv2.VideoCapture(0)

    def read(self):
        ret, frame = self.cap.read()
        if not ret:
            return None
        return frame

    def release(self):
        self.cap.release()


class VideoFileStream(InputStream):
    def __init__(self, path):
        self.cap = cv2.VideoCapture(path)
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        if self.fps <= 0:
            self.fps = 30  # default fallback
        self.frame_interval = 1.0 / self.fps
        self.last_frame_time = time.time()

    def read(self):
        current_time = time.time()
        elapsed = current_time - self.last_frame_time
        
        # If we're behind, read frame immediately
        if elapsed >= self.frame_interval:
            ret, frame = self.cap.read()
            if not ret:
                return None
            self.last_frame_time = current_time
            return frame
        
        # If we're ahead of schedule, return None to maintain timing
        return None

    def release(self):
        self.cap.release()