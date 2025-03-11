"""
Test script for the AI Document Organizer V2 media processing plugins.

This script tests the new media plugins added in Phase 2:
- Audio Analyzer
- Video Analyzer
- Transcription Service

Usage:
    python test_media_plugins.py [--audio AUDIO_PATH] [--video VIDEO_PATH]
"""

import os
import sys
import logging
import argparse
import tempfile
from pprint import pprint

# Add the project root to the Python path
sys.path.append('.')

# Import the plugin manager and plugin classes
from ai_document_organizer_v2.core.plugin_manager import PluginManager
from ai_document_organizer_v2.core.settings import SettingsManager
from ai_document_organizer_v2.plugins.audio_analyzer import AudioAnalyzerPlugin
from ai_document_organizer_v2.plugins.video_analyzer import VideoAnalyzerPlugin
from ai_document_organizer_v2.plugins.transcription_service import TranscriptionServicePlugin

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("MediaPluginsTest")

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Test AI Document Organizer V2 media plugins")
    parser.add_argument("--audio", help="Path to an audio file for testing")
    parser.add_argument("--video", help="Path to a video file for testing")
    parser.add_argument("--transcribe", action="store_true", help="Test transcription service")
    return parser.parse_args()

def test_audio_analyzer(audio_path):
    """Test the Audio Analyzer plugin."""
    logger.info("Testing Audio Analyzer plugin")
    
    if not audio_path:
        logger.warning("No audio file provided. Creating a test file...")
        audio_path = create_test_audio()
    
    if not os.path.exists(audio_path):
        logger.error(f"Audio file not found: {audio_path}")
        return False
    
    # Create a settings manager
    settings_manager = SettingsManager()
    
    # Create the plugin directly
    plugin = AudioAnalyzerPlugin("audio_analyzer.test")
    plugin.settings_manager = settings_manager
    plugin.initialize()
    
    # Test the plugin
    logger.info(f"Analyzing audio file: {audio_path}")
    result = plugin.analyze_media(audio_path)
    
    if result['success']:
        logger.info("Audio analysis successful!")
        logger.info("Metadata:")
        pprint(result['metadata'])
        
        if result['preview_path']:
            logger.info(f"Waveform generated: {result['preview_path']}")
        
        # Test advanced audio analysis features (if available)
        logger.info("Testing advanced audio analysis features...")
        test_advanced_audio_analysis(plugin, audio_path)
        
        return True
    else:
        logger.error(f"Audio analysis failed: {result['error']}")
        return False
        
def test_advanced_audio_analysis(plugin, audio_path):
    """Test the advanced audio analysis features."""
    try:
        # Check if librosa is available
        librosa_available = False
        try:
            # noinspection PyUnresolvedReferences
            import librosa
            librosa_available = True
        except ImportError:
            logger.warning("Librosa not available. Skipping advanced audio analysis tests.")
            return
            
        if not librosa_available:
            return
            
        logger.info("Running advanced audio analysis...")
        advanced_features = plugin.analyze_audio_features(audio_path)
        
        if advanced_features.get('success', False):
            logger.info("Advanced audio analysis successful!")
            
            # Display the most interesting features
            logger.info(f"Tempo (BPM): {advanced_features.get('tempo')}")
            logger.info(f"Beat count: {advanced_features.get('beat_count')}")
            logger.info(f"Beat regularity: {advanced_features.get('beat_regularity')}")
            logger.info(f"Dominant pitch: {advanced_features.get('dominant_pitch')}")
            logger.info(f"Tonal strength: {advanced_features.get('tonal_strength')}")
            logger.info(f"Spectral centroid: {advanced_features.get('spectral_centroid')}")
            logger.info(f"RMS energy: {advanced_features.get('rms_energy')}")
            
            # Check if at least some features were successfully analyzed
            success = any([
                advanced_features.get('tempo') is not None,
                advanced_features.get('beat_count') is not None,
                advanced_features.get('spectral_centroid') is not None
            ])
            
            if success:
                logger.info("Advanced audio analysis features detected!")
                return True
            else:
                logger.warning("Advanced audio analysis returned success but no features were found.")
                return False
        else:
            logger.warning(f"Advanced audio analysis failed: {advanced_features.get('error')}")
            return False
    except Exception as e:
        logger.error(f"Error testing advanced audio analysis: {e}")
        return False

def test_video_analyzer(video_path):
    """Test the Video Analyzer plugin."""
    logger.info("Testing Video Analyzer plugin")
    
    if not video_path:
        logger.warning("No video file provided. Creating a test file...")
        video_path = create_test_video()
    
    if not os.path.exists(video_path):
        logger.error(f"Video file not found: {video_path}")
        return False
    
    # Create a settings manager
    settings_manager = SettingsManager()
    
    # Create the plugin directly
    plugin = VideoAnalyzerPlugin("video_analyzer.test")
    plugin.settings_manager = settings_manager
    plugin.initialize()
    
    # Test the plugin
    logger.info(f"Analyzing video file: {video_path}")
    result = plugin.analyze_media(video_path)
    
    if result['success']:
        logger.info("Video analysis successful!")
        logger.info("Metadata:")
        pprint(result['metadata'])
        
        if result['preview_path']:
            logger.info(f"Thumbnail generated: {result['preview_path']}")
        
        return True
    else:
        logger.error(f"Video analysis failed: {result['error']}")
        return False

def test_transcription_service(media_path):
    """Test the Transcription Service plugin."""
    logger.info("Testing Transcription Service plugin")
    
    if not media_path:
        logger.warning("No media file provided. Creating a test file...")
        media_path = create_test_audio()
    
    if not os.path.exists(media_path):
        logger.error(f"Media file not found: {media_path}")
        return False
    
    # Create a settings manager
    settings_manager = SettingsManager()
    
    # Create the plugin directly
    plugin = TranscriptionServicePlugin("transcription_service.test")
    plugin.settings_manager = settings_manager
    plugin.initialize()
    
    # Test the plugin
    logger.info(f"Transcribing media file: {media_path}")
    result = plugin.transcribe(media_path)
    
    if result['success']:
        logger.info("Transcription successful!")
        logger.info(f"Transcribed text: {result['text']}")
        logger.info(f"Confidence: {result['confidence']}")
        logger.info(f"Provider: {result.get('provider', 'unknown')}")
        
        if result.get('segments'):
            logger.info(f"Number of segments: {len(result['segments'])}")
        
        return True
    else:
        logger.error(f"Transcription failed: {result['error']}")
        return False

def test_with_plugin_manager():
    """Test the plugins using the plugin manager."""
    logger.info("Testing plugins with the plugin manager")
    
    # Create a settings manager
    settings_manager = SettingsManager()
    
    # Create a plugin manager
    plugin_manager = PluginManager(settings_manager)
    
    # Discover plugins
    logger.info("Discovering plugins...")
    discovery_result = plugin_manager.discover_plugins()
    
    logger.info(f"Found {discovery_result['found']} plugins")
    logger.info(f"Loaded {discovery_result['loaded']} plugins")
    
    if discovery_result['failed'] > 0:
        logger.warning(f"Failed to load {discovery_result['failed']} plugins")
        for failure in discovery_result['failures']:
            logger.warning(f"  {failure['path']}: {failure['error']}")
    
    # Initialize plugins
    logger.info("Initializing plugins...")
    init_result = plugin_manager.initialize_plugins()
    
    logger.info(f"Initialized {init_result['successful']} plugins")
    
    if init_result['failed'] > 0:
        logger.warning(f"Failed to initialize {init_result['failed']} plugins")
        for failure in init_result['failures']:
            logger.warning(f"  {failure['plugin_name']} ({failure['plugin_id']}): {failure['error']}")
    
    # Get plugin types
    plugin_types = plugin_manager.get_plugin_types()
    logger.info(f"Plugin types: {plugin_types}")
    
    # Check for media analyzer plugins
    media_analyzers = plugin_manager.get_plugins_of_type("media_analyzer")
    logger.info(f"Found {len(media_analyzers)} media analyzer plugins")
    for plugin_id, plugin in media_analyzers.items():
        logger.info(f"  {plugin.name} ({plugin_id}) - Supports: {plugin.supported_extensions}")
    
    # Check for transcription plugins
    transcription_plugins = plugin_manager.get_plugins_of_type("transcription")
    logger.info(f"Found {len(transcription_plugins)} transcription plugins")
    for plugin_id, plugin in transcription_plugins.items():
        logger.info(f"  {plugin.name} ({plugin_id})")
    
    # Shutdown plugins
    logger.info("Shutting down plugins...")
    shutdown_result = plugin_manager.shutdown_plugins()
    
    logger.info(f"Shut down {shutdown_result['successful']} plugins")
    
    if shutdown_result['failed'] > 0:
        logger.warning(f"Failed to shut down {shutdown_result['failed']} plugins")

def create_test_audio():
    """Create a test audio file if none is provided."""
    try:
        # Check if we can use scipy and numpy
        try:
            import numpy as np
            from scipy.io import wavfile
            
            # Create a simple sine wave
            sample_rate = 44100
            duration = 3  # seconds
            t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
            
            # Create a 440 Hz sine wave (A4 note)
            frequency = 440
            audio_data = np.sin(2 * np.pi * frequency * t) * 0.5
            
            # Add a different tone
            frequency2 = 880
            audio_data += np.sin(2 * np.pi * frequency2 * t) * 0.25
            
            # Normalize
            audio_data = audio_data / np.max(np.abs(audio_data))
            
            # Convert to 16-bit PCM
            audio_data = (audio_data * 32767).astype(np.int16)
            
            # Create a temporary file
            output_dir = os.path.join(tempfile.gettempdir(), "test_media")
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, "test_audio.wav")
            
            # Write the WAV file
            wavfile.write(output_path, sample_rate, audio_data)
            
            logger.info(f"Created test audio file: {output_path}")
            return output_path
            
        except ImportError:
            logger.warning("scipy or numpy not available, using simple test file method")
            
            # Create a basic WAV file with minimal header
            output_dir = os.path.join(tempfile.gettempdir(), "test_media")
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, "test_audio.wav")
            
            # Create a basic WAV file with header only (will be silent but valid format)
            with open(output_path, 'wb') as f:
                # RIFF header
                f.write(b'RIFF')
                f.write((36).to_bytes(4, byteorder='little'))  # File size - 8
                f.write(b'WAVE')
                
                # Format chunk
                f.write(b'fmt ')
                f.write((16).to_bytes(4, byteorder='little'))  # Chunk size
                f.write((1).to_bytes(2, byteorder='little'))   # PCM format
                f.write((1).to_bytes(2, byteorder='little'))   # Mono
                f.write((44100).to_bytes(4, byteorder='little'))  # Sample rate
                f.write((44100 * 2).to_bytes(4, byteorder='little'))  # Byte rate
                f.write((2).to_bytes(2, byteorder='little'))   # Block align
                f.write((16).to_bytes(2, byteorder='little'))  # Bits per sample
                
                # Data chunk
                f.write(b'data')
                f.write((0).to_bytes(4, byteorder='little'))   # Empty data
            
            logger.info(f"Created basic test audio file: {output_path}")
            return output_path
    
    except Exception as e:
        logger.error(f"Error creating test audio: {e}")
        return None

def create_test_video():
    """Create a test video file if none is provided."""
    logger.error("Test video creation not implemented")
    logger.info("Please provide a video file with --video option")
    return None

def main():
    """Main function."""
    args = parse_args()
    
    # Test with plugin manager
    test_with_plugin_manager()
    
    # Test individual plugins
    if args.audio or not args.video:
        test_audio_analyzer(args.audio)
    
    if args.video:
        test_video_analyzer(args.video)
    
    if args.transcribe:
        # Use audio file for transcription if available, otherwise use video
        media_path = args.audio if args.audio else args.video
        test_transcription_service(media_path)

if __name__ == "__main__":
    main()