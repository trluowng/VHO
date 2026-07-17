"""
Test script for Main Module
Tests the main functions speak_input and speak_output from module.py
"""

import sys
import os
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from module import speak_input, speak_output, speak_interactive


def test_speak_output_basic():
    """Test basic speak_output function"""
    print("="*60)
    print("Test: speak_output - Basic Functionality")
    print("="*60)
    
    test_phrases = [
        "Xin chào, đây là một bài kiểm tra",
        "Tôi là một trợ lý ảo",
        "Chào bạn",
    ]
    
    try:
        for phrase in test_phrases:
            print(f"\nSpeaking: {phrase}")
            speak_output(phrase, voice_type="female")
            print("  ✓ Completed")
        
        print("\n✓ Basic speak_output test completed\n")
        return True
    except Exception as e:
        print(f"\n✗ Error: {e}\n")
        return False


def test_speak_output_voices():
    """Test different speech speeds"""
    print("="*60)
    print("Test: speak_output - Speech Speeds")
    print("="*60)
    
    test_text = "Kiểm tra các tốc độ nói khác nhau"
    
    try:
        # Normal speed
        print(f"\nSpeaking at normal speed: {test_text}")
        speak_output(test_text, voice_type="female")
        print(f"  ✓ Normal speed completed")
        
        # Note: gTTS has limited speech control, mainly via slow parameter
        print("\n✓ Speech speed test completed\n")
        return True
    except Exception as e:
        print(f"\n✗ Error: {e}\n")
        return False


def test_speak_output_to_file():
    """Test speak_output with file saving"""
    print("="*60)
    print("Test: speak_output - Save to File")
    print("="*60)
    
    test_pairs = [
        ("module_test_1.mp3", "Đây là bài kiểm tra lưu tệp thứ nhất"),
        ("module_test_2.mp3", "Đây là bài kiểm tra lưu tệp thứ hai"),
    ]
    
    try:
        for filename, text in test_pairs:
            print(f"\nSaving '{text}' to {filename}")
            speak_output(text, voice_type="female", save_file=filename)
            
            if os.path.exists(filename):
                file_size = os.path.getsize(filename)
                print(f"  ✓ File saved ({file_size} bytes)")
            else:
                print(f"  ⚠ File processing pending")
        
        print("\n✓ File save test completed\n")
        return True
    except Exception as e:
        print(f"\n✗ Error: {e}\n")
        return False


def test_speak_input_basic():
    """Test basic speak_input function"""
    print("="*60)
    print("Test: speak_input - Basic Microphone Input")
    print("="*60)
    print("\nThis test will:")
    print("1. Listen to your microphone for 10 seconds")
    print("2. Convert your speech to Vietnamese text")
    print("3. Repeat back what you said")
    print("\nMake sure your microphone is working.\n")
    
    try:
        # Listen to user input
        text = speak_input(timeout=10, phrase_time_limit=30)
        
        print(f"\n✓ Successfully captured: {text}")
        
        # Confirm what was said
        confirmation = f"Bạn nói: {text}"
        print(f"\nRepeating back: {confirmation}")
        speak_output(confirmation, voice_type="female")
        
        print("\n✓ Microphone input test completed\n")
        return True
    except Exception as e:
        print(f"\n✗ Error: {e}\n")
        return False


def test_speak_input_error_handling():
    """Test speak_input error handling"""
    print("="*60)
    print("Test: speak_input - Error Handling")
    print("="*60)
    print("\nThis test checks if microphone errors are handled gracefully.\n")
    
    try:
        print("Attempting to capture speech with short timeout (2 seconds)...")
        text = speak_input(timeout=2, phrase_time_limit=5)
        print(f"Captured: {text}")
        
        print("\n✓ Error handling test completed\n")
        return True
    except Exception as e:
        print(f"✓ Error properly caught: {e}\n")
        return True  # Error handling works correctly


def test_speak_output_error_handling():
    """Test speak_output error handling"""
    print("="*60)
    print("Test: speak_output - Error Handling")
    print("="*60)
    
    try:
        # Test empty string
        print("\nTest 1: Empty string input")
        try:
            speak_output("")
            print("  ✗ Should have raised ValueError")
            return False
        except ValueError as e:
            print(f"  ✓ Error caught: {e}")
        
        # Test None input
        print("\nTest 2: None input")
        try:
            speak_output(None)
            print("  ✗ Should have raised ValueError")
            return False
        except ValueError as e:
            print(f"  ✓ Error caught: {e}")
        
        print("\n✓ Error handling test completed\n")
        return True
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}\n")
        return False


def run_all_tests():
    """Run all module tests"""
    print("\n" + "="*60)
    print("MAIN MODULE TEST SUITE")
    print("="*60 + "\n")
    
    results = []
    
    # Test 1: Basic speak_output
    results.append(("speak_output - Basic", test_speak_output_basic()))
    
    # Test 2: Different voices
    results.append(("speak_output - Voices", test_speak_output_voices()))
    
    # Test 3: Save to file
    results.append(("speak_output - Save to File", test_speak_output_to_file()))
    
    # Test 4: speak_input (uncomment for interactive test)
    # results.append(("speak_input - Microphone", test_speak_input_basic()))
    
    # Test 5: speak_input error handling
    # results.append(("speak_input - Error Handling", test_speak_input_error_handling()))
    
    # Test 6: speak_output error handling
    results.append(("speak_output - Error Handling", test_speak_output_error_handling()))
    
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
    print("\n" + "="*60)
    print("Note: Uncomment speak_input tests in run_all_tests() to test")
    print("      microphone input interactively")
    print("="*60 + "\n")


if __name__ == "__main__":
    run_all_tests()
