"""
Profile Manager - User Profile Management

This module handles creating, loading, switching, and managing
user profiles for the NodBoard application.
"""

import json
import os
import shutil
from tkinter import messagebox

# Configuration constants
CONFIG = {
    'profiles_dir': 'profiles',
    'profile_list_file': 'profiles.json',
    'max_profiles': 10,
}

class ProfileManager:
    """
    Manages user profiles with settings, calibration, and history.
    """

    def __init__(self):
        """Initialize profile manager."""
        self.current_profile = None
        self.profiles = []
        self._ensure_profiles_directory()
        self._load_profile_list()

    def _ensure_profiles_directory(self):
        """Ensure the profiles directory exists."""
        if not os.path.exists(CONFIG['profiles_dir']):
            os.makedirs(CONFIG['profiles_dir'])
            print(f"Created profiles directory: {CONFIG['profiles_dir']}")

    def _load_profile_list(self):
        """Load the list of available profiles."""
        profile_list_file = os.path.join(CONFIG['profiles_dir'], CONFIG['profile_list_file'])

        try:
            if os.path.exists(profile_list_file):
                with open(profile_list_file, 'r') as f:
                    data = json.load(f)
                    self.profiles = data.get('profiles', [])
                print(f"Loaded {len(self.profiles)} profiles")
            else:
                print("No profile list found, starting with empty list")
        except Exception as e:
            print(f"Error loading profile list: {e}")
            self.profiles = []

    def _save_profile_list(self):
        """Save the list of available profiles."""
        profile_list_file = os.path.join(CONFIG['profiles_dir'], CONFIG['profile_list_file'])

        try:
            data = {
                'profiles': self.profiles,
                'last_updated': self._get_timestamp()
            }
            with open(profile_list_file, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"Saved profile list with {len(self.profiles)} profiles")
        except Exception as e:
            print(f"Error saving profile list: {e}")

    def _get_timestamp(self):
        """Get current timestamp."""
        import time
        return int(time.time())

    def create_profile(self, profile_name):
        """
        Create a new user profile.

        Args:
            profile_name: Name of the profile to create

        Returns:
            bool: True if successful
        """
        if not profile_name or not profile_name.strip():
            messagebox.showerror("Error", "Profile name cannot be empty.")
            return False

        profile_name = profile_name.strip()

        if profile_name in self.profiles:
            messagebox.showerror("Error", f"Profile '{profile_name}' already exists.")
            return False

        if len(self.profiles) >= CONFIG['max_profiles']:
            messagebox.showerror("Error", f"Maximum number of profiles ({CONFIG['max_profiles']}) reached.")
            return False

        try:
            # Create profile directory
            profile_dir = os.path.join(CONFIG['profiles_dir'], profile_name)
            os.makedirs(profile_dir, exist_ok=True)

            # Create default profile files
            self._create_default_profile_files(profile_dir, profile_name)

            # Add to profile list
            self.profiles.append(profile_name)
            self._save_profile_list()

            print(f"Created profile: {profile_name}")
            messagebox.showinfo("Success", f"Profile '{profile_name}' created successfully.")
            return True

        except Exception as e:
            print(f"Error creating profile {profile_name}: {e}")
            messagebox.showerror("Error", f"Failed to create profile: {str(e)}")
            return False

    def _create_default_profile_files(self, profile_dir, profile_name):
        """Create default files for a new profile."""
        # Settings file
        settings_file = os.path.join(profile_dir, 'settings.json')
        default_settings = {
            'profile_name': profile_name,
            'created': self._get_timestamp(),
            'last_used': self._get_timestamp()
        }

        with open(settings_file, 'w') as f:
            json.dump(default_settings, f, indent=2)

        # Create empty files for other profile data
        files_to_create = [
            'calibration_data.json',
            'word_history.json',
            'tts_settings.json',
            'session_stats.json'
        ]

        for filename in files_to_create:
            filepath = os.path.join(profile_dir, filename)
            with open(filepath, 'w') as f:
                json.dump({}, f, indent=2)

    def delete_profile(self, profile_name):
        """
        Delete a user profile.

        Args:
            profile_name: Name of the profile to delete

        Returns:
            bool: True if successful
        """
        if profile_name not in self.profiles:
            messagebox.showerror("Error", f"Profile '{profile_name}' not found.")
            return False

        # Prevent deleting current profile
        if self.current_profile == profile_name:
            messagebox.showerror("Error", "Cannot delete currently active profile.")
            return False

        # Confirm deletion
        if not messagebox.askyesno("Confirm Delete",
                                  f"Are you sure you want to delete profile '{profile_name}'? This action cannot be undone."):
            return False

        try:
            # Remove profile directory
            profile_dir = os.path.join(CONFIG['profiles_dir'], profile_name)
            if os.path.exists(profile_dir):
                shutil.rmtree(profile_dir)

            # Remove from profile list
            self.profiles.remove(profile_name)
            self._save_profile_list()

            print(f"Deleted profile: {profile_name}")
            messagebox.showinfo("Success", f"Profile '{profile_name}' deleted successfully.")
            return True

        except Exception as e:
            print(f"Error deleting profile {profile_name}: {e}")
            messagebox.showerror("Error", f"Failed to delete profile: {str(e)}")
            return False

    def rename_profile(self, old_name, new_name):
        """
        Rename a user profile.

        Args:
            old_name: Current profile name
            new_name: New profile name

        Returns:
            bool: True if successful
        """
        if old_name not in self.profiles:
            messagebox.showerror("Error", f"Profile '{old_name}' not found.")
            return False

        if new_name in self.profiles:
            messagebox.showerror("Error", f"Profile '{new_name}' already exists.")
            return False

        if not new_name or not new_name.strip():
            messagebox.showerror("Error", "New profile name cannot be empty.")
            return False

        try:
            # Rename directory
            old_dir = os.path.join(CONFIG['profiles_dir'], old_name)
            new_dir = os.path.join(CONFIG['profiles_dir'], new_name)

            if os.path.exists(old_dir):
                os.rename(old_dir, new_dir)

                # Update profile name in settings
                settings_file = os.path.join(new_dir, 'settings.json')
                if os.path.exists(settings_file):
                    with open(settings_file, 'r') as f:
                        settings = json.load(f)
                    settings['profile_name'] = new_name
                    with open(settings_file, 'w') as f:
                        json.dump(settings, f, indent=2)

            # Update profile list
            idx = self.profiles.index(old_name)
            self.profiles[idx] = new_name
            self._save_profile_list()

            # Update current profile if it was renamed
            if self.current_profile == old_name:
                self.current_profile = new_name

            print(f"Renamed profile: {old_name} -> {new_name}")
            messagebox.showinfo("Success", f"Profile renamed to '{new_name}'.")
            return True

        except Exception as e:
            print(f"Error renaming profile {old_name}: {e}")
            messagebox.showerror("Error", f"Failed to rename profile: {str(e)}")
            return False

    def get_profiles(self):
        """
        Get list of available profiles.

        Returns:
            list: List of profile names
        """
        return self.profiles.copy()

    def get_profile_info(self, profile_name):
        """
        Get detailed information about a profile.

        Args:
            profile_name: Name of the profile

        Returns:
            dict or None: Profile information
        """
        if profile_name not in self.profiles:
            return None

        profile_dir = os.path.join(CONFIG['profiles_dir'], profile_name)
        settings_file = os.path.join(profile_dir, 'settings.json')

        try:
            info = {
                'name': profile_name,
                'exists': os.path.exists(profile_dir),
                'files': {}
            }

            if os.path.exists(settings_file):
                with open(settings_file, 'r') as f:
                    settings = json.load(f)
                    info.update(settings)

            # Check for other profile files
            profile_files = [
                'calibration_data.json',
                'word_history.json',
                'tts_settings.json',
                'session_stats.json'
            ]

            for filename in profile_files:
                filepath = os.path.join(profile_dir, filename)
                info['files'][filename] = os.path.exists(filepath)

            return info

        except Exception as e:
            print(f"Error getting profile info for {profile_name}: {e}")
            return None

    def switch_profile(self, profile_name):
        """
        Switch to a different profile.

        Args:
            profile_name: Name of the profile to switch to

        Returns:
            bool: True if successful
        """
        if profile_name not in self.profiles and profile_name is not None:
            messagebox.showerror("Error", f"Profile '{profile_name}' not found.")
            return False

        try:
            # Update last used time for current profile
            if self.current_profile:
                self._update_profile_timestamp(self.current_profile, 'last_used')

            self.current_profile = profile_name

            # Update last used time for new profile
            if profile_name:
                self._update_profile_timestamp(profile_name, 'last_used')

            print(f"Switched to profile: {profile_name}")
            return True

        except Exception as e:
            print(f"Error switching to profile {profile_name}: {e}")
            return False

    def _update_profile_timestamp(self, profile_name, timestamp_key):
        """Update a timestamp in profile settings."""
        profile_dir = os.path.join(CONFIG['profiles_dir'], profile_name)
        settings_file = os.path.join(profile_dir, 'settings.json')

        try:
            if os.path.exists(settings_file):
                with open(settings_file, 'r') as f:
                    settings = json.load(f)
                settings[timestamp_key] = self._get_timestamp()
                with open(settings_file, 'w') as f:
                    json.dump(settings, f, indent=2)
        except Exception as e:
            print(f"Error updating timestamp for {profile_name}: {e}")

    def export_profile(self, profile_name, export_path):
        """
        Export a profile to a zip file.

        Args:
            profile_name: Name of the profile to export
            export_path: Path for the exported zip file

        Returns:
            bool: True if successful
        """
        if profile_name not in self.profiles:
            messagebox.showerror("Error", f"Profile '{profile_name}' not found.")
            return False

        try:
            import zipfile

            profile_dir = os.path.join(CONFIG['profiles_dir'], profile_name)

            with zipfile.ZipFile(export_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(profile_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, CONFIG['profiles_dir'])
                        zipf.write(file_path, arcname)

            print(f"Exported profile {profile_name} to {export_path}")
            messagebox.showinfo("Success", f"Profile exported to {export_path}")
            return True

        except Exception as e:
            print(f"Error exporting profile {profile_name}: {e}")
            messagebox.showerror("Error", f"Failed to export profile: {str(e)}")
            return False

    def import_profile(self, import_path, profile_name=None):
        """
        Import a profile from a zip file.

        Args:
            import_path: Path to the zip file to import
            profile_name: Name for the imported profile (optional)

        Returns:
            bool: True if successful
        """
        try:
            import zipfile
            import tempfile

            if not profile_name:
                # Extract profile name from zip filename
                base_name = os.path.basename(import_path)
                profile_name = os.path.splitext(base_name)[0]

            if profile_name in self.profiles:
                messagebox.showerror("Error", f"Profile '{profile_name}' already exists.")
                return False

            # Extract to temporary directory first
            with tempfile.TemporaryDirectory() as temp_dir:
                with zipfile.ZipFile(import_path, 'r') as zipf:
                    zipf.extractall(temp_dir)

                # Check if it's a valid profile
                temp_profile_dir = os.path.join(temp_dir, profile_name)
                if not os.path.exists(temp_profile_dir):
                    # Try to find profile directory
                    subdirs = [d for d in os.listdir(temp_dir) if os.path.isdir(os.path.join(temp_dir, d))]
                    if subdirs:
                        temp_profile_dir = os.path.join(temp_dir, subdirs[0])
                        profile_name = subdirs[0]

                if not os.path.exists(temp_profile_dir):
                    messagebox.showerror("Error", "Invalid profile archive.")
                    return False

                # Copy to profiles directory
                profile_dir = os.path.join(CONFIG['profiles_dir'], profile_name)
                if os.path.exists(profile_dir):
                    shutil.rmtree(profile_dir)
                shutil.copytree(temp_profile_dir, profile_dir)

            # Add to profile list
            if profile_name not in self.profiles:
                self.profiles.append(profile_name)
                self._save_profile_list()

            print(f"Imported profile: {profile_name}")
            messagebox.showinfo("Success", f"Profile '{profile_name}' imported successfully.")
            return True

        except Exception as e:
            print(f"Error importing profile: {e}")
            messagebox.showerror("Error", f"Failed to import profile: {str(e)}")
            return False

    def get_profile_stats(self, profile_name):
        """
        Get statistics for a profile.

        Args:
            profile_name: Name of the profile

        Returns:
            dict: Profile statistics
        """
        info = self.get_profile_info(profile_name)
        if not info:
            return {}

        stats = {
            'name': profile_name,
            'created': info.get('created', 0),
            'last_used': info.get('last_used', 0),
            'has_calibration': info['files'].get('calibration_data.json', False),
            'has_word_history': info['files'].get('word_history.json', False),
            'has_tts_settings': info['files'].get('tts_settings.json', False),
        }

        # Try to get more detailed stats
        profile_dir = os.path.join(CONFIG['profiles_dir'], profile_name)

        # Word history stats
        word_history_file = os.path.join(profile_dir, 'word_history.json')
        if os.path.exists(word_history_file):
            try:
                with open(word_history_file, 'r') as f:
                    word_data = json.load(f)
                    user_history = word_data.get('user_history', {})
                    stats['unique_words'] = len(user_history)
                    stats['total_word_count'] = sum(user_history.values())
            except:
                pass

        return stats

# Example usage
if __name__ == "__main__":
    # Test profile manager
    pm = ProfileManager()

    print("Available profiles:")
    for profile in pm.get_profiles():
        print(f"  {profile}")

    # Create a test profile
    if 'test_profile' not in pm.get_profiles():
        pm.create_profile('test_profile')

    # Get profile info
    info = pm.get_profile_info('test_profile')
    if info:
        print(f"\nProfile info for 'test_profile':")
        for key, value in info.items():
            print(f"  {key}: {value}")

    # Get profile stats
    stats = pm.get_profile_stats('test_profile')
    if stats:
        print(f"\nProfile stats for 'test_profile':")
        for key, value in stats.items():
            print(f"  {key}: {value}")