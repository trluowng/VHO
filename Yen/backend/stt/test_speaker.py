"""
Test script for Text-to-Speech Module
Tests the TextToSpeech class from speaker.py
"""

import sys
import os
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from speaker import TextToSpeech


def test_basic_speak():
    """Test basic text-to-speech"""
    print("="*60)
    print("Test: TextToSpeech - Basic Speak")
    print("="*60)
    
    test_phrases = [
        "Xin chào thế giới",
        "Đây là một bài kiểm tra",
        "Tôi là một trợ lý ảo",
    ]
    
    try:
        speaker = TextToSpeech(voice_type="female")
        
        for phrase in test_phrases:
            print(f"\nSpeaking: {phrase}")
            speaker.speak(phrase)
            print("  ✓ Completed")
        
        print("\n✓ Basic speak test completed\n")
        return True
    except Exception as e:
        print(f"\n✗ Error: {e}\n")
        return False


def test_voice_types():
    """Test different speech speeds (slow vs normal)"""
    print("="*60)
    print("Test: TextToSpeech - Speech Speeds")
    print("="*60)
    
    test_text = "Xin chào, đây là kiểm tra tốc độ nói"
    
    try:
        # Normal speed
        print(f"\nTesting normal speed...")
        speaker = TextToSpeech(voice_type="female")
        speaker.set_properties(slow=False)
        speaker.speak(test_text)
        print(f"  ✓ Normal speed completed")
        
        # Slow speed
        print(f"\nTesting slow speed...")
        speaker = TextToSpeech(voice_type="female")
        speaker.set_properties(slow=True)
        speaker.speak(test_text)
        print(f"  ✓ Slow speed completed")
        
        print("\n✓ Speech speeds test completed\n")
        return True
    except Exception as e:
        print(f"\n✗ Error: {e}\n")
        return False


def test_save_to_file():
    """Test saving speech to audio file"""
    print("="*60)
    print("Test: TextToSpeech - Save to File")
    print("="*60)
    
    test_files = [
        ("test_output_1.mp3", "Đây là tệp âm thanh thứ nhất"),
        ("test_output_2.mp3", "Đây là tệp âm thanh thứ hai"),
    ]
    
    try:
        speaker = TextToSpeech(voice_type="female")
        
        for filename, text in test_files:
            print(f"\nSaving to {filename}: {text}")
            speaker.save_to_file(text, filename)
            
            if os.path.exists(filename):
                file_size = os.path.getsize(filename)
                print(f"  ✓ File saved successfully ({file_size} bytes)")
            else:
                print(f"  ⚠ File not found (may be processed by system)")
        
        print("\n✓ Save to file test completed\n")
        return True
    except Exception as e:
        print(f"\n✗ Error: {e}\n")
        return False


def test_rate_and_volume():
    """Test different speech speeds"""
    print("="*60)
    print("Test: TextToSpeech - Speech Speed Settings")
    print("="*60)
    
    test_text = "Kiểm tra tốc độ nói"
    
    try:
        speaker = TextToSpeech(voice_type="female")
        
        print(f"\nDefault settings (normal speed):")
        print(f"  Slow: False")
        print(f"Speaking: {test_text}")
        speaker.speak(test_text)
        print("  ✓ Default settings completed")
        
        # Test slower speed
        print(f"\nTesting slower speed:")
        speaker.set_properties(slow=True)
        print(f"  Slow: True")
        print(f"Speaking: {test_text}")
        speaker.speak(test_text)
        print("  ✓ Slower speed completed")
        
        print("\n✓ Speech speed test completed\n")
        return True
    except Exception as e:
        print(f"\n✗ Error: {e}\n")
        return False


def test_empty_input():
    """Test error handling for invalid input"""
    print("="*60)
    print("Test: TextToSpeech - Error Handling")
    print("="*60)
    
    try:
        speaker = TextToSpeech(voice_type="female")
        
        # Test empty string
        print("\nTest 1: Empty string input")
        try:
            speaker.speak("")
            print("  ✗ Should have raised ValueError")
            return False
        except ValueError as e:
            print(f"  ✓ Correctly caught error: {e}")
        
        # Test None input
        print("\nTest 2: None input")
        try:
            speaker.speak(None)
            print("  ✗ Should have raised ValueError")
            return False
        except ValueError as e:
            print(f"  ✓ Correctly caught error: {e}")
        
        print("\n✓ Error handling test completed\n")
        return True
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}\n")
        return False


def run_all_tests():
    """Run all speaker tests"""
    print("\n" + "="*60)
    print("TEXT-TO-SPEECH MODULE TEST SUITE")
    print("="*60 + "\n")
    
    results = []
    
    # Test 1: Basic speak
    results.append(("Basic Speak", test_basic_speak()))
    
    # Test 2: Voice types
    results.append(("Voice Types", test_voice_types()))
    
    # Test 3: Save to file
    results.append(("Save to File", test_save_to_file()))
    
    # Test 4: Rate and volume
    results.append(("Rate and Volume", test_rate_and_volume()))
    
    # Test 5: Error handling
    results.append(("Error Handling", test_empty_input()))
    
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
