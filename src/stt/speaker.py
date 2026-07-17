"""
Text-to-Speech Module using gTTS (Google Text-to-Speech) library
"""

import os
import sys
import time
import uuid
import gc
from gtts import gTTS
from config import TTS_CONFIG, LANGUAGE, AVAILABLE_VOICES

# Use pygame for cross-platform audio playback
import pygame

# Initialize pygame mixer
pygame.mixer.init()

# Create temp folder for audio files
TEMP_AUDIO_DIR = os.path.join(os.path.dirname(__file__), "temp_audio")
if not os.path.exists(TEMP_AUDIO_DIR):
    os.makedirs(TEMP_AUDIO_DIR)


class TextToSpeech:
    """Handle text-to-speech conversion for Vietnamese using Google TTS"""
    
    def __init__(self, voice_type="female"):
        """
        Initialize the TTS engine
        
        Args:
            voice_type (str): "male" or "female" (affects pitch/speed in some contexts)
        """
        self.language = LANGUAGE
        self.voice_type = voice_type
        self.slow = False  # Set to True for slower speech
    
    def set_properties(self, voice_type="female", slow=False):
        """
        Set TTS properties
        
        Args:
            voice_type (str): "male" or "female"
            slow (bool): If True, speak slowly
        """
        self.voice_type = voice_type
        self.slow = slow
    
    def _play_audio(self, filepath):
        """
        Play audio file silently using pygame mixer
        
        Args:
            filepath (str): Path to audio file to play (MP3, WAV, etc.)
        """
        try:
            if not os.path.exists(filepath):
                raise FileNotFoundError(f"Audio file not found: {filepath}")
            
            # Get absolute path
            abs_path = os.path.abspath(filepath)
            print(f"🔊 Playing audio...")
            
            # Load and play with pygame
            pygame.mixer.music.load(abs_path)
            pygame.mixer.music.play()
            
            # Wait for playback to finish
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
            
            print(f"✓ Playback completed")
        except Exception as e:
            raise Exception(f"Error playing audio: {e}")
    
    def speak(self, text):
        """
        Speak the given text using speaker
        
        Args:
            text (str): Text to speak
        """
        if not text or not isinstance(text, str):
            raise ValueError("Text must be a non-empty string")
        
        print(f"\n💬 Speaking: {text}")
        temp_file = None
        try:
            # Create TTS object
            print("📡 Generating audio with Google TTS...")
            tts = gTTS(text=text, lang=self.language, slow=self.slow)
            
            # Use unique filename to avoid file conflicts
            unique_id = str(uuid.uuid4())[:8]
            temp_file = os.path.join(TEMP_AUDIO_DIR, f"speech_{unique_id}.mp3")
            tts.save(temp_file)
            print(f"✓ Audio saved")
            
            # Wait longer to ensure file is completely written
            time.sleep(1)
            
            # Play the audio (this will block until playback is complete)
            self._play_audio(temp_file)
            
            # Wait before stopping
            time.sleep(0.5)
            
            # Stop and unload pygame mixer
            pygame.mixer.music.stop()
            pygame.mixer.music.unload()
            time.sleep(0.3)
            
            # Force garbage collection to release file handles
            gc.collect()
            time.sleep(0.5)
            
            # Clean up temporary file
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                    print(f"🗑️  Cleaned up temporary file\n")
                except PermissionError:
                    # If still can't delete, just leave it (will be overwritten next time)
                    print(f"⚠️  File in use, will cleanup on next run\n")
                except Exception as cleanup_error:
                    print(f"⚠️  Could not delete temp file: {cleanup_error}\n")
        except Exception as e:
            # Ensure cleanup even on error
            if temp_file and os.path.exists(temp_file):
                try:
                    pygame.mixer.music.stop()
                    pygame.mixer.music.unload()
                    gc.collect()
                    time.sleep(0.5)
                    os.remove(temp_file)
                except:
                    pass
            raise Exception(f"Error during speech playback: {e}")
    
    def save_to_file(self, text, filename):
        """
        Save speech to audio file
        
        Args:
            text (str): Text to convert to speech
            filename (str): Output filename (e.g., "output.mp3")
        """
        if not text or not isinstance(text, str):
            raise ValueError("Text must be a non-empty string")
        
        print(f"\n💾 Saving speech to {filename}")
        try:
            # Create TTS object
            print("📡 Generating audio with Google TTS...")
            tts = gTTS(text=text, lang=self.language, slow=self.slow)
            
            # Save to file
            tts.save(filename)
            print(f"✓ Saved to {filename}\n")
        except Exception as e:
            raise Exception(f"Error saving to file: {e}")
    
    def stop(self):
        """Stop any ongoing speech (no-op for gTTS)"""
        pass
