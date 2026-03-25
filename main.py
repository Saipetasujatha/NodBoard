"""
NodBoard - Main Application Entry Point
- No profile popup, opens directly
- Guest mode by default
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import time
import json
import os
import pyperclip
from PIL import Image, ImageTk
import cv2

try:
    import keyboard as kb_module
    KEYBOARD_HOTKEYS = True
except ImportError:
    KEYBOARD_HOTKEYS = False
    print("Warning: 'keyboard' module not found. Hotkeys disabled.")

from gaze_engine import GazeEngine
from calibration import CalibrationSystem
from keyboard_ui import VirtualKeyboard
from word_predictor import WordPredictor
from voice_output import VoiceOutput
from blink_detector import BlinkDetector
from settings import SettingsManager
from profiles import ProfileManager
from heatmap import GazeHeatmap

CONFIG = {
    'window_title': 'NodBoard',
    'window_width': 1200,
    'window_height': 800,
    'camera_width': 320,
    'camera_height': 240,
    'update_interval': 30,
    'autosave_interval': 30,
    'max_undo_steps': 20,
    'bg_color': '#f5f5f5',
    'text_bg': '#ffffff',
    'text_fg': '#222222',
}


class EyeGazeTyperApp:

    def __init__(self, root):
        self.root = root
        self.root.title(CONFIG['window_title'])
        self.root.geometry(f"{CONFIG['window_width']}x{CONFIG['window_height']}")
        self.root.minsize(1000, 600)
        self.root.configure(bg=CONFIG['bg_color'])

        self.settings_manager = SettingsManager()
        self.profile_manager  = ProfileManager()
        self.voice_output     = VoiceOutput()
        self.word_predictor   = WordPredictor()
        self.blink_detector   = BlinkDetector()
        self.gaze_heatmap     = GazeHeatmap()

        self.gaze_engine        = None
        self.calibration_system = None
        self.virtual_keyboard   = None

        self.is_running          = False
        self.is_calibrated       = False
        self.is_tracking_paused  = False
        self.current_text        = ""
        self.undo_stack          = []
        self.redo_stack          = []
        self.last_autosave       = time.time()
        self.gaze_points         = []
        self.session_start_time  = time.time()
        self.current_profile     = None
        self.calibration_data    = None

        self.camera_label           = None
        self.text_area              = None
        self.word_suggestions_frame = None
        self.keyboard_frame         = None
        self.fps_var   = tk.StringVar(value="FPS: 0")
        self.wpm_var   = tk.StringVar(value="WPM: 0")
        self.blink_var = tk.StringVar(value="BLINK: ready")

        self._setup_hotkeys()

        # ── Skip popup, open directly in Guest Mode ────────────────────────────
        self._load_profile(None)
        self.initialize_main_ui()

    def _setup_hotkeys(self):
        if not KEYBOARD_HOTKEYS:
            return
        try:
            kb_module.add_hotkey('r',      self.start_recalibration)
            kb_module.add_hotkey('ctrl+s', self.save_text)
            kb_module.add_hotkey('ctrl+z', self.undo)
            kb_module.add_hotkey('ctrl+y', self.redo)
            kb_module.add_hotkey('ctrl+c', self.copy_text)
            kb_module.add_hotkey('f1',     self.toggle_theme)
            kb_module.add_hotkey('f2',     self.toggle_word_prediction)
            kb_module.add_hotkey('f3',     self.show_heatmap)
            kb_module.add_hotkey('space',  self.toggle_tracking_pause)
        except Exception as e:
            print(f"Hotkey setup warning: {e}")

    def _load_profile(self, name):
        self.current_profile = name
        if name:
            self.settings_manager.load_settings(name)
            self.word_predictor.load_history(name)
            calib_file = f"profiles/{name}/calibration_data.json"
            if os.path.exists(calib_file):
                try:
                    with open(calib_file) as f:
                        self.calibration_data = json.load(f)
                    self.is_calibrated = True
                except Exception as e:
                    print(f"Could not load calibration: {e}")
                    self.is_calibrated = False
        else:
            self.is_calibrated = False

    def initialize_main_ui(self):
        self._build_ui()
        self._init_components()
        # Skip calibration, go directly to app
        self.start_application()

    def _build_ui(self):
        root_frame = tk.Frame(self.root, bg=CONFIG['bg_color'])
        root_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # ── Top bar ────────────────────────────────────────────────────────────
        top = tk.Frame(root_frame, bg=CONFIG['bg_color'])
        top.pack(fill=tk.X, pady=(0, 4))

        self.camera_label = tk.Label(top, bg='#000000',
                                     width=CONFIG['camera_width'],
                                     height=CONFIG['camera_height'])
        self.camera_label.pack(side=tk.LEFT, padx=(0, 8))

        info = tk.Frame(top, bg=CONFIG['bg_color'])
        info.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tk.Label(info, text="👁 NodBoard",
                 bg=CONFIG['bg_color'], fg='#1565C0',
                 font=('Arial', 18, 'bold')).pack(anchor='w')

        tk.Label(info, textvariable=self.fps_var,
                 bg=CONFIG['bg_color'], fg='#388e3c',
                 font=('Courier', 11)).pack(anchor='w')

        tk.Label(info, text="Guest Mode",
                 bg=CONFIG['bg_color'], fg='#888888',
                 font=('Arial', 10)).pack(anchor='w')

        # ── Text area ──────────────────────────────────────────────────────────
        text_outer = tk.Frame(root_frame, bg='#1565C0', bd=1)
        text_outer.pack(fill=tk.BOTH, expand=False, pady=(0, 4))

        tk.Label(text_outer, text="Typed text",
                 bg='#1565C0', fg='#ffffff',
                 font=('Arial', 9)).pack(anchor='w', padx=4)

        self.text_area = tk.Text(
            text_outer,
            height=5,
            bg=CONFIG['text_bg'],
            fg=CONFIG['text_fg'],
            insertbackground='black',
            font=('Arial', 14),
            wrap=tk.WORD,
            relief='flat',
            padx=8, pady=6
        )
        self.text_area.pack(fill=tk.BOTH, expand=True, padx=2, pady=(0, 2))

        # ── Word suggestions (hidden) ──────────────────────────────────────────
        self.word_suggestions_frame = tk.Frame(root_frame, bg=CONFIG["bg_color"])
        self.suggestion_buttons = []
        for i in range(4):
            btn = tk.Button(
                self.word_suggestions_frame,
                text="",
                bg='#1976D2', fg='white',
                font=('Arial', 12),
                relief='flat', padx=8, pady=4,
                command=lambda idx=i: self._select_suggestion(idx)
            )
            btn.pack(side=tk.LEFT, padx=3, expand=True, fill=tk.X)
            self.suggestion_buttons.append(btn)

        # ── Keyboard frame ─────────────────────────────────────────────────────
        self.keyboard_frame = tk.Frame(root_frame, bg='#f5f5f5')
        self.keyboard_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 4))

        # ── Status bar ─────────────────────────────────────────────────────────
        status = tk.Frame(root_frame, bg='#e3f2fd')
        status.pack(fill=tk.X)

        tk.Label(status, textvariable=self.blink_var,
                 bg='#e3f2fd', fg='#1565C0',
                 font=('Courier', 10)).pack(side=tk.LEFT, padx=6)

        tk.Label(status, textvariable=self.wpm_var,
                 bg='#e3f2fd', fg='#555555',
                 font=('Courier', 10)).pack(side=tk.RIGHT, padx=6)

        tk.Button(status, text="⚙ Settings",
                  bg='#1565C0', fg='white',
                  relief='flat', padx=6,
                  command=self.show_settings).pack(side=tk.RIGHT, padx=6)

    def _init_components(self):
        try:
            self.gaze_engine = GazeEngine()
            self.calibration_system = CalibrationSystem(self.gaze_engine)

            self.virtual_keyboard = VirtualKeyboard(
                self.keyboard_frame,
                self.on_key_pressed
            )
            self.virtual_keyboard.set_theme('dark')

        except Exception as e:
            messagebox.showerror("Init Error", f"Failed to start components:\n{e}")
            self.root.quit()

    def start_calibration(self):
        if messagebox.askyesno("Calibration",
                               "Start 9-point calibration now?\n"
                               "Look at each red dot until it moves."):
            self.calibration_system.start_calibration(
                self.root, self._on_calibration_done
            )
        else:
            self.start_application()

    def _on_calibration_done(self, success, data):
        if success:
            self.calibration_data = data
            self.is_calibrated = True
            self.start_application()
        else:
            messagebox.showerror("Calibration Failed", "Press R to try again.")
            self.start_application()

    def start_recalibration(self):
        if self.is_running:
            self.is_tracking_paused = True
            self.calibration_system.start_calibration(
                self.root, self._on_recalibration_done
            )

    def _on_recalibration_done(self, success, data):
        self.is_tracking_paused = False
        if success:
            self.calibration_data = data
            self.is_calibrated = True
            messagebox.showinfo("Done", "Recalibration successful!")
        else:
            messagebox.showerror("Error", "Recalibration failed.")

    def start_application(self):
        self.is_running = True
        self.session_start_time = time.time()
        self.update_ui()

    def update_ui(self):
        try:
            if not self.is_tracking_paused:
                frame, gaze_point, fps = self.gaze_engine.get_frame_and_gaze()

                if frame is not None:
                    self._update_camera(frame)
                    self.fps_var.set(f"FPS: {fps}")

                if gaze_point is not None:
                    self._process_gaze(gaze_point)

                eye_lm = self.gaze_engine.get_eye_landmarks()
                if eye_lm:
                    blink = self.blink_detector.detect_blink(eye_lm)
                    if blink:
                        self._handle_blink(blink)

            self._update_suggestions()

            if time.time() - self.last_autosave > CONFIG['autosave_interval']:
                self._auto_save()
                self.last_autosave = time.time()

            elapsed = max(1, time.time() - self.session_start_time)
            words = len(self.current_text.split())
            self.wpm_var.set(f"WPM: {int(words / elapsed * 60)}")

        except Exception as e:
            print(f"Update loop error: {e}")
        finally:
            self.root.after(CONFIG['update_interval'], self.update_ui)

    def _update_camera(self, frame):
        try:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(rgb).resize(
                (CONFIG['camera_width'], CONFIG['camera_height'])
            )
            imgtk = ImageTk.PhotoImage(image=img)
            self.camera_label.config(image=imgtk)
            self.camera_label.image = imgtk
        except Exception as e:
            print(f"Camera update error: {e}")

    def _process_gaze(self, gaze_point):
        try:
            gaze_x = float(gaze_point[0])
            gaze_y = float(gaze_point[1])

            if self.is_calibrated:
                try:
                    gaze_x, gaze_y = self.calibration_system.map_gaze_to_screen(
                        (gaze_x, gaze_y)
                    )
                    gaze_x = float(gaze_x)
                    gaze_y = float(gaze_y)
                except Exception:
                    pass

            # Wait until keyboard frame has real size
            kb_w = self.keyboard_frame.winfo_width()
            kb_h = self.keyboard_frame.winfo_height()
            if kb_w < 10 or kb_h < 10:
                return

            # Exact measured range from hardware
            GAZE_MIN_X = 0.4012
            GAZE_MAX_X = 0.4896
            GAZE_MIN_Y = 0.8574
            GAZE_MAX_Y = 0.9503

            mapped_x = (gaze_x - GAZE_MIN_X) / (GAZE_MAX_X - GAZE_MIN_X)
            mapped_y = (gaze_y - GAZE_MIN_Y) / (GAZE_MAX_Y - GAZE_MIN_Y)

            mapped_x = max(0.0, min(1.0, mapped_x))
            mapped_y = max(0.0, min(1.0, mapped_y))

            self.virtual_keyboard.update_gaze(mapped_x, mapped_y)
            self.gaze_points.append((gaze_x, gaze_y))

        except Exception as e:
            print(f"Gaze processing error: {e}")

    def on_key_pressed(self, key):
        self.undo_stack.append(self.text_area.get("1.0", tk.END))
        if len(self.undo_stack) > CONFIG['max_undo_steps']:
            self.undo_stack.pop(0)
        self.redo_stack.clear()

        if key == 'BKSP':
            self.text_area.delete("end-2c", tk.END)
        elif key == 'ENTER':
            self.text_area.insert(tk.END, '\n')
        elif key == 'SPACE':
            self.text_area.insert(tk.END, ' ')
        elif key == 'CLEAR':
            self.text_area.delete("1.0", tk.END)
        elif key == 'SPEAK':
            text = self.text_area.get("1.0", tk.END).strip()
            if text:
                self.voice_output.speak(text)
        elif key == 'SAVE':
            self.save_text()
        elif key in ('PREDICT', 'SETTINGS'):
            print(f"Action: {key}")
        else:
            self.text_area.insert(tk.END, key)

    def _handle_blink(self, blink_type):
        if blink_type == 'double':
            self.text_area.delete("end-2c", tk.END)
        elif blink_type == 'long':
            self.text_area.insert(tk.END, ' ')
        self.blink_var.set(f"BLINK: {blink_type}")

    def _update_suggestions(self):
        try:
            text = self.text_area.get("1.0", tk.END).strip()
            if text != self.current_text:
                self.current_text = text
                suggestions = self.word_predictor.get_suggestions(text)
                for i, btn in enumerate(self.suggestion_buttons):
                    word = suggestions[i] if i < len(suggestions) else ""
                    btn.config(text=word)
        except Exception:
            pass

    def _select_suggestion(self, index):
        try:
            word = self.suggestion_buttons[index].cget("text")
            if word:
                text = self.text_area.get("1.0", tk.END)
                words = text.split()
                if words:
                    words[-1] = word
                    self.text_area.delete("1.0", tk.END)
                    self.text_area.insert("1.0", ' '.join(words) + ' ')
        except Exception as e:
            print(f"Suggestion error: {e}")

    def save_text(self):
        text = self.text_area.get("1.0", tk.END).strip()
        if not text:
            messagebox.showwarning("Empty", "Nothing to save yet.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if path:
            with open(path, 'w') as f:
                f.write(text)
            messagebox.showinfo("Saved", f"Saved to {path}")

    def _auto_save(self):
        text = self.text_area.get("1.0", tk.END).strip()
        if text:
            try:
                with open("autosave.txt", 'w') as f:
                    f.write(text)
            except Exception:
                pass

    def undo(self):
        if self.undo_stack:
            self.redo_stack.append(self.text_area.get("1.0", tk.END))
            self.text_area.delete("1.0", tk.END)
            self.text_area.insert("1.0", self.undo_stack.pop())

    def redo(self):
        if self.redo_stack:
            self.undo_stack.append(self.text_area.get("1.0", tk.END))
            self.text_area.delete("1.0", tk.END)
            self.text_area.insert("1.0", self.redo_stack.pop())

    def copy_text(self):
        text = self.text_area.get("1.0", tk.END).strip()
        pyperclip.copy(text)
        messagebox.showinfo("Copied", "Text copied to clipboard.")

    def toggle_theme(self):
        cur = self.settings_manager.get_setting('theme', 'dark')
        new = 'light' if cur == 'dark' else 'dark'
        self.settings_manager.set_setting('theme', new)
        self.virtual_keyboard.set_theme(new)

    def toggle_word_prediction(self):
        cur = self.settings_manager.get_setting('word_prediction', True)
        new = not cur
        self.settings_manager.set_setting('word_prediction', new)
        if new:
            pass
        else:
            self.word_suggestions_frame.pack_forget()

    def show_heatmap(self):
        if self.gaze_points:
            self.gaze_heatmap.generate_heatmap(
                self.gaze_points,
                self.virtual_keyboard.get_key_positions()
            )
            self.gaze_heatmap.show_heatmap()
        else:
            messagebox.showinfo("Info", "No gaze data yet.")

    def toggle_tracking_pause(self):
        self.is_tracking_paused = not self.is_tracking_paused
        state = "PAUSED" if self.is_tracking_paused else "ACTIVE"
        self.fps_var.set(f"Tracking: {state}")

    def show_settings(self):
        messagebox.showinfo(
            "Settings",
            "Keyboard shortcuts:\n"
            "R = Recalibrate\n"
            "F1 = Toggle theme\n"
            "F2 = Toggle word prediction\n"
            "F3 = Show heatmap\n"
            "SPACE = Pause/resume tracking\n"
            "Ctrl+S = Save text\n"
            "Ctrl+Z = Undo\n"
            "Ctrl+C = Copy"
        )

    def quit_app(self):
        if messagebox.askyesno("Quit", "Exit NodBoard?"):
            self.is_running = False
            try:
                self.root.quit()
            except Exception:
                pass


def main():
    root = tk.Tk()
    app = EyeGazeTyperApp(root)
    root.protocol("WM_DELETE_WINDOW", app.quit_app)
    root.mainloop()


if __name__ == "__main__":
    main()