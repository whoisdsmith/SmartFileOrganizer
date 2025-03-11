"""
Test script for the integrated media processing system.

This script demonstrates the integrated functionality of all media plugins
working together through the MediaIntegration module.

Usage:
    python test_media_integration.py [--audio AUDIO_PATH] [--video VIDEO_PATH] [--transcribe]
"""

import os
import time
import argparse
import logging
from pprint import pprint
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_media_integration")

# Import required components
from ai_document_organizer_v2.core.settings import SettingsManager
from ai_document_organizer_v2.media_integration import MediaIntegration

def progress_callback(progress, total, message):
    """Simple progress callback function"""
    percent = progress / total * 100
    bar_length = 30
    filled_length = int(bar_length * progress // total)
    bar = '█' * filled_length + '-' * (bar_length - filled_length)
    print(f'\r[{bar}] {percent:.1f}% {progress}/{total} {message}', end='')
    if progress == total:
        print()

def test_media_integration(audio_path=None, video_path=None, transcribe=False):
    """Test the integrated media processing system"""
    print("\n=== Testing Integrated Media Processing System ===\n")
    
    # Create a settings manager
    settings = SettingsManager()
    
    # Create and initialize media integration
    media_integration = MediaIntegration(settings)
    if not media_integration.initialize():
        print("Failed to initialize media integration")
        return
    
    # Print available providers
    providers = media_integration.get_available_providers()
    print("Available providers:")
    for plugin_type, provider_list in providers.items():
        print(f"  {plugin_type}: {', '.join(provider_list)}")
    
    # Print supported extensions
    extensions = media_integration.get_supported_extensions()
    print("\nSupported extensions:")
    for media_type, ext_list in extensions.items():
        print(f"  {media_type}: {', '.join(ext_list)}")
    
    # Test with audio file if provided
    if audio_path and os.path.exists(audio_path):
        print(f"\nAnalyzing audio file: {audio_path}")
        
        # Set analysis options
        options = {
            'transcribe': transcribe,
            'analyze_content': True
        }
        
        # Analyze audio
        start_time = time.time()
        audio_result = media_integration.analyze_media(audio_path, options, progress_callback)
        processing_time = time.time() - start_time
        
        # Print results
        print(f"\nAudio analysis completed in {processing_time:.2f} seconds")
        
        if audio_result.get('success', False):
            # Print audio metadata
            metadata = audio_result.get('metadata', {})
            print("\nAudio Metadata:")
            print(f"  Duration: {metadata.get('duration_formatted', 'Unknown')}")
            print(f"  Format: {metadata.get('format', 'Unknown')}")
            print(f"  Sample Rate: {metadata.get('sample_rate', 'Unknown')} Hz")
            print(f"  Channels: {metadata.get('channels', 'Unknown')}")
            print(f"  Bitrate: {metadata.get('bitrate', 'Unknown')} bps")
            
            # Print advanced analysis if available
            if 'advanced_analysis' in metadata:
                print("\nAdvanced Audio Analysis:")
                print(f"  Tempo: {metadata.get('tempo', 'Unknown')} BPM")
                print(f"  Beat Count: {metadata.get('beat_count', 'Unknown')}")
                print(f"  Quality Rating: {metadata.get('quality_rating', 'Unknown')}/10")
                print(f"  Dominant Pitch: {metadata.get('dominant_pitch', 'Unknown')}")
            
            # Print transcription if requested and available
            if transcribe and 'transcription' in audio_result:
                transcription = audio_result['transcription']
                print("\nTranscription:")
                print(f"  Success: {transcription.get('success', False)}")
                print(f"  Language: {transcription.get('language', 'Unknown')}")
                
                text = transcription.get('text', '')
                if text:
                    print(f"  Text: {text[:200]}..." if len(text) > 200 else f"  Text: {text}")
                else:
                    print(f"  Transcription failed: {transcription.get('error', 'Unknown error')}")
            
            # Print waveform path if available
            if 'waveform_path' in metadata:
                print(f"\nWaveform image: {metadata['waveform_path']}")
        else:
            print(f"\nAudio analysis failed: {audio_result.get('error', 'Unknown error')}")
    
    # Test with video file if provided
    if video_path and os.path.exists(video_path):
        print(f"\nAnalyzing video file: {video_path}")
        
        # Set analysis options
        options = {
            'transcribe': transcribe,
            'analyze_content': True
        }
        
        # Analyze video
        start_time = time.time()
        video_result = media_integration.analyze_media(video_path, options, progress_callback)
        processing_time = time.time() - start_time
        
        # Print results
        print(f"\nVideo analysis completed in {processing_time:.2f} seconds")
        
        if video_result.get('success', False):
            # Print video metadata
            metadata = video_result.get('metadata', {})
            print("\nVideo Metadata:")
            print(f"  Duration: {metadata.get('duration_formatted', 'Unknown')}")
            print(f"  Resolution: {metadata.get('width', 'Unknown')}x{metadata.get('height', 'Unknown')}")
            print(f"  Frame Rate: {metadata.get('frame_rate', 'Unknown')} fps")
            print(f"  Video Codec: {metadata.get('codec', 'Unknown')}")
            print(f"  Has Audio: {metadata.get('has_audio', 'Unknown')}")
            print(f"  Quality Rating: {metadata.get('quality_rating', 'Unknown')}/10")
            
            # Print scene information if available
            if 'scenes' in metadata:
                scenes = metadata['scenes']
                print(f"\nScene Detection:")
                print(f"  Number of scenes: {len(scenes)}")
                
                if scenes:
                    print("  First 3 scenes:")
                    for i, scene in enumerate(scenes[:3]):
                        print(f"    Scene {i+1}: {scene.get('start_time'):.1f}s - {scene.get('end_time'):.1f}s " +
                             f"(duration: {scene.get('duration'):.1f}s)")
            
            # Print transcription if requested and available
            if transcribe and 'transcription' in video_result:
                transcription = video_result['transcription']
                print("\nTranscription:")
                print(f"  Success: {transcription.get('success', False)}")
                print(f"  Language: {transcription.get('language', 'Unknown')}")
                
                text = transcription.get('text', '')
                if text:
                    print(f"  Text: {text[:200]}..." if len(text) > 200 else f"  Text: {text}")
                else:
                    print(f"  Transcription failed: {transcription.get('error', 'Unknown error')}")
            
            # Print thumbnail path if available
            if 'preview_path' in video_result:
                print(f"\nThumbnail image: {video_result['preview_path']}")
        else:
            print(f"\nVideo analysis failed: {video_result.get('error', 'Unknown error')}")
    
    # Print cache statistics
    cache_stats = media_integration.get_cache_statistics()
    print("\nCache Statistics:")
    for plugin_name, stats in cache_stats.items():
        print(f"  {plugin_name}:")
        print(f"    Hit rate: {stats.get('hit_rate', 0):.1f}%")
        print(f"    Cache entries: {stats.get('cache_entries', 0)}")
        cache_size_mb = stats.get('cache_size_bytes', 0) / (1024 * 1024)
        print(f"    Cache size: {cache_size_mb:.2f} MB")

def create_test_audio(output_path='test_audio.wav', duration=5):
    """Create a test audio file if none is provided"""
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

def create_test_video(output_path='test_video.mp4', duration=5):
    """Create a simple test video file if no video file is provided"""
    try:
        # Check for required libraries
        import numpy as np
        import cv2
        from moviepy.editor import ImageSequenceClip
        
        print(f"Creating test video file: {output_path}")
        
        # Create a sequence of colored frames
        frames = []
        fps = 24
        frame_count = int(duration * fps)
        
        # Create frames with different colors and shapes
        height, width = 360, 640
        
        for i in range(frame_count):
            # Create a blank frame
            frame = np.zeros((height, width, 3), dtype=np.uint8)
            
            # Define animation phase (0 to 1)
            phase = i / frame_count
            
            if i < frame_count * 0.3:  # First scene - moving red circle
                # Draw red circle
                center_x = int(width * (0.2 + 0.6 * (i / (frame_count * 0.3))))
                center_y = int(height * 0.5)
                radius = int(min(width, height) * 0.1)
                cv2.circle(frame, (center_x, center_y), radius, (0, 0, 255), -1)
                
            elif i < frame_count * 0.6:  # Second scene - growing blue rectangle
                # Draw blue rectangle
                scale = (i - frame_count * 0.3) / (frame_count * 0.3)
                rect_width = int(width * 0.3 * scale)
                rect_height = int(height * 0.3 * scale)
                x1 = width // 2 - rect_width // 2
                y1 = height // 2 - rect_height // 2
                cv2.rectangle(frame, (x1, y1), (x1 + rect_width, y1 + rect_height), (255, 0, 0), -1)
                
            else:  # Third scene - green triangle
                # Draw green triangle
                scale = (i - frame_count * 0.6) / (frame_count * 0.4)
                size = int(min(width, height) * 0.3 * scale)
                
                # Define triangle vertices
                p1 = (width // 2, height // 2 - size)
                p2 = (width // 2 - size, height // 2 + size)
                p3 = (width // 2 + size, height // 2 + size)
                
                # Draw filled triangle
                triangle_points = np.array([p1, p2, p3], np.int32)
                triangle_points = triangle_points.reshape((-1, 1, 2))
                cv2.fillPoly(frame, [triangle_points], (0, 255, 0))
            
            # Add frame number text
            font = cv2.FONT_HERSHEY_SIMPLEX
            text = f"Frame: {i}/{frame_count-1}"
            cv2.putText(frame, text, (20, 30), font, 0.7, (255, 255, 255), 1, cv2.LINE_AA)
            
            # Add timestamp
            timestamp = f"Time: {i/fps:.2f}s"
            cv2.putText(frame, timestamp, (20, 60), font, 0.7, (255, 255, 255), 1, cv2.LINE_AA)
            
            # Convert BGR to RGB for moviepy
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frames.append(frame_rgb)
        
        # Create video from frames
        clip = ImageSequenceClip(frames, fps=fps)
        
        # Add simple audio (sine wave)
        from moviepy.audio.AudioClip import AudioClip
        import math
        
        def make_audio_frame(t):
            # Simple sine wave with varying frequency
            freq = 440 + 220 * math.sin(t * 2)  # Frequency between 220 and 660 Hz
            return 0.5 * math.sin(2 * math.pi * freq * t)
        
        audio = AudioClip(make_audio_frame, duration=duration)
        clip = clip.set_audio(audio)
        
        # Write video file
        clip.write_videofile(output_path, codec='libx264', audio_codec='aac', fps=fps, logger=None)
        
        print(f"Created test video file: {output_path}")
        return output_path
        
    except ImportError as e:
        print(f"Error importing dependencies for video creation: {e}")
        return None
    except Exception as e:
        print(f"Error creating test video: {e}")
        return None

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Test the integrated media processing system')
    parser.add_argument('--audio', help='Path to audio file for testing')
    parser.add_argument('--video', help='Path to video file for testing')
    parser.add_argument('--transcribe', action='store_true', help='Enable transcription')
    return parser.parse_args()

def main():
    """Main test function"""
    args = parse_args()
    
    # Get audio path from arguments or create test audio
    audio_path = args.audio
    if args.audio and not os.path.exists(args.audio):
        print(f"Audio file not found: {args.audio}")
        audio_path = None
    
    if not audio_path:
        print("No valid audio file provided, creating test audio")
        audio_path = create_test_audio()
        
    # Get video path from arguments or create test video
    video_path = args.video
    if args.video and not os.path.exists(args.video):
        print(f"Video file not found: {args.video}")
        video_path = None
    
    if not video_path:
        print("No valid video file provided, creating test video")
        video_path = create_test_video()
    
    # Test the integrated media processing
    test_media_integration(audio_path, video_path, args.transcribe)

if __name__ == "__main__":
    main()