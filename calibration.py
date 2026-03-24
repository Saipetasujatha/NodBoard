"""
calibration.py
--------------
9-point fullscreen calibration screen.
Collects gaze samples at each point, fits a polynomial regression
model, saves calibration_data.json, and returns the trained model.
"""

import tkinter as tk
import numpy as np
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
