"""
<<<<<<< HEAD
Settings Manager - User Configuration Management

This module handles loading, saving, and managing user settings
for the NodBoard application.
"""

import json
import os
from tkinter import ttk, Toplevel, Scale, Checkbutton, OptionMenu, Button, Label
import tkinter as tk

# Default settings
DEFAULT_SETTINGS = {
    'dwell_time': 1.2,  # seconds
    'gaze_smoothing': 'medium',  # 'low', 'medium', 'high'
    'theme': 'dark',  # 'dark', 'light', 'high_contrast'
    'tts_speed': 200,  # words per minute
    'tts_voice': 0,  # voice index
    'tts_volume': 0.8,  # 0.0 to 1.0
    'auto_speak_sentences': True,
    'word_prediction': True,
    'blink_to_click': True,
    'camera_index': 0,
    'keyboard_layout': 'qwerty',  # 'qwerty', 'abc', 'frequency'
    'show_fps': True,
    'auto_save': True,
    'auto_save_interval': 30,  # seconds
}

class SettingsManager:
    """
    Manages user settings with persistence and UI.
    """

    def __init__(self):
        """Initialize settings manager."""
        self.settings = DEFAULT_SETTINGS.copy()
        self.settings_file = None

    def load_settings(self, profile_name):
        """
        Load settings for a user profile.

        Args:
            profile_name: Name of the user profile
        """
        if not profile_name:
            return

        self.settings_file = f"profiles/{profile_name}/settings.json"

        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    loaded_settings = json.load(f)
                    # Merge with defaults to handle new settings
                    self.settings.update(loaded_settings)
                print(f"Loaded settings for profile {profile_name}")
            else:
                print(f"No settings file found for {profile_name}, using defaults")
        except Exception as e:
            print(f"Error loading settings for {profile_name}: {e}")

    def save_settings(self, profile_name):
        """
        Save current settings to profile.

        Args:
            profile_name: Name of the user profile
        """
        if not profile_name:
            return

        if not self.settings_file:
            self.settings_file = f"profiles/{profile_name}/settings.json"

        os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)

        try:
            with open(self.settings_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
            print(f"Saved settings for profile {profile_name}")
        except Exception as e:
            print(f"Error saving settings for {profile_name}: {e}")

    def get_setting(self, key, default=None):
        """
        Get a setting value.

        Args:
            key: Setting key
            default: Default value if key not found

        Returns:
            Setting value
        """
        return self.settings.get(key, default if default is not None else DEFAULT_SETTINGS.get(key))

    def set_setting(self, key, value):
        """
        Set a setting value.

        Args:
            key: Setting key
            value: New value
        """
        self.settings[key] = value

    def reset_to_defaults(self):
        """Reset all settings to defaults."""
        self.settings = DEFAULT_SETTINGS.copy()

    def show_settings_dialog(self, parent_window, apply_callback=None):
        """
        Show settings dialog window.

        Args:
            parent_window: Parent Tkinter window
            apply_callback: Function to call when settings are applied
        """
        dialog = Toplevel(parent_window)
        dialog.title("Settings")
        dialog.geometry("500x600")
        dialog.resizable(False, False)

        # Create notebook for tabbed interface
        notebook = ttk.Notebook(dialog)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # General tab
        general_frame = ttk.Frame(notebook)
        notebook.add(general_frame, text="General")

        self._create_general_settings(general_frame)

        # Gaze tab
        gaze_frame = ttk.Frame(notebook)
        notebook.add(gaze_frame, text="Gaze")

        self._create_gaze_settings(gaze_frame)

        # Keyboard tab
        keyboard_frame = ttk.Frame(notebook)
        notebook.add(keyboard_frame, text="Keyboard")

        self._create_keyboard_settings(keyboard_frame)

        # Voice tab
        voice_frame = ttk.Frame(notebook)
        notebook.add(voice_frame, text="Voice")

        self._create_voice_settings(voice_frame)

        # Advanced tab
        advanced_frame = ttk.Frame(notebook)
        notebook.add(advanced_frame, text="Advanced")

        self._create_advanced_settings(advanced_frame)

        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, pady=10)

        def apply_settings():
            # Collect values from UI elements
            self._collect_settings_from_ui(general_frame, gaze_frame, keyboard_frame, voice_frame, advanced_frame)
            if apply_callback:
                apply_callback()
            dialog.destroy()

        def reset_settings():
            self.reset_to_defaults()
            # Refresh UI with defaults
            self._refresh_settings_ui(general_frame, gaze_frame, keyboard_frame, voice_frame, advanced_frame)

        ttk.Button(button_frame, text="Apply", command=apply_settings).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Reset to Defaults", command=reset_settings).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)

    def _create_general_settings(self, parent):
        """Create general settings UI."""
        # Theme selection
        Label(parent, text="Theme:").grid(row=0, column=0, sticky=tk.W, pady=5, padx=5)
        theme_var = tk.StringVar(value=self.get_setting('theme'))
        theme_menu = OptionMenu(parent, theme_var, 'dark', 'light', 'high_contrast')
        theme_menu.grid(row=0, column=1, sticky=tk.W, pady=5, padx=5)
        parent.theme_var = theme_var

        # Auto-save
        auto_save_var = tk.BooleanVar(value=self.get_setting('auto_save'))
        Checkbutton(parent, text="Auto-save text", variable=auto_save_var).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=5, padx=5)
        parent.auto_save_var = auto_save_var

        # Show FPS
        show_fps_var = tk.BooleanVar(value=self.get_setting('show_fps'))
        Checkbutton(parent, text="Show FPS counter", variable=show_fps_var).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=5, padx=5)
        parent.show_fps_var = show_fps_var

    def _create_gaze_settings(self, parent):
        """Create gaze settings UI."""
        # Dwell time
        Label(parent, text="Dwell Time (seconds):").grid(row=0, column=0, sticky=tk.W, pady=5, padx=5)
        dwell_scale = Scale(parent, from_=0.5, to=3.0, resolution=0.1, orient=tk.HORIZONTAL)
        dwell_scale.set(self.get_setting('dwell_time'))
        dwell_scale.grid(row=0, column=1, sticky=tk.EW, pady=5, padx=5)
        parent.dwell_scale = dwell_scale

        # Gaze smoothing
        Label(parent, text="Gaze Smoothing:").grid(row=1, column=0, sticky=tk.W, pady=5, padx=5)
        smoothing_var = tk.StringVar(value=self.get_setting('gaze_smoothing'))
        smoothing_menu = OptionMenu(parent, smoothing_var, 'low', 'medium', 'high')
        smoothing_menu.grid(row=1, column=1, sticky=tk.W, pady=5, padx=5)
        parent.smoothing_var = smoothing_var

        # Blink to click
        blink_var = tk.BooleanVar(value=self.get_setting('blink_to_click'))
        Checkbutton(parent, text="Enable blink-to-click", variable=blink_var).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=5, padx=5)
        parent.blink_var = blink_var

        # Camera index
        Label(parent, text="Camera Index:").grid(row=3, column=0, sticky=tk.W, pady=5, padx=5)
        camera_var = tk.IntVar(value=self.get_setting('camera_index'))
        camera_entry = tk.Entry(parent, textvariable=camera_var, width=10)
        camera_entry.grid(row=3, column=1, sticky=tk.W, pady=5, padx=5)
        parent.camera_var = camera_var

    def _create_keyboard_settings(self, parent):
        """Create keyboard settings UI."""
        # Word prediction
        word_pred_var = tk.BooleanVar(value=self.get_setting('word_prediction'))
        Checkbutton(parent, text="Enable word prediction", variable=word_pred_var).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=5, padx=5)
        parent.word_pred_var = word_pred_var

        # Keyboard layout
        Label(parent, text="Keyboard Layout:").grid(row=1, column=0, sticky=tk.W, pady=5, padx=5)
        layout_var = tk.StringVar(value=self.get_setting('keyboard_layout'))
        layout_menu = OptionMenu(parent, layout_var, 'qwerty', 'abc', 'frequency')
        layout_menu.grid(row=1, column=1, sticky=tk.W, pady=5, padx=5)
        parent.layout_var = layout_var

    def _create_voice_settings(self, parent):
        """Create voice settings UI."""
        # TTS Speed
        Label(parent, text="Speech Speed (WPM):").grid(row=0, column=0, sticky=tk.W, pady=5, padx=5)
        speed_scale = Scale(parent, from_=100, to=300, orient=tk.HORIZONTAL)
        speed_scale.set(self.get_setting('tts_speed'))
        speed_scale.grid(row=0, column=1, sticky=tk.EW, pady=5, padx=5)
        parent.speed_scale = speed_scale

        # TTS Volume
        Label(parent, text="Speech Volume:").grid(row=1, column=0, sticky=tk.W, pady=5, padx=5)
        volume_scale = Scale(parent, from_=0.0, to=1.0, resolution=0.1, orient=tk.HORIZONTAL)
        volume_scale.set(self.get_setting('tts_volume'))
        volume_scale.grid(row=1, column=1, sticky=tk.EW, pady=5, padx=5)
        parent.volume_scale = volume_scale

        # Auto-speak sentences
        auto_speak_var = tk.BooleanVar(value=self.get_setting('auto_speak_sentences'))
        Checkbutton(parent, text="Auto-speak complete sentences", variable=auto_speak_var).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=5, padx=5)
        parent.auto_speak_var = auto_speak_var

        # Voice selection would go here (requires voice_output integration)

    def _create_advanced_settings(self, parent):
        """Create advanced settings UI."""
        # Auto-save interval
        Label(parent, text="Auto-save Interval (seconds):").grid(row=0, column=0, sticky=tk.W, pady=5, padx=5)
        interval_var = tk.IntVar(value=self.get_setting('auto_save_interval'))
        interval_entry = tk.Entry(parent, textvariable=interval_var, width=10)
        interval_entry.grid(row=0, column=1, sticky=tk.W, pady=5, padx=5)
        parent.interval_var = interval_var

    def _collect_settings_from_ui(self, general_frame, gaze_frame, keyboard_frame, voice_frame, advanced_frame):
        """Collect settings values from UI elements."""
        # General
        self.set_setting('theme', general_frame.theme_var.get())
        self.set_setting('auto_save', general_frame.auto_save_var.get())
        self.set_setting('show_fps', general_frame.show_fps_var.get())

        # Gaze
        self.set_setting('dwell_time', gaze_frame.dwell_scale.get())
        self.set_setting('gaze_smoothing', gaze_frame.smoothing_var.get())
        self.set_setting('blink_to_click', gaze_frame.blink_var.get())
        self.set_setting('camera_index', gaze_frame.camera_var.get())

        # Keyboard
        self.set_setting('word_prediction', keyboard_frame.word_pred_var.get())
        self.set_setting('keyboard_layout', keyboard_frame.layout_var.get())

        # Voice
        self.set_setting('tts_speed', int(voice_frame.speed_scale.get()))
        self.set_setting('tts_volume', voice_frame.volume_scale.get())
        self.set_setting('auto_speak_sentences', voice_frame.auto_speak_var.get())

        # Advanced
        self.set_setting('auto_save_interval', advanced_frame.interval_var.get())

    def _refresh_settings_ui(self, general_frame, gaze_frame, keyboard_frame, voice_frame, advanced_frame):
        """Refresh UI elements with current settings."""
        # General
        general_frame.theme_var.set(self.get_setting('theme'))
        general_frame.auto_save_var.set(self.get_setting('auto_save'))
        general_frame.show_fps_var.set(self.get_setting('show_fps'))

        # Gaze
        gaze_frame.dwell_scale.set(self.get_setting('dwell_time'))
        gaze_frame.smoothing_var.set(self.get_setting('gaze_smoothing'))
        gaze_frame.blink_var.set(self.get_setting('blink_to_click'))
        gaze_frame.camera_var.set(self.get_setting('camera_index'))

        # Keyboard
        keyboard_frame.word_pred_var.set(self.get_setting('word_prediction'))
        keyboard_frame.layout_var.set(self.get_setting('keyboard_layout'))

        # Voice
        voice_frame.speed_scale.set(self.get_setting('tts_speed'))
        voice_frame.volume_scale.set(self.get_setting('tts_volume'))
        voice_frame.auto_speak_var.set(self.get_setting('auto_speak_sentences'))

        # Advanced
        advanced_frame.interval_var.set(self.get_setting('auto_save_interval'))

    def get_all_settings(self):
        """
        Get all current settings.

        Returns:
            dict: Copy of all settings
        """
        return self.settings.copy()

    def export_settings(self, filename):
        """Export settings to a file."""
        try:
            with open(filename, 'w') as f:
                json.dump(self.settings, f, indent=2)
            print(f"Settings exported to {filename}")
        except Exception as e:
            print(f"Error exporting settings: {e}")

    def import_settings(self, filename):
        """Import settings from a file."""
        try:
            with open(filename, 'r') as f:
                imported_settings = json.load(f)
                self.settings.update(imported_settings)
            print(f"Settings imported from {filename}")
        except Exception as e:
            print(f"Error importing settings: {e}")

# Example usage
if __name__ == "__main__":
    # Test settings manager
    settings = SettingsManager()
    settings.load_settings("test_profile")

    print("Current settings:")
    for key, value in settings.get_all_settings().items():
        print(f"  {key}: {value}")

    # Modify some settings
    settings.set_setting('dwell_time', 1.5)
    settings.set_setting('theme', 'light')

    print("\nModified settings:")
    print(f"  dwell_time: {settings.get_setting('dwell_time')}")
    print(f"  theme: {settings.get_setting('theme')}")
=======
settings.py
-----------
Settings panel UI and settings.json persistence.
All user-configurable options live here.
"""

import tkinter as tk
from tkinter import ttk
import json
import os

# ── CONFIG ──────────────────────────────────────────────────────────────────
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

# Default settings values
DEFAULTS = {
    "dwell_time": 2.0,              # seconds
    "smoothing_level": "medium",    # low / medium / high
    "theme": "dark",                # dark / light / high_contrast
    "tts_rate": 150,
    "tts_voice_index": 0,
    "keyboard_layout": "qwerty",    # qwerty / abc / frequency
    "blink_to_click": True,
    "word_prediction": True,
    "auto_speak_sentence": False,
    "camera_index": 0,
}
# ────────────────────────────────────────────────────────────────────────────


def load_settings():
    """Load settings from JSON file, falling back to DEFAULTS."""
    path = CONFIG["SETTINGS_FILE"]
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                data = json.load(f)
            # Merge with defaults so new keys always exist
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


class SettingsPanel:
    """
    Tkinter Toplevel window for editing all user settings.
    Changes are applied immediately and saved on close.
    """

    def __init__(self, parent, settings_dict, voice_names=None, on_apply=None):
        """
        parent        : Tk root or Toplevel
        settings_dict : current settings (will be mutated on apply)
        voice_names   : list of TTS voice name strings
        on_apply      : callable(settings_dict) called when user clicks Apply
        """
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

        self._vars = {}     # tk variable references
        self._build_ui(bg, fg)

    # ── UI Construction ──────────────────────────────────────────────────────

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

        # ── Gaze ──
        section("Gaze & Dwell")

        dwell_var = tk.DoubleVar(value=self.settings["dwell_time"])
        self._vars["dwell_time"] = dwell_var

        def dwell_widget(parent):
            f = tk.Frame(parent, bg=bg)
            f.pack(side="left")
            lbl = tk.Label(f, textvariable=dwell_var, font=label_font, bg=bg, fg=fg, width=4)
            lbl.pack(side="right")
            tk.Scale(
                f, from_=0.5, to=3.0, resolution=0.1, orient="horizontal",
                variable=dwell_var, bg=bg, fg=fg, highlightthickness=0,
                troughcolor="#333", length=200,
                command=lambda v: dwell_var.set(round(float(v), 1))
            ).pack(side="left")

        row("Dwell Time (seconds)", dwell_widget)

        smooth_var = tk.StringVar(value=self.settings["smoothing_level"])
        self._vars["smoothing_level"] = smooth_var
        row("Gaze Smoothing", lambda p: ttk.Combobox(
            p, textvariable=smooth_var, values=["low", "medium", "high"],
            state="readonly", width=12
        ).pack(side="left"))

        cam_var = tk.IntVar(value=self.settings["camera_index"])
        self._vars["camera_index"] = cam_var
        row("Camera Index", lambda p: ttk.Combobox(
            p, textvariable=cam_var, values=[0, 1, 2, 3],
            state="readonly", width=6
        ).pack(side="left"))

        # ── Appearance ──
        section("Appearance")

        theme_var = tk.StringVar(value=self.settings["theme"])
        self._vars["theme"] = theme_var
        row("Theme", lambda p: ttk.Combobox(
            p, textvariable=theme_var, values=["dark", "light", "high_contrast"],
            state="readonly", width=16
        ).pack(side="left"))

        layout_var = tk.StringVar(value=self.settings["keyboard_layout"])
        self._vars["keyboard_layout"] = layout_var
        row("Keyboard Layout", lambda p: ttk.Combobox(
            p, textvariable=layout_var, values=["qwerty", "abc", "frequency"],
            state="readonly", width=16
        ).pack(side="left"))

        # ── TTS ──
        section("Text-to-Speech")

        rate_var = tk.IntVar(value=self.settings["tts_rate"])
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

        voice_var = tk.IntVar(value=self.settings["tts_voice_index"])
        self._vars["tts_voice_index"] = voice_var
        row("Voice", lambda p: ttk.Combobox(
            p, textvariable=voice_var,
            values=list(range(len(self.voice_names))),
            state="readonly", width=6
        ).pack(side="left"))

        # ── Toggles ──
        section("Features")

        def toggle_row(label, key):
            var = tk.BooleanVar(value=self.settings[key])
            self._vars[key] = var
            r = tk.Frame(frame, bg=bg)
            r.pack(fill="x", **pad)
            tk.Label(r, text=label, font=label_font, bg=bg, fg=fg, width=26, anchor="w").pack(side="left")
            tk.Checkbutton(r, variable=var, bg=bg, fg=fg, selectcolor="#333",
                           activebackground=bg).pack(side="left")

        toggle_row("Blink-to-Click", "blink_to_click")
        toggle_row("Word Prediction", "word_prediction")
        toggle_row("Auto-Speak Sentence", "auto_speak_sentence")

        # ── Buttons ──
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
        """Read all widget values, update settings dict, save, call callback."""
        for key, var in self._vars.items():
            self.settings[key] = var.get()
        save_settings(self.settings)
        if self.on_apply:
            self.on_apply(self.settings)
        self.win.destroy()
>>>>>>> 52c3d7ea5ed405484f229b508704a40d14764e6c
