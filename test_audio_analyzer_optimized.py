"""
Test script for the optimized Audio Analyzer Plugin.

This script tests the performance-optimized plugin with caching
and adaptive processing features. It also benchmarks processing time
and cache hit rate.

Usage:
    python test_audio_analyzer_optimized.py [--audio AUDIO_PATH]
"""

import os
import time
import argparse
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_audio_analyzer_optimized")

# Import required components
from ai_document_organizer_v2.core.settings import SettingsManager
from ai_document_organizer_v2.plugins.audio_analyzer.plugin_optimized import AudioAnalyzerPlugin

def progress_callback(progress, total, message):
    """Simple progress callback function"""
    percent = progress / total * 100
    bar_length = 30
    filled_length = int(bar_length * progress // total)
    bar = '█' * filled_length + '-' * (bar_length - filled_length)
    print(f'\r[{bar}] {percent:.1f}% {progress}/{total} {message}', end='')
    if progress == total:
        print()

def test_audio_analyzer_optimized(audio_path, cache_enabled=True):
    """Test the optimized Audio Analyzer plugin with caching support"""
    print("\n=== Testing Optimized Audio Analyzer Plugin ===\n")
    
    # Create a settings manager
    settings = SettingsManager()
    
    # Create plugin instance
    plugin = AudioAnalyzerPlugin("audio-analyzer-1", "Audio Analyzer", "1.1.0", 
                                "Optimized Audio Analyzer Plugin")
    
    # Set settings manager
    plugin.settings_manager = settings
    
    # Initialize the plugin
    if not plugin.initialize():
        print("Failed to initialize plugin")
        return
    
    # Configure the plugin
    plugin.set_setting("audio_analyzer.cache_enabled", cache_enabled)
    plugin.set_setting("audio_analyzer.processing_mode", "full")
    plugin.set_setting("audio_analyzer.adaptive_processing", True)
    plugin.set_setting("audio_analyzer.time_limit_enabled", True)
    plugin.set_setting("audio_analyzer.max_duration", 60)  # 1 minute max for testing
    
    # Check if the file exists
    if not os.path.exists(audio_path):
        print(f"File not found: {audio_path}")
        return
    
    print(f"Analyzing audio file: {audio_path}")
    
    # First run (should be slower)
    start_time = time.time()
    print("First analysis run (cache miss expected)...")
    results = plugin.analyze_media(audio_path, progress_callback)
    first_run_time = time.time() - start_time
    
    # Print basic results from first run
    print(f"\nFirst run completed in {first_run_time:.2f} seconds")
    print(f"Metadata extracted: {len(results.get('metadata', {}))}")
    print(f"Waveform generated: {results.get('preview_path') is not None}")
    
    # Check for advanced analysis results
    metadata = results.get('metadata', {})
    if 'advanced_analysis' in metadata:
        print("\nAdvanced audio analysis results:")
        print(f"  Tempo: {metadata.get('tempo')} BPM")
        print(f"  Beat count: {metadata.get('beat_count')}")
        print(f"  Beat regularity: {metadata.get('beat_regularity', 0):.2f}")
        print(f"  Dominant pitch: {metadata.get('dominant_pitch')}")
        print(f"  Audio quality rating: {metadata.get('quality_rating', 0):.1f}/10")
    
    # Second run (should be faster if cache is enabled)
    if cache_enabled:
        print("\nSecond analysis run (cache hit expected)...")
        start_time = time.time()
        results2 = plugin.analyze_media(audio_path, progress_callback)
        second_run_time = time.time() - start_time
        
        print(f"\nSecond run completed in {second_run_time:.2f} seconds")
        
        # Calculate speedup
        if first_run_time > 0:
            speedup = first_run_time / second_run_time
            print(f"Cache speedup: {speedup:.1f}x faster")
        
        # Get cache stats
        cache_stats = plugin.cache.get_stats()
        print("\nCache statistics:")
        print(f"  Hits: {cache_stats.get('hits')}")
        print(f"  Misses: {cache_stats.get('misses')}")
        print(f"  Hit rate: {cache_stats.get('hit_rate'):.1f}%")
        print(f"  Cache entries: {cache_stats.get('cache_entries')}")
        cache_size_mb = cache_stats.get('cache_size_bytes', 0) / (1024 * 1024)
        print(f"  Cache size: {cache_size_mb:.2f} MB")
    
    # Test adaptive processing modes
    print("\nTesting adaptive processing modes...")
    
    # Test with different processing modes
    for mode in ["minimal", "standard", "full"]:
        plugin.set_setting("audio_analyzer.processing_mode", mode)
        plugin.set_setting("audio_analyzer.adaptive_processing", False)  # Disable adaptive override
        
        # Clear cache for this test
        plugin.cache.clear()
        
        print(f"\nRunning with '{mode}' processing mode...")
        start_time = time.time()
        results = plugin.analyze_media(audio_path, progress_callback)
        run_time = time.time() - start_time
        
        # Print results
        print(f"\nCompleted in {run_time:.2f} seconds")
        metadata = results.get('metadata', {})
        has_advanced = 'advanced_analysis' in metadata
        print(f"Advanced analysis: {'Yes' if has_advanced else 'No'}")
        
        # Check for specific features based on mode
        if has_advanced:
            features = metadata['advanced_analysis']
            feature_count = sum(1 for f in features if features[f] is not None)
            print(f"Number of advanced features: {feature_count}")
    
    return results

def create_test_audio(output_path='test_audio.wav', duration=5):
    """Create a test audio file using scipy if no audio file is provided"""
    try:
        import numpy as np
        from scipy.io import wavfile
        print(f"Creating test audio file: {output_path}")
        
        # Sample rate (CD quality)
        sample_rate = 44100
        
        # Generate a simple sine wave with frequency sweep
        t = np.linspace(0, duration, duration * sample_rate, endpoint=False)
        
        # Create frequency sweep
        freq_start = 220.0  # A3
        freq_end = 880.0    # A5
        
        # Linear sweep
        freq = np.linspace(freq_start, freq_end, len(t))
        
        # Generate sine wave with frequency sweep
        signal = 0.5 * np.sin(2 * np.pi * freq * t)
        
        # Add some harmonics
        signal += 0.25 * np.sin(4 * np.pi * freq * t)
        signal += 0.125 * np.sin(6 * np.pi * freq * t)
        
        # Add beats/amplitude modulation
        beat_freq = 2.0  # 2 Hz beat
        amplitude = 0.75 + 0.25 * np.sin(2 * np.pi * beat_freq * t)
        signal = signal * amplitude
        
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
    parser = argparse.ArgumentParser(description='Test the optimized Audio Analyzer plugin')
    parser.add_argument('--audio', help='Path to audio file for testing')
    parser.add_argument('--no-cache', dest='cache', action='store_false',
                       help='Disable caching for testing')
    parser.set_defaults(cache=True)
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
    
    # Test the optimized plugin
    test_audio_analyzer_optimized(audio_path, args.cache)

if __name__ == "__main__":
    main()