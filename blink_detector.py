"""
blink_detector.py
-----------------
Detects blinks using the Eye Aspect Ratio (EAR) formula.
Single blink  -> confirm/click current key
Double blink  -> delete last character
Long blink    -> insert SPACE
"""

import numpy as np
import time

CONFIG = {
    "EAR_THRESHOLD": 0.21,
    "BLINK_FRAMES_MIN": 2,
    "BLINK_FRAMES_MAX": 8,
    "LONG_BLINK_SECONDS": 1.5,
    "DOUBLE_BLINK_WINDOW": 0.4,
    "ANTI_FATIGUE_SECONDS": 8.0,
    "LEFT_EYE_EAR_IDX": [33, 160, 158, 133, 153, 144],
    "RIGHT_EYE_EAR_IDX": [362, 385, 387, 263, 373, 380],
}

BLINK_NONE   = "none"
BLINK_SINGLE = "single"
BLINK_DOUBLE = "double"
BLINK_LONG   = "long"


class BlinkDetector:
    """
    Stateful blink detector.
    Call detect_blink(eye_landmarks) each frame.
    Also supports update(landmarks) for MediaPipe landmark objects.
    """

    def __init__(self):
        self._closed_frames = 0
        self._eye_closed = False
        self._blink_times = []
        self._last_blink_time = 0.0
        self._last_natural_blink = time.time()
        self._long_blink_start = None

        self.on_single_blink = None
        self.on_double_blink = None
        self.on_long_blink = None

        self.current_ear = 1.0
        self.blink_ready = True

    # ── Public API ───────────────────────────────────────────────────────────

    def detect_blink(self, eye_landmarks):
        """
        Detect blink from eye landmarks dict.
        eye_landmarks: {'left_eye': [[x,y],...], 'right_eye': [[x,y],...]}
        Returns: 'single', 'double', 'long', or None
        """
        if not eye_landmarks:
            return None

        left_ear  = self._calculate_ear(eye_landmarks.get('left_eye', []))
        right_ear = self._calculate_ear(eye_landmarks.get('right_eye', []))

        if left_ear is None and right_ear is None:
            return None

        if left_ear is not None and right_ear is not None:
            ear = (left_ear + right_ear) / 2.0
        elif left_ear is not None:
            ear = left_ear
        else:
            ear = right_ear

        self.current_ear = ear
        now = time.time()

        if now - self._last_natural_blink > CONFIG["ANTI_FATIGUE_SECONDS"]:
            self._last_natural_blink = now
            self.blink_ready = False
        else:
            self.blink_ready = True

        if ear < CONFIG["EAR_THRESHOLD"]:
            if not self._eye_closed:
                self._eye_closed = True
                self._closed_frames = 1
                self._long_blink_start = now
            else:
                self._closed_frames += 1

            if self._long_blink_start and (now - self._long_blink_start) >= CONFIG["LONG_BLINK_SECONDS"]:
                self._eye_closed = False
                self._closed_frames = 0
                self._long_blink_start = None
                self._last_natural_blink = now
                if self.on_long_blink:
                    self.on_long_blink()
                return 'long'
        else:
            if self._eye_closed:
                frames = self._closed_frames
                self._eye_closed = False
                self._closed_frames = 0
                self._long_blink_start = None

                if CONFIG["BLINK_FRAMES_MIN"] <= frames <= CONFIG["BLINK_FRAMES_MAX"]:
                    if not self.blink_ready:
                        self._last_natural_blink = now
                        self.blink_ready = True
                        return None
                    self._last_natural_blink = now
                    return self._classify_blink(now)

        return None

    def update(self, landmarks):
        """
        Process one frame of MediaPipe NormalizedLandmark objects.
        Returns BLINK_NONE / BLINK_SINGLE / BLINK_DOUBLE / BLINK_LONG.
        """
        if landmarks is None:
            return BLINK_NONE

        left_ear  = self._compute_ear(landmarks, CONFIG["LEFT_EYE_EAR_IDX"])
        right_ear = self._compute_ear(landmarks, CONFIG["RIGHT_EYE_EAR_IDX"])
        ear = (left_ear + right_ear) / 2.0
        self.current_ear = ear
        now = time.time()

        if now - self._last_natural_blink > CONFIG["ANTI_FATIGUE_SECONDS"]:
            self._last_natural_blink = now
            self.blink_ready = False
        else:
            self.blink_ready = True

        if ear < CONFIG["EAR_THRESHOLD"]:
            if not self._eye_closed:
                self._eye_closed = True
                self._closed_frames = 1
                self._long_blink_start = now
            else:
                self._closed_frames += 1

            if self._long_blink_start and (now - self._long_blink_start) >= CONFIG["LONG_BLINK_SECONDS"]:
                self._eye_closed = False
                self._closed_frames = 0
                self._long_blink_start = None
                self._last_natural_blink = now
                if self.blink_ready and self.on_long_blink:
                    self.on_long_blink()
                return BLINK_LONG
        else:
            if self._eye_closed:
                frames = self._closed_frames
                self._eye_closed = False
                self._closed_frames = 0
                self._long_blink_start = None

                if CONFIG["BLINK_FRAMES_MIN"] <= frames <= CONFIG["BLINK_FRAMES_MAX"]:
                    if not self.blink_ready:
                        self._last_natural_blink = now
                        self.blink_ready = True
                        return BLINK_NONE
                    self._last_natural_blink = now
                    result = self._classify_blink(now)
                    return result if result else BLINK_NONE

        return BLINK_NONE

    # ── Internal ─────────────────────────────────────────────────────────────

    def _classify_blink(self, now):
        self._blink_times.append(now)
        self._blink_times = [
            t for t in self._blink_times
            if now - t <= CONFIG["DOUBLE_BLINK_WINDOW"]
        ]

        if len(self._blink_times) >= 2:
            self._blink_times.clear()
            if self.on_double_blink:
                self.on_double_blink()
            return 'double'
        else:
            self._last_blink_time = now
            if self.on_single_blink:
                self.on_single_blink()
            return 'single'

    def _calculate_ear(self, eye_landmarks):
        """Calculate EAR from list of [x, y] points."""
        if not eye_landmarks or len(eye_landmarks) < 6:
            return None
        try:
            pts = np.array(eye_landmarks, dtype=float)
            vert1 = np.linalg.norm(pts[1] - pts[5])
            vert2 = np.linalg.norm(pts[2] - pts[4])
            horiz = np.linalg.norm(pts[0] - pts[3])
            if horiz == 0:
                return None
            return (vert1 + vert2) / (2.0 * horiz)
        except Exception as e:
            print(f"EAR calculation error: {e}")
            return None

    @staticmethod
    def _compute_ear(landmarks, indices):
        """Calculate EAR from MediaPipe NormalizedLandmark objects."""
        pts = np.array([[landmarks[i].x, landmarks[i].y] for i in indices])
        p1, p2, p3, p4, p5, p6 = pts
        vert1    = np.linalg.norm(p2 - p6)
        vert2    = np.linalg.norm(p3 - p5)
        horiz    = np.linalg.norm(p1 - p4)
        return (vert1 + vert2) / (2.0 * horiz + 1e-6)


if __name__ == "__main__":
    detector = BlinkDetector()
    print("BlinkDetector initialized successfully.")
    print(f"EAR threshold: {CONFIG['EAR_THRESHOLD']}")