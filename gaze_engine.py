"""
gaze_engine.py
--------------
Core eye tracking using MediaPipe FaceLandmarker (Tasks API).
Compatible with mediapipe 0.10.30+
"""

import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision
from mediapipe.tasks.python.vision import FaceLandmarker, FaceLandmarkerOptions, RunningMode
import numpy as np
import time
import urllib.request
import os


MODEL_PATH = "face_landmarker.task"
MODEL_URL  = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"


def _ensure_model():
    if not os.path.exists(MODEL_PATH):
        print("Downloading face_landmarker.task model (~30 MB)...")
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
        print("Model downloaded.")


class GazeEngine:
    LEFT_IRIS        = [468, 469, 470, 471, 472]
    RIGHT_IRIS       = [473, 474, 475, 476, 477]
    LEFT_EYE_EAR_IDX = [33, 160, 158, 133, 153, 144]
    RIGHT_EYE_EAR_IDX= [362, 385, 387, 263, 373, 380]

    def __init__(self, camera_index=0):
        self.camera_index = camera_index
        self.fps = 0
        self._fps_counter = 0
        self._fps_timer   = time.time()
        self.last_frame_time = time.time()

        self.last_face_landmarks = None
        self.last_frame_shape    = None

        # Open camera
        self.cap = cv2.VideoCapture(camera_index)
        if not self.cap.isOpened():
            raise RuntimeError(f"Cannot open camera index {camera_index}.")

        # Download model if needed
        _ensure_model()

        # Build FaceLandmarker with Tasks API
        base_opts = mp_python.BaseOptions(model_asset_path=MODEL_PATH)
        opts = FaceLandmarkerOptions(
            base_options=base_opts,
            running_mode=RunningMode.IMAGE,
            num_faces=1,
            min_face_detection_confidence=0.3,
            min_face_presence_confidence=0.3,
            min_tracking_confidence=0.3,
            output_face_blendshapes=False,
            output_facial_transformation_matrixes=False,
        )
        self.landmarker = FaceLandmarker.create_from_options(opts)
        print(f"GazeEngine ready (mediapipe {mp.__version__}, Tasks API)")

    # ── Public API ────────────────────────────────────────────────────────────

    def get_frame_and_gaze(self):
        if not self.cap or not self.cap.isOpened():
            return None, None, 0

        ret, frame = self.cap.read()
        if not ret or frame is None:
            return None, None, 0

        frame = cv2.flip(frame, 1)

        # FPS
        now = time.time()
        self._fps_counter += 1
        if (now - self._fps_timer) >= 1.0:
            self.fps = self._fps_counter / (now - self._fps_timer)
            self._fps_counter = 0
            self._fps_timer   = now
        self.last_frame_time = now

        # Run detection
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = self.landmarker.detect(mp_image)

        gaze_point = None
        if result.face_landmarks:
            landmarks = result.face_landmarks[0]   # list of NormalizedLandmark
            self.last_face_landmarks = landmarks
            self.last_frame_shape    = frame.shape
            gaze_point = self._estimate_gaze(landmarks, frame.shape)

        return frame, gaze_point, int(self.fps)

    def get_eye_landmarks(self):
        if self.last_face_landmarks is None or self.last_frame_shape is None:
            return {}

        h, w, _ = self.last_frame_shape

        def extract(indices):
            pts = []
            for idx in indices:
                lm = self.last_face_landmarks[idx]
                pts.append([int(lm.x * w), int(lm.y * h)])
            return pts

        return {
            'left_eye':  extract(self.LEFT_EYE_EAR_IDX),
            'right_eye': extract(self.RIGHT_EYE_EAR_IDX),
        }

    def release(self):
        if self.cap:
            self.cap.release()
        try:
            self.landmarker.close()
        except Exception:
            pass

    def __del__(self):
        self.release()

    # ── Internal ──────────────────────────────────────────────────────────────

    def _estimate_gaze(self, landmarks, frame_shape):
        try:
            h, w, _ = frame_shape

            def pt(idx):
                lm = landmarks[idx]
                return np.array([lm.x * w, lm.y * h])

            left_iris  = np.mean([pt(i) for i in self.LEFT_IRIS],  axis=0)
            right_iris = np.mean([pt(i) for i in self.RIGHT_IRIS], axis=0)
            avg = (left_iris + right_iris) / 2.0

            norm_x = float(np.clip(avg[0] / w, 0, 1))
            norm_y = float(np.clip(avg[1] / h, 0, 1))
            return (norm_x, norm_y)

        except Exception as e:
            print(f"Gaze estimation error: {e}")
            return None


if __name__ == "__main__":
    engine = GazeEngine()
    print("Press Q to quit")
    while True:
        frame, gaze, fps = engine.get_frame_and_gaze()
        if frame is not None:
            if gaze:
                h, w = frame.shape[:2]
                cx, cy = int(gaze[0] * w), int(gaze[1] * h)
                cv2.circle(frame, (cx, cy), 10, (0, 255, 0), -1)
            cv2.putText(frame, f"FPS:{fps}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.imshow("GazeEngine", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    engine.release()
    cv2.destroyAllWindows()