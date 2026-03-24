"""
blink_detector.py
-----------------
Detects blinks using the Eye Aspect Ratio (EAR) formula.
Single blink  → confirm/click current key
Double blink  → delete last character
Long blink    → insert SPACE
"""

import numpy as np
import time

# ── CONFIG ──────────────────────────────────────────────────────────────────
CONFIG = {
    "EAR_THRESHOLD": 0.21,          # below this = eye closed
    "BLINK_FRAMES_MIN": 2,          # min frames for a valid blink
    "BLINK_FRAMES_MAX": 8,          # max frames before it's a long blink
    "LONG_BLINK_SECONDS": 1.5,      # seconds for long-blink (SPACE)
    "DOUBLE_BLINK_WINDOW": 0.4,     # seconds between two blinks = double
    "ANTI_FATIGUE_SECONDS": 8.0,    # ignore blink if no blink in this window
    # MediaPipe landmark indices for EAR calculation
    # Left eye:  p1=33, p2=160, p3=158, p4=133, p5=153, p6=144
    # Right eye: p1=362, p2=385, p3=387, p4=263, p5=373, p6=380
    "LEFT_EYE_EAR_IDX": [33, 160, 158, 133, 153, 144],
    "RIGHT_EYE_EAR_IDX": [362, 385, 387, 263, 373, 380],
}
# ────────────────────────────────────────────────────────────────────────────

# Blink event type constants
BLINK_NONE = "none"
BLINK_SINGLE = "single"
BLINK_DOUBLE = "double"
BLINK_LONG = "long"


class BlinkDetector:
    """
    Stateful blink detector.
    Call update(landmarks) each frame; it fires callbacks on blink events.
    """

    def __init__(self):
        self._closed_frames = 0         # consecutive frames eye is closed
        self._eye_closed = False
        self._blink_times = []          # timestamps of recent blinks
        self._last_blink_time = 0.0
        self._last_natural_blink = time.time()
        self._long_blink_start = None

        # Callbacks – set these from outside
        self.on_single_blink = None     # callable()
        self.on_double_blink = None     # callable()
        self.on_long_blink = None       # callable()

        # Public state for UI indicator
        self.current_ear = 1.0
        self.blink_ready = True         # False during anti-fatigue window

    # ── Public API ───────────────────────────────────────────────────────────

    def update(self, landmarks):
        """
        Process one frame of landmarks.
        landmarks: list of MediaPipe NormalizedLandmark objects (or None).
        Returns one of BLINK_NONE / BLINK_SINGLE / BLINK_DOUBLE / BLINK_LONG.
        """
        if landmarks is None:
            return BLINK_NONE

        left_ear = self._compute_ear(landmarks, CONFIG["LEFT_EYE_EAR_IDX"])
        right_ear = self._compute_ear(landmarks, CONFIG["RIGHT_EYE_EAR_IDX"])
        ear = (left_ear + right_ear) / 2.0
        self.current_ear = ear

        now = time.time()

        # Anti-fatigue: if user hasn't blinked in 8s, next blink is natural
        if now - self._last_natural_blink > CONFIG["ANTI_FATIGUE_SECONDS"]:
            self._last_natural_blink = now
            self.blink_ready = False
            # Reset ready after one natural blink passes
        else:
            self.blink_ready = True

        if ear < CONFIG["EAR_THRESHOLD"]:
            # Eye is closed this frame
            if not self._eye_closed:
                self._eye_closed = True
                self._closed_frames = 1
                self._long_blink_start = now
            else:
                self._closed_frames += 1

            # Detect long blink in progress
            if self._long_blink_start and (now - self._long_blink_start) >= CONFIG["LONG_BLINK_SECONDS"]:
                self._eye_closed = False
                self._closed_frames = 0
                self._long_blink_start = None
                self._last_natural_blink = now
                if self.blink_ready and self.on_long_blink:
                    self.on_long_blink()
                return BLINK_LONG

        else:
            # Eye just opened
            if self._eye_closed:
                frames = self._closed_frames
                self._eye_closed = False
                self._closed_frames = 0
                self._long_blink_start = None

                if CONFIG["BLINK_FRAMES_MIN"] <= frames <= CONFIG["BLINK_FRAMES_MAX"]:
                    if not self.blink_ready:
                        # This was the natural blink – reset and ignore
                        self._last_natural_blink = now
                        self.blink_ready = True
                        return BLINK_NONE

                    self._last_natural_blink = now
                    return self._classify_blink(now)

        return BLINK_NONE

    # ── Internal ─────────────────────────────────────────────────────────────

    def _classify_blink(self, now):
        """Decide if this blink is single or double."""
        self._blink_times.append(now)
        # Keep only recent blinks within the double-blink window
        self._blink_times = [
            t for t in self._blink_times
            if now - t <= CONFIG["DOUBLE_BLINK_WINDOW"]
        ]

        if len(self._blink_times) >= 2:
            self._blink_times.clear()
            if self.on_double_blink:
                self.on_double_blink()
            return BLINK_DOUBLE
        else:
            # Schedule single-blink fire after window expires
            # (so we can still upgrade to double)
            self._last_blink_time = now
            # Fire single after window
            # Caller should check after DOUBLE_BLINK_WINDOW if still single
            # We use a simple delayed approach via the main loop
            if self.on_single_blink:
                # Slight delay handled externally; fire immediately here
                self.on_single_blink()
            return BLINK_SINGLE

    @staticmethod
    def _compute_ear(landmarks, indices):
        """
        Eye Aspect Ratio formula:
        EAR = (||p2-p6|| + ||p3-p5||) / (2 * ||p1-p4||)
        indices: [p1, p2, p3, p4, p5, p6]
        """
        pts = np.array([
            [landmarks[i].x, landmarks[i].y] for i in indices
        ])
        p1, p2, p3, p4, p5, p6 = pts
        vertical_1 = np.linalg.norm(p2 - p6)
        vertical_2 = np.linalg.norm(p3 - p5)
        horizontal = np.linalg.norm(p1 - p4)
        ear = (vertical_1 + vertical_2) / (2.0 * horizontal + 1e-6)
        return ear
