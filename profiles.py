"""
profiles.py
-----------
User profile management: create, save, load, switch profiles.
Each profile stores calibration data, settings, and word history.
"""

import json
import os
import shutil
import tkinter as tk
from tkinter import simpledialog, messagebox

# ── CONFIG ──────────────────────────────────────────────────────────────────
CONFIG = {
    "PROFILES_DIR": "profiles",
    "PROFILE_SETTINGS_FILE": "settings.json",
    "PROFILE_CALIBRATION_FILE": "calibration_data.json",
    "PROFILE_WORDS_FILE": "user_words.json",
    "GUEST_PROFILE": "Guest",
    "BG_COLOR": "#1a1a2e",
    "FG_COLOR": "#FFFFFF",
    "ACCENT_COLOR": "#4a90d9",
    "WINDOW_SIZE": "400x500",
}
# ────────────────────────────────────────────────────────────────────────────


class ProfileManager:
    """
    Manages named user profiles stored as subdirectories under profiles/.
    Each profile directory contains settings.json, calibration_data.json,
    and user_words.json.
    """

    def __init__(self):
        self.profiles_dir = CONFIG["PROFILES_DIR"]
        os.makedirs(self.profiles_dir, exist_ok=True)
        self.current_profile = CONFIG["GUEST_PROFILE"]
        self._ensure_guest_profile()

    # ── Public API ───────────────────────────────────────────────────────────

    def list_profiles(self):
        """Return list of profile names (directory names under profiles/)."""
        try:
            return sorted([
                d for d in os.listdir(self.profiles_dir)
                if os.path.isdir(os.path.join(self.profiles_dir, d))
            ])
        except Exception:
            return [CONFIG["GUEST_PROFILE"]]

    def create_profile(self, name):
        """Create a new empty profile directory."""
        name = name.strip()
        if not name:
            return False
        path = os.path.join(self.profiles_dir, name)
        os.makedirs(path, exist_ok=True)
        return True

    def delete_profile(self, name):
        """Delete a profile (cannot delete Guest)."""
        if name == CONFIG["GUEST_PROFILE"]:
            return False
        path = os.path.join(self.profiles_dir, name)
        if os.path.exists(path):
            shutil.rmtree(path)
            return True
        return False

    def switch_profile(self, name):
        """
        Switch to a named profile.
        Copies profile-specific files to the working directory.
        """
        path = os.path.join(self.profiles_dir, name)
        if not os.path.exists(path):
            return False
        self.current_profile = name
        # Copy profile files to working directory
        for fname in [
            CONFIG["PROFILE_SETTINGS_FILE"],
            CONFIG["PROFILE_CALIBRATION_FILE"],
            CONFIG["PROFILE_WORDS_FILE"],
        ]:
            src = os.path.join(path, fname)
            if os.path.exists(src):
                shutil.copy2(src, fname)
        return True

    def save_current_profile(self):
        """Save current working files back into the active profile directory."""
        path = os.path.join(self.profiles_dir, self.current_profile)
        os.makedirs(path, exist_ok=True)
        for fname in [
            CONFIG["PROFILE_SETTINGS_FILE"],
            CONFIG["PROFILE_CALIBRATION_FILE"],
            CONFIG["PROFILE_WORDS_FILE"],
        ]:
            if os.path.exists(fname):
                shutil.copy2(fname, os.path.join(path, fname))

    def get_profile_path(self, name=None):
        """Return filesystem path for a profile."""
        name = name or self.current_profile
        return os.path.join(self.profiles_dir, name)

    # ── Internal ─────────────────────────────────────────────────────────────

    def _ensure_guest_profile(self):
        """Make sure the Guest profile directory exists."""
        guest_path = os.path.join(self.profiles_dir, CONFIG["GUEST_PROFILE"])
        os.makedirs(guest_path, exist_ok=True)


class ProfileSelector:
    """
    Tkinter dialog shown at startup to select or create a profile.
    Returns the chosen profile name via .chosen attribute.
    """

    def __init__(self, parent, profile_manager):
        self.manager = profile_manager
        self.chosen = CONFIG["GUEST_PROFILE"]

        self.win = tk.Toplevel(parent)
        self.win.title("Select Profile")
        self.win.geometry(CONFIG["WINDOW_SIZE"])
        self.win.configure(bg=CONFIG["BG_COLOR"])
        self.win.grab_set()     # modal

        self._build_ui()
        parent.wait_window(self.win)

    def _build_ui(self):
        bg = CONFIG["BG_COLOR"]
        fg = CONFIG["FG_COLOR"]
        accent = CONFIG["ACCENT_COLOR"]

        tk.Label(
            self.win, text="👤  Select Profile",
            font=("Arial", 18, "bold"), bg=bg, fg=fg
        ).pack(pady=(24, 8))

        tk.Label(
            self.win, text="Choose a profile or continue as Guest.",
            font=("Arial", 11), bg=bg, fg="#aaaaaa"
        ).pack(pady=(0, 16))

        # Profile listbox
        list_frame = tk.Frame(self.win, bg=bg)
        list_frame.pack(fill="both", expand=True, padx=30)

        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")

        self.listbox = tk.Listbox(
            list_frame, font=("Arial", 13), bg="#16213e", fg=fg,
            selectbackground=accent, selectforeground="white",
            relief="flat", bd=0, yscrollcommand=scrollbar.set,
            height=8
        )
        self.listbox.pack(fill="both", expand=True)
        scrollbar.config(command=self.listbox.yview)

        self._refresh_list()

        # Buttons
        btn_frame = tk.Frame(self.win, bg=bg)
        btn_frame.pack(pady=16)

        def btn(text, cmd, color=None):
            tk.Button(
                btn_frame, text=text, command=cmd,
                font=("Arial", 11, "bold"),
                bg=color or accent, fg="white",
                relief="flat", padx=14, pady=7
            ).pack(side="left", padx=6)

        btn("Select", self._select)
        btn("New Profile", self._new_profile, "#27ae60")
        btn("Delete", self._delete_profile, "#c0392b")
        btn("Guest Mode", self._guest, "#555555")

    def _refresh_list(self):
        self.listbox.delete(0, "end")
        for name in self.manager.list_profiles():
            self.listbox.insert("end", f"  {name}")

    def _select(self):
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showwarning("No Selection", "Please select a profile.", parent=self.win)
            return
        name = self.listbox.get(sel[0]).strip()
        self.manager.switch_profile(name)
        self.chosen = name
        self.win.destroy()

    def _new_profile(self):
        name = simpledialog.askstring("New Profile", "Enter profile name:", parent=self.win)
        if name:
            if self.manager.create_profile(name):
                self._refresh_list()
            else:
                messagebox.showerror("Error", "Invalid profile name.", parent=self.win)

    def _delete_profile(self):
        sel = self.listbox.curselection()
        if not sel:
            return
        name = self.listbox.get(sel[0]).strip()
        if messagebox.askyesno("Delete", f"Delete profile '{name}'?", parent=self.win):
            self.manager.delete_profile(name)
            self._refresh_list()

    def _guest(self):
        self.chosen = CONFIG["GUEST_PROFILE"]
        self.win.destroy()
