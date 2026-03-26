"""
settings.py
-----------
Settings panel UI and settings.json persistence.
All user-configurable options live here.
"""

import tkinter as tk
from tkinter import ttk
import json
import os

CONFIG = {
    "SETTINGS_FILE": "settings.json",
    "WINDOW_TITLE": "Settings",
    "WINDOW_SIZE": "520x620",
    "BG_DARK": "#1a1a2e",
    "BG_LIGHT": "#f0f0f0",
    "FG_DARK": "#FFFFFF",
    "FG_LIGHT": "#000000",
    "ACCENT": "#4a90d9",
}

DEFAULTS = {
    "dwell_time": 2.0,
    "smoothing_level": "medium",
    "theme": "dark",
    "tts_rate": 150,
    "tts_voice_index": 0,
    "keyboard_layout": "qwerty",
    "blink_to_click": True,
    "word_prediction": True,
    "auto_speak_sentence": False,
    "camera_index": 0,
}


def load_settings():
    """Load settings from JSON file, falling back to DEFAULTS."""
    path = CONFIG["SETTINGS_FILE"]
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                data = json.load(f)
            merged = dict(DEFAULTS)
            merged.update(data)
            return merged
        except Exception as e:
            print(f"[Settings] Load error: {e}")
    return dict(DEFAULTS)


def save_settings(settings_dict):
    """Persist settings dict to JSON."""
    try:
        with open(CONFIG["SETTINGS_FILE"], "w") as f:
            json.dump(settings_dict, f, indent=2)
    except Exception as e:
        print(f"[Settings] Save error: {e}")


class SettingsManager:
    """
    Simple settings manager for loading/saving per-profile settings.
    Compatible with main.py usage.
    """

    def __init__(self):
        self.settings = dict(DEFAULTS)
        self.settings_file = None

    def load_settings(self, profile_name):
        if not profile_name:
            return
        self.settings_file = f"profiles/{profile_name}/settings.json"
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, "r") as f:
                    loaded = json.load(f)
                self.settings.update(loaded)
        except Exception as e:
            print(f"[SettingsManager] Load error: {e}")

    def save_settings(self, profile_name=None):
        path = self.settings_file
        if profile_name:
            path = f"profiles/{profile_name}/settings.json"
        if not path:
            return
        os.makedirs(os.path.dirname(path), exist_ok=True)
        try:
            with open(path, "w") as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            print(f"[SettingsManager] Save error: {e}")

    def get_setting(self, key, default=None):
        return self.settings.get(key, default if default is not None else DEFAULTS.get(key))

    def set_setting(self, key, value):
        self.settings[key] = value

    def reset_to_defaults(self):
        self.settings = dict(DEFAULTS)

    def get_all_settings(self):
        return self.settings.copy()


class SettingsPanel:
    """
    Tkinter Toplevel window for editing all user settings.
    """

    def __init__(self, parent, settings_dict, voice_names=None, on_apply=None):
        self.settings = settings_dict
        self.voice_names = voice_names or ["Default"]
        self.on_apply = on_apply

        self.win = tk.Toplevel(parent)
        self.win.title(CONFIG["WINDOW_TITLE"])
        self.win.geometry(CONFIG["WINDOW_SIZE"])
        self.win.resizable(False, False)

        bg = CONFIG["BG_DARK"] if settings_dict.get("theme") == "dark" else CONFIG["BG_LIGHT"]
        fg = CONFIG["FG_DARK"] if settings_dict.get("theme") == "dark" else CONFIG["FG_LIGHT"]
        self.win.configure(bg=bg)

        self._vars = {}
        self._build_ui(bg, fg)

    def _build_ui(self, bg, fg):
        pad = {"padx": 16, "pady": 6}
        label_font = ("Arial", 11)
        header_font = ("Arial", 13, "bold")

        frame = tk.Frame(self.win, bg=bg)
        frame.pack(fill="both", expand=True, padx=20, pady=10)

        def section(text):
            tk.Label(frame, text=text, font=header_font, bg=bg, fg=CONFIG["ACCENT"]).pack(
                anchor="w", pady=(12, 2)
            )

        def row(label_text, widget_factory):
            r = tk.Frame(frame, bg=bg)
            r.pack(fill="x", **pad)
            tk.Label(r, text=label_text, font=label_font, bg=bg, fg=fg, width=26, anchor="w").pack(
                side="left"
            )
            widget_factory(r)

        # Gaze
        section("Gaze & Dwell")

        dwell_var = tk.DoubleVar(value=self.settings.get("dwell_time", 2.0))
        self._vars["dwell_time"] = dwell_var

        def dwell_widget(parent):
            f = tk.Frame(parent, bg=bg)
            f.pack(side="left")
            tk.Label(f, textvariable=dwell_var, font=label_font, bg=bg, fg=fg, width=4).pack(side="right")
            tk.Scale(
                f, from_=0.5, to=3.0, resolution=0.1, orient="horizontal",
                variable=dwell_var, bg=bg, fg=fg, highlightthickness=0,
                troughcolor="#333", length=200,
                command=lambda v: dwell_var.set(round(float(v), 1))
            ).pack(side="left")

        row("Dwell Time (seconds)", dwell_widget)

        smooth_var = tk.StringVar(value=self.settings.get("smoothing_level", "medium"))
        self._vars["smoothing_level"] = smooth_var
        row("Gaze Smoothing", lambda p: ttk.Combobox(
            p, textvariable=smooth_var, values=["low", "medium", "high"],
            state="readonly", width=12
        ).pack(side="left"))

        cam_var = tk.IntVar(value=self.settings.get("camera_index", 0))
        self._vars["camera_index"] = cam_var
        row("Camera Index", lambda p: ttk.Combobox(
            p, textvariable=cam_var, values=[0, 1, 2, 3],
            state="readonly", width=6
        ).pack(side="left"))

        # Appearance
        section("Appearance")

        theme_var = tk.StringVar(value=self.settings.get("theme", "dark"))
        self._vars["theme"] = theme_var
        row("Theme", lambda p: ttk.Combobox(
            p, textvariable=theme_var, values=["dark", "light", "high_contrast"],
            state="readonly", width=16
        ).pack(side="left"))

        layout_var = tk.StringVar(value=self.settings.get("keyboard_layout", "qwerty"))
        self._vars["keyboard_layout"] = layout_var
        row("Keyboard Layout", lambda p: ttk.Combobox(
            p, textvariable=layout_var, values=["qwerty", "abc", "frequency"],
            state="readonly", width=16
        ).pack(side="left"))

        # TTS
        section("Text-to-Speech")

        rate_var = tk.IntVar(value=self.settings.get("tts_rate", 150))
        self._vars["tts_rate"] = rate_var

        def rate_widget(parent):
            f = tk.Frame(parent, bg=bg)
            f.pack(side="left")
            tk.Scale(
                f, from_=80, to=300, resolution=10, orient="horizontal",
                variable=rate_var, bg=bg, fg=fg, highlightthickness=0,
                troughcolor="#333", length=200
            ).pack(side="left")
            tk.Label(f, textvariable=rate_var, font=label_font, bg=bg, fg=fg, width=4).pack(side="left")

        row("Speech Rate (WPM)", rate_widget)

        voice_var = tk.IntVar(value=self.settings.get("tts_voice_index", 0))
        self._vars["tts_voice_index"] = voice_var
        row("Voice", lambda p: ttk.Combobox(
            p, textvariable=voice_var,
            values=list(range(len(self.voice_names))),
            state="readonly", width=6
        ).pack(side="left"))

        # Toggles
        section("Features")

        def toggle_row(label, key):
            var = tk.BooleanVar(value=self.settings.get(key, True))
            self._vars[key] = var
            r = tk.Frame(frame, bg=bg)
            r.pack(fill="x", **pad)
            tk.Label(r, text=label, font=label_font, bg=bg, fg=fg, width=26, anchor="w").pack(side="left")
            tk.Checkbutton(r, variable=var, bg=bg, fg=fg, selectcolor="#333",
                           activebackground=bg).pack(side="left")

        toggle_row("Blink-to-Click", "blink_to_click")
        toggle_row("Word Prediction", "word_prediction")
        toggle_row("Auto-Speak Sentence", "auto_speak_sentence")

        # Buttons
        btn_frame = tk.Frame(self.win, bg=bg)
        btn_frame.pack(pady=14)

        tk.Button(
            btn_frame, text="Apply & Close", font=("Arial", 12, "bold"),
            bg=CONFIG["ACCENT"], fg="white", relief="flat", padx=20, pady=8,
            command=self._apply
        ).pack(side="left", padx=8)

        tk.Button(
            btn_frame, text="Cancel", font=("Arial", 12),
            bg="#555", fg="white", relief="flat", padx=20, pady=8,
            command=self.win.destroy
        ).pack(side="left", padx=8)

    def _apply(self):
        for key, var in self._vars.items():
            self.settings[key] = var.get()
        save_settings(self.settings)
        if self.on_apply:
            self.on_apply(self.settings)
        self.win.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    s = load_settings()
    panel = SettingsPanel(root, s, on_apply=lambda x: print("Applied:", x))
    root.mainloop()