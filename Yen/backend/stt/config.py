"""
Configuration settings for Speech-to-Text and Text-to-Speech
"""

# Language settings
LANGUAGE = "vi"  # Vietnamese
LANGUAGE_FULL = "vi-VN"

# Speech Recognition settings
RECOGNITION_CONFIG = {
    "language": LANGUAGE_FULL,
    "timeout": 10,  # seconds
    "phrase_time_limit": 30,  # seconds
}

# Text-to-Speech settings (gTTS)
TTS_CONFIG = {
    "language": "vi",  # vi for Vietnamese
    "slow": False,  # Set True for slower speech
    "tld": "com",  # Top-level domain for Google TTS (com, co.uk, etc.)
}

# Supported voices for Vietnamese
AVAILABLE_VOICES = {
    "male": "Microsoft Huy",
    "female": "Microsoft Linh",
}

# Error messages
ERROR_MESSAGES = {
    "mic_not_found": "Microphone not found. Please check your audio input device.",
    "timeout": "No speech detected. Please try again.",
    "request_error": "Could not request results from speech recognition service.",
    "unknown_error": "An unknown error occurred.",
}
