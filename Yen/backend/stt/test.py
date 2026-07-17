"""
Test script for Speech-to-Text and Text-to-Speech Module
"""

import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from module import speak_input, speak_output


def test_speak_output():
    """Test text-to-speech functionality"""
    print("="*50)
    print("Test 1: Text-to-Speech (speak_output)")
    print("="*50)
    
    test_phrases = [
        "Xin chào thế giới",
        "Đây là một bài kiểm tra",
        "Tôi là một trợ lý ảo",
    ]
    
    for phrase in test_phrases:
        try:
            print(f"\nSpeaking: {phrase}")
            speak_output(phrase, voice_type="female")
        except Exception as e:
            print(f"Error: {e}")
    
    print("\n✓ speak_output test completed\n")


def test_speak_input():
    """Test speech-to-text functionality"""
    print("="*50)
    print("Test 2: Speech-to-Text (speak_input)")
    print("="*50)
    print("\nPlease speak when prompted...")
    
    try:
        text = speak_input(timeout=10, phrase_time_limit=30)
        print(f"Recognized text: {text}")
        
        # Repeat back what was said
        print("\nRepeating back...")
        response = f"Bạn nói: {text}"
        speak_output(response)
        
        print("\n✓ speak_input test completed\n")
    except Exception as e:
        print(f"Error: {e}")
        print("✗ speak_input test failed\n")


def test_save_to_file():
    """Test saving speech to audio file"""
    print("="*50)
    print("Test 3: Save Speech to File")
    print("="*50)
    
    try:
        text = "Đây là một tệp âm thanh"
        filename = "test_output.mp3"
        print(f"Saving to {filename}: {text}")
        speak_output(text, save_file=filename)
        print(f"✓ File saved as {filename}\n")
    except Exception as e:
        print(f"Error: {e}\n")


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*50)
    print("STT/TTS Module Test Suite")
    print("="*50 + "\n")
    
    # Test 1: speak_output
    test_speak_output()
    
    # Test 2: speak_input (uncomment to enable)
    # test_speak_input()
    
    # Test 3: save to file
    test_save_to_file()
    
    print("="*50)
    print("All tests completed!")
    print("="*50)


if __name__ == "__main__":
    run_all_tests()
