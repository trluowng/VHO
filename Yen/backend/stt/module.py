"""
Main Speech-to-Text and Text-to-Speech Module
Combines recognizer and speaker for Vietnamese language
Uses Google Speech-to-Text API and Google TTS (gTTS)
"""

from .recognizer import SpeechRecognizer
from .speaker import TextToSpeech


def speak_input(timeout=None, phrase_time_limit=None):
    """
    Listen to user input via microphone and convert speech to text
    
    Args:
        timeout (int, optional): How long to wait before giving up (seconds)
        phrase_time_limit (int, optional): Maximum phrase duration (seconds)
    
    Returns:
        str: Recognized text from speech
    
    Raises:
        Exception: If speech recognition fails
    
    Example:
        >>> text = speak_input()
        >>> print(f"You said: {text}")
    """
    try:
        recognizer = SpeechRecognizer()
        text = recognizer.recognize_from_mic(timeout, phrase_time_limit)
        print(f"You said: {text}")
        return text
    except Exception as e:
        print(f"Error during speech input: {str(e)}")
        raise


def speak_output(text, voice_type="female", save_file=None):
    """
    Convert text to speech and output via speaker
    
    Args:
        text (str): Text to convert to speech
        voice_type (str, optional): "male" or "female" voice (default: "female")
        save_file (str, optional): If provided, save audio to this file instead of speaking
    
    Returns:
        None
    
    Raises:
        ValueError: If text is invalid
        Exception: If TTS fails
    
    Example:
        >>> speak_output("Xin chào thế giới")  # Speaks Vietnamese text
        >>> speak_output("Xin chào", save_file="greeting.mp3")  # Saves to file
    """
    try:
        if not text or not isinstance(text, str):
            raise ValueError("Text must be a non-empty string")
        
        speaker = TextToSpeech(voice_type=voice_type)
        
        if save_file:
            speaker.save_to_file(text, save_file)
        else:
            speaker.speak(text)
    except Exception as e:
        print(f"Error during speech output: {str(e)}")
        raise


def speak_interactive():
    """
    Interactive conversation mode - alternates between input and output
    
    Example:
        >>> speak_interactive()
    """
    print("Entering interactive mode. Say something to hear it back!")
    print("Press Ctrl+C to exit.\n")
    
    try:
        while True:
            try:
                # Listen to user
                text = speak_input()
                
                # Repeat back the text
                response = f"Bạn nói: {text}"
                speak_output(response)
            except Exception as e:
                print(f"Error: {str(e)}\nTrying again...\n")
                continue
    except KeyboardInterrupt:
        print("\n\nInteractive mode terminated.")


if __name__ == "__main__":
    # Test the module
    print("=== Speech-to-Text and Text-to-Speech Module ===\n")
    
    # Test speak_output
    print("Testing speak_output:")
    speak_output("Xin chào, đây là một bài kiểm tra")
    
    print("\n" + "="*40 + "\n")
    
    # Test speak_input (uncomment to use)
    # print("Testing speak_input:")
    # text = speak_input()
    # speak_output(f"Bạn nói: {text}")
