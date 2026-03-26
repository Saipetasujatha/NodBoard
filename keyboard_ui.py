"""
keyboard_ui.py
--------------
Virtual QWERTY keyboard with head-gaze dwell typing.
- Numbers row added
- SPACE/CLEAR/SPEAK/SAVE always visible
- Gaze dot correctly mapped across full keyboard
"""

import tkinter as tk
import time

CONFIG = {
    "DWELL_TIME_DEFAULT": 3.0,
    "DWELL_ARC_WIDTH": 5,
    "DWELL_COOLDOWN": 0.5,
    "STICKY_MARGIN": 50,
    "KEY_FONT": ("Arial", 15, "bold"),
    "SUGGESTION_FONT": ("Arial", 13, "bold"),
    "TEXT_FONT": ("Arial", 14),
    "THEMES": {
        "classic": {
            "bg": "#f5f5f5", "key_bg": "#ffffff", "key_fg": "#222222",
            "key_hover": "#4a90d9", "key_dwell": "#27ae60", "key_special": "#dde3f0",
            "key_border": "#bbbbbb", "text_bg": "#ffffff", "text_fg": "#000000",
            "suggest_bg": "#e8eaf6", "suggest_fg": "#222222",
            "status_bg": "#eeeeee", "status_fg": "#555555", "dot_color": "#e74c3c",
        },
        "dark": {
            "bg": "#1a1a2e", "key_bg": "#16213e", "key_fg": "#FFFFFF",
            "key_hover": "#4a90d9", "key_dwell": "#27ae60", "key_special": "#0f3460",
            "key_border": "#333355", "text_bg": "#0d0d1a", "text_fg": "#FFFFFF",
            "suggest_bg": "#0f3460", "suggest_fg": "#FFFFFF",
            "status_bg": "#0d0d1a", "status_fg": "#aaaaaa", "dot_color": "#ff4444",
        },
        "light": {
            "bg": "#f0f0f0", "key_bg": "#FFFFFF", "key_fg": "#000000",
            "key_hover": "#4a90d9", "key_dwell": "#27ae60", "key_special": "#dde3f0",
            "key_border": "#cccccc", "text_bg": "#FFFFFF", "text_fg": "#000000",
            "suggest_bg": "#dde3f0", "suggest_fg": "#000000",
            "status_bg": "#e0e0e0", "status_fg": "#333333", "dot_color": "#e74c3c",
        },
        "high_contrast": {
            "bg": "#000000", "key_bg": "#000000", "key_fg": "#FFFF00",
            "key_hover": "#FF0000", "key_dwell": "#00FF00", "key_special": "#111111",
            "key_border": "#ffffff", "text_bg": "#000000", "text_fg": "#FFFF00",
            "suggest_bg": "#111111", "suggest_fg": "#FFFF00",
            "status_bg": "#000000", "status_fg": "#FFFFFF", "dot_color": "#ff0000",
        },
    },
}

# Layout with numbers row at top
LAYOUT = [
    ["1","2","3","4","5","6","7","8","9","0","<"],
    ["Q","W","E","R","T","Y","U","I","O","P"],
    ["A","S","D","F","G","H","J","K","L","ENTER"],
    ["Z","X","C","V","B","N","M",",","."],
    ["SPACE","CLEAR","SPEAK","SAVE"],
]

SPECIAL_KEYS = {"<", "ENTER", "SPACE", "CLEAR", "SPEAK", "SAVE", "SETTINGS"}


class VirtualKeyboard(tk.Frame):
    def __init__(self, parent, key_callback=None, settings=None, **kwargs):
        # Handle both VirtualKeyboard(parent, callback) and VirtualKeyboard(parent, settings, ...)
        if callable(key_callback):
            pass
        elif isinstance(key_callback, dict):
            settings = key_callback
            key_callback = kwargs.get("key_callback", None)

        self.settings = settings or {}
        self.theme_name = self.settings.get("theme", "dark")
        self.theme = CONFIG["THEMES"].get(self.theme_name, CONFIG["THEMES"]["dark"])
        self.dwell_time = self.settings.get("dwell_time", CONFIG["DWELL_TIME_DEFAULT"])
        self._key_callback = key_callback

        super().__init__(parent, bg=self.theme["bg"])
        self.pack(fill="both", expand=True)

        self.typed_text = ""
        self.undo_stack = []
        self.redo_stack = []

        self._hovered_key = None
        self._dwell_start = None
        self._last_fired_key = None
        self._last_fired_time = 0.0
        self._dwell_origin_x = None
        self._dwell_origin_y = None

        self._suggestions = ["the", "that", "this", "they"]
        self._key_rects = {}
        self._gaze_dot_id = None

        self._build_ui()
        self.canvas.bind("<Configure>", lambda e: self._draw_keyboard())
        self.canvas.after(200, self._draw_keyboard)

    def _build_ui(self):
        t = self.theme

        # Suggestion bar
        self.suggest_frame = tk.Frame(self, bg=t["bg"], pady=2)
        self.suggest_frame.pack(fill="x", padx=8, pady=(4, 0))
        tk.Label(
            self.suggest_frame, text="Suggestions:",
            font=("Arial", 11), bg=t["bg"], fg=t["status_fg"]
        ).pack(side="left", padx=(0, 6))
        self.suggest_buttons = []
        for i in range(4):
            btn = tk.Button(
                self.suggest_frame, text="",
                font=CONFIG["SUGGESTION_FONT"],
                bg=t["suggest_bg"], fg=t["suggest_fg"],
                relief="flat", padx=10, pady=3,
                command=lambda idx=i: self._insert_suggestion(idx),
            )
            btn.pack(side="left", padx=3)
            self.suggest_buttons.append(btn)

        # Canvas for keyboard
        self.canvas = tk.Canvas(self, bg=t["bg"], highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=4, pady=4)

        # Debug/status bar
        self._debug_var = tk.StringVar(value="Gaze: waiting...")
        tk.Label(
            self, textvariable=self._debug_var,
            font=("Courier", 9),
            bg=t.get("status_bg", t["bg"]), fg="#00cc55"
        ).pack(fill="x", padx=8, pady=(0, 2))

    def _draw_keyboard(self):
        self.canvas.delete("all")
        self._key_rects.clear()
        self._gaze_dot_id = None

        t = self.theme
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw < 50: cw = 900
        if ch < 50: ch = 350

        gap = 6
        num_rows = len(LAYOUT)
        # Reserve equal height for each row
        row_h = (ch - gap * (num_rows + 1)) // num_rows

        for row_idx, row in enumerate(LAYOUT):
            y = gap + row_idx * (row_h + gap)
            n = len(row)

            if row_idx == len(LAYOUT) - 1:
                # Bottom action row — equal wide buttons
                kw = (cw - gap * (n + 1)) // n
                for col_idx, label in enumerate(row):
                    x = gap + col_idx * (kw + gap)
                    self._draw_key(x, y, kw, row_h, label, t["key_special"], t["key_fg"])
                    self._key_rects[label] = (x, y, kw, row_h)
            else:
                # Normal rows — fit across full width
                kw = (cw - gap * (n + 1)) // n
                for col_idx, label in enumerate(row):
                    x = gap + col_idx * (kw + gap)
                    bg = t["key_special"] if label in SPECIAL_KEYS else t["key_bg"]
                    self._draw_key(x, y, kw, row_h, label, bg, t["key_fg"])
                    self._key_rects[label] = (x, y, kw, row_h)

        # Gaze dot — start off screen
        self._gaze_dot_id = self.canvas.create_oval(
            -20, -20, -4, -4,
            fill=t["dot_color"], outline="white", width=2,
            tags="gaze_dot"
        )
        self.canvas.tag_raise("gaze_dot")

    def _draw_key(self, x, y, w, h, label, bg, fg, arc_progress=0.0, is_hovered=False):
        t = self.theme
        r = min(10, h // 4, w // 4)
        tag = f"key_{label}"

        self.canvas.delete(tag)
        self.canvas.delete(f"arc_{label}")
        self.canvas.delete(f"txt_{label}")

        fill = t["key_hover"] if is_hovered else bg
        border = t.get("key_border", "#444466")

        self.canvas.create_polygon(
            x + r, y,  x + w - r, y,
            x + w, y + r,  x + w, y + h - r,
            x + w - r, y + h,  x + r, y + h,
            x, y + h - r,  x, y + r,
            smooth=True, fill=fill, outline=border, width=1, tags=tag
        )

        font_size = 15 if len(label) == 1 else 11
        self.canvas.create_text(
            x + w // 2, y + h // 2,
            text=label,
            font=(CONFIG["KEY_FONT"][0], font_size, "bold"),
            fill=fg, tags=f"txt_{label}"
        )

        if arc_progress > 0:
            pad = 4
            extent = arc_progress * 359.9
            self.canvas.create_arc(
                x + pad, y + pad, x + w - pad, y + h - pad,
                start=90, extent=-extent,
                outline=t["key_dwell"],
                width=CONFIG["DWELL_ARC_WIDTH"],
                style="arc", tags=f"arc_{label}"
            )

    def update_gaze(self, gaze_x, gaze_y):
        """
        gaze_x, gaze_y are normalized 0.0-1.0 from the gaze engine.
        Maps directly to canvas coordinates.
        """
        try:
            gx = float(gaze_x)
            gy = float(gaze_y)
        except (TypeError, ValueError):
            return

        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw < 10 or ch < 10:
            return

        # Direct mapping — no clamping offset, use full canvas
        local_x = gx * cw
        local_y = gy * ch

        self._move_dot(local_x, local_y)
        hit_now = self._hit_test(local_x, local_y)

        # Sticky dwell zone
        if self._hovered_key and self._dwell_start and self._dwell_origin_x is not None:
            drift_x = abs(local_x - self._dwell_origin_x)
            drift_y = abs(local_y - self._dwell_origin_y)
            if drift_x < CONFIG["STICKY_MARGIN"] and drift_y < CONFIG["STICKY_MARGIN"]:
                hit_now = self._hovered_key

        if hit_now != self._hovered_key:
            self._unhighlight(self._hovered_key)
            self._hovered_key = hit_now
            self._dwell_origin_x = local_x if hit_now else None
            self._dwell_origin_y = local_y if hit_now else None

            if hit_now:
                self._highlight_key(hit_now)
                cooldown_ok = (time.time() - self._last_fired_time > CONFIG["DWELL_COOLDOWN"])
                if hit_now != self._last_fired_key or cooldown_ok:
                    if hit_now != self._last_fired_key:
                        self._last_fired_key = None
                    self._dwell_start = time.time()
                else:
                    self._dwell_start = None
            else:
                self._dwell_start = None

        if self._hovered_key and self._dwell_start:
            elapsed = time.time() - self._dwell_start
            progress = min(elapsed / self.dwell_time, 1.0)
            self._update_arc(self._hovered_key, progress)

            if elapsed >= self.dwell_time:
                self._trigger_key(self._hovered_key)
                self._last_fired_key = self._hovered_key
                self._last_fired_time = time.time()
                self._dwell_start = None
                self._dwell_origin_x = None
                self._dwell_origin_y = None

        info = f"Gaze: ({gx:.2f}, {gy:.2f}) → px({int(local_x)}, {int(local_y)})  Key: {self._hovered_key or 'none'}"
        self._debug_var.set(info)

    def _move_dot(self, lx, ly):
        if self._gaze_dot_id is None:
            return
        r = 9
        self.canvas.coords(self._gaze_dot_id, lx - r, ly - r, lx + r, ly + r)
        self.canvas.tag_raise("gaze_dot")

    def _trigger_key(self, label):
        print(f"KEY FIRED: {label}")
        self._push_undo()

        # Flash effect
        if label in self._key_rects:
            x, y, w, h = self._key_rects[label]
            flash = self.canvas.create_rectangle(
                x, y, x + w, y + h, fill="#ffffff", outline="", tags="flash"
            )
            self.canvas.after(180, lambda: self.canvas.delete(flash))

        if label == "<":
            self.typed_text = self.typed_text[:-1]
        elif label == "ENTER":
            self.typed_text += "\n"
        elif label == "SPACE":
            self.typed_text += " "
        elif label == "CLEAR":
            self.typed_text = ""
        elif label in ("SPEAK", "SAVE", "SETTINGS"):
            if self._key_callback:
                self._key_callback(label)
            return
        else:
            self.typed_text += label

        if self._key_callback:
            mapped = {"<": "BKSP", "ENTER": "ENTER"}.get(label, label)
            self._key_callback(mapped)

    def _hit_test(self, lx, ly):
        for label, (x, y, w, h) in self._key_rects.items():
            if x <= lx <= x + w and y <= ly <= y + h:
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
        word = self._suggestions[idx]
        parts = self.typed_text.rstrip().rsplit(" ", 1)
        self.typed_text = (parts[0] + " " + word + " ") if len(parts) == 2 else (word + " ")

    def _push_undo(self):
        self.undo_stack.append(self.typed_text)
        if len(self.undo_stack) > 20:
            self.undo_stack.pop(0)
        self.redo_stack.clear()

    def apply_theme(self, theme_name):
        self.theme_name = theme_name
        self.theme = CONFIG["THEMES"].get(theme_name, CONFIG["THEMES"]["dark"])
        self.configure(bg=self.theme["bg"])
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

    def get_key_positions(self):
        return {k: (v[0] + v[2] // 2, v[1] + v[3] // 2) for k, v in self._key_rects.items()}

    def undo(self):
        if self.undo_stack:
            self.redo_stack.append(self.typed_text)
            self.typed_text = self.undo_stack.pop()

    def redo(self):
        if self.redo_stack:
            self.undo_stack.append(self.typed_text)
            self.typed_text = self.redo_stack.pop()

    def confirm_selection(self):
        if self._hovered_key:
            self._trigger_key(self._hovered_key)

    def type_character(self, char):
        self._push_undo()
        self.typed_text += char

    def delete_last(self):
        self._push_undo()
        self.typed_text = self.typed_text[:-1]

    def insert_space(self):
        self._push_undo()
        self.typed_text += " "


if __name__ == "__main__":
    root = tk.Tk()
    root.title("NodBoard - Keyboard Test")
    root.geometry("1100x500")

    def on_key(key):
        print(f"Key pressed: {key}")

    frame = tk.Frame(root, bg="#1a1a2e")
    frame.pack(fill=tk.BOTH, expand=True)
    kb = VirtualKeyboard(frame, key_callback=on_key)

    def on_mouse(event):
        cw = kb.canvas.winfo_width()
        ch = kb.canvas.winfo_height()
        if cw > 0 and ch > 0:
            kb.update_gaze(event.x / cw, event.y / ch)

    kb.canvas.bind('<Motion>', on_mouse)
    root.mainloop()