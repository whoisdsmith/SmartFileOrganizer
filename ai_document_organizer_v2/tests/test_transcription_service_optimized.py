"""
Test script for the optimized Transcription Service Plugin.

This script tests the performance-optimized plugin with caching
and multiple provider support. It also benchmarks processing time
and cache hit rate.

Usage:
    python test_transcription_service_optimized.py [--audio AUDIO_PATH] [--provider PROVIDER]
"""

import os
import time
import argparse
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_transcription_service_optimized")

# Import required components
from ai_document_organizer_v2.core.settings import SettingsManager
from ai_document_organizer_v2.plugins.transcription_service.plugin_optimized import TranscriptionServicePlugin

def progress_callback(progress, total, message):
    """Simple progress callback function"""
    percent = progress / total * 100
    bar_length = 30
    filled_length = int(bar_length * progress // total)
    bar = '█' * filled_length + '-' * (bar_length - filled_length)
    print(f'\r[{bar}] {percent:.1f}% {progress}/{total} {message}', end='')
    if progress == total:
        print()

def test_transcription_service_optimized(audio_path, provider=None, cache_enabled=True):
    """Test the optimized Transcription Service plugin with caching support"""
    print(f"\n=== Testing Optimized Transcription Service Plugin with {provider if provider else 'default'} provider ===\n")
    
    # Create a settings manager
    settings = SettingsManager()
    
    # Create plugin instance
    plugin = TranscriptionServicePlugin("transcription-service-1", "Transcription Service", "1.1.0", 
                                "Optimized Transcription Service Plugin")
    
    # Set settings manager
    plugin.settings_manager = settings
    
    # Initialize the plugin
    if not plugin.initialize():
        print("Failed to initialize plugin")
        return
    
    # Configure the plugin
    plugin.set_setting("transcription.cache_enabled", cache_enabled)
    
    # Set provider if specified
    if provider:
        plugin.set_setting("transcription.default_provider", provider)
    else:
        # Use mock provider by default for testing
        provider = plugin.get_setting("transcription.default_provider", "mock")
        
    # Check if the file exists
    if not os.path.exists(audio_path):
        print(f"File not found: {audio_path}")
        return
    
    print(f"Transcribing audio file: {audio_path}")
    print(f"Using provider: {provider}")
    
    # First run (should be slower)
    start_time = time.time()
    print("First transcription run (cache miss expected)...")
    results = plugin.transcribe(audio_path, provider=provider, callback=progress_callback)
    first_run_time = time.time() - start_time
    
    # Print basic results from first run
    print(f"\nFirst run completed in {first_run_time:.2f} seconds")
    
    # Check for transcription results
    if results.get('success', False):
        print(f"\nTranscription results:")
        print(f"  Text length: {len(results.get('text', ''))}")
        print(f"  Segments: {len(results.get('segments', []))}")
        print(f"  Language: {results.get('language')}")
        
        # Print a sample of the text
        text = results.get('text', '')
        if text:
            print(f"\nSample text: {text[:200]}..." if len(text) > 200 else f"\nFull text: {text}")
            
        # Print formatted output if available
        if 'formatted_output' in results:
            format_type = plugin.get_setting("transcription.output_format", "text")
            print(f"\nFormatted output ({format_type}):")
            formatted_text = results['formatted_output']
            print(f"{formatted_text[:200]}..." if len(formatted_text) > 200 else formatted_text)
    else:
        print(f"\nTranscription failed: {results.get('error', 'Unknown error')}")
    
    # Second run (should be faster if cache is enabled)
    if cache_enabled:
        print("\nSecond transcription run (cache hit expected)...")
        start_time = time.time()
        results2 = plugin.transcribe(audio_path, provider=provider, callback=progress_callback)
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
    
    # Test different output formats
    print("\nTesting different output formats...")
    
    for format_type in ["text", "srt", "vtt", "json"]:
        plugin.set_setting("transcription.output_format", format_type)
        
        print(f"\nRunning with '{format_type}' output format...")
        results = plugin.transcribe(audio_path, provider=provider, callback=progress_callback)
        
        if results.get('success', False):
            print(f"  {format_type.upper()} output generated:")
            formatted_text = results.get('formatted_output', '')
            print(f"  {formatted_text[:100]}..." if len(formatted_text) > 100 else f"  {formatted_text}")
        else:
            print(f"  Failed to generate {format_type.upper()} output: {results.get('error', 'Unknown error')}")
    
    return results

def create_test_audio(output_path='test_audio.wav', duration=5):
    """Create a test audio file if none is provided"""
    try:
        import numpy as np
        from scipy.io import wavfile
        print(f"Creating test audio file: {output_path}")
        
        # Sample rate (CD quality)
        sample_rate = 16000
        
        # Generate a simple sine wave
        t = np.linspace(0, duration, duration * sample_rate, endpoint=False)
        
        # Create a signal with speech-like characteristics
        # Mix multiple frequencies to simulate speech
        signal = 0.5 * np.sin(2 * np.pi * 110 * t)  # Base frequency (110 Hz)
        
        # Add harmonics to simulate voice
        for harmonic in [2, 3, 4, 5]:
            signal += (0.5 / harmonic) * np.sin(2 * np.pi * 110 * harmonic * t)
        
        # Add some amplitude modulation to simulate syllables
        syllable_rate = 3  # 3 syllables per second
        am = 0.5 + 0.5 * np.sin(2 * np.pi * syllable_rate * t)
        signal = signal * am
        
        # Add some noise
        noise = np.random.normal(0, 0.05, len(signal))
        signal = signal + noise
        
        # Normalize
        signal = signal / np.max(np.abs(signal))
        
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
    parser = argparse.ArgumentParser(description='Test the optimized Transcription Service plugin')
    parser.add_argument('--audio', help='Path to audio file for testing')
    parser.add_argument('--provider', choices=['whisper', 'google', 'azure', 'mock'], 
                        default='mock', help='Transcription provider to use')
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
    test_transcription_service_optimized(audio_path, args.provider, args.cache)

if __name__ == "__main__":
    main()