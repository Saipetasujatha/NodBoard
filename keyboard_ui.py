"""
<<<<<<< HEAD
Virtual Keyboard UI - Full screen fit, no word suggestions, all rows visible.
=======
keyboard_ui.py
--------------
Virtual QWERTY keyboard with eye-gaze dwell typing.

KEY FIXES:
- Sticky dwell zone: once a key is selected, dot can drift 30px
  without resetting the timer. Fixes "shaky dot never fires" bug.
- Dwell time increased to 1.5s default for reliability.
- Cooldown reduced so retrying a key is fast.
>>>>>>> 52c3d7ea5ed405484f229b508704a40d14764e6c
"""

import tkinter as tk
import time

<<<<<<< HEAD
CONFIG = {
    'key_padding': 4,
    'dwell_time_default': 2.0,
    'cooldown': 0.8,
    'font_family': 'Arial',
    'font_size': 14,
}

KEYBOARD_LAYOUT = [
    ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0'],
    ['Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P', 'BKSP'],
    ['A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L', 'ENTER'],
    ['Z', 'X', 'C', 'V', 'B', 'N', 'M', ',', '.'],
    ['CLEAR', 'SPACE', 'SPEAK', 'SAVE', 'PREDICT', 'SETTINGS']   # SPACE moved after CLEAR
]

THEMES = {
    'dark': {
        'bg': '#f5f5f5',
        'key_bg': '#ffffff',
        'key_fg': '#222222',
        'key_hover': '#dce8ff',
        'progress': '#0080ff',
        'border': '#cccccc'
    },
    'light': {
        'bg': '#f5f5f5',
        'key_bg': '#ffffff',
        'key_fg': '#222222',
        'key_hover': '#dce8ff',
        'progress': '#0080ff',
        'border': '#cccccc'
    },
}

SPECIAL_KEY_COLORS = {
    'CLEAR':    {'bg': '#1565C0', 'fg': '#ffffff', 'border': '#0D47A1'},
    'SPEAK':    {'bg': '#1976D2', 'fg': '#ffffff', 'border': '#1565C0'},
    'SAVE':     {'bg': '#1976D2', 'fg': '#ffffff', 'border': '#1565C0'},
    'PREDICT':  {'bg': '#1976D2', 'fg': '#ffffff', 'border': '#1565C0'},
    'SETTINGS': {'bg': '#1565C0', 'fg': '#ffffff', 'border': '#0D47A1'},
    'BKSP':     {'bg': '#e53935', 'fg': '#ffffff', 'border': '#b71c1c'},
    'ENTER':    {'bg': '#43a047', 'fg': '#ffffff', 'border': '#2e7d32'},
    'SPACE':    {'bg': '#90caf9', 'fg': '#000000', 'border': '#1976D2'},
}

NUMBER_KEY_COLOR = {'bg': '#e8f4fd', 'fg': '#0d47a1', 'border': '#90caf9'}


class VirtualKeyboard:
    def __init__(self, parent_frame, key_callback):
        self.parent = parent_frame
        self.key_callback = key_callback
        self.current_theme = 'dark'
        self.dwell_time = CONFIG['dwell_time_default']

        self.current_hovered_key = None
        self.dwell_start_time = 0.0
        self.last_trigger_time = {}
        self.stable_key = None
        self.stable_start_time = 0.0
        self.last_stable_px = -999
        self.last_stable_py = -999
        self.stability_threshold = 30  # pixels - dot must stay within this to count as stable

        self.gaze_px = -100
        self.gaze_py = -100
        self.smooth_px = -100.0
        self.smooth_py = -100.0
        self.smoothing = 0.85  # slow smooth dot movement for easy dwell typing

        self.keys = {}
        self.key_positions = {}
        self.gaze_cursor_id = None
        self.progress_ids = {}

        self.canvas = tk.Canvas(
            self.parent,
            bg=THEMES[self.current_theme]['bg'],
            highlightthickness=0
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.debug_var = tk.StringVar(value="Waiting for gaze...")
        self.debug_label = tk.Label(
            self.parent,
            textvariable=self.debug_var,
            bg='#e3f2fd',
            fg='#1565C0',
            font=('Courier', 10)
        )
        self.debug_label.pack(fill=tk.X)

        self.canvas.after(200, self._build_keyboard)
        self.canvas.bind('<Configure>', self._on_resize)
        self.canvas.after(30, self._dwell_loop)

    def _build_keyboard(self):
        self.canvas.delete('all')
        self.keys.clear()
        self.key_positions.clear()
        self.progress_ids.clear()
        self.gaze_cursor_id = None

        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()

        if cw < 50: cw = 900
        if ch < 50: ch = 350

        gap = CONFIG['key_padding']
        num_rows = len(KEYBOARD_LAYOUT)

        # Calculate key height to fit all rows
        kh = max(40, (ch - (num_rows + 1) * gap) // num_rows)

        # Find widest row to calculate key width
        max_keys = max(len(row) for row in KEYBOARD_LAYOUT)
        kw = max(40, (cw - (max_keys + 1) * gap) // max_keys)

        start_y = gap

        for row_idx, row in enumerate(KEYBOARD_LAYOUT):
            y = start_y + row_idx * (kh + gap)
            n = len(row)

            if row_idx == 4:
                # Action row: full width split evenly
                total_w = cw - 2 * gap
                sp_w = (total_w - (n - 1) * gap) // n
                rx = gap
                for col_idx, key in enumerate(row):
                    x = rx + col_idx * (sp_w + gap)
                    self._create_key(key, x, y, sp_w, kh)

            elif row_idx == 0:
                # Number row: 10 keys evenly across full width
                total_w = cw - 2 * gap
                nw = (total_w - (n - 1) * gap) // n
                rx = gap
                for col_idx, key in enumerate(row):
                    x = rx + col_idx * (nw + gap)
                    self._create_key(key, x, y, nw, kh)

            else:
                # Letter rows: centered
                total_row_w = n * kw + (n - 1) * gap
                rx = (cw - total_row_w) // 2
                for col_idx, key in enumerate(row):
                    x = rx + col_idx * (kw + gap)
                    self._create_key(key, x, y, kw, kh)

        # Gaze cursor red dot
        self.gaze_cursor_id = self.canvas.create_oval(
            -20, -20, -6, -6,
            fill='#ff0000',
            outline='#880000',
            width=2,
            tags='gaze_cursor'
        )
        self.canvas.tag_raise('gaze_cursor')

    def _create_key(self, key_text, x, y, w, h):
        self.key_positions[key_text] = (x, y, w, h)

        if key_text in SPECIAL_KEY_COLORS:
            key_color    = SPECIAL_KEY_COLORS[key_text]['bg']
            text_color   = SPECIAL_KEY_COLORS[key_text]['fg']
            border_color = SPECIAL_KEY_COLORS[key_text]['border']
        elif key_text.isdigit():
            key_color    = NUMBER_KEY_COLOR['bg']
            text_color   = NUMBER_KEY_COLOR['fg']
            border_color = NUMBER_KEY_COLOR['border']
        else:
            key_color    = THEMES[self.current_theme]['key_bg']
            text_color   = THEMES[self.current_theme]['key_fg']
            border_color = THEMES[self.current_theme]['border']

        rect_id = self.canvas.create_rectangle(
            x, y, x + w, y + h,
            fill=key_color,
            outline=border_color,
            width=2,
            tags=f'key_{key_text}'
        )

        label = self._format_key(key_text)
        font_size = CONFIG['font_size'] if len(label) <= 5 else 10
        text_id = self.canvas.create_text(
            x + w // 2, y + h // 2,
            text=label,
            font=(CONFIG['font_family'], font_size, 'bold'),
            fill=text_color,
            tags=f'text_{key_text}'
        )

        self.keys[key_text] = {'rect': rect_id, 'text': text_id}
        self.progress_ids[key_text] = []

    def _format_key(self, key_text):
        mapping = {
            'BKSP': '⌫', 'ENTER': '↵ ENTER', 'SPACE': '─ SPACE ─',
            'CLEAR': 'CLEAR', 'SPEAK': 'SPEAK', 'SAVE': 'SAVE',
            'PREDICT': 'PREDICT', 'SETTINGS': 'SETTINGS'
        }
        return mapping.get(key_text, key_text)

    def _on_resize(self, event=None):
        self._build_keyboard()

    def update_gaze(self, gaze_x, gaze_y):
        try:
            gx = max(0.0, min(1.0, float(gaze_x)))
            gy = max(0.0, min(1.0, float(gaze_y)))
=======
# ── CONFIG ────────────────────────────────────────────────────────────────────
CONFIG = {
    "KEY_H":            80,
    "KEY_GAP":          8,
    "KEY_RADIUS":       10,
    "KEY_FONT":         ("Arial", 17, "bold"),
    "SUGGESTION_FONT":  ("Arial", 13, "bold"),
    "TEXT_FONT":        ("Arial", 15),
    "DWELL_TIME_DEFAULT": 3.0,   # seconds — increased for reliability
    "DWELL_ARC_WIDTH":  5,
    "DWELL_COOLDOWN":   0.5,     # cooldown before same key fires again
    # How many pixels the dot can drift OFF a key before dwell resets.
    # This is the core fix for shaky/jumpy dots.
    "STICKY_MARGIN":    50,
    "THEMES": {
        "classic": {
            "bg":            "#f5f5f5",
            "key_bg":        "#ffffff",
            "key_fg":        "#222222",
            "key_hover":     "#4a90d9",
            "key_dwell":     "#27ae60",
            "key_special":   "#dde3f0",
            "key_border":    "#bbbbbb",
            "text_bg":       "#ffffff",
            "text_fg":       "#000000",
            "suggest_bg":    "#e8eaf6",
            "suggest_fg":    "#222222",
            "suggest_hover": "#4a90d9",
            "status_bg":     "#eeeeee",
            "status_fg":     "#555555",
            "dot_color":     "#e74c3c",
        },
        "dark": {
            "bg":            "#1a1a2e",
            "key_bg":        "#16213e",
            "key_fg":        "#FFFFFF",
            "key_hover":     "#4a90d9",
            "key_dwell":     "#27ae60",
            "key_special":   "#0f3460",
            "key_border":    "#333333",
            "text_bg":       "#0d0d1a",
            "text_fg":       "#FFFFFF",
            "suggest_bg":    "#0f3460",
            "suggest_fg":    "#FFFFFF",
            "suggest_hover": "#4a90d9",
            "status_bg":     "#0d0d1a",
            "status_fg":     "#aaaaaa",
            "dot_color":     "#ff0000",
        },
        "light": {
            "bg":            "#f0f0f0",
            "key_bg":        "#FFFFFF",
            "key_fg":        "#000000",
            "key_hover":     "#4a90d9",
            "key_dwell":     "#27ae60",
            "key_special":   "#dde3f0",
            "key_border":    "#cccccc",
            "text_bg":       "#FFFFFF",
            "text_fg":       "#000000",
            "suggest_bg":    "#dde3f0",
            "suggest_fg":    "#000000",
            "suggest_hover": "#4a90d9",
            "status_bg":     "#e0e0e0",
            "status_fg":     "#333333",
            "dot_color":     "#e74c3c",
        },
        "high_contrast": {
            "bg":            "#000000",
            "key_bg":        "#000000",
            "key_fg":        "#FFFF00",
            "key_hover":     "#FF0000",
            "key_dwell":     "#00FF00",
            "key_special":   "#111111",
            "key_border":    "#ffffff",
            "text_bg":       "#000000",
            "text_fg":       "#FFFF00",
            "suggest_bg":    "#111111",
            "suggest_fg":    "#FFFF00",
            "suggest_hover": "#FF0000",
            "status_bg":     "#000000",
            "status_fg":     "#FFFFFF",
            "dot_color":     "#ff0000",
        },
    },
}

LAYOUTS = {
    "qwerty": [
        ["Q","W","E","R","T","Y","U","I","O","P","⌫"],
        ["A","S","D","F","G","H","J","K","L","↵"],
        ["Z","X","C","V","B","N","M",",","."],
        ["SPACE","CLEAR","SPEAK","SAVE","⚙"],
    ],
    "abc": [
        ["A","B","C","D","E","F","G","H","I","J","⌫"],
        ["K","L","M","N","O","P","Q","R","S","↵"],
        ["T","U","V","W","X","Y","Z",",","."],
        ["SPACE","CLEAR","SPEAK","SAVE","⚙"],
    ],
    "frequency": [
        ["E","T","A","O","I","N","S","H","R","L","⌫"],
        ["D","C","U","M","F","P","G","W","Y","↵"],
        ["B","V","K","X","J","Q","Z",",","."],
        ["SPACE","CLEAR","SPEAK","SAVE","⚙"],
    ],
}

SPECIAL_KEYS = {"⌫","↵","SPACE","CLEAR","SPEAK","SAVE","⚙"}
BOTTOM_ROW   = {"SPACE","CLEAR","SPEAK","SAVE","⚙"}


class VirtualKeyboard(tk.Frame):
    """
    Full-width virtual keyboard with eye-gaze dwell typing.
    Sticky dwell zone prevents shaky dot from resetting the timer.
    """

    def __init__(self, parent, settings=None, on_text_change=None,
                 on_speak=None, on_save=None, on_settings=None,
                 on_predict_request=None, key_callback=None):

        if callable(settings):
            key_callback = settings
            settings = {}

        self.settings           = settings or {}
        self.theme_name         = self.settings.get("theme", "classic")
        self.theme              = CONFIG["THEMES"].get(
                                    self.theme_name, CONFIG["THEMES"]["classic"])
        self.dwell_time         = self.settings.get(
                                    "dwell_time", CONFIG["DWELL_TIME_DEFAULT"])
        self.layout_name        = self.settings.get("keyboard_layout", "qwerty")
        self.layout             = LAYOUTS.get(self.layout_name, LAYOUTS["qwerty"])

        super().__init__(parent, bg=self.theme["bg"])
        self.pack(fill="both", expand=True)

        self.on_text_change     = on_text_change
        self.on_speak           = on_speak
        self.on_save            = on_save
        self.on_settings        = on_settings
        self.on_predict_request = on_predict_request
        self._key_callback      = key_callback

        self.typed_text         = ""
        self.undo_stack         = []
        self.redo_stack         = []

        # Dwell state
        self._hovered_key       = None   # key currently being dwelled on
        self._dwell_start       = None   # when dwell started
        self._last_fired_key    = None
        self._last_fired_time   = 0.0

        # Sticky zone: track where dwell started (canvas pixels)
        self._dwell_origin_x    = None
        self._dwell_origin_y    = None

        self._suggestions       = ["the","that","this","they"]
        self._key_rects         = {}     # label → (x, y, w, h)
        self._gaze_dot_id       = None

        self._build_ui()
        self.canvas.bind("<Configure>", lambda e: self._draw_keyboard())
        self.canvas.after(150, self._draw_keyboard)

    # ── UI build ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        t = self.theme

        text_outer = tk.Frame(self, bg=t["bg"], pady=2)
        text_outer.pack(fill="x", padx=8)
        self.text_area = tk.Text(
            text_outer, height=3,
            font=CONFIG["TEXT_FONT"],
            bg=t["text_bg"], fg=t["text_fg"],
            insertbackground=t["text_fg"],
            relief="flat", bd=6, wrap="word",
        )
        self.text_area.pack(fill="x")
        self.text_area.bind("<KeyRelease>", self._on_manual_type)

        self.suggest_frame = tk.Frame(self, bg=t["bg"], pady=2)
        self.suggest_frame.pack(fill="x", padx=8)
        tk.Label(
            self.suggest_frame, text="💡 Suggestions:",
            font=("Arial", 11), bg=t["bg"], fg=t["status_fg"]
        ).pack(side="left", padx=(0, 6))
        self.suggest_buttons = []
        for i in range(4):
            btn = tk.Button(
                self.suggest_frame, text="",
                font=CONFIG["SUGGESTION_FONT"],
                bg=t["suggest_bg"], fg=t["suggest_fg"],
                relief="flat", padx=10, pady=4,
                command=lambda idx=i: self._insert_suggestion(idx),
            )
            btn.pack(side="left", padx=3)
            self.suggest_buttons.append(btn)

        self.canvas = tk.Canvas(self, bg=t["bg"], highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=4, pady=4)

        self._debug_var = tk.StringVar(value="Gaze: waiting...")
        tk.Label(
            self, textvariable=self._debug_var,
            font=("Courier", 9),
            bg=t["status_bg"], fg="#00aa44"
        ).pack(fill="x", padx=8, pady=(0, 2))

    # ── Keyboard drawing ──────────────────────────────────────────────────────

    def _draw_keyboard(self):
        self.canvas.delete("all")
        self._key_rects.clear()
        self._gaze_dot_id = None

        t   = self.theme
        kh  = CONFIG["KEY_H"]
        gap = CONFIG["KEY_GAP"]
        cw  = self.canvas.winfo_width()
        ch  = self.canvas.winfo_height()
        if cw < 50: cw = 800
        if ch < 50: ch = 400

        normal_rows = self.layout[:-1]
        max_keys    = max(len(r) for r in normal_rows)
        kw          = (cw - gap * (max_keys + 1)) // max_keys
        row_indent  = [0, kw // 4, kw // 2, 0]
        total_h     = len(self.layout) * (kh + gap) + gap
        start_y     = max(gap, (ch - total_h) // 2)

        for row_idx, row in enumerate(self.layout):
            y      = start_y + row_idx * (kh + gap)
            indent = row_indent[row_idx] if row_idx < len(row_indent) else 0

            if row_idx == len(self.layout) - 1:
                n     = len(row)
                sp_w  = (cw - 2*gap - (n-1)*gap) // n
                rx    = gap
                for col_idx, label in enumerate(row):
                    x = rx + col_idx * (sp_w + gap)
                    self._draw_key(x, y, sp_w, kh, label,
                                   t["key_special"], t["key_fg"])
                    self._key_rects[label] = (x, y, sp_w, kh)
            else:
                n        = len(row)
                total_rw = n*kw + (n-1)*gap
                rx       = indent + (cw - total_rw - indent*2) // 2
                for col_idx, label in enumerate(row):
                    x  = rx + col_idx * (kw + gap)
                    bg = t["key_special"] if label in SPECIAL_KEYS else t["key_bg"]
                    self._draw_key(x, y, kw, kh, label, bg, t["key_fg"])
                    self._key_rects[label] = (x, y, kw, kh)

        # Gaze dot on top
        self._gaze_dot_id = self.canvas.create_oval(
            -20, -20, -6, -6,
            fill=t["dot_color"], outline="white", width=2,
            tags="gaze_dot"
        )
        self.canvas.tag_raise("gaze_dot")

    def _draw_key(self, x, y, w, h, label, bg, fg,
                  arc_progress=0.0, is_hovered=False):
        t   = self.theme
        r   = min(CONFIG["KEY_RADIUS"], h//3, w//3)
        tag = f"key_{label}"

        self.canvas.delete(tag)
        self.canvas.delete(f"arc_{label}")
        self.canvas.delete(f"txt_{label}")

        fill   = t["key_hover"] if is_hovered else bg
        border = t.get("key_border", "#333333")

        self.canvas.create_polygon(
            x+r, y,   x+w-r, y,
            x+w, y+r, x+w,   y+h-r,
            x+w-r, y+h, x+r, y+h,
            x, y+h-r,  x,    y+r,
            smooth=True,
            fill=fill, outline=border, width=1,
            tags=tag
        )

        font_size = 17 if len(label) == 1 else 12
        self.canvas.create_text(
            x + w//2, y + h//2,
            text=label,
            font=(CONFIG["KEY_FONT"][0], font_size, "bold"),
            fill=fg,
            tags=f"txt_{label}"
        )

        if arc_progress > 0:
            pad    = 4
            extent = arc_progress * 359.9
            self.canvas.create_arc(
                x+pad, y+pad, x+w-pad, y+h-pad,
                start=90, extent=-extent,
                outline=t["key_dwell"],
                width=CONFIG["DWELL_ARC_WIDTH"],
                style="arc",
                tags=f"arc_{label}"
            )

    # ── Gaze interface ─────────────────────────────────────────────────────────

    def update_gaze(self, gaze_x, gaze_y):
        """
        Accept normalized 0-1 gaze coordinates.
        Uses sticky zone: once dwell starts on a key, dot can drift
        STICKY_MARGIN pixels without resetting the timer.
        """
        try:
            gx = float(gaze_x)
            gy = float(gaze_y)
>>>>>>> 52c3d7ea5ed405484f229b508704a40d14764e6c
        except (TypeError, ValueError):
            return

        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw < 10 or ch < 10:
            return

<<<<<<< HEAD
        a = self.smoothing
        self.smooth_px = a * self.smooth_px + (1 - a) * gx * cw
        self.smooth_py = a * self.smooth_py + (1 - a) * gy * ch
        self.gaze_px = int(self.smooth_px)
        self.gaze_py = int(self.smooth_py)

        # If locked on a key, use a LARGE exit zone (40px margin)
        # so tiny fluctuations never kick the dot off the key
        if self.current_hovered_key is not None:
            kx, ky, kw, kh = self.key_positions[self.current_hovered_key]
            margin = 40
            still_inside = (
                (kx - margin) <= self.gaze_px <= (kx + kw + margin) and
                (ky - margin) <= self.gaze_py <= (ky + kh + margin)
            )
            if still_inside:
                # Stay locked - show dot at key center
                cx = kx + kw // 2
                cy = ky + kh // 2
                self._update_cursor(cx, cy)
                elapsed = time.time() - self.dwell_start_time
                self._draw_progress(self.current_hovered_key, min(elapsed / self.dwell_time, 1.0))
                self.debug_var.set(f"LOCKED: [{self.current_hovered_key}]  {elapsed:.1f}s / {self.dwell_time:.1f}s — hold still!")
                return
            else:
                # Really left the key
                orig = self._get_key_color(self.current_hovered_key)
                self.canvas.itemconfig(self.keys[self.current_hovered_key]['rect'], fill=orig)
                self._clear_progress(self.current_hovered_key)
                self.current_hovered_key = None

        # Not locked — use expanded zone to enter a key
        self._update_cursor(self.gaze_px, self.gaze_py)
        hit = self._hit_test_expanded(self.gaze_px, self.gaze_py, expand=10)
        if hit:
            self.current_hovered_key = hit
            self.dwell_start_time = time.time()
            self.canvas.itemconfig(self.keys[hit]['rect'],
                fill=THEMES[self.current_theme]['key_hover'])
            self.debug_var.set(f"Entered: [{hit}] — hold still for {self.dwell_time:.1f}s")
        else:
            self.debug_var.set(f"Move head to a key")

    def _get_key_color(self, key):
        if key in SPECIAL_KEY_COLORS:
            return SPECIAL_KEY_COLORS[key]['bg']
        elif key.isdigit():
            return NUMBER_KEY_COLOR['bg']
        return THEMES[self.current_theme]['key_bg']

    def _hit_test(self, px, py):
        for key, (x, y, w, h) in self.key_positions.items():
            if x <= px <= x + w and y <= py <= y + h:
                return key
        return None

    def _hit_test_expanded(self, px, py, expand=20):
        """Expanded hit zone - easier to enter a key"""
        for key, (x, y, w, h) in self.key_positions.items():
            if (x - expand) <= px <= (x + w + expand) and \
               (y - expand) <= py <= (y + h + expand):
                return key
        return None

    def _update_cursor(self, px, py):
        if self.gaze_cursor_id:
            r = 8
            self.canvas.coords(self.gaze_cursor_id, px-r, py-r, px+r, py+r)
            self.canvas.tag_raise('gaze_cursor')

    def _dwell_loop(self):
        try:
            if self.current_hovered_key is not None:
                elapsed = time.time() - self.dwell_start_time
                key = self.current_hovered_key
                last = self.last_trigger_time.get(key, 0)
                if elapsed >= self.dwell_time and (time.time() - last) > CONFIG['cooldown']:
                    self._fire_key(key)
        except Exception as e:
            print(f"Dwell loop error: {e}")
        finally:
            self.canvas.after(30, self._dwell_loop)

    def _fire_key(self, key):
        print(f"KEY PRESSED: {key}")
        self.last_trigger_time[key] = time.time()
        self.dwell_start_time = time.time()
        if key in self.keys:
            rect = self.keys[key]['rect']
            self.canvas.itemconfig(rect, fill='#ffff00')
            orig = self._get_key_color(key)
            self.canvas.after(200, lambda r=rect, c=orig: self.canvas.itemconfig(r, fill=c))
        self._clear_progress(key)
        self.key_callback(key)

    def _draw_progress(self, key, progress):
        self._clear_progress(key)
        if progress <= 0 or key not in self.key_positions:
            return
        x, y, w, h = self.key_positions[key]
        bar_w = int(w * progress)
        pid = self.canvas.create_rectangle(
            x, y + h - 5, x + bar_w, y + h,
            fill=THEMES[self.current_theme]['progress'],
            outline='', tags=f'prog_{key}'
        )
        self.progress_ids[key] = [pid]

    def _clear_progress(self, key):
        self.canvas.delete(f'prog_{key}')
        self.progress_ids[key] = []

    def set_theme(self, theme_name):
        if theme_name in THEMES:
            self.current_theme = theme_name
            self._apply_theme()

    def _apply_theme(self):
        self.canvas.config(bg=THEMES[self.current_theme]['bg'])
        self._build_keyboard()

    def set_dwell_time(self, seconds):
        self.dwell_time = max(0.5, min(3.0, float(seconds)))

    def get_key_positions(self):
        return {k: (v[0] + v[2]//2, v[1] + v[3]//2) for k, v in self.key_positions.items()}

    def setup_keyboard(self): self._build_keyboard()
    def apply_theme(self): self._apply_theme()
    def start_dwell_timer(self): pass
    def resize_keyboard(self, event=None): self._on_resize(event)


if __name__ == "__main__":
    root = tk.Tk()
    root.title("NodBoard - Keyboard Test")
    root.geometry("1000x400")
    root.configure(bg='#f5f5f5')

    typed = ['']
    text_var = tk.StringVar(value="Hover mouse over a key for 1.2 seconds to type...")
    tk.Label(root, textvariable=text_var, bg='#f5f5f5', fg='#222222',
             font=('Arial', 16), wraplength=980, anchor='w').pack(fill=tk.X, padx=10, pady=8)

    def on_key(key):
        if key == 'BKSP':    typed[0] = typed[0][:-1]
        elif key == 'ENTER': typed[0] += ' | '
        elif key == 'SPACE': typed[0] += ' '
        elif key == 'CLEAR': typed[0] = ''
        elif key in ('SPEAK', 'SAVE', 'PREDICT', 'SETTINGS'): return
        else: typed[0] += key
        text_var.set(typed[0] or "...")

    frame = tk.Frame(root, bg='#f5f5f5')
    frame.pack(fill=tk.BOTH, expand=True, padx=5)

    kb = VirtualKeyboard(frame, key_callback=on_key)

    def on_mouse(event):
        cw = kb.canvas.winfo_width()
        ch = kb.canvas.winfo_height()
        if cw > 0 and ch > 0:
            kb.update_gaze(event.x / cw, event.y / ch)

    kb.canvas.bind('<Motion>', on_mouse)
    root.mainloop()
=======
        local_x = gx * cw
        local_y = gy * ch

        # Move dot
        self._move_dot(local_x, local_y)

        # What key is the dot directly over right now?
        hit_now = self._hit_test(local_x, local_y)

        # ── STICKY ZONE LOGIC ─────────────────────────────────────────────
        # If we are currently dwelling on a key, check if dot is still
        # "close enough" to where the dwell started — if yes, keep dwelling
        # even if dot drifted off the key boundary.
        if self._hovered_key and self._dwell_start:
            if self._dwell_origin_x is not None:
                drift_x = abs(local_x - self._dwell_origin_x)
                drift_y = abs(local_y - self._dwell_origin_y)
                still_sticky = (drift_x < CONFIG["STICKY_MARGIN"] and
                                drift_y < CONFIG["STICKY_MARGIN"])
                if still_sticky:
                    # Stay on current key — ignore drift
                    hit_now = self._hovered_key

        # ── KEY CHANGE DETECTION ──────────────────────────────────────────
        if hit_now != self._hovered_key:
            self._unhighlight(self._hovered_key)
            self._hovered_key    = hit_now
            self._dwell_origin_x = local_x if hit_now else None
            self._dwell_origin_y = local_y if hit_now else None

            if hit_now:
                self._highlight_key(hit_now)
                # Start dwell timer — but respect cooldown for same key
                if hit_now != self._last_fired_key:
                    self._dwell_start = time.time()
                else:
                    cooldown_ok = (time.time() - self._last_fired_time
                                   > CONFIG["DWELL_COOLDOWN"])
                    if cooldown_ok:
                        self._last_fired_key = None
                        self._dwell_start    = time.time()
                    else:
                        self._dwell_start = None
            else:
                self._dwell_start = None

        # ── DWELL PROGRESS + TRIGGER ──────────────────────────────────────
        if self._hovered_key and self._dwell_start:
            elapsed  = time.time() - self._dwell_start
            progress = min(elapsed / self.dwell_time, 1.0)
            self._update_arc(self._hovered_key, progress)

            if elapsed >= self.dwell_time:
                self._trigger_key(self._hovered_key)
                self._last_fired_key  = self._hovered_key
                self._last_fired_time = time.time()
                self._dwell_start     = None
                self._dwell_origin_x  = None
                self._dwell_origin_y  = None

        # Debug bar
        elapsed_str = ""
        if self._dwell_start and self._hovered_key:
            e = time.time() - self._dwell_start
            elapsed_str = f"  dwell={e:.1f}s/{self.dwell_time:.1f}s"
        self._debug_var.set(
            f"Canvas px: ({int(local_x)}, {int(local_y)})"
            f"  Key: {self._hovered_key or 'none'}{elapsed_str}"
        )

        # Word suggestions
        if self.on_predict_request and self.settings.get("word_prediction", True):
            sugg = self.on_predict_request(self.typed_text)
            self._set_suggestions(sugg)

    def _move_dot(self, lx, ly):
        if self._gaze_dot_id is None:
            return
        r = 8
        self.canvas.coords(
            self._gaze_dot_id,
            lx-r, ly-r, lx+r, ly+r
        )
        self.canvas.tag_raise("gaze_dot")

    # ── Key trigger ───────────────────────────────────────────────────────────

    def _trigger_key(self, label):
        print(f"KEY FIRED: {label}")
        self._push_undo()

        # Flash
        if label in self._key_rects:
            x, y, w, h = self._key_rects[label]
            flash = self.canvas.create_rectangle(
                x, y, x+w, y+h,
                fill="#ffffff", outline="", tags="flash"
            )
            self.canvas.after(180, lambda: self.canvas.delete(flash))

        if label == "⌫":
            self.typed_text = self.typed_text[:-1]
        elif label == "↵":
            self.typed_text += "\n"
        elif label == "SPACE":
            self.typed_text += " "
        elif label == "CLEAR":
            self.typed_text = ""
        elif label == "SPEAK":
            if self.on_speak:
                self.on_speak(self.typed_text)
            if self._key_callback:
                self._key_callback("SPEAK")
            return
        elif label == "SAVE":
            if self.on_save:
                self.on_save(self.typed_text)
            if self._key_callback:
                self._key_callback("SAVE")
            return
        elif label == "⚙":
            if self.on_settings:
                self.on_settings()
            if self._key_callback:
                self._key_callback("SETTINGS")
            return
        else:
            self.typed_text += label

        self._sync_text()

        if self.on_text_change:
            self.on_text_change(self.typed_text)

        if self._key_callback:
            lk = {"⌫": "BKSP", "↵": "ENTER"}.get(label, label)
            self._key_callback(lk)

    # ── Hit test & highlights ─────────────────────────────────────────────────

    def _hit_test(self, lx, ly):
        for label, (x, y, w, h) in self._key_rects.items():
            if x <= lx <= x+w and y <= ly <= y+h:
                return label
        return None

    def _highlight_key(self, label):
        if label not in self._key_rects:
            return
        x, y, w, h = self._key_rects[label]
        bg = self.theme["key_special"] if label in SPECIAL_KEYS else self.theme["key_bg"]
        self._draw_key(x, y, w, h, label, bg, self.theme["key_fg"], is_hovered=True)

    def _unhighlight(self, label):
        if not label or label not in self._key_rects:
            return
        x, y, w, h = self._key_rects[label]
        bg = self.theme["key_special"] if label in SPECIAL_KEYS else self.theme["key_bg"]
        self._draw_key(x, y, w, h, label, bg, self.theme["key_fg"])

    def _update_arc(self, label, progress):
        if label not in self._key_rects:
            return
        x, y, w, h = self._key_rects[label]
        bg = self.theme["key_special"] if label in SPECIAL_KEYS else self.theme["key_bg"]
        self._draw_key(x, y, w, h, label, bg, self.theme["key_fg"],
                       arc_progress=progress, is_hovered=True)

    # ── Suggestions ───────────────────────────────────────────────────────────

    def _set_suggestions(self, suggestions):
        self._suggestions = suggestions or []
        for i, btn in enumerate(self.suggest_buttons):
            if i < len(self._suggestions):
                btn.configure(text=self._suggestions[i], state="normal")
            else:
                btn.configure(text="", state="disabled")

    def _insert_suggestion(self, idx):
        if idx >= len(self._suggestions):
            return
        word  = self._suggestions[idx]
        parts = self.typed_text.rstrip().rsplit(" ", 1)
        self.typed_text = (
            (parts[0] + " " + word + " ")
            if len(parts) == 2
            else (word + " ")
        )
        self._sync_text()
        if self.on_text_change:
            self.on_text_change(self.typed_text)

    # ── Text sync ─────────────────────────────────────────────────────────────

    def _sync_text(self):
        self.text_area.delete("1.0", "end")
        self.text_area.insert("1.0", self.typed_text)
        self.text_area.see("end")

    def _on_manual_type(self, _event):
        self.typed_text = self.text_area.get("1.0", "end-1c")
        if self.on_text_change:
            self.on_text_change(self.typed_text)

    def _push_undo(self):
        self.undo_stack.append(self.typed_text)
        if len(self.undo_stack) > 20:
            self.undo_stack.pop(0)
        self.redo_stack.clear()

    # ── Public API ────────────────────────────────────────────────────────────

    def apply_theme(self, theme_name):
        self.theme_name = theme_name
        self.theme = CONFIG["THEMES"].get(theme_name, CONFIG["THEMES"]["classic"])
        self.configure(bg=self.theme["bg"])
        self.text_area.configure(
            bg=self.theme["text_bg"],
            fg=self.theme["text_fg"],
            insertbackground=self.theme["text_fg"]
        )
        self.suggest_frame.configure(bg=self.theme["bg"])
        for btn in self.suggest_buttons:
            btn.configure(bg=self.theme["suggest_bg"], fg=self.theme["suggest_fg"])
        self._draw_keyboard()

    def set_theme(self, theme_name):
        self.apply_theme(theme_name)

    def set_dwell_time(self, seconds):
        self.dwell_time = max(0.3, min(5.0, float(seconds)))

    def get_text(self):
        return self.typed_text

    def set_text(self, text):
        self.typed_text = text
        self._sync_text()

    def get_key_positions(self):
        return {
            k: (v[0]+v[2]//2, v[1]+v[3]//2)
            for k, v in self._key_rects.items()
        }

    def undo(self):
        if self.undo_stack:
            self.redo_stack.append(self.typed_text)
            self.typed_text = self.undo_stack.pop()
            self._sync_text()

    def redo(self):
        if self.redo_stack:
            self.undo_stack.append(self.typed_text)
            self.typed_text = self.redo_stack.pop()
            self._sync_text()

    def confirm_selection(self):
        if self._hovered_key:
            self._trigger_key(self._hovered_key)

    def type_character(self, char):
        self._push_undo()
        self.typed_text += char
        self._sync_text()

    def delete_last(self):
        self._push_undo()
        self.typed_text = self.typed_text[:-1]
        self._sync_text()

    def insert_space(self):
        self._push_undo()
        self.typed_text += " "
        self._sync_text()
>>>>>>> 52c3d7ea5ed405484f229b508704a40d14764e6c
