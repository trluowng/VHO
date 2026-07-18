"""Vietnamese speech-to-text helpers built on ``SpeechRecognition``.

The original module only listened to the microphone attached to the Python
process. A web backend cannot access the browser's microphone, so the chat
integration records a WAV file in the browser and passes those bytes here.
The direct-microphone methods are kept for the standalone STT demos.
"""

from __future__ import annotations

import io
import wave

import speech_recognition as sr

from .config import ERROR_MESSAGES, LANGUAGE_FULL, RECOGNITION_CONFIG


class InvalidAudioError(ValueError):
    """The uploaded payload is not a readable WAV audio stream."""


class NoSpeechRecognizedError(RuntimeError):
    """Audio was readable, but no intelligible speech was detected."""


class SpeechServiceError(RuntimeError):
    """The upstream Google recognition service could not be reached."""


class SpeechRecognizer:
    """Handle speech recognition for Vietnamese"""

    def __init__(self):
        """Initialize without opening a microphone device.

        Keeping microphone creation lazy is important on Render/Linux servers,
        where PyAudio and an input device are normally unavailable.
        """
        self.recognizer = sr.Recognizer()

    def listen(self, timeout=None, phrase_time_limit=None):
        """
        Listen to microphone input and return audio data
        
        Args:
            timeout (int): How long to wait before giving up (seconds)
            phrase_time_limit (int): Maximum phrase time (seconds)
        
        Returns:
            sr.AudioData: Audio data object
        """
        timeout = timeout or RECOGNITION_CONFIG["timeout"]
        phrase_time_limit = phrase_time_limit or RECOGNITION_CONFIG["phrase_time_limit"]
        
        try:
            microphone = sr.Microphone()
            with microphone as source:
                print("Listening... Please speak now.")
                audio = self.recognizer.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=phrase_time_limit
                )
            return audio
        except sr.WaitTimeoutError:
            raise NoSpeechRecognizedError(ERROR_MESSAGES["timeout"])
        except (AttributeError, OSError) as exc:
            raise RuntimeError(ERROR_MESSAGES["mic_not_found"]) from exc

    def recognize(self, audio):
        """
        Recognize speech from audio data
        
        Args:
            audio (sr.AudioData): Audio data to recognize
        
        Returns:
            str: Recognized text
        """
        try:
            text = self.recognizer.recognize_google(
                audio,
                language=LANGUAGE_FULL
            )
            text = (text or "").strip()
            if not text:
                raise NoSpeechRecognizedError("Không nhận diện được lời nói trong bản ghi âm.")
            return text
        except sr.UnknownValueError as exc:
            raise NoSpeechRecognizedError("Không nhận diện được lời nói trong bản ghi âm.") from exc
        except sr.RequestError as exc:
            raise SpeechServiceError(ERROR_MESSAGES["request_error"]) from exc

    def recognize_wav_bytes(self, payload: bytes) -> str:
        """Transcribe PCM WAV bytes sent by the web client."""
        if not payload:
            raise InvalidAudioError("Bản ghi âm đang trống.")

        try:
            with sr.AudioFile(io.BytesIO(payload)) as source:
                audio = self.recognizer.record(source)
        except (EOFError, OSError, ValueError, wave.Error) as exc:
            raise InvalidAudioError("Tệp âm thanh không phải WAV hợp lệ.") from exc

        return self.recognize(audio)

    def recognize_from_mic(self, timeout=None, phrase_time_limit=None):
        """
        Recognize speech directly from microphone
        
        Args:
            timeout (int): How long to wait before giving up (seconds)
            phrase_time_limit (int): Maximum phrase time (seconds)
        
        Returns:
            str: Recognized text
        """
        audio = self.listen(timeout, phrase_time_limit)
        text = self.recognize(audio)
        return text
