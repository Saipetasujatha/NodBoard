"""
<<<<<<< HEAD
Gaze Engine - Eye Tracking and Gaze Estimation Core

This module handles real-time eye tracking using MediaPipe FaceMesh
and estimates gaze direction for screen coordinate mapping.
"""

import cv2
import numpy as np
import time
from collections import deque

# MediaPipe import with fallback for compatibility
# First try optional local shim included in project, if available.
try:
    import mediapipe_solutions_shim
except ImportError:
    pass

try:
    import mediapipe as mp
    mp_face_mesh = mp.solutions.face_mesh
except Exception:
    # Some installations (or name collisions) may not expose mp.solutions directly.
    try:
        from mediapipe.python import solutions as mp_solutions
        mp_face_mesh = mp_solutions.face_mesh
    except Exception as e:
        raise ImportError(
            "Unable to import MediaPipe FaceMesh. "
            "Make sure mediapipe 0.10.32 is installed and no file is named 'mediapipe.py'. "
            "If you are using a virtual environment, run: pip install mediapipe==0.10.32"
        ) from e

# Configuration constants
CONFIG = {
    'camera_index': 0,
    'frame_width': 640,
    'frame_height': 480,
    'fps_buffer_size': 30,
    'smoothing_buffer_size': 10,
    'kalman_process_noise': 1e-5,
    'kalman_measurement_noise': 1e-4,
}

class KalmanFilter:
    """
    Simple Kalman filter for smoothing gaze coordinates.
    """

    def __init__(self, process_noise=CONFIG['kalman_process_noise'],
                 measurement_noise=CONFIG['kalman_measurement_noise']):
        """Initialize Kalman filter."""
        self.process_noise = process_noise
        self.measurement_noise = measurement_noise

        # State: [x, y, vx, vy] (position and velocity)
        self.state = np.zeros(4)
        self.covariance = np.eye(4) * 1000

        # State transition matrix
        self.F = np.array([[1, 0, 1, 0],
                          [0, 1, 0, 1],
                          [0, 0, 1, 0],
                          [0, 0, 0, 1]])

        # Measurement matrix (we only measure position)
        self.H = np.array([[1, 0, 0, 0],
                          [0, 1, 0, 0]])

        # Process noise
        self.Q = np.eye(4) * self.process_noise

        # Measurement noise
        self.R = np.eye(2) * self.measurement_noise

    def predict(self):
        """Predict next state."""
        self.state = self.F @ self.state
        self.covariance = self.F @ self.covariance @ self.F.T + self.Q

    def update(self, measurement):
        """Update state with measurement."""
        if measurement is None:
            return

        # Innovation
        y = measurement - self.H @ self.state
        S = self.H @ self.covariance @ self.H.T + self.R

        # Kalman gain
        K = self.covariance @ self.H.T @ np.linalg.inv(S)

        # Update state
        self.state = self.state + K @ y
        self.covariance = (np.eye(4) - K @ self.H) @ self.covariance

    def get_state(self):
        """Get current state estimate."""
        return self.state[:2]  # Return position only

class GazeEngine:
    """
    Main gaze tracking engine using MediaPipe FaceMesh.
    """

    def __init__(self, camera_index=CONFIG['camera_index']):
        """Initialize the gaze engine."""
        self.camera_index = camera_index
        self.cap = None
        self.face_mesh = None
        self.fps_buffer = deque(maxlen=CONFIG['fps_buffer_size'])
        self.smoothing_buffer = deque(maxlen=CONFIG['smoothing_buffer_size'])
        self.kalman_filter = KalmanFilter()
        self.last_frame_time = time.time()
        self.is_initialized = False

        # Latest landmarks for blink detection
        self.last_face_landmarks = None
        self.last_frame_shape = None

        # Iris landmark indices (left eye: 468-472, right eye: 473-477)
        self.LEFT_IRIS = [468, 469, 470, 471, 472]
        self.RIGHT_IRIS = [473, 474, 475, 476, 477]

        # Eye corner indices for gaze estimation
        self.LEFT_EYE_CORNERS = [33, 133]  # Left eye corners
        self.RIGHT_EYE_CORNERS = [362, 263]  # Right eye corners

        self.initialize_camera()
        self.initialize_face_mesh()

    def initialize_camera(self):
        """Initialize the camera capture."""
        try:
            self.cap = cv2.VideoCapture(self.camera_index)
            if not self.cap.isOpened():
                raise ValueError(f"Could not open camera {self.camera_index}")

            # Set camera properties
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, CONFIG['frame_width'])
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CONFIG['frame_height'])
            self.cap.set(cv2.CAP_PROP_FPS, 30)

            print(f"Camera {self.camera_index} initialized successfully")
        except Exception as e:
            print(f"Failed to initialize camera: {e}")
            raise

    def initialize_face_mesh(self):
        """Initialize MediaPipe FaceMesh."""
        try:
            # mp_face_mesh is imported at module load time with a fallback path
            self.mp_face_mesh = mp_face_mesh
            self.face_mesh = self.mp_face_mesh.FaceMesh(
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )
            print("FaceMesh initialized successfully")
        except Exception as e:
            print(f"Failed to initialize FaceMesh: {e}")
            raise

    def get_frame_and_gaze(self):
        """
        Get camera frame and estimate gaze direction.

        Returns:
            tuple: (frame, gaze_point, fps)
                - frame: OpenCV BGR frame
                - gaze_point: (x, y) tuple of gaze coordinates (0-1 normalized)
                - fps: current FPS
        """
        if not self.cap or not self.cap.isOpened():
            return None, None, 0

        try:
            ret, frame = self.cap.read()
            if not ret:
                return None, None, 0

            # Calculate FPS
            current_time = time.time()
            fps = 1.0 / (current_time - self.last_frame_time) if self.last_frame_time > 0 else 0
            self.last_frame_time = current_time
            self.fps_buffer.append(fps)
            avg_fps = sum(self.fps_buffer) / len(self.fps_buffer) if self.fps_buffer else 0

            # Process frame for face landmarks
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.face_mesh.process(frame_rgb)

            gaze_point = None
            if results.multi_face_landmarks:
                landmarks = results.multi_face_landmarks[0]
                self.last_face_landmarks = landmarks
                self.last_frame_shape = frame.shape

                # Estimate gaze
                gaze_point = self.estimate_gaze_direction(landmarks, frame.shape)

                # Apply Kalman filtering for smoothing
                if gaze_point is not None:
                    self.kalman_filter.predict()
                    self.kalman_filter.update(gaze_point)
                    gaze_point = self.kalman_filter.get_state()

                    # Apply additional exponential smoothing
                    self.smoothing_buffer.append(gaze_point)
                    if len(self.smoothing_buffer) >= 3:
                        smoothed = np.mean(list(self.smoothing_buffer), axis=0)
                        gaze_point = smoothed

            return frame, gaze_point, int(avg_fps)

        except Exception as e:
            print(f"Error in get_frame_and_gaze: {e}")
            return None, None, 0

    def estimate_gaze_direction(self, landmarks, frame_shape):
        """
        Estimate gaze direction from iris landmarks.

        Args:
            landmarks: MediaPipe face landmarks
            frame_shape: Shape of the camera frame (height, width, channels)

        Returns:
            tuple: (x, y) normalized gaze coordinates (0-1)
        """
        try:
            h, w, _ = frame_shape

            # Get iris center points
            left_iris_center = self.get_iris_center(landmarks, self.LEFT_IRIS, w, h)
            right_iris_center = self.get_iris_center(landmarks, self.RIGHT_IRIS, w, h)

            if left_iris_center is None or right_iris_center is None:
                return None

            # Get eye corner points
            left_eye_left_corner = self.get_landmark_point(landmarks, self.LEFT_EYE_CORNERS[0], w, h)
            left_eye_right_corner = self.get_landmark_point(landmarks, self.LEFT_EYE_CORNERS[1], w, h)
            right_eye_left_corner = self.get_landmark_point(landmarks, self.RIGHT_EYE_CORNERS[0], w, h)
            right_eye_right_corner = self.get_landmark_point(landmarks, self.RIGHT_EYE_CORNERS[1], w, h)

            if None in [left_eye_left_corner, left_eye_right_corner, right_eye_left_corner, right_eye_right_corner]:
                return None

            # Calculate gaze direction for each eye
            left_gaze = self.calculate_eye_gaze(left_iris_center, left_eye_left_corner, left_eye_right_corner)
            right_gaze = self.calculate_eye_gaze(right_iris_center, right_eye_left_corner, right_eye_right_corner)

            if left_gaze is None or right_gaze is None:
                return None

            # Average both eyes for more stable estimation
            avg_gaze_x = (left_gaze[0] + right_gaze[0]) / 2
            avg_gaze_y = (left_gaze[1] + right_gaze[1]) / 2

            # Normalize to 0-1 range (this is a simplified mapping)
            # In a real calibration system, this would be mapped to screen coordinates
            normalized_x = np.clip(avg_gaze_x, 0, 1)
            normalized_y = np.clip(avg_gaze_y, 0, 1)

            return (normalized_x, normalized_y)

        except Exception as e:
            print(f"Error in estimate_gaze_direction: {e}")
            return None

    def get_iris_center(self, landmarks, iris_indices, frame_width, frame_height):
        """
        Calculate the center point of iris landmarks.

        Args:
            landmarks: MediaPipe face landmarks
            iris_indices: List of iris landmark indices
            frame_width: Width of camera frame
            frame_height: Height of camera frame

        Returns:
            tuple: (x, y) center coordinates
        """
        points = []
        for idx in iris_indices:
            point = self.get_landmark_point(landmarks, idx, frame_width, frame_height)
            if point:
                points.append(point)

        if len(points) < 3:
            return None

        # Calculate centroid
        center_x = sum(p[0] for p in points) / len(points)
        center_y = sum(p[1] for p in points) / len(points)

        return (center_x, center_y)

    def get_landmark_point(self, landmarks, index, frame_width, frame_height):
        """
        Get landmark point coordinates.

        Args:
            landmarks: MediaPipe face landmarks
            index: Landmark index
            frame_width: Width of camera frame
            frame_height: Height of camera frame

        Returns:
            tuple: (x, y) pixel coordinates
        """
        landmark = landmarks.landmark[index]
        x = int(landmark.x * frame_width)
        y = int(landmark.y * frame_height)
        return (x, y)

    def calculate_eye_gaze(self, iris_center, eye_left_corner, eye_right_corner):
        """
        Calculate gaze direction for a single eye.

        Args:
            iris_center: (x, y) iris center coordinates
            eye_left_corner: (x, y) left eye corner
            eye_right_corner: (x, y) right eye corner

        Returns:
            tuple: (x, y) normalized gaze direction
        """
        try:
            # Calculate eye center
            eye_center_x = (eye_left_corner[0] + eye_right_corner[0]) / 2
            eye_center_y = (eye_left_corner[1] + eye_right_corner[1]) / 2

            # Calculate relative iris position
            relative_x = iris_center[0] - eye_center_x
            relative_y = iris_center[1] - eye_center_y

            # Calculate eye width for normalization
            eye_width = abs(eye_right_corner[0] - eye_left_corner[0])

            if eye_width == 0:
                return None

            # Normalize relative position
            normalized_x = relative_x / eye_width
            normalized_y = relative_y / eye_width  # Using width for both for simplicity

            # Convert to 0-1 range (simplified mapping)
            gaze_x = (normalized_x + 1) / 2  # -1 to 1 -> 0 to 1
            gaze_y = (normalized_y + 1) / 2

            return (gaze_x, gaze_y)

        except Exception as e:
            print(f"Error in calculate_eye_gaze: {e}")
            return None

    def get_eye_landmarks(self):
        """
        Get current eye landmarks for blink detection.

        Returns:
            dict: Eye landmark coordinates structured for BlinkDetector.
                  Keys: 'left_eye', 'right_eye' with list of 6 [x, y] points.
        """
        if self.last_face_landmarks is None or self.last_frame_shape is None:
            return {}

        h, w, _ = self.last_frame_shape

        # MediaPipe eye landmarks for EAR calculation (6 points per eye)
        LEFT_EYE_INDICES = [33, 160, 158, 133, 153, 144]
        RIGHT_EYE_INDICES = [362, 385, 387, 263, 373, 380]

        def extract_points(indices):
            points = []
            for idx in indices:
                lm = self.last_face_landmarks.landmark[idx]
                x = int(lm.x * w)
                y = int(lm.y * h)
                points.append([x, y])
            return points

        return {
            'left_eye': extract_points(LEFT_EYE_INDICES),
            'right_eye': extract_points(RIGHT_EYE_INDICES)
        }

    def set_camera_index(self, index):
        """Change camera source."""
        if self.cap:
            self.cap.release()
        self.camera_index = index
        self.initialize_camera()

    def release(self):
        """Release camera and cleanup resources."""
        if self.cap:
            self.cap.release()
        if self.face_mesh:
            self.face_mesh.close()

    def __del__(self):
        """Destructor to ensure cleanup."""
        self.release()
=======
gaze_engine.py
--------------
Core eye tracking module using MediaPipe FaceMesh.
"""

import cv2
import mediapipe as mp
import numpy as np
import time


class GazeEngine:
    """
    Captures webcam frames and runs MediaPipe FaceMesh for gaze detection.
    """

    def __init__(self, camera_index=0):
        self.camera_index = camera_index
        self.cap = cv2.VideoCapture(self.camera_index)
        if not self.cap.isOpened():
            raise RuntimeError(f"Cannot open camera index {self.camera_index}.")
        
        mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.3,
            min_tracking_confidence=0.3
        )

    # ── Public API ───────────────────────────────────────────────────────────

    def start(self):
        """Open camera and start background capture thread."""
        self.cap = cv2.VideoCapture(self.camera_index)
        if not self.cap.isOpened():
            raise RuntimeError(
                f"Cannot open camera index {self.camera_index}."
            )
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, CONFIG["FRAME_WIDTH"])
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CONFIG["FRAME_HEIGHT"])
        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop capture thread and release camera."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        if self.cap:
            self.cap.release()

    def get_frame(self):
        """Return the latest annotated camera frame (thread-safe copy)."""
        with self.frame_lock:
            return self.frame.copy() if self.frame is not None else None

    def get_gaze(self):
        """Return smoothed screen-space gaze (x, y) in pixels."""
        return tuple(self.screen_gaze)

    def get_frame_and_gaze(self):
        """
        Direct iris-based gaze calculation.
        Returns (frame, gaze_point, fps) with normalized 0-1 coordinates.
        """
        # Lazy initialization: start camera if not already running
        if self.cap is None:
            try:
                self.start()
            except Exception as e:
                print(f"Failed to start camera: {e}")
                return None, None, 0
        
        if not self.cap or not self.cap.isOpened():
            return None, None, 0
        
        ret, frame = self.cap.read()
        if not ret:
            return None, None, 0
        
        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        
        # Timestamp for VIDEO mode
        self._frame_ts += 33  # ~30fps
        
        gaze_point = None
        try:
            results = self._landmarker.detect_for_video(mp_image, self._frame_ts)
            
            if results.face_landmarks and len(results.face_landmarks) > 0:
                lm = results.face_landmarks[0]
                
                # Left iris center (landmark 468)
                lx = lm[468].x
                ly = lm[468].y
                
                # Right iris center (landmark 473)
                rx = lm[473].x
                ry = lm[473].y
                
                # Average both eyes
                gaze_x = (lx + rx) / 2.0
                gaze_y = (ly + ry) / 2.0
                
                gaze_point = (float(gaze_x), float(gaze_y))
            else:
                print(f"DEBUG: No face landmarks detected. face_landmarks={results.face_landmarks}")
        except Exception as e:
            print(f"MediaPipe error in get_frame_and_gaze: {e}")
            import traceback
            traceback.print_exc()
        
        fps = int(self.fps) if self.fps > 0 else 30
        return frame, gaze_point, fps

    def get_eye_landmarks(self):
        """
        Return the latest face landmarks for blink detection.
        Returns list of NormalizedLandmark objects or None.
        """
        with self.landmarks_lock:
            return self.landmarks

    def set_calibration_model(self, model):
        """Attach a trained sklearn regressor for gaze→screen mapping."""
        self.calibration_model = model

    # ── Internal ─────────────────────────────────────────────────────────────

    def _capture_loop(self):
        """Background thread: read frames, run FaceLandmarker, update gaze."""
        while self._running:
            ret, frame = self.cap.read()
            if not ret:
                time.sleep(0.01)
                continue

            frame = cv2.flip(frame, 1)

            # Convert BGR → RGB numpy array → mp.Image
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

            # Timestamp in ms (required for VIDEO mode)
            self._frame_ts += 33   # ~30 fps
            try:
                result = self._landmarker.detect_for_video(mp_image, self._frame_ts)
            except Exception as e:
                print(f"[GazeEngine] Detection error: {e}")
                time.sleep(0.01)
                continue

            if result.face_landmarks:
                lm = result.face_landmarks[0]   # list of NormalizedLandmark
                with self.landmarks_lock:
                    self.landmarks = lm
                gaze = self._extract_gaze(lm, frame.shape)
                self._update_smooth_gaze(gaze)
            else:
                with self.landmarks_lock:
                    self.landmarks = None

            self._update_fps()
            annotated = self._draw_overlay(frame.copy())

            with self.frame_lock:
                self.frame = annotated

            if self.on_frame_ready:
                self.on_frame_ready(annotated)
            if self.on_gaze_update:
                self.on_gaze_update(*self.screen_gaze)

    def _extract_gaze(self, landmarks, shape):
        """
        Compute normalised gaze [0,1] from iris centre relative to eye corners.
        landmarks: list of NormalizedLandmark (x, y, z all in [0,1])
        """
        h, w = shape[:2]

        def lm_xy(idx):
            return np.array([landmarks[idx].x * w, landmarks[idx].y * h])

        # ── Left eye ──
        left_iris_pts = np.array([lm_xy(i) for i in CONFIG["LEFT_IRIS"]])
        left_iris_center = left_iris_pts.mean(axis=0)
        left_corner_l = lm_xy(CONFIG["LEFT_EYE_CORNERS"][0])
        left_corner_r = lm_xy(CONFIG["LEFT_EYE_CORNERS"][1])
        left_eye_width = np.linalg.norm(left_corner_r - left_corner_l) + 1e-6
        left_gaze_x = (left_iris_center[0] - left_corner_l[0]) / left_eye_width
        left_gaze_y = (left_iris_center[1] - left_corner_l[1]) / left_eye_width

        # ── Right eye ──
        right_iris_pts = np.array([lm_xy(i) for i in CONFIG["RIGHT_IRIS"]])
        right_iris_center = right_iris_pts.mean(axis=0)
        right_corner_l = lm_xy(CONFIG["RIGHT_EYE_CORNERS"][0])
        right_corner_r = lm_xy(CONFIG["RIGHT_EYE_CORNERS"][1])
        right_eye_width = np.linalg.norm(right_corner_r - right_corner_l) + 1e-6
        right_gaze_x = (right_iris_center[0] - right_corner_l[0]) / right_eye_width
        right_gaze_y = (right_iris_center[1] - right_corner_l[1]) / right_eye_width

        gaze_x = (left_gaze_x + right_gaze_x) / 2.0
        gaze_y = (left_gaze_y + right_gaze_y) / 2.0
        return np.array([gaze_x, gaze_y])

    def _update_smooth_gaze(self, raw):
        """Apply EMA smoothing and update screen coordinates."""
        self.raw_gaze = raw
        self.smooth_gaze = self.alpha * raw + (1 - self.alpha) * self.smooth_gaze

        if self.calibration_model is not None:
            try:
                pred = self.calibration_model.predict([self.smooth_gaze])[0]
                self.screen_gaze = np.array(pred, dtype=int)
            except Exception:
                self._fallback_mapping()
        else:
            self._fallback_mapping()

    def _fallback_mapping(self):
        """Simple linear mapping when no calibration model is available."""
        try:
            import tkinter as tk
            root = tk.Tk()
            sw = root.winfo_screenwidth()
            sh = root.winfo_screenheight()
            root.destroy()
        except Exception:
            sw, sh = 1920, 1080
        x = int(np.clip(self.smooth_gaze[0], 0, 1) * sw)
        y = int(np.clip(self.smooth_gaze[1], 0, 1) * sh)
        self.screen_gaze = np.array([x, y])

    def _update_fps(self):
        self._fps_counter += 1
        elapsed = time.time() - self._fps_timer
        if elapsed >= 1.0:
            self.fps = self._fps_counter / elapsed
            self._fps_counter = 0
            self._fps_timer = time.time()

    def _draw_overlay(self, frame):
        """Draw FPS and gaze dot on the camera preview frame."""
        cv2.putText(
            frame, f"FPS: {self.fps:.1f}",
            (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2
        )
        h, w = frame.shape[:2]
        gx = int(np.clip(self.smooth_gaze[0], 0, 1) * w)
        gy = int(np.clip(self.smooth_gaze[1], 0, 1) * h)
        cv2.circle(frame, (gx, gy), 8, (0, 0, 255), -1)
        cv2.circle(frame, (gx, gy), 10, (255, 255, 255), 2)
        return frame
>>>>>>> 52c3d7ea5ed405484f229b508704a40d14764e6c
