"""
Virtual Keyboard UI - Full screen fit, no word suggestions, all rows visible.
"""

import tkinter as tk
import time

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
        except (TypeError, ValueError):
            return

        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw < 10 or ch < 10:
            return

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