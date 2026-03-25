"""
<<<<<<< HEAD
Calibration System - 9-Point Calibration for Gaze Mapping

This module handles the calibration process to map raw gaze coordinates
to screen coordinates using polynomial regression.
=======
calibration.py
--------------
9-point fullscreen calibration screen.
Collects gaze samples at each point, fits a polynomial regression
model, saves calibration_data.json, and returns the trained model.
>>>>>>> 52c3d7ea5ed405484f229b508704a40d14764e6c
"""

import tkinter as tk
import numpy as np
<<<<<<< HEAD
from sklearn.preprocessing import PolynomialFeatures
from sklearn.linear_model import LinearRegression
import time
import threading

# Configuration constants
CONFIG = {
    'calibration_points': 9,
    'samples_per_point': 30,
    'dwell_time': 2.0,  # seconds
    'point_radius': 15,
    'grid_margin': 50,
    'polynomial_degree': 2,
}

class CalibrationSystem:
    """
    Handles the 9-point calibration process for gaze-to-screen mapping.
    """

    def __init__(self, gaze_engine):
        """Initialize calibration system."""
        self.gaze_engine = gaze_engine
        self.calibration_data = None
        self.is_calibrating = False

        # 9-point grid positions (normalized 0-1) - FULL RANGE
        self.grid_points = [
            (0.0, 0.0), (0.5, 0.0), (1.0, 0.0),  # Top row
            (0.0, 0.5), (0.5, 0.5), (1.0, 0.5),  # Middle row
            (0.0, 1.0), (0.5, 1.0), (1.0, 1.0),  # Bottom row
        ]

    def start_calibration(self, parent_window, callback):
        """
        Start the calibration process.

        Args:
            parent_window: Parent Tkinter window
            callback: Function to call when calibration completes
        """
        self.callback = callback
        self.calibration_window = tk.Toplevel(parent_window)
        self.calibration_window.title("Gaze Calibration")
        self.calibration_window.attributes('-fullscreen', True)
        self.calibration_window.configure(bg='black')

        # Calibration data storage
        self.raw_gaze_samples = []
        self.screen_targets = []

        # UI elements
        self.instruction_label = tk.Label(
            self.calibration_window,
            text="Look at the red dot and keep your eyes still",
            font=('Arial', 24),
            fg='white',
            bg='black'
        )
        self.instruction_label.pack(pady=50)

        self.progress_label = tk.Label(
            self.calibration_window,
            text="",
            font=('Arial', 18),
            fg='white',
            bg='black'
        )
        self.progress_label.pack(pady=20)

        self.canvas = tk.Canvas(
            self.calibration_window,
            bg='black',
            highlightthickness=0
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Bind escape key to cancel
        self.calibration_window.bind('<Escape>', lambda e: self.cancel_calibration())

        # Start calibration process
        self.is_calibrating = True
        self.current_point_index = 0
        self.samples_collected = 0
        self.point_start_time = time.time()

        self.calibration_thread = threading.Thread(target=self.calibration_loop, daemon=True)
        self.calibration_thread.start()

    def calibration_loop(self):
        """Main calibration loop."""
        while self.is_calibrating and self.current_point_index < len(self.grid_points):
            try:
                # Get current gaze data
                frame, gaze_point, fps = self.gaze_engine.get_frame_and_gaze()

                if gaze_point is not None:
                    current_time = time.time()

                    # Check if we've stared at current point long enough
                    if current_time - self.point_start_time >= CONFIG['dwell_time']:
                        # Collect sample
                        self.raw_gaze_samples.append(gaze_point)
                        screen_point = self.grid_points[self.current_point_index]
                        self.screen_targets.append(screen_point)
                        self.samples_collected += 1

                        # Update progress
                        self.update_progress()

                        # Move to next point when enough samples collected
                        if self.samples_collected >= CONFIG['samples_per_point']:
                            self.next_point()

                    # Update UI
                    self.update_calibration_display()

                # Small delay to prevent excessive CPU usage
                time.sleep(0.03)

            except Exception as e:
                print(f"Calibration error: {e}")
                self.cancel_calibration()
                break

        if self.is_calibrating:
            # Calibration completed
            self.complete_calibration()

    def update_calibration_display(self):
        """Update the calibration display with current point and progress."""
        if not self.is_calibrating:
            return

        # Clear canvas
        self.canvas.delete("all")

        # Draw current target point
        if self.current_point_index < len(self.grid_points):
            screen_width = self.calibration_window.winfo_width()
            screen_height = self.calibration_window.winfo_height()

            if screen_width > 1 and screen_height > 1:  # Window fully initialized
                target_x, target_y = self.grid_points[self.current_point_index]
                pixel_x = int(target_x * screen_width)
                pixel_y = int(target_y * screen_height)

                # Draw target circle
                radius = CONFIG['point_radius']
                self.canvas.create_oval(
                    pixel_x - radius, pixel_y - radius,
                    pixel_x + radius, pixel_y + radius,
                    fill='red', outline='white', width=2
                )

                # Draw crosshair
                cross_size = 10
                self.canvas.create_line(
                    pixel_x - cross_size, pixel_y,
                    pixel_x + cross_size, pixel_y,
                    fill='white', width=2
                )
                self.canvas.create_line(
                    pixel_x, pixel_y - cross_size,
                    pixel_x, pixel_y + cross_size,
                    fill='white', width=2
                )

    def update_progress(self):
        """Update progress display."""
        point_num = self.current_point_index + 1
        sample_num = self.samples_collected + 1
        progress_text = f"Point {point_num}/9 - Sample {sample_num}/{CONFIG['samples_per_point']}"
        self.progress_label.config(text=progress_text)

    def next_point(self):
        """Move to the next calibration point."""
        self.current_point_index += 1
        self.samples_collected = 0
        self.point_start_time = time.time()

        if self.current_point_index >= len(self.grid_points):
            # Calibration complete
            return

        # Update instruction
        remaining = len(self.grid_points) - self.current_point_index
        if remaining > 0:
            self.instruction_label.config(
                text=f"Look at the red dot. {remaining} points remaining."
            )

    def complete_calibration(self):
        """Complete the calibration and compute mapping."""
        try:
            # Convert data to numpy arrays
            X = np.array(self.raw_gaze_samples)  # Gaze coordinates (x, y)
            y = np.array(self.screen_targets)    # Screen targets (x, y)

            # Create polynomial features
            degree = CONFIG['polynomial_degree']
            poly = PolynomialFeatures(degree=degree, include_bias=True)
            X_poly = poly.fit_transform(X)

            # Train regression models for x and y coordinates
            model_x = LinearRegression()
            model_y = LinearRegression()

            model_x.fit(X_poly, y[:, 0])
            model_y.fit(X_poly, y[:, 1])

            # Calculate accuracy
            y_pred_x = model_x.predict(X_poly)
            y_pred_y = model_y.predict(X_poly)

            errors_x = np.abs(y_pred_x - y[:, 0])
            errors_y = np.abs(y_pred_y - y[:, 1])
            mean_error = np.mean(np.sqrt(errors_x**2 + errors_y**2))
            accuracy_score = max(0, 100 - (mean_error * 100))  # Simplified accuracy score

            # Store calibration data in a serializable format
            self.calibration_data = {
                'degree': degree,
                'coef_x': model_x.coef_.tolist(),
                'intercept_x': float(model_x.intercept_),
                'coef_y': model_y.coef_.tolist(),
                'intercept_y': float(model_y.intercept_),
                'accuracy': accuracy_score,
                'samples': len(self.raw_gaze_samples),
                'timestamp': time.time()
            }

            # Show completion message
            self.instruction_label.config(text="Calibration Complete!")
            self.progress_label.config(text=f"Accuracy: {accuracy_score:.1f}%")

            # Close window after delay
            self.calibration_window.after(3000, lambda: self.finish_calibration(True))

        except Exception as e:
            print(f"Calibration completion error: {e}")
            self.finish_calibration(False)

    def finish_calibration(self, success):
        """Finish calibration and call callback."""
        self.is_calibrating = False
        if self.calibration_window:
            self.calibration_window.destroy()

        if self.callback:
            self.callback(success, self.calibration_data if success else None)

    def cancel_calibration(self):
        """Cancel the calibration process."""
        self.is_calibrating = False
        if self.calibration_window:
            self.calibration_window.destroy()

        if self.callback:
            self.callback(False, None)

    def map_gaze_to_screen(self, gaze_point):
        """Map raw gaze coordinates to screen coordinates using calibration data."""
        if not self.calibration_data or gaze_point is None:
            return gaze_point

        try:
            degree = self.calibration_data.get('degree')
            if degree is None:
                return gaze_point

            # Transform gaze point into polynomial feature vector
            poly = PolynomialFeatures(degree=degree, include_bias=True)
            X_poly = poly.fit_transform(np.array([gaze_point]))

            # Apply stored coefficients
            coef_x = np.array(self.calibration_data.get('coef_x', []))
            intercept_x = float(self.calibration_data.get('intercept_x', 0.0))
            coef_y = np.array(self.calibration_data.get('coef_y', []))
            intercept_y = float(self.calibration_data.get('intercept_y', 0.0))

            if coef_x.size != X_poly.shape[1] or coef_y.size != X_poly.shape[1]:
                return gaze_point

            screen_x = float(X_poly.dot(coef_x) + intercept_x)
            screen_y = float(X_poly.dot(coef_y) + intercept_y)

            # Clamp to valid range
            screen_x = np.clip(screen_x, 0, 1)
            screen_y = np.clip(screen_y, 0, 1)

            return (screen_x, screen_y)

        except Exception as e:
            print(f"Gaze mapping error: {e}")
            return gaze_point

    def get_calibration_accuracy(self):
        """
        Get the calibration accuracy score.

        Returns:
            float: Accuracy percentage (0-100)
        """
        if self.calibration_data:
            return self.calibration_data.get('accuracy', 0)
        return 0

    def is_calibrated(self):
        """
        Check if calibration has been performed.

        Returns:
            bool: True if calibrated
        """
        return self.calibration_data is not None
=======
import json
import time
import os
from sklearn.preprocessing import PolynomialFeatures
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline

# ── CONFIG ──────────────────────────────────────────────────────────────────
CONFIG = {
    "GRID_SIZE": 3,                 # 3x3 = 9 points
    "SAMPLES_PER_POINT": 30,        # gaze samples collected per dot
    "STARE_DURATION": 2.0,          # seconds to stare at each dot
    "DOT_RADIUS": 18,               # calibration dot radius (px)
    "DOT_COLOR_IDLE": "#FF3333",    # red dot
    "DOT_COLOR_ACTIVE": "#33FF33",  # green when collecting
    "DOT_COLOR_DONE": "#3333FF",    # blue when done
    "BG_COLOR": "#1a1a2e",
    "TEXT_COLOR": "#FFFFFF",
    "CALIBRATION_FILE": "calibration_data.json",
    "POLY_DEGREE": 2,               # polynomial degree for regression
    "MARGIN_FRACTION": 0.1,         # fraction of screen kept as margin
}
# ────────────────────────────────────────────────────────────────────────────


class CalibrationScreen:
    """
    Fullscreen Tkinter window that guides the user through 9-point calibration.
    After completion, returns a trained sklearn Pipeline for gaze→screen mapping.
    """

    def __init__(self, gaze_engine):
        self.gaze_engine = gaze_engine
        self.root = None
        self.canvas = None
        self.screen_w = 0
        self.screen_h = 0
        self.calibration_points = []    # list of (screen_x, screen_y)
        self.gaze_samples = []          # list of lists of raw gaze vectors
        self.model = None
        self.accuracy_score = None
        self._current_point_idx = 0
        self._collecting = False
        self._done = False

    # ── Public API ───────────────────────────────────────────────────────────

    def run(self):
        """
        Block until calibration is complete.
        Returns trained sklearn Pipeline or None on failure.
        """
        self.root = tk.Tk()
        self.root.attributes("-fullscreen", True)
        self.root.configure(bg=CONFIG["BG_COLOR"])
        self.root.title("Eye Gaze Typer – Calibration")

        self.screen_w = self.root.winfo_screenwidth()
        self.screen_h = self.root.winfo_screenheight()

        self.canvas = tk.Canvas(
            self.root,
            width=self.screen_w,
            height=self.screen_h,
            bg=CONFIG["BG_COLOR"],
            highlightthickness=0,
        )
        self.canvas.pack()

        self._build_calibration_points()
        self._draw_instructions()

        # Start calibration after a short delay
        self.root.after(2000, self._start_calibration)
        self.root.mainloop()

        return self.model

    def load_saved_model(self):
        """
        Load a previously saved calibration model from JSON.
        Returns a trained Pipeline or None.
        """
        path = CONFIG["CALIBRATION_FILE"]
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r") as f:
                data = json.load(f)
            raw = np.array(data["raw_gaze"])
            screen = np.array(data["screen_coords"])
            return self._fit_model(raw, screen)
        except Exception as e:
            print(f"[Calibration] Failed to load saved data: {e}")
            return None

    # ── Internal ─────────────────────────────────────────────────────────────

    def _build_calibration_points(self):
        """Generate 9 evenly-spaced calibration points with margin."""
        margin_x = int(self.screen_w * CONFIG["MARGIN_FRACTION"])
        margin_y = int(self.screen_h * CONFIG["MARGIN_FRACTION"])
        xs = np.linspace(margin_x, self.screen_w - margin_x, CONFIG["GRID_SIZE"])
        ys = np.linspace(margin_y, self.screen_h - margin_y, CONFIG["GRID_SIZE"])
        self.calibration_points = [(int(x), int(y)) for y in ys for x in xs]

    def _draw_instructions(self):
        """Show initial instruction text."""
        self.canvas.delete("all")
        self.canvas.create_text(
            self.screen_w // 2, self.screen_h // 2,
            text="CALIBRATION\n\nStare at each red dot until it turns green.\nKeep your head still.\n\nStarting in 2 seconds...",
            fill=CONFIG["TEXT_COLOR"],
            font=("Arial", 28, "bold"),
            justify="center",
        )

    def _start_calibration(self):
        """Begin the calibration sequence."""
        self._current_point_idx = 0
        self.gaze_samples = []
        self._show_point(self._current_point_idx)

    def _show_point(self, idx):
        """Draw the current calibration dot and schedule sample collection."""
        if idx >= len(self.calibration_points):
            self._finish_calibration()
            return

        px, py = self.calibration_points[idx]
        self.canvas.delete("all")

        # Progress indicator
        self.canvas.create_text(
            self.screen_w // 2, 40,
            text=f"Point {idx + 1} of {len(self.calibration_points)} – Stare at the dot",
            fill=CONFIG["TEXT_COLOR"],
            font=("Arial", 20),
        )

        # Draw all upcoming dots faintly
        for i, (x, y) in enumerate(self.calibration_points):
            if i > idx:
                self.canvas.create_oval(
                    x - 6, y - 6, x + 6, y + 6,
                    fill="#555555", outline=""
                )
            elif i < idx:
                self.canvas.create_oval(
                    x - 8, y - 8, x + 8, y + 8,
                    fill=CONFIG["DOT_COLOR_DONE"], outline=""
                )

        # Current dot (idle colour)
        r = CONFIG["DOT_RADIUS"]
        dot_id = self.canvas.create_oval(
            px - r, py - r, px + r, py + r,
            fill=CONFIG["DOT_COLOR_IDLE"], outline="#FFFFFF", width=2,
            tags="current_dot"
        )

        # After a brief look-ahead pause, start collecting
        self.root.after(800, lambda: self._collect_samples(idx, px, py))

    def _collect_samples(self, idx, px, py):
        """Change dot to green and collect gaze samples over STARE_DURATION."""
        self.canvas.itemconfig("current_dot", fill=CONFIG["DOT_COLOR_ACTIVE"])
        samples = []
        start = time.time()
        interval_ms = int(CONFIG["STARE_DURATION"] * 1000 / CONFIG["SAMPLES_PER_POINT"])

        def collect_one():
            raw = self.gaze_engine.get_raw_gaze()
            samples.append(list(raw))
            elapsed = time.time() - start
            # Update progress ring
            progress = min(elapsed / CONFIG["STARE_DURATION"], 1.0)
            self._draw_progress_ring(px, py, progress)

            if len(samples) < CONFIG["SAMPLES_PER_POINT"]:
                self.root.after(interval_ms, collect_one)
            else:
                self.gaze_samples.append(samples)
                self._current_point_idx += 1
                self.root.after(300, lambda: self._show_point(self._current_point_idx))

        collect_one()

    def _draw_progress_ring(self, cx, cy, progress):
        """Draw an arc around the dot showing collection progress."""
        self.canvas.delete("progress_ring")
        r = CONFIG["DOT_RADIUS"] + 8
        extent = progress * 359.9
        self.canvas.create_arc(
            cx - r, cy - r, cx + r, cy + r,
            start=90, extent=-extent,
            outline="#FFFF00", width=4, style="arc",
            tags="progress_ring"
        )

    def _finish_calibration(self):
        """Fit regression model and show accuracy."""
        self.canvas.delete("all")
        self.canvas.create_text(
            self.screen_w // 2, self.screen_h // 2,
            text="Processing calibration data...",
            fill=CONFIG["TEXT_COLOR"],
            font=("Arial", 24, "bold"),
        )
        self.root.update()

        # Build training arrays
        raw_list, screen_list = [], []
        for i, samples in enumerate(self.gaze_samples):
            px, py = self.calibration_points[i]
            for s in samples:
                raw_list.append(s)
                screen_list.append([px, py])

        raw_arr = np.array(raw_list)
        screen_arr = np.array(screen_list)

        self.model = self._fit_model(raw_arr, screen_arr)
        self.accuracy_score = self._compute_accuracy(raw_arr, screen_arr)

        # Save to JSON
        self._save_calibration(raw_arr, screen_arr)

        # Show result
        self.canvas.delete("all")
        self.canvas.create_text(
            self.screen_w // 2, self.screen_h // 2,
            text=f"Calibration Complete!\n\nAccuracy: {self.accuracy_score:.1f}%\n\nClosing in 3 seconds...",
            fill="#33FF33",
            font=("Arial", 28, "bold"),
            justify="center",
        )
        self.root.after(3000, self.root.destroy)

    def _fit_model(self, raw, screen):
        """Fit a polynomial regression pipeline: raw gaze → screen XY."""
        model = Pipeline([
            ("poly", PolynomialFeatures(degree=CONFIG["POLY_DEGREE"])),
            ("reg", Ridge(alpha=1.0)),
        ])
        model.fit(raw, screen)
        return model

    def _compute_accuracy(self, raw, screen):
        """
        Compute accuracy as 100 - mean_error_fraction.
        Mean error is normalised by screen diagonal.
        """
        pred = self.model.predict(raw)
        errors = np.linalg.norm(pred - screen, axis=1)
        diag = np.sqrt(self.screen_w ** 2 + self.screen_h ** 2)
        mean_err_frac = errors.mean() / diag
        return max(0.0, (1.0 - mean_err_frac) * 100)

    def _save_calibration(self, raw, screen):
        """Persist calibration data to JSON for future sessions."""
        data = {
            "raw_gaze": raw.tolist(),
            "screen_coords": screen.tolist(),
            "screen_size": [self.screen_w, self.screen_h],
            "accuracy": self.accuracy_score,
        }
        with open(CONFIG["CALIBRATION_FILE"], "w") as f:
            json.dump(data, f, indent=2)
        print(f"[Calibration] Saved to {CONFIG['CALIBRATION_FILE']}")
>>>>>>> 52c3d7ea5ed405484f229b508704a40d14764e6c
