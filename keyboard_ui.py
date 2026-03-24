"""
keyboard_ui.py
--------------
Virtual QWERTY keyboard with eye-gaze dwell typing.

KEY FIXES:
- Sticky dwell zone: once a key is selected, dot can drift 30px
  without resetting the timer. Fixes "shaky dot never fires" bug.
- Dwell time increased to 1.5s default for reliability.
- Cooldown reduced so retrying a key is fast.
"""

import tkinter as tk
import time

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
        except (TypeError, ValueError):
            return

        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw < 10 or ch < 10:
            return

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