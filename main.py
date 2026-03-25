<<<<<<< HEAD
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
=======
import ctypes
ctypes.windll.user32.SetProcessDPIAware()
import cv2
import mediapipe as mp
import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk
import threading
import time

try:
    import speech_recognition as sr
except ImportError:
    sr = None

try:
    from voice_output import VoiceOutput
    vo = VoiceOutput()
except:
    vo = None

# ── DEBUG CONFIG ─────────────────────────────────────────────────────────────
DEBUG_MODE = True  # Set False for production fullscreen

# ── WINDOW SETUP ──────────────────────────────────────────────────────────────
root = tk.Tk()
root.title("Eye Gaze Typer")
if DEBUG_MODE:
    root.geometry('1280x800')
    root.attributes('-fullscreen', False)
else:
    root.attributes('-fullscreen', True)
root.attributes('-topmost', True)
root.configure(bg='#f0f4f8')
root.focus_force()

# ── STATE VARIABLES ───────────────────────────────────────────────────────────
typed_text = ['']
dwell_time = [0.8]
auto_speak = [False]
session_start = time.time()
fps_counter = [0]
last_fps_time = [time.time()]

# ── TOP BAR ───────────────────────────────────────────────────────────────────
top_frame = tk.Frame(root, bg='#f0f4f8', height=160)
top_frame.pack(fill='x', padx=4, pady=4)

# Camera preview (200x150 actual pixels)
cam_label = tk.Label(top_frame, bg='black')
cam_label.pack(side='left', padx=(0, 12), pady=4)
cam_label.configure(width=200, height=150)

# Ensure camera label has a fixed pixel size in debug mode
cam_label.bind('<Configure>', lambda e: cam_label.config(width=200, height=150))

# Title and stats
info_frame = tk.Frame(top_frame, bg='#f0f4f8')
info_frame.pack(side='left', fill='both', expand=True)

title_label = tk.Label(info_frame, text="GAZE TYPER", font=("Arial", 24, "bold"),
                       bg='#f0f4f8', fg='#000')
title_label.pack(anchor='w')

fps_label = tk.Label(info_frame, text="FPS: --", font=('Arial', 12), bg='#f0f4f8')
fps_label.pack(side='left', padx=10)

wpm_label = tk.Label(info_frame, text="WPM: 0", font=('Arial', 12), bg='#f0f4f8')
wpm_label.pack(side='left', padx=10)

timer_label = tk.Label(info_frame, text="00:00", font=('Arial', 12), bg='#f0f4f8')
timer_label.pack(side='left', padx=10)

# Status
sv = tk.StringVar(value='Starting...')
status_label = tk.Label(root, textvariable=sv, bg='#f0f4f8', fg='green',
                        font=('Arial', 14, 'bold'))
status_label.pack(fill='x', padx=4, pady=2)

# ── TEXT AREA ─────────────────────────────────────────────────────────────────
text_frame = tk.Frame(root, bg='white', height=80)
text_frame.pack(fill='x', padx=4, pady=4)

text_display = tk.Label(text_frame, text='', bg='white', fg='black',
                        font=('Arial', 18), anchor='w', justify='left')
text_display.pack(fill='both', expand=True, padx=10, pady=10)

# Suggestions
suggestion_frame = tk.Frame(root, bg='#f0f4f8', height=40)
suggestion_frame.pack(fill='x', padx=4, pady=2)

suggestion_vars = [tk.StringVar() for _ in range(4)]
suggestion_labels = []
for i in range(4):
    lbl = tk.Label(suggestion_frame, textvariable=suggestion_vars[i], bg='#e3f2fd',
                   fg='#000', font=('Arial', 12), relief='raised', padx=8, pady=4)
    lbl.pack(side='left', padx=2)
    suggestion_labels.append(lbl)

# ── KEYBOARD CANVAS ───────────────────────────────────────────────────────────
canvas = tk.Canvas(root, bg='white', highlightthickness=0)
canvas.pack(fill='both', expand=True, padx=4, pady=4)
canvas.bind('<Configure>', lambda e: setup_keys())

# ── WORD LIST ─────────────────────────────────────────────────────────────────
WORD_LIST = ["the","and","you","have","that","this","with","for",
             "are","not","but","can","was","will","from","they",
             "what","when","your","said","she","which","do","their",
             "time","if","up","other","about","out","many","then",
             "some","her","would","make","like","him","into","has",
             "look","more","go","no","most","people","my","over"]

# ── FUNCTIONS ─────────────────────────────────────────────────────────────────

def update_suggestions():
    if not typed_text[0].strip():
        words = ["the", "and", "you", "have"]
    else:
        last = typed_text[0].strip().split()[-1].lower()
        matches = [w for w in WORD_LIST if w.startswith(last) and w != last]
        words = matches[:4] if matches else ["the", "and", "you", "have"]
    for i, var in enumerate(suggestion_vars):
        var.set(words[i] if i < len(words) else '')

def type_char(char):
    typed_text[0] += char
    text_display.config(text=typed_text[0])
    update_suggestions()

def do_backspace():
    typed_text[0] = typed_text[0][:-1]
    text_display.config(text=typed_text[0])
    update_suggestions()

def do_enter():
    typed_text[0] += '\n'
    text_display.config(text=typed_text[0])
    update_suggestions()

def do_space():
    if auto_speak[0] and typed_text[0].strip():
        words = typed_text[0].strip().split()
        if words:
            threading.Thread(target=lambda: vo.speak(words[-1]) if vo else None, daemon=True).start()
    typed_text[0] += ' '
    text_display.config(text=typed_text[0])
    update_suggestions()

def do_clear():
    typed_text[0] = ''
    text_display.config(text='')
    update_suggestions()

def do_speak():
    if vo and typed_text[0].strip():
        threading.Thread(target=lambda: vo.speak(typed_text[0]), daemon=True).start()

def do_save():
    if not typed_text[0].strip():
        return
    path = filedialog.asksaveasfilename(defaultextension='.txt',
           filetypes=[('Text','*.txt')], parent=root)
    if path:
        open(path, 'w', encoding='utf-8').write(typed_text[0])
        sv.set('Saved! ✅')
        root.after(2000, lambda: sv.set('TRACKING'))

def do_copy():
    try:
        import pyperclip
        pyperclip.copy(typed_text[0])
    except:
        root.clipboard_clear()
        root.clipboard_append(typed_text[0])
        root.update()
    sv.set('Copied! ✅')
    root.after(2000, lambda: sv.set('TRACKING'))

def do_mic():
    threading.Thread(target=listen_and_type, daemon=True).start()

def listen_and_type():
    sv.set('🎤 Listening...')
    try:
        if sr:
            r = sr.Recognizer()
            with sr.Microphone() as source:
                r.adjust_for_ambient_noise(source, duration=0.3)
                audio = r.listen(source, timeout=5, phrase_time_limit=8)
            text = r.recognize_google(audio)
            typed_text[0] += text + ' '
            text_display.config(text=typed_text[0])
            sv.set(f'✅ Typed: {text}')
    except:
        sv.set('❌ Could not hear')
    root.after(2000, lambda: sv.set('TRACKING'))

def dwell_minus():
    dwell_time[0] = max(0.3, dwell_time[0] - 0.1)
    sv.set(f'Dwell: {dwell_time[0]:.1f}s')
    root.after(1500, lambda: sv.set('TRACKING'))

def dwell_plus():
    dwell_time[0] = min(3.0, dwell_time[0] + 0.1)
    sv.set(f'Dwell: {dwell_time[0]:.1f}s')
    root.after(1500, lambda: sv.set('TRACKING'))

def sens_minus():
    sv.set('Sensitivity decreased')
    root.after(1500, lambda: sv.set('TRACKING'))

def sens_plus():
    sv.set('Sensitivity increased')
    root.after(1500, lambda: sv.set('TRACKING'))

def toggle_auto():
    auto_speak[0] = not auto_speak[0]
    sv.set(f'Auto-speak: {"ON" if auto_speak[0] else "OFF"}')
    root.after(1500, lambda: sv.set('TRACKING'))

def toggle_theme():
    sv.set('Theme toggled')
    root.after(1500, lambda: sv.set('TRACKING'))

def toggle_size():
    sv.set('Size toggled')
    root.after(1500, lambda: sv.set('TRACKING'))

# ── KEY DEFINITIONS ───────────────────────────────────────────────────────────
all_keys = []

def make_key(x, y, w, h, label, color, action):
    rect = canvas.create_rectangle(x, y, x+w, y+h, fill=color, outline='#ccc', width=1)
    text = canvas.create_text(x+w//2, y+h//2, text=label, font=('Arial', 14, 'bold'), fill='black' if color == '#FFFFFF' else 'white')
    progress = canvas.create_rectangle(x, y+h-4, x, y+h, fill='#2196F3', outline='')
    key = {
        'rect': rect, 'text': text, 'progress': progress,
        'x': x, 'y': y, 'w': w, 'h': h, 'action': action,
        'label': label, 'color': color, 'dwell_start': None
    }
    all_keys.append(key)
    return key

# Get canvas dimensions
def setup_keys(event=None):
    cw = canvas.winfo_width()
    ch = canvas.winfo_height()
    if cw < 100 or ch < 100:
        root.after(100, setup_keys)
        return

    # Clear existing keys and gaze dot
    canvas.delete('all')
    all_keys.clear()
    global gaze_dot
    gaze_dot = None

    key_h = max(60, ch // 6)
    y = 0

    # Row 1: Numbers
    numbers = ['1','2','3','4','5','6','7','8','9','0','!','?',',','.']
    row1_w = cw / len(numbers)
    for i, char in enumerate(numbers):
        x = int(i * row1_w)
        w = int(row1_w) if i < len(numbers) - 1 else cw - x
        make_key(x, y, w, key_h, char, '#E3F2FD', lambda c=char: type_char(c))
    y += key_h

    # Row 2: QWERTY
    qwerty = ['Q','W','E','R','T','Y','U','I','O','P','⌫']
    row2_w = cw / len(qwerty)
    for i, char in enumerate(qwerty):
        x = int(i * row2_w)
        w = int(row2_w) if i < len(qwerty) - 1 else cw - x
        action = do_backspace if char == '⌫' else lambda c=char: type_char(c)
        make_key(x, y, w, key_h, char, '#FFFFFF', action)
    y += key_h

    # Row 3: ASDF
    asdf = ['A','S','D','F','G','H','J','K','L','↵']
    row3_w = cw / len(asdf)
    for i, char in enumerate(asdf):
        x = int(i * row3_w)
        w = int(row3_w) if i < len(asdf) - 1 else cw - x
        action = do_enter if char == '↵' else lambda c=char: type_char(c)
        make_key(x, y, w, key_h, char, '#FFFFFF', action)
    y += key_h

    # Row 4: ZXCV
    zxcv = ['Z','X','C','V','B','N','M']
    row4_w = cw / len(zxcv)
    for i, char in enumerate(zxcv):
        x = int(i * row4_w)
        w = int(row4_w) if i < len(zxcv) - 1 else cw - x
        make_key(x, y, w, key_h, char, '#FFFFFF', lambda c=char: type_char(c))
    y += key_h

    # Row 5: Actions
    actions = ['SPACE', 'CLEAR', 'SPEAK', 'SAVE', 'COPY', '🎤 MIC']
    actions_funcs = [do_space, do_clear, do_speak, do_save, do_copy, do_mic]
    row5_w = cw / len(actions)
    for i, label in enumerate(actions):
        x = int(i * row5_w)
        w = int(row5_w) if i < len(actions) - 1 else cw - x
        make_key(x, y, w, key_h, label, '#2196F3', actions_funcs[i])
    y += key_h


# ── GAZE DETECTION ────────────────────────────────────────────────────────────
gaze_dot = None

def check_gaze(cx, cy):
    global gaze_dot
    # Draw gaze dot
    if gaze_dot:
        canvas.coords(gaze_dot, cx-10, cy-10, cx+10, cy+10)
    else:
        gaze_dot = canvas.create_oval(cx-10, cy-10, cx+10, cy+10, fill='red', outline='red')
    
    # Check keys
    for key in all_keys:
        if key['x'] <= cx <= key['x'] + key['w'] and key['y'] <= cy <= key['y'] + key['h']:
            # Gaze on key
            if key['dwell_start'] is None:
                key['dwell_start'] = time.time()
                canvas.itemconfig(key['rect'], fill='#FFF176')
            else:
                elapsed = time.time() - key['dwell_start']
                progress = elapsed / dwell_time[0]
                pw = int(key['w'] * min(1.0, progress))
                canvas.coords(key['progress'], key['x'], key['y']+key['h']-4, key['x']+pw, key['y']+key['h'])
                if elapsed >= dwell_time[0]:
                    key['action']()
                    key['dwell_start'] = None
                    canvas.itemconfig(key['rect'], fill='#A5D6A7')
                    canvas.coords(key['progress'], key['x'], key['y']+key['h']-4, key['x'], key['y']+key['h'])
                    root.after(300, lambda k=key: canvas.itemconfig(k['rect'], fill=k['color']))
        else:
            if key['dwell_start'] is not None:
                key['dwell_start'] = None
                canvas.itemconfig(key['rect'], fill=key['color'])
                canvas.coords(key['progress'], key['x'], key['y']+key['h']-4, key['x'], key['y']+key['h'])

# ── TIMING ────────────────────────────────────────────────────────────────────
def update_timer():
    elapsed = int(time.time() - session_start)
    minutes, seconds = divmod(elapsed, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        timer_label.config(text=f"{hours:02d}:{minutes:02d}:{seconds:02d}")
    else:
        timer_label.config(text=f"{minutes:02d}:{seconds:02d}")
    root.after(1000, update_timer)

def update_wpm():
    elapsed = max(1, (time.time() - session_start) / 60)
    words = len(typed_text[0].split())
    wpm = int(words / elapsed)
    wpm_label.config(text=f"WPM: {wpm}")
    root.after(5000, update_wpm)

def update_fps():
    now = time.time()
    elapsed = now - last_fps_time[0]
    if elapsed >= 1.0:
        fps = fps_counter[0] / elapsed
        fps_label.config(text=f"FPS: {int(fps)}")
        fps_counter[0] = 0
        last_fps_time[0] = now
    root.after(1000, update_fps)

# ── CAMERA & POLLING ──────────────────────────────────────────────────────────
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
if not cap.isOpened():
    cap = cv2.VideoCapture(0)

camera_available = cap.isOpened()
if not camera_available:
    print('Warning: camera not available. Running in degraded mode.')

fm = mp.solutions.face_mesh.FaceMesh(
    max_num_faces=1, refine_landmarks=True,
    min_detection_confidence=0.3, min_tracking_confidence=0.3
)

def poll():
    try:
        if not camera_available:
            sv.set('Camera unavailable - gaze disabled')
            root.after(333, poll)
            return

        ret, frame = cap.read()
        if not ret or frame is None:
            sv.set('No camera frame')
            root.after(33, poll)
            return

        frame = cv2.flip(frame, 1)

        # Camera preview
        try:
            small = cv2.resize(frame, (200, 150))
            photo = ImageTk.PhotoImage(Image.fromarray(cv2.cvtColor(small, cv2.COLOR_BGR2RGB)))
            cam_label.configure(image=photo)
            cam_label.image = photo
        except Exception as e:
            print('Camera preview error:', e)

        # Face detection
        try:
            results = fm.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            if results.multi_face_landmarks:
                lm = results.multi_face_landmarks[0].landmark
                gx = (lm[468].x + lm[473].x) / 2
                gy = (lm[468].y + lm[473].y) / 2
                sw = root.winfo_screenwidth()
                sh = root.winfo_screenheight()
                screen_x = gx * sw
                screen_y = gy * sh
                cx = screen_x - canvas.winfo_rootx()
                cy = screen_y - canvas.winfo_rooty()
                check_gaze(cx, cy)
                sv.set('TRACKING - Look at key 0.8s to type')
            else:
                sv.set('Move closer to camera')
        except Exception as e:
            print('Face detection error:', e)
            sv.set('Face detection error')

        fps_counter[0] += 1
    except Exception as e:
        print('Poll loop error:', e)
    finally:
        root.after(33, poll)

# ── BINDINGS ──────────────────────────────────────────────────────────────────
root.bind('<Escape>', lambda e: (cap.release(), root.destroy()))

# ── LAUNCH ────────────────────────────────────────────────────────────────────
root.after(100, setup_keys)
root.after(100, poll)
root.after(1000, update_timer)
root.after(5000, update_wpm)
root.after(1000, update_fps)

root.mainloop()
cap.release()
>>>>>>> 52c3d7ea5ed405484f229b508704a40d14764e6c
