"""
Speech-to-Text Module using speech_recognition library
"""

import speech_recognition as sr
from config import RECOGNITION_CONFIG, ERROR_MESSAGES, LANGUAGE_FULL


class SpeechRecognizer:
    """Handle speech recognition for Vietnamese"""
    
    def __init__(self):
        """Initialize the speech recognizer"""
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
    
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
            with self.microphone as source:
                print("Listening... Please speak now.")
                audio = self.recognizer.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=phrase_time_limit
                )
            return audio
        except sr.UnknownValueError:
            raise Exception(ERROR_MESSAGES["unknown_error"])
        except sr.RequestError as e:
            raise Exception(f"{ERROR_MESSAGES['request_error']}: {e}")
        except sr.MicrophoneError:
            raise Exception(ERROR_MESSAGES["mic_not_found"])
        except sr.WaitTimeoutError:
            raise Exception(ERROR_MESSAGES["timeout"])
    
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
            return text
        except sr.UnknownValueError:
            raise Exception("Could not understand the audio. Please try again.")
        except sr.RequestError as e:
            raise Exception(f"{ERROR_MESSAGES['request_error']}: {e}")
    
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
