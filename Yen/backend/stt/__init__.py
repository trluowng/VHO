"""Speech-to-text and text-to-speech helpers for Vietnamese.

TTS imports gTTS/pygame and initializes an audio device, so it is loaded lazily.
The web server only needs :class:`SpeechRecognizer` and can therefore run on a
headless deployment without importing the playback stack.
"""

from .recognizer import (
    InvalidAudioError,
    NoSpeechRecognizedError,
    SpeechRecognizer,
    SpeechServiceError,
)


def speak_input(*args, **kwargs):
    from .module import speak_input as _speak_input

    return _speak_input(*args, **kwargs)


def speak_output(*args, **kwargs):
    from .module import speak_output as _speak_output

    return _speak_output(*args, **kwargs)


__all__ = [
    "InvalidAudioError",
    "NoSpeechRecognizedError",
    "SpeechRecognizer",
    "SpeechServiceError",
    "speak_input",
    "speak_output",
]
