"""
Blink Detector - Eye Blink Detection and Classification

This module detects and classifies different types of eye blinks
using Eye Aspect Ratio (EAR) calculations.
"""

import numpy as np
import time
from collections import deque

# Configuration constants
CONFIG = {
    'ear_threshold': 0.21,  # EAR threshold for blink detection
    'blink_frames': 2,      # Minimum frames for blink detection
    'double_blink_window': 0.4,  # seconds
    'long_blink_duration': 1.5,  # seconds
    'anti_fatigue_window': 8.0,  # seconds
    'smoothing_window': 5,   # frames for EAR smoothing
    'calibration_frames': 30,  # frames for baseline calibration
}

class BlinkDetector:
    """
    Detects and classifies eye blinks for hands-free interaction.
    """

    def __init__(self):
        """Initialize blink detector."""
        self.ear_history = deque(maxlen=CONFIG['smoothing_window'])
        self.blink_history = deque(maxlen=10)  # Recent blinks
        self.baseline_ear = None
        self.is_calibrating = True
        self.calibration_frames = 0

        # Blink state tracking
        self.current_blink_start = None
        self.last_blink_time = 0
        self.blink_count = 0

        # Anti-fatigue mechanism
        self.last_natural_blink = time.time()

    def detect_blink(self, eye_landmarks):
        """
        Detect blink from eye landmarks.

        Args:
            eye_landmarks: Dictionary of eye landmark coordinates

        Returns:
            str or None: Blink type ('single', 'double', 'long') or None
        """
        if not eye_landmarks:
            return None

        # Calculate EAR for both eyes
        left_ear = self.calculate_ear(eye_landmarks.get('left_eye', []))
        right_ear = self.calculate_ear(eye_landmarks.get('right_eye', []))

        if left_ear is None and right_ear is None:
            return None

        # Use the average EAR if both eyes are available
        if left_ear is not None and right_ear is not None:
            ear = (left_ear + right_ear) / 2
        elif left_ear is not None:
            ear = left_ear
        else:
            ear = right_ear

        # Add to history for smoothing
        self.ear_history.append(ear)
        smoothed_ear = np.mean(self.ear_history) if self.ear_history else ear

        # Calibrate baseline EAR during initial frames
        if self.is_calibrating:
            self.calibration_frames += 1
            if self.calibration_frames >= CONFIG['calibration_frames']:
                self.baseline_ear = np.mean(list(self.ear_history))
                self.is_calibrating = False
                print(f"Baseline EAR calibrated: {self.baseline_ear:.3f}")  # FIXED LINE

        if self.is_calibrating:
            return None

        # Detect blink based on EAR threshold
        is_blinking = smoothed_ear < CONFIG['ear_threshold']

        current_time = time.time()
        blink_type = None

        if is_blinking:
            if self.current_blink_start is None:
                # Start of blink
                self.current_blink_start = current_time
        else:
            if self.current_blink_start is not None:
                # End of blink
                blink_duration = current_time - self.current_blink_start
                blink_type = self.classify_blink(blink_duration, current_time)
                self.current_blink_start = None

                if blink_type:
                    self.blink_history.append((current_time, blink_type))
                    self.last_blink_time = current_time
                    self.blink_count += 1

        return blink_type

    def calculate_ear(self, eye_landmarks):
        """
        Calculate Eye Aspect Ratio (EAR) for eye landmarks.

        Args:
            eye_landmarks: List of 6 eye landmark points [p1, p2, p3, p4, p5, p6]
                          where p1-p4 are eye corners, p2-p3 and p5-p6 are vertical points

        Returns:
            float or None: Eye Aspect Ratio value
        """
        if not eye_landmarks or len(eye_landmarks) < 6:
            return None

        try:
            # Convert landmarks to numpy array for easier calculation
            points = np.array(eye_landmarks)

            # EAR formula: (||p2-p6|| + ||p3-p5||) / (2 * ||p1-p4||)
            # Vertical distances
            vert1 = np.linalg.norm(points[1] - points[5])  # p2 to p6
            vert2 = np.linalg.norm(points[2] - points[4])  # p3 to p5

            # Horizontal distance
            horiz = np.linalg.norm(points[0] - points[3])  # p1 to p4

            if horiz == 0:
                return None

            ear = (vert1 + vert2) / (2 * horiz)
            return ear

        except Exception as e:
            print(f"Error calculating EAR: {e}")
            return None

    def classify_blink(self, duration, current_time):
        """
        Classify blink type based on duration and timing.

        Args:
            duration: Blink duration in seconds
            current_time: Current timestamp

        Returns:
            str or None: Blink classification
        """
        # Check for anti-fatigue (ignore if no blink in 8+ seconds)
        if current_time - self.last_natural_blink > CONFIG['anti_fatigue_window']:
            # This might be a natural blink, ignore for interaction
            self.last_natural_blink = current_time
            return None

        # Classify based on duration
        if duration >= CONFIG['long_blink_duration']:
            return 'long'
        elif duration >= CONFIG['blink_frames'] * 0.1:  # Convert frames to approximate seconds
            # Check for double blink
            if self._is_double_blink(current_time):
                return 'double'
            else:
                return 'single'

        return None

    def _is_double_blink(self, current_time):
        """Check if current blink is part of a double blink."""
        # Look for recent blinks within the double blink window
        recent_blinks = [t for t, _ in self.blink_history
                        if current_time - t <= CONFIG['double_blink_window']]

        # Need at least one previous blink in the window
        return len(recent_blinks) >= 1

    def get_eye_landmarks_from_face_mesh(self, face_landmarks, frame_shape):
        """
        Extract eye landmarks from MediaPipe FaceMesh results.

        Args:
            face_landmarks: MediaPipe face landmarks
            frame_shape: Frame shape (height, width, channels)

        Returns:
            dict: Eye landmarks for left and right eyes
        """
        if not face_landmarks:
            return {}

        h, w, _ = frame_shape

        # MediaPipe eye landmark indices
        LEFT_EYE_INDICES = [33, 160, 158, 133, 153, 144]   # p1, p2, p3, p4, p5, p6
        RIGHT_EYE_INDICES = [362, 385, 387, 263, 373, 380]

        def extract_eye_points(indices):
            points = []
            for idx in indices:
                landmark = face_landmarks.landmark[idx]
                x = int(landmark.x * w)
                y = int(landmark.y * h)
                points.append([x, y])
            return points

        eye_landmarks = {
            'left_eye': extract_eye_points(LEFT_EYE_INDICES),
            'right_eye': extract_eye_points(RIGHT_EYE_INDICES)
        }

        return eye_landmarks

    def reset_calibration(self):
        """Reset EAR baseline calibration."""
        self.baseline_ear = None
        self.is_calibrating = True
        self.calibration_frames = 0
        self.ear_history.clear()

    def get_blink_stats(self):
        """
        Get blink detection statistics.

        Returns:
            dict: Blink statistics
        """
        current_time = time.time()

        # Calculate blink rate (blinks per minute)
        recent_blinks = [t for t, _ in self.blink_history
                        if current_time - t <= 60]  # Last minute
        blink_rate = len(recent_blinks)

        return {
            'total_blinks': self.blink_count,
            'blink_rate_bpm': blink_rate,
            'baseline_ear': self.baseline_ear,
            'is_calibrated': not self.is_calibrating,
            'last_blink_type': self.blink_history[-1][1] if self.blink_history else None,
            'time_since_last_blink': current_time - self.last_blink_time
        }

    def set_sensitivity(self, threshold=None, min_frames=None):
        """
        Adjust blink detection sensitivity.

        Args:
            threshold: EAR threshold (lower = more sensitive)
            min_frames: Minimum frames for blink detection
        """
        if threshold is not None:
            CONFIG['ear_threshold'] = max(0.1, min(0.4, threshold))
        if min_frames is not None:
            CONFIG['blink_frames'] = max(1, min(10, min_frames))

    def detect_fatigue(self):
        """
        Detect potential eye fatigue based on blink patterns.

        Returns:
            bool: True if fatigue patterns detected
        """
        stats = self.get_blink_stats()

        # Fatigue indicators:
        # - Low blink rate (< 10 per minute)
        # - Very high blink rate (> 30 per minute, could indicate strain)
        # - Long time since last blink (> 10 seconds)

        blink_rate = stats['blink_rate_bpm']
        time_since_blink = stats['time_since_last_blink']

        fatigue_indicators = [
            blink_rate < 8,       # Too few blinks
            blink_rate > 35,      # Too many blinks (strain)
            time_since_blink > 12 # Too long without blinking
        ]

        return any(fatigue_indicators)

    def get_fatigue_warning(self):
        """
        Get fatigue warning message if applicable.

        Returns:
            str or None: Warning message or None
        """
        if self.detect_fatigue():
            stats = self.get_blink_stats()
            blink_rate = stats['blink_rate_bpm']
            time_since_blink = stats['time_since_last_blink']

            if blink_rate < 8:
                return "Low blink rate detected. Consider taking a break to prevent eye strain."
            elif blink_rate > 35:
                return "High blink rate detected. You may be experiencing eye strain."
            elif time_since_blink > 12:
                return "Long time without blinking. Remember to blink naturally."

        return None


# Example usage and testing
if __name__ == "__main__":
    # Test blink detector with mock data
    detector = BlinkDetector()

    # Simulate some EAR values
    test_ear_values = [
        0.25, 0.26, 0.25, 0.24,  # Normal open eyes
        0.15, 0.12, 0.18,         # Blink
        0.25, 0.26, 0.25,         # Back to normal
        0.14, 0.11, 0.16,         # Another blink (double blink)
        0.25, 0.26,               # Normal again
    ]

    print("Testing blink detection...")
    for i, ear in enumerate(test_ear_values):
        mock_landmarks = {
            'left_eye': [[100, 100], [95, 105], [105, 105], [90, 100], [110, 100], [100, 110]]
        }

        blink_type = detector.detect_blink(mock_landmarks)
        if blink_type:
            print(f"Frame {i}: Detected {blink_type} blink")

        time.sleep(0.1)  # Simulate frame timing

    print("Blink detection test completed.")
    print(f"Total blinks detected: {detector.get_blink_stats()['total_blinks']}")