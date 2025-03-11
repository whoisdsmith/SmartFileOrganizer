"""
Test script for the optimized Video Analyzer Plugin.

This script tests the performance-optimized plugin with caching
and adaptive processing features. It also benchmarks processing time
and cache hit rate.

Usage:
    python test_video_analyzer_optimized.py [--video VIDEO_PATH]
"""

import os
import time
import argparse
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_video_analyzer_optimized")

# Import required components
from ai_document_organizer_v2.core.settings import SettingsManager
from ai_document_organizer_v2.plugins.video_analyzer.plugin_optimized import VideoAnalyzerPlugin

def progress_callback(progress, total, message):
    """Simple progress callback function"""
    percent = progress / total * 100
    bar_length = 30
    filled_length = int(bar_length * progress // total)
    bar = '█' * filled_length + '-' * (bar_length - filled_length)
    print(f'\r[{bar}] {percent:.1f}% {progress}/{total} {message}', end='')
    if progress == total:
        print()

def test_video_analyzer_optimized(video_path, cache_enabled=True):
    """Test the optimized Video Analyzer plugin with caching support"""
    print("\n=== Testing Optimized Video Analyzer Plugin ===\n")
    
    # Create a settings manager
    settings = SettingsManager()
    
    # Create plugin instance
    plugin = VideoAnalyzerPlugin("video-analyzer-1", "Video Analyzer", "1.1.0", 
                                "Optimized Video Analyzer Plugin")
    
    # Set settings manager
    plugin.settings_manager = settings
    
    # Initialize the plugin
    if not plugin.initialize():
        print("Failed to initialize plugin")
        return
    
    # Configure the plugin
    plugin.set_setting("video_analyzer.cache_enabled", cache_enabled)
    plugin.set_setting("video_analyzer.processing_mode", "full")
    plugin.set_setting("video_analyzer.adaptive_processing", True)
    plugin.set_setting("video_analyzer.thumbnail_count", 3)
    plugin.set_setting("video_analyzer.scene_detection_enabled", True)
    plugin.set_setting("video_analyzer.time_limit_enabled", True)
    plugin.set_setting("video_analyzer.max_duration", 60)  # 1 minute max for testing
    
    # Check if the file exists
    if not os.path.exists(video_path):
        print(f"File not found: {video_path}")
        return
    
    print(f"Analyzing video file: {video_path}")
    
    # First run (should be slower)
    start_time = time.time()
    print("First analysis run (cache miss expected)...")
    results = plugin.analyze_media(video_path, progress_callback)
    first_run_time = time.time() - start_time
    
    # Print basic results from first run
    print(f"\nFirst run completed in {first_run_time:.2f} seconds")
    print(f"Metadata extracted: {len(results.get('metadata', {}))}")
    print(f"Thumbnail generated: {results.get('preview_path') is not None}")
    
    # Check for scene detection results
    metadata = results.get('metadata', {})
    if 'scenes' in metadata:
        scenes = metadata['scenes']
        print(f"\nScene detection results:")
        print(f"  Detected scenes: {len(scenes)}")
        if scenes:
            print("\nFirst 3 scenes:")
            for i, scene in enumerate(scenes[:3]):
                print(f"  Scene {i+1}: {scene.get('start_time'):.1f}s - {scene.get('end_time'):.1f}s " +
                     f"(duration: {scene.get('duration'):.1f}s)")
    
    # Second run (should be faster if cache is enabled)
    if cache_enabled:
        print("\nSecond analysis run (cache hit expected)...")
        start_time = time.time()
        results2 = plugin.analyze_media(video_path, progress_callback)
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
        plugin.set_setting("video_analyzer.processing_mode", mode)
        plugin.set_setting("video_analyzer.adaptive_processing", False)  # Disable adaptive override
        
        # Clear cache for this test
        plugin.cache.clear()
        
        print(f"\nRunning with '{mode}' processing mode...")
        start_time = time.time()
        results = plugin.analyze_media(video_path, progress_callback)
        run_time = time.time() - start_time
        
        # Print results
        print(f"\nCompleted in {run_time:.2f} seconds")
        metadata = results.get('metadata', {})
        has_scenes = 'scenes' in metadata
        print(f"Scene detection: {'Yes' if has_scenes else 'No'}")
        
        # Check for specific features based on mode
        feature_count = len(metadata)
        print(f"Number of metadata fields: {feature_count}")
    
    return results

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
    parser = argparse.ArgumentParser(description='Test the optimized Video Analyzer plugin')
    parser.add_argument('--video', help='Path to video file for testing')
    parser.add_argument('--no-cache', dest='cache', action='store_false',
                       help='Disable caching for testing')
    parser.set_defaults(cache=True)
    return parser.parse_args()

def main():
    """Main test function"""
    args = parse_args()
    
    # Get video path from arguments or create test video
    video_path = args.video
    if not video_path or not os.path.exists(video_path):
        print("No valid video file provided, creating test video")
        video_path = create_test_video()
        if not video_path:
            print("Failed to create test video, please provide a video file")
            return
    
    # Test the optimized plugin
    test_video_analyzer_optimized(video_path, args.cache)

if __name__ == "__main__":
    main()