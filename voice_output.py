"""
<<<<<<< HEAD
Voice Output - Text-to-Speech Engine

This module handles text-to-speech functionality using pyttsx3
for offline speech synthesis.
"""

import pyttsx3
import threading
import time
import re

# Configuration constants
CONFIG = {
    'default_rate': 200,  # words per minute
    'default_volume': 0.8,  # 0.0 to 1.0
    'sentence_pause': 0.5,  # seconds
    'word_highlight_delay': 0.1,  # seconds
}

class VoiceOutput:
    """
    Text-to-speech engine with word highlighting and voice control.
    """

    def __init__(self):
        """Initialize text-to-speech engine."""
        self.engine = None
        self.is_speaking = False
        self.current_voice = None
        self.rate = CONFIG['default_rate']
        self.volume = CONFIG['default_volume']
        self.auto_speak_sentences = True

        # Word highlighting callback
        self.highlight_callback = None

        self.initialize_engine()

    def initialize_engine(self):
        """Initialize the TTS engine."""
        try:
            self.engine = pyttsx3.init()

            # Configure engine
            self.engine.setProperty('rate', self.rate)
            self.engine.setProperty('volume', self.volume)

            # Get available voices
            self.voices = self.engine.getProperty('voices')
            if self.voices:
                # Set default voice (usually the first one)
                self.current_voice = self.voices[0]
                self.engine.setProperty('voice', self.current_voice.id)

            print("TTS engine initialized successfully")
            print(f"Available voices: {len(self.voices) if self.voices else 0}")

        except Exception as e:
            print(f"Failed to initialize TTS engine: {e}")
            self.engine = None

    def speak(self, text, highlight_words=True):
        """
        Speak the given text.

        Args:
            text: Text to speak
            highlight_words: Whether to highlight words as they are spoken
        """
        if not self.engine or not text or not text.strip():
            return

        if self.is_speaking:
            self.stop()

        # Start speaking in a separate thread
        speak_thread = threading.Thread(
            target=self._speak_text,
            args=(text, highlight_words),
            daemon=True
        )
        speak_thread.start()

    def _speak_text(self, text, highlight_words):
        """Internal method to handle text speaking."""
        try:
            self.is_speaking = True

            if highlight_words and self.highlight_callback:
                self._speak_with_highlighting(text)
            else:
                self.engine.say(text)
                self.engine.runAndWait()

        except Exception as e:
            print(f"Error during speech: {e}")
        finally:
            self.is_speaking = False

    def _speak_with_highlighting(self, text):
        """Speak text with word-by-word highlighting."""
        # Split text into sentences
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())

        for sentence in sentences:
            if not self.is_speaking:
                break

            # Split sentence into words
            words = re.findall(r'\b\w+\b', sentence)

            for i, word in enumerate(words):
                if not self.is_speaking:
                    break

                # Highlight current word
                if self.highlight_callback:
                    self.highlight_callback(word, i, len(words))

                # Speak current word
                self.engine.say(word)
                self.engine.runAndWait()

                # Small pause between words
                time.sleep(CONFIG['word_highlight_delay'])

            # Pause between sentences
            if self.is_speaking and sentence != sentences[-1]:
                time.sleep(CONFIG['sentence_pause'])

    def stop(self):
        """Stop current speech."""
        if self.engine and self.is_speaking:
            try:
                self.engine.stop()
            except:
                pass
            self.is_speaking = False

    def set_voice(self, voice_index=None, voice_name=None):
        """
        Set the TTS voice.

        Args:
            voice_index: Index of voice in voices list
            voice_name: Name of the voice to select
        """
        if not self.engine or not self.voices:
            return

        try:
            if voice_index is not None and 0 <= voice_index < len(self.voices):
                self.current_voice = self.voices[voice_index]
            elif voice_name:
                for voice in self.voices:
                    if voice_name.lower() in voice.name.lower():
                        self.current_voice = voice
                        break

            if self.current_voice:
                self.engine.setProperty('voice', self.current_voice.id)
                print(f"Voice set to: {self.current_voice.name}")

        except Exception as e:
            print(f"Error setting voice: {e}")

    def set_rate(self, rate):
        """
        Set speech rate.

        Args:
            rate: Words per minute (typically 100-300)
        """
        if not self.engine:
            return

        try:
            self.rate = max(50, min(400, rate))  # Clamp to reasonable range
            self.engine.setProperty('rate', self.rate)
            print(f"Speech rate set to: {self.rate} WPM")
        except Exception as e:
            print(f"Error setting rate: {e}")

    def set_volume(self, volume):
        """
        Set speech volume.

        Args:
            volume: Volume level (0.0 to 1.0)
        """
        if not self.engine:
            return

        try:
            self.volume = max(0.0, min(1.0, volume))
            self.engine.setProperty('volume', self.volume)
            print(f"Volume set to: {self.volume}")
        except Exception as e:
            print(f"Error setting volume: {e}")

    def get_available_voices(self):
        """
        Get list of available voices.

        Returns:
            list: List of voice information dictionaries
        """
        if not self.voices:
            return []

        voice_list = []
        for i, voice in enumerate(self.voices):
            voice_info = {
                'index': i,
                'id': voice.id,
                'name': voice.name,
                'languages': getattr(voice, 'languages', []),
                'gender': getattr(voice, 'gender', None),
                'age': getattr(voice, 'age', None)
            }
            voice_list.append(voice_info)

        return voice_list

    def speak_sentence_auto(self, text):
        """Automatically speak complete sentences."""
        if not self.auto_speak_sentences:
            return

        # Check if text ends with sentence-ending punctuation
        if text.strip().endswith(('.', '!', '?')):
            # Extract the last sentence
            sentences = re.split(r'(?<=[.!?])\s+', text.strip())
            if sentences:
                last_sentence = sentences[-1]
                self.speak(last_sentence, highlight_words=False)

    def set_highlight_callback(self, callback):
        """
        Set callback function for word highlighting.

        Args:
            callback: Function that takes (word, word_index, total_words)
        """
        self.highlight_callback = callback

    def is_engine_available(self):
        """
        Check if TTS engine is available.

        Returns:
            bool: True if engine is initialized
        """
        return self.engine is not None

    def get_current_settings(self):
        """
        Get current TTS settings.

        Returns:
            dict: Current settings
        """
        return {
            'rate': self.rate,
            'volume': self.volume,
            'voice': self.current_voice.name if self.current_voice else None,
            'auto_speak': self.auto_speak_sentences,
            'is_speaking': self.is_speaking
        }

    def test_voice(self, test_text="Hello, this is a test of the text-to-speech system."):
        """Test the current voice settings."""
        self.speak(test_text, highlight_words=False)

    def save_settings(self, profile_name):
        """Save TTS settings to profile."""
        if not profile_name:
            return

        settings = self.get_current_settings()
        settings_file = f"profiles/{profile_name}/tts_settings.json"

        try:
            import json
            with open(settings_file, 'w') as f:
                json.dump(settings, f, indent=2)
            print(f"Saved TTS settings for profile {profile_name}")
        except Exception as e:
            print(f"Error saving TTS settings: {e}")

    def load_settings(self, profile_name):
        """Load TTS settings from profile."""
        if not profile_name:
            return

        settings_file = f"profiles/{profile_name}/tts_settings.json"

        try:
            import json
            if os.path.exists(settings_file):
                with open(settings_file, 'r') as f:
                    settings = json.load(f)

                self.set_rate(settings.get('rate', CONFIG['default_rate']))
                self.set_volume(settings.get('volume', CONFIG['default_volume']))
                self.auto_speak_sentences = settings.get('auto_speak', True)

                # Try to restore voice
                voice_name = settings.get('voice')
                if voice_name:
                    self.set_voice(voice_name=voice_name)

                print(f"Loaded TTS settings for profile {profile_name}")
        except Exception as e:
            print(f"Error loading TTS settings: {e}")

# Example usage and testing
if __name__ == "__main__":
    # Test the TTS engine
    tts = VoiceOutput()

    if tts.is_engine_available():
        print("TTS engine is available")
        print("Available voices:")
        voices = tts.get_available_voices()
        for voice in voices[:5]:  # Show first 5 voices
            print(f"  {voice['index']}: {voice['name']}")

        # Test speech
        tts.test_voice()
    else:
        print("TTS engine is not available")
=======
voice_output.py
---------------
Offline text-to-speech using pyttsx3.
Supports voice selection, speed/pitch control, and word-by-word callbacks.
"""

import threading
import pyttsx3

# ── CONFIG ──────────────────────────────────────────────────────────────────
CONFIG = {
    "DEFAULT_RATE": 150,        # words per minute
    "DEFAULT_VOLUME": 1.0,      # 0.0 – 1.0
    "DEFAULT_VOICE_INDEX": 0,   # index into available voices
}
# ────────────────────────────────────────────────────────────────────────────


class VoiceOutput:
    """
    Wraps pyttsx3 for thread-safe TTS.
    Runs speech in a background thread so the UI never blocks.
    """

    def __init__(self):
        self._engine = None
        self._lock = threading.Lock()
        self._speaking = False
        self._thread = None
        self.available_voices = []
        self.current_voice_index = CONFIG["DEFAULT_VOICE_INDEX"]
        self.rate = CONFIG["DEFAULT_RATE"]
        self.volume = CONFIG["DEFAULT_VOLUME"]

        # Optional callback: called with each word as it's spoken
        self.on_word = None     # callable(word: str)

        self._init_engine()

    # ── Public API ───────────────────────────────────────────────────────────

    def speak(self, text):
        """Speak text asynchronously. Stops any current speech first."""
        if not text.strip():
            return
        self.stop()
        self._thread = threading.Thread(
            target=self._speak_worker, args=(text,), daemon=True
        )
        self._thread.start()

    def stop(self):
        """Stop current speech immediately."""
        with self._lock:
            if self._engine and self._speaking:
                try:
                    self._engine.stop()
                except Exception:
                    pass
                self._speaking = False

    def set_rate(self, rate):
        """Set speech rate (words per minute). Typical range: 80–300."""
        self.rate = int(rate)
        with self._lock:
            if self._engine:
                self._engine.setProperty("rate", self.rate)

    def set_volume(self, volume):
        """Set volume 0.0 – 1.0."""
        self.volume = max(0.0, min(1.0, float(volume)))
        with self._lock:
            if self._engine:
                self._engine.setProperty("volume", self.volume)

    def set_voice(self, index):
        """Select voice by index from available_voices list."""
        if 0 <= index < len(self.available_voices):
            self.current_voice_index = index
            with self._lock:
                if self._engine:
                    self._engine.setProperty(
                        "voice", self.available_voices[index].id
                    )

    def get_voice_names(self):
        """Return list of available voice display names."""
        return [v.name for v in self.available_voices]

    def is_speaking(self):
        return self._speaking

    # ── Internal ─────────────────────────────────────────────────────────────

    def _init_engine(self):
        """Initialise pyttsx3 engine and load voices."""
        try:
            self._engine = pyttsx3.init()
            self._engine.setProperty("rate", self.rate)
            self._engine.setProperty("volume", self.volume)
            self.available_voices = self._engine.getProperty("voices") or []
            if self.available_voices:
                self._engine.setProperty(
                    "voice", self.available_voices[self.current_voice_index].id
                )
            # Word callback
            self._engine.connect("started-word", self._on_word_event)
        except Exception as e:
            print(f"[VoiceOutput] TTS engine init failed: {e}")
            self._engine = None

    def _on_word_event(self, name, location, length):
        """pyttsx3 word-start event – fire on_word callback."""
        if self.on_word:
            try:
                self.on_word(name)
            except Exception:
                pass

    def _speak_worker(self, text):
        """Background thread: actually run the TTS engine."""
        with self._lock:
            if self._engine is None:
                return
            self._speaking = True
        try:
            self._engine.say(text)
            self._engine.runAndWait()
        except Exception as e:
            print(f"[VoiceOutput] Speech error: {e}")
        finally:
            self._speaking = False
>>>>>>> 52c3d7ea5ed405484f229b508704a40d14764e6c
