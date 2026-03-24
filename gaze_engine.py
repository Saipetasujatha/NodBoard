"""
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
