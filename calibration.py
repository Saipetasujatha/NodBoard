"""
calibration.py
--------------
9-point fullscreen calibration for gaze-to-screen mapping.
"""

import tkinter as tk
import numpy as np
import json
import time
import os
import threading
from sklearn.preprocessing import PolynomialFeatures
from sklearn.linear_model import LinearRegression

CONFIG = {
    'calibration_points': 9,
    'samples_per_point': 30,
    'dwell_time': 2.0,
    'point_radius': 15,
    'polynomial_degree': 2,
}


class CalibrationSystem:

    def __init__(self, gaze_engine):
        self.gaze_engine = gaze_engine
        self.calibration_data = None
        self.is_calibrating = False
        self.callback = None
        self.calibration_window = None

        self.grid_points = [
            (0.1, 0.1), (0.5, 0.1), (0.9, 0.1),
            (0.1, 0.5), (0.5, 0.5), (0.9, 0.5),
            (0.1, 0.9), (0.5, 0.9), (0.9, 0.9),
        ]

    def start_calibration(self, parent_window, callback):
        self.callback = callback
        self.calibration_window = tk.Toplevel(parent_window)
        self.calibration_window.title("Gaze Calibration")
        self.calibration_window.attributes('-fullscreen', True)
        self.calibration_window.configure(bg='black')

        self.raw_gaze_samples = []
        self.screen_targets = []

        self.instruction_label = tk.Label(
            self.calibration_window,
            text="Look at the red dot and keep your eyes still",
            font=('Arial', 24), fg='white', bg='black'
        )
        self.instruction_label.pack(pady=50)

        self.progress_label = tk.Label(
            self.calibration_window,
            text="", font=('Arial', 18), fg='white', bg='black'
        )
        self.progress_label.pack(pady=20)

        self.canvas = tk.Canvas(
            self.calibration_window, bg='black', highlightthickness=0
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.calibration_window.bind('<Escape>', lambda e: self.cancel_calibration())

        self.is_calibrating = True
        self.current_point_index = 0
        self.samples_collected = 0
        self.point_start_time = time.time()

        t = threading.Thread(target=self._calibration_loop, daemon=True)
        t.start()

    def _calibration_loop(self):
        while self.is_calibrating and self.current_point_index < len(self.grid_points):
            try:
                frame, gaze_point, fps = self.gaze_engine.get_frame_and_gaze()
                if gaze_point is not None:
                    current_time = time.time()
                    if current_time - self.point_start_time >= CONFIG['dwell_time']:
                        self.raw_gaze_samples.append(gaze_point)
                        self.screen_targets.append(self.grid_points[self.current_point_index])
                        self.samples_collected += 1
                        self._update_progress()
                        if self.samples_collected >= CONFIG['samples_per_point']:
                            self._next_point()
                    self._update_display()
                time.sleep(0.03)
            except Exception as e:
                print(f"Calibration error: {e}")
                self.cancel_calibration()
                break

        if self.is_calibrating:
            self._complete_calibration()

    def _update_display(self):
        if not self.is_calibrating:
            return
        try:
            self.canvas.delete("all")
            if self.current_point_index < len(self.grid_points):
                sw = self.calibration_window.winfo_width()
                sh = self.calibration_window.winfo_height()
                if sw > 1 and sh > 1:
                    tx, ty = self.grid_points[self.current_point_index]
                    px = int(tx * sw)
                    py = int(ty * sh)
                    r = CONFIG['point_radius']
                    self.canvas.create_oval(px-r, py-r, px+r, py+r,
                                            fill='red', outline='white', width=2)
                    self.canvas.create_line(px-10, py, px+10, py, fill='white', width=2)
                    self.canvas.create_line(px, py-10, px, py+10, fill='white', width=2)
        except Exception:
            pass

    def _update_progress(self):
        try:
            pt = self.current_point_index + 1
            sp = self.samples_collected + 1
            self.progress_label.config(
                text=f"Point {pt}/9 — Sample {sp}/{CONFIG['samples_per_point']}"
            )
        except Exception:
            pass

    def _next_point(self):
        self.current_point_index += 1
        self.samples_collected = 0
        self.point_start_time = time.time()
        remaining = len(self.grid_points) - self.current_point_index
        if remaining > 0:
            try:
                self.instruction_label.config(
                    text=f"Look at the red dot. {remaining} points remaining."
                )
            except Exception:
                pass

    def _complete_calibration(self):
        try:
            X = np.array(self.raw_gaze_samples)
            y = np.array(self.screen_targets)
            degree = CONFIG['polynomial_degree']
            poly = PolynomialFeatures(degree=degree, include_bias=True)
            X_poly = poly.fit_transform(X)
            model_x = LinearRegression()
            model_y = LinearRegression()
            model_x.fit(X_poly, y[:, 0])
            model_y.fit(X_poly, y[:, 1])
            y_pred_x = model_x.predict(X_poly)
            y_pred_y = model_y.predict(X_poly)
            errors = np.sqrt((y_pred_x - y[:, 0])**2 + (y_pred_y - y[:, 1])**2)
            accuracy = max(0, 100 - float(errors.mean()) * 100)

            self.calibration_data = {
                'degree': degree,
                'coef_x': model_x.coef_.tolist(),
                'intercept_x': float(model_x.intercept_),
                'coef_y': model_y.coef_.tolist(),
                'intercept_y': float(model_y.intercept_),
                'accuracy': accuracy,
                'samples': len(self.raw_gaze_samples),
            }
            try:
                self.instruction_label.config(text="Calibration Complete!")
                self.progress_label.config(text=f"Accuracy: {accuracy:.1f}%")
            except Exception:
                pass
            self.calibration_window.after(2500, lambda: self._finish(True))
        except Exception as e:
            print(f"Calibration completion error: {e}")
            self._finish(False)

    def _finish(self, success):
        self.is_calibrating = False
        try:
            self.calibration_window.destroy()
        except Exception:
            pass
        if self.callback:
            self.callback(success, self.calibration_data if success else None)

    def cancel_calibration(self):
        self.is_calibrating = False
        try:
            self.calibration_window.destroy()
        except Exception:
            pass
        if self.callback:
            self.callback(False, None)

    def map_gaze_to_screen(self, gaze_point):
        if not self.calibration_data or gaze_point is None:
            return gaze_point
        try:
            degree = self.calibration_data.get('degree', 2)
            poly = PolynomialFeatures(degree=degree, include_bias=True)
            X_poly = poly.fit_transform(np.array([gaze_point]))
            coef_x = np.array(self.calibration_data['coef_x'])
            intercept_x = float(self.calibration_data['intercept_x'])
            coef_y = np.array(self.calibration_data['coef_y'])
            intercept_y = float(self.calibration_data['intercept_y'])
            screen_x = float(X_poly.dot(coef_x) + intercept_x)
            screen_y = float(X_poly.dot(coef_y) + intercept_y)
            return (np.clip(screen_x, 0, 1), np.clip(screen_y, 0, 1))
        except Exception as e:
            print(f"Gaze mapping error: {e}")
            return gaze_point