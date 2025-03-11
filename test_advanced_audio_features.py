"""
Test script for the advanced audio features module.

This script demonstrates the key detection, harmonic analysis,
voice/instrumental detection, and audio segmentation capabilities.

Usage:
    python test_advanced_audio_features.py [--audio AUDIO_PATH]
"""

import os
import argparse
import logging
from pprint import pprint

# Set up logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_advanced_audio_features")

def test_advanced_features(audio_path):
    """Test the advanced audio features module"""
    print(f"\n=== Testing Advanced Audio Features on {audio_path} ===\n")
    
    try:
        # Try importing required dependencies
        try:
            import numpy as np
            import librosa
            import matplotlib.pyplot as plt
            DEPS_AVAILABLE = True
        except ImportError as e:
            print(f"Error importing dependencies: {e}")
            DEPS_AVAILABLE = False
            return
            
        # Try importing the advanced features module
        try:
            from ai_document_organizer_v2.plugins.audio_analyzer.advanced_features import (
                detect_musical_key,
                analyze_harmonic_content,
                detect_voice_instrumental,
                segment_audio,
                analyze_advanced_features
            )
        except ImportError as e:
            print(f"Error importing advanced features module: {e}")
            return
            
        # Check if the file exists
        if not os.path.exists(audio_path):
            print(f"File not found: {audio_path}")
            return
            
        # Load the audio file
        print("Loading audio file...")
        y, sr = librosa.load(audio_path, sr=None)
        print(f"Audio loaded: {len(y)/sr:.2f} seconds, {sr} Hz sample rate")
        
        # Test the individual feature functions
        
        # 1. Test key detection
        print("\n--- Musical Key Detection ---")
        key_info = detect_musical_key(y, sr)
        if 'error' in key_info:
            print(f"Error in key detection: {key_info['error']}")
        else:
            print(f"Detected key: {key_info.get('key')}")
            print(f"Confidence: {key_info.get('confidence', 0):.2f}")
            print("Alternate interpretations:")
            for alt in key_info.get('alternates', []):
                print(f"  - {alt.get('key')}: {alt.get('confidence', 0):.2f}")
        
        # 2. Test harmonic content analysis
        print("\n--- Harmonic Content Analysis ---")
        harmonic_info = analyze_harmonic_content(y, sr)
        if 'error' in harmonic_info:
            print(f"Error in harmonic analysis: {harmonic_info['error']}")
        else:
            print(f"Harmonic ratio: {harmonic_info.get('harmonic_ratio', 0):.2f}")
            print(f"Harmonicity: {harmonic_info.get('harmonicity', 0):.2f}")
            print(f"Character: {harmonic_info.get('character')}")
            print(f"Brightness: {harmonic_info.get('brightness')}")
            print("Frequency band distribution:")
            bands = harmonic_info.get('frequency_band_distribution', [])
            for i, energy in enumerate(bands):
                print(f"  Band {i+1}: {energy:.3f}")
        
        # 3. Test voice/instrumental detection
        print("\n--- Voice/Instrumental Detection ---")
        vocal_info = detect_voice_instrumental(y, sr)
        if 'error' in vocal_info:
            print(f"Error in voice detection: {vocal_info['error']}")
        else:
            print(f"Classification: {vocal_info.get('classification')}")
            print(f"Confidence: {vocal_info.get('confidence', 0):.2f}")
            print(f"Vocal score: {vocal_info.get('vocal_score', 0):.2f}")
        
        # 4. Test audio segmentation (only for longer audio)
        if len(y) > 10 * sr:  # Only for audio > 10 seconds
            print("\n--- Audio Segmentation ---")
            segment_info = segment_audio(y, sr, min_segment_length=2.0)
            if 'error' in segment_info:
                print(f"Error in audio segmentation: {segment_info['error']}")
            else:
                segments = segment_info.get('segments', [])
                print(f"Number of segments: {len(segments)}")
                for i, segment in enumerate(segments):
                    print(f"  Segment {i+1}: {segment.get('start'):.1f}s - {segment.get('end'):.1f}s " +
                         f"(duration: {segment.get('duration'):.1f}s)")
                    if 'group' in segment:
                        print(f"    Group: {segment.get('group')}")
        else:
            print("\n--- Audio Segmentation (Skipped - Audio too short) ---")
        
        # 5. Test comprehensive analysis
        print("\n--- Comprehensive Advanced Analysis ---")
        all_features = analyze_advanced_features(y, sr)
        if 'error' in all_features:
            print(f"Error in comprehensive analysis: {all_features['error']}")
        elif not all_features.get('success', False):
            print(f"Comprehensive analysis failed: {all_features.get('error', 'Unknown error')}")
        else:
            print("Advanced analysis successful!")
            print(f"Number of analysis components: {sum(1 for k in all_features if k != 'success')}")
            
            # Plot the audio waveform
            plt.figure(figsize=(10, 4))
            plt.plot(librosa.times_like(y, sr=sr), y, color='blue', alpha=0.7)
            plt.title(f"Waveform with Key: {key_info.get('key', 'Unknown')}, " +
                     f"Type: {vocal_info.get('classification', 'Unknown')}")
            plt.xlabel("Time (s)")
            plt.ylabel("Amplitude")
            plt.tight_layout()
            
            # Save the figure
            output_path = f"{os.path.splitext(audio_path)[0]}_analysis.png"
            plt.savefig(output_path)
            plt.close()
            print(f"Analysis visualization saved to: {output_path}")
            
    except Exception as e:
        print(f"Error in advanced audio features test: {e}")

def create_test_audio(output_path='test_audio.wav', duration=10):
    """Create a test audio file if none is provided"""
    try:
        import numpy as np
        from scipy.io import wavfile
        print(f"Creating test audio file: {output_path}")
        
        # Sample rate (CD quality)
        sample_rate = 44100
        
        # Generate a simple sine wave with frequency sweep
        t = np.linspace(0, duration, duration * sample_rate, endpoint=False)
        
        # Create frequency sweep for first part (C major scale frequencies)
        # C4 to C5: 261.63, 293.66, 329.63, 349.23, 392.00, 440.00, 493.88, 523.25
        notes = [261.63, 293.66, 329.63, 349.23, 392.00, 440.00, 493.88, 523.25]
        
        # Create segments
        segments = []
        segment_duration = duration / 4  # 4 segments
        
        # Segment 1: C major chord (C, E, G)
        t1 = np.linspace(0, segment_duration, int(segment_duration * sample_rate), endpoint=False)
        chord = np.sin(2 * np.pi * 261.63 * t1)  # C
        chord += np.sin(2 * np.pi * 329.63 * t1)  # E
        chord += np.sin(2 * np.pi * 392.00 * t1)  # G
        segments.append(chord / 3.0)  # Normalize
        
        # Segment 2: G major chord (G, B, D)
        t2 = np.linspace(0, segment_duration, int(segment_duration * sample_rate), endpoint=False)
        chord = np.sin(2 * np.pi * 392.00 * t2)  # G
        chord += np.sin(2 * np.pi * 493.88 * t2)  # B
        chord += np.sin(2 * np.pi * 587.33 * t2)  # D
        segments.append(chord / 3.0)  # Normalize
        
        # Segment 3: A minor chord (A, C, E)
        t3 = np.linspace(0, segment_duration, int(segment_duration * sample_rate), endpoint=False)
        chord = np.sin(2 * np.pi * 440.00 * t3)  # A
        chord += np.sin(2 * np.pi * 523.25 * t3)  # C
        chord += np.sin(2 * np.pi * 659.25 * t3)  # E
        segments.append(chord / 3.0)  # Normalize
        
        # Segment 4: F major chord (F, A, C)
        t4 = np.linspace(0, segment_duration, int(segment_duration * sample_rate), endpoint=False)
        chord = np.sin(2 * np.pi * 349.23 * t4)  # F
        chord += np.sin(2 * np.pi * 440.00 * t4)  # A
        chord += np.sin(2 * np.pi * 523.25 * t4)  # C
        segments.append(chord / 3.0)  # Normalize
        
        # Concatenate segments
        signal = np.concatenate(segments)
        
        # Add some amplitude modulation for "rhythm"
        am_freq = 4.0  # 4 Hz modulation
        am = 0.5 + 0.5 * np.sin(2 * np.pi * am_freq * np.linspace(0, duration, len(signal)))
        signal = signal * am
        
        # Convert to 16-bit PCM
        signal = (signal * 32767).astype(np.int16)
        
        # Write to file
        wavfile.write(output_path, sample_rate, signal)
        
        print(f"Created test audio file: {output_path}")
        return output_path
    except ImportError:
        print("scipy or numpy not available for test audio creation")
        return None

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Test the advanced audio features module')
    parser.add_argument('--audio', help='Path to audio file for testing')
    return parser.parse_args()

def main():
    """Main test function"""
    args = parse_args()
    
    # Get audio path from arguments or create test audio
    audio_path = args.audio
    if not audio_path or not os.path.exists(audio_path):
        print("No valid audio file provided, creating test audio")
        audio_path = create_test_audio()
        if not audio_path:
            print("Failed to create test audio, please provide an audio file")
            return
    
    # Test the advanced features
    test_advanced_features(audio_path)

if __name__ == "__main__":
    main()