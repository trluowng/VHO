"""
Test script for Speech Recognition Module
Tests the SpeechRecognizer class from recognizer.py
"""

import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from recognizer import SpeechRecognizer


def test_listen_and_recognize():
    """Test listening to microphone and recognizing speech"""
    print("="*60)
    print("Test: SpeechRecognizer - Listen and Recognize")
    print("="*60)
    print("\nThis test will:")
    print("1. Listen to your microphone for 10 seconds")
    print("2. Convert your speech to Vietnamese text")
    print("\nMake sure your microphone is working and speak clearly.\n")
    
    try:
        recognizer = SpeechRecognizer()
        
        # Test recognize_from_mic (combined listen + recognize)
        print("Listening for speech...\n")
        text = recognizer.recognize_from_mic(timeout=10, phrase_time_limit=30)
        
        print(f"✓ Speech recognized successfully!")
        print(f"  Recognized text: {text}\n")
        
        return True
    except Exception as e:
        print(f"✗ Error during recognition: {e}\n")
        return False


def test_listen_only():
    """Test listening to microphone only"""
    print("="*60)
    print("Test: SpeechRecognizer - Listen Only")
    print("="*60)
    print("\nThis test will listen to microphone without recognition.\n")
    
    try:
        recognizer = SpeechRecognizer()
        
        print("Listening for audio...\n")
        audio = recognizer.listen(timeout=10, phrase_time_limit=30)
        
        print(f"✓ Audio captured successfully!")
        print(f"  Audio duration: {len(audio.get_wav_data())} bytes\n")
        
        return True
    except Exception as e:
        print(f"✗ Error during listening: {e}\n")
        return False


def test_recognize_from_mic():
    """Test full speech recognition workflow"""
    print("="*60)
    print("Test: SpeechRecognizer - Full Workflow")
    print("="*60)
    print("\nThis test demonstrates the complete speech-to-text workflow:\n")
    
    try:
        recognizer = SpeechRecognizer()
        print("Step 1: Listening to microphone...")
        audio = recognizer.listen(timeout=10, phrase_time_limit=30)
        print("  ✓ Audio captured\n")
        
        print("Step 2: Recognizing speech...")
        text = recognizer.recognize(audio)
        print("  ✓ Speech recognized\n")
        
        print(f"Final result: {text}\n")
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}\n")
        return False


def run_all_tests():
    """Run all recognizer tests"""
    print("\n" + "="*60)
    print("SPEECH RECOGNIZER TEST SUITE")
    print("="*60 + "\n")
    
    results = []
    
    # Test 1: Listen and Recognize (combined)
    results.append(("Listen and Recognize", test_listen_and_recognize()))
    
    # Test 2: Listen only
    results.append(("Listen Only", test_listen_only()))
    
    # Test 3: Full workflow
    results.append(("Full Workflow", test_recognize_from_mic()))
    
    # Summary
    print("="*60)
    print("Test Summary")
    print("="*60)
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{test_name}: {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    print("="*60 + "\n")


if __name__ == "__main__":
    run_all_tests()
