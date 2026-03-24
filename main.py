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
