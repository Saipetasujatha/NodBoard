"""
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