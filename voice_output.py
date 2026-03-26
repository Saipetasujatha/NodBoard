"""
voice_output.py
---------------
Offline text-to-speech using pyttsx3.
Supports voice selection, speed/volume control, and word-by-word callbacks.
"""

import threading
import pyttsx3

CONFIG = {
    "DEFAULT_RATE": 150,
    "DEFAULT_VOLUME": 1.0,
    "DEFAULT_VOICE_INDEX": 0,
}


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
        self.on_word = None
        self._init_engine()

    # ── Public API ───────────────────────────────────────────────────────────

    def speak(self, text):
        """Speak text asynchronously. Stops any current speech first."""
        if not text or not text.strip():
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
        """Set speech rate (words per minute)."""
        self.rate = int(rate)
        with self._lock:
            if self._engine:
                self._engine.setProperty("rate", self.rate)

    def set_volume(self, volume):
        """Set volume 0.0 to 1.0."""
        self.volume = max(0.0, min(1.0, float(volume)))
        with self._lock:
            if self._engine:
                self._engine.setProperty("volume", self.volume)

    def set_voice(self, index):
        """Select voice by index."""
        if 0 <= index < len(self.available_voices):
            self.current_voice_index = index
            with self._lock:
                if self._engine:
                    self._engine.setProperty("voice", self.available_voices[index].id)

    def get_voice_names(self):
        """Return list of available voice display names."""
        return [v.name for v in self.available_voices]

    def is_engine_available(self):
        return self._engine is not None

    # ── Internal ─────────────────────────────────────────────────────────────

    def _init_engine(self):
        try:
            self._engine = pyttsx3.init()
            self._engine.setProperty("rate", self.rate)
            self._engine.setProperty("volume", self.volume)
            self.available_voices = self._engine.getProperty("voices") or []
            if self.available_voices:
                self._engine.setProperty(
                    "voice", self.available_voices[self.current_voice_index].id
                )
            self._engine.connect("started-word", self._on_word_event)
        except Exception as e:
            print(f"[VoiceOutput] TTS engine init failed: {e}")
            self._engine = None

    def _on_word_event(self, name, location, length):
        if self.on_word:
            try:
                self.on_word(name)
            except Exception:
                pass

    def _speak_worker(self, text):
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


if __name__ == "__main__":
    tts = VoiceOutput()
    if tts.is_engine_available():
        print("TTS engine available")
        print("Voices:", tts.get_voice_names())
        tts.speak("Hello, NodBoard is ready.")
    else:
        print("TTS engine not available")