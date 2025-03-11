"""
Lightweight version of the Audio Analyzer for testing purposes
Uses minimal processing to avoid timeouts while maintaining the same interface
"""

import os
import logging
import tempfile
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("LiteAudioAnalyzer")

class LiteAudioAnalyzer:
    """A lightweight version of the audio analyzer for testing"""
    
    # File extensions supported by this analyzer
    supported_extensions = [".mp3", ".wav", ".flac", ".ogg", ".aac", ".m4a"]
    
    def __init__(self):
        """Initialize the lite audio analyzer"""
        self.name = "Lite Audio Analyzer"
        self.version = "1.0.0"
        
    def analyze_audio(self, audio_path):
        """
        Analyze an audio file with minimal processing to avoid timeouts
        
        Args:
            audio_path: Path to the audio file
            
        Returns:
            Dictionary with simplified analysis results
        """
        logger.info(f"Analyzing audio file: {audio_path}")
        
        if not os.path.exists(audio_path):
            logger.error(f"Audio file not found: {audio_path}")
            return {
                'success': False,
                'error': f"File not found: {audio_path}"
            }
        
        try:
            # Get basic file information
            file_stat = os.stat(audio_path)
            file_size = file_stat.st_size
            created_time = datetime.fromtimestamp(file_stat.st_ctime).isoformat()
            modified_time = datetime.fromtimestamp(file_stat.st_mtime).isoformat()
            _, file_ext = os.path.splitext(audio_path)
            file_ext = file_ext.lower()
            
            # Mock audio analysis results instead of using librosa
            # This avoids the heavyweight processing while maintaining the interface
            mock_results = {
                'success': True,
                'file_path': audio_path,
                'file_size': file_size,
                'file_type': file_ext[1:],  # Remove the dot
                'created_time': created_time,
                'modified_time': modified_time,
                
                # Mocked audio feature data
                'sample_rate': 44100,  # Standard sample rate
                'duration': 120.5,  # Mock duration
                'tempo': 120.0,  # Mock tempo (BPM)
                'beat_count': 240,  # Mock beat count
                'beat_regularity': 0.85,  # Mock beat regularity
                'dominant_pitch': 'A',  # Mock dominant pitch
                'spectral_centroid': 2500.0,  # Mock spectral centroid
                'spectral_bandwidth': 1500.0,  # Mock spectral bandwidth
                
                # Mock waveform generation
                'waveform_path': self._generate_mock_waveform(audio_path)
            }
            
            logger.info("Audio analysis completed successfully")
            return mock_results
            
        except Exception as e:
            logger.error(f"Error analyzing audio: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _generate_mock_waveform(self, audio_path):
        """
        Generate a mock waveform visualization
        
        Args:
            audio_path: Path to the audio file
            
        Returns:
            Path to the mock waveform image
        """
        try:
            # Use a simple text file as a placeholder
            output_path = os.path.splitext(audio_path)[0] + "_waveform.txt"
            
            with open(output_path, 'w') as f:
                f.write(f"Mock waveform visualization for {audio_path}\n")
                f.write("This is a placeholder for the actual waveform visualization.\n")
                f.write("In the full implementation, this would be a PNG image.\n")
            
            logger.info(f"Generated mock waveform at: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error generating mock waveform: {e}")
            return None

def analyze_file(audio_path):
    """
    Standalone function to analyze an audio file
    
    Args:
        audio_path: Path to the audio file
        
    Returns:
        Analysis results
    """
    analyzer = LiteAudioAnalyzer()
    return analyzer.analyze_audio(audio_path)