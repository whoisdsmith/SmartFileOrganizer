"""
Audio Analyzer Plugin for AI Document Organizer V2.

This plugin provides audio file analysis, metadata extraction, and waveform visualization.
"""

import os
import io
import logging
import tempfile
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple

# Import plugin base class
from ai_document_organizer_v2.core.plugin_base import MediaAnalyzerPlugin

# Import utilities
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import numpy as np

# Try importing required libraries
try:
    import mutagen
    from mutagen.mp3 import MP3
    from mutagen.flac import FLAC
    from mutagen.oggvorbis import OggVorbis
    from mutagen.wave import WAVE
    from mutagen.aac import AAC
    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False

try:
    import ffmpeg
    FFMPEG_AVAILABLE = True
except ImportError:
    FFMPEG_AVAILABLE = False

logger = logging.getLogger("AIDocumentOrganizerV2.AudioAnalyzer")

class AudioAnalyzerPlugin(MediaAnalyzerPlugin):
    """
    Plugin for analyzing audio files.
    
    This plugin extracts metadata and generates waveform visualizations from audio files.
    """
    
    # Plugin metadata
    name = "Audio Analyzer"
    version = "1.0.0"
    description = "Analyzes audio files, extracts metadata, and generates waveform visualizations"
    author = "AI Document Organizer Team"
    dependencies = ["mutagen", "matplotlib", "ffmpeg-python"]
    
    # File extensions supported by this plugin
    supported_extensions = [".mp3", ".wav", ".flac", ".ogg", ".aac", ".m4a"]
    
    def __init__(self, plugin_id: str, name: Optional[str] = None, version: Optional[str] = None,
                 description: Optional[str] = None):
        """
        Initialize the audio analyzer plugin.
        
        Args:
            plugin_id: Unique identifier for the plugin
            name: Plugin name (if None, uses class attribute)
            version: Plugin version (if None, uses class attribute)
            description: Plugin description (if None, uses class attribute)
        """
        super().__init__(plugin_id, name, version, description)
        
        # Check if required libraries are available
        self.mutagen_available = MUTAGEN_AVAILABLE
        self.ffmpeg_available = FFMPEG_AVAILABLE
        
        if not self.mutagen_available:
            logger.warning("Mutagen library not available. Audio metadata extraction will be limited.")
        
        if not self.ffmpeg_available:
            logger.warning("FFmpeg library not available. Audio waveform generation will be limited.")
    
    def initialize(self) -> bool:
        """
        Initialize the plugin.
        
        Returns:
            True if initialization was successful, False otherwise
        """
        # Check dependencies
        if not self.mutagen_available:
            logger.warning("Mutagen library not available. Install mutagen for full audio analysis.")
            # Return True anyway to allow partial functionality
        
        if not self.ffmpeg_available:
            logger.warning("FFmpeg library not available. Install ffmpeg-python for waveform generation.")
            # Return True anyway to allow partial functionality
        
        # Register default settings if not already present
        if self.settings_manager is not None:
            # Use get_setting/set_setting to access settings manager
            waveform_enabled = self.get_setting("audio_analyzer.waveform_enabled", None)
            if waveform_enabled is None:
                self.set_setting("audio_analyzer.waveform_enabled", True)
                
            waveform_height = self.get_setting("audio_analyzer.waveform_height", None)
            if waveform_height is None:
                self.set_setting("audio_analyzer.waveform_height", 240)
                
            waveform_width = self.get_setting("audio_analyzer.waveform_width", None)
            if waveform_width is None:
                self.set_setting("audio_analyzer.waveform_width", 800)
                
            waveform_color = self.get_setting("audio_analyzer.waveform_color", None)
            if waveform_color is None:
                self.set_setting("audio_analyzer.waveform_color", "#1E90FF")  # Dodger blue
                
            waveform_bg_color = self.get_setting("audio_analyzer.waveform_bg_color", None)
            if waveform_bg_color is None:
                self.set_setting("audio_analyzer.waveform_bg_color", "#F5F5F5")  # White smoke
                
            waveform_dpi = self.get_setting("audio_analyzer.waveform_dpi", None)
            if waveform_dpi is None:
                self.set_setting("audio_analyzer.waveform_dpi", 100)
                
            logger.info("Audio analyzer settings initialized")
            
        return True
    
    def analyze_media(self, file_path: str) -> Dict[str, Any]:
        """
        Analyze an audio file and extract metadata and generate waveform.
        
        Args:
            file_path: Path to the audio file
            
        Returns:
            Dictionary containing analysis results
        """
        if not os.path.exists(file_path):
            return {
                'metadata': {},
                'preview_path': None,
                'transcription': None,
                'success': False,
                'error': f"File not found: {file_path}"
            }
        
        # Extract file extension
        _, file_ext = os.path.splitext(file_path)
        file_ext = file_ext.lower()
        
        if file_ext not in [ext.lower() for ext in self.supported_extensions]:
            return {
                'metadata': {},
                'preview_path': None,
                'transcription': None,
                'success': False,
                'error': f"Unsupported file extension: {file_ext}"
            }
        
        try:
            # Extract metadata and analyze audio
            metadata = self._extract_audio_metadata(file_path)
            
            # Generate waveform if enabled
            preview_path = None
            waveform_enabled = self.get_setting("audio_analyzer.waveform_enabled", True)
            
            if waveform_enabled:
                preview_path = self._generate_waveform(file_path)
                if preview_path:
                    metadata['waveform_path'] = preview_path
            
            # Return analysis results
            return {
                'metadata': metadata,
                'preview_path': preview_path,
                'transcription': None,  # Handled by transcription plugin
                'success': True,
                'error': ""
            }
        except Exception as e:
            logger.error(f"Error analyzing audio file {file_path}: {e}")
            return {
                'metadata': {},
                'preview_path': None,
                'transcription': None,
                'success': False,
                'error': str(e)
            }
    
    def generate_preview(self, file_path: str, output_path: Optional[str] = None) -> Optional[str]:
        """
        Generate a waveform visualization for the audio file.
        
        Args:
            file_path: Path to the audio file
            output_path: Optional path to save the waveform image
            
        Returns:
            Path to the generated waveform image or None if generation failed
        """
        return self._generate_waveform(file_path, output_path)
    
    def _extract_audio_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        Extract metadata from an audio file.
        
        Args:
            file_path: Path to the audio file
            
        Returns:
            Dictionary with audio metadata
        """
        # Get basic file information
        file_stat = os.stat(file_path)
        _, file_ext = os.path.splitext(file_path)
        file_ext = file_ext.lower()
        
        metadata = {
            'filename': os.path.basename(file_path),
            'filepath': file_path,
            'file_size': file_stat.st_size,
            'created_time': datetime.fromtimestamp(file_stat.st_ctime).isoformat(),
            'modified_time': datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
            'file_type': file_ext[1:],  # Remove the dot
            'sample_rate': None,
            'channels': None,
            'bit_rate': None,
            'bit_depth': None,
            'duration': None,
            'format': None
        }
        
        # Extract detailed metadata if mutagen is available
        if self.mutagen_available:
            try:
                # Use appropriate Mutagen class based on file extension
                audio = None
                if file_ext == '.mp3':
                    audio = MP3(file_path)
                elif file_ext == '.flac':
                    audio = FLAC(file_path)
                elif file_ext == '.ogg':
                    audio = OggVorbis(file_path)
                elif file_ext == '.wav':
                    audio = WAVE(file_path)
                elif file_ext == '.aac':
                    audio = AAC(file_path)
                else:
                    # Try with generic mutagen
                    audio = mutagen.File(file_path)
                
                if audio:
                    # Extract common metadata
                    if hasattr(audio, 'info'):
                        info = audio.info
                        if hasattr(info, 'sample_rate'):
                            metadata['sample_rate'] = info.sample_rate
                        if hasattr(info, 'channels'):
                            metadata['channels'] = info.channels
                        if hasattr(info, 'bitrate'):
                            metadata['bit_rate'] = info.bitrate
                        if hasattr(info, 'bits_per_sample'):
                            metadata['bit_depth'] = info.bits_per_sample
                        if hasattr(info, 'length'):
                            metadata['duration'] = info.length
                            metadata['duration_formatted'] = str(timedelta(seconds=int(info.length)))
                    
                    # Extract tag data
                    metadata['tags'] = {}
                    for key, value in audio.items():
                        # Handle different tag formats
                        if isinstance(value, list) and len(value) == 1:
                            metadata['tags'][key] = value[0]
                        else:
                            metadata['tags'][key] = value
                    
                    # Extract common tags into top-level metadata
                    tag_mapping = {
                        'title': ['title', 'TITLE', 'TIT2'],
                        'artist': ['artist', 'ARTIST', 'TPE1'],
                        'album': ['album', 'ALBUM', 'TALB'],
                        'year': ['date', 'year', 'TDRC', 'TYER'],
                        'track_number': ['tracknumber', 'TRCK'],
                        'genre': ['genre', 'GENRE', 'TCON'],
                        'composer': ['composer', 'COMPOSER', 'TCOM'],
                    }
                    
                    for meta_key, tag_keys in tag_mapping.items():
                        for tag_key in tag_keys:
                            if tag_key in audio:
                                value = audio[tag_key]
                                if isinstance(value, list) and len(value) == 1:
                                    metadata[meta_key] = str(value[0])
                                else:
                                    metadata[meta_key] = str(value)
                                break
            except Exception as e:
                logger.error(f"Error extracting audio metadata with mutagen: {e}")
                metadata['mutagen_error'] = str(e)
        
        # Try extracting metadata with ffmpeg if available and mutagen failed
        if self.ffmpeg_available and not metadata.get('duration'):
            try:
                probe = ffmpeg.probe(file_path)
                
                # Get audio stream info
                audio_stream = next((stream for stream in probe['streams'] 
                                    if stream['codec_type'] == 'audio'), None)
                
                if audio_stream:
                    metadata['format'] = probe['format']['format_name']
                    
                    if 'duration' in probe['format']:
                        duration = float(probe['format']['duration'])
                        metadata['duration'] = duration
                        metadata['duration_formatted'] = str(timedelta(seconds=int(duration)))
                    
                    if 'bit_rate' in probe['format']:
                        metadata['bit_rate'] = int(probe['format']['bit_rate'])
                    
                    metadata['codec'] = audio_stream.get('codec_name')
                    metadata['codec_long'] = audio_stream.get('codec_long_name')
                    
                    if 'sample_rate' in audio_stream:
                        metadata['sample_rate'] = int(audio_stream['sample_rate'])
                    
                    if 'channels' in audio_stream:
                        metadata['channels'] = int(audio_stream['channels'])
                    
                    # Extract tags from format section
                    if 'tags' in probe['format']:
                        ffmpeg_tags = probe['format']['tags']
                        if not 'tags' in metadata:
                            metadata['tags'] = {}
                        
                        # Add to existing tags
                        for key, value in ffmpeg_tags.items():
                            metadata['tags'][key] = value
                        
                        # Extract common tags
                        tag_mapping = {
                            'title': ['title', 'TITLE'],
                            'artist': ['artist', 'ARTIST'],
                            'album': ['album', 'ALBUM'],
                            'year': ['date', 'year', 'YEAR'],
                            'track_number': ['track', 'TRACK'],
                            'genre': ['genre', 'GENRE'],
                            'composer': ['composer', 'COMPOSER'],
                        }
                        
                        for meta_key, tag_keys in tag_mapping.items():
                            if meta_key not in metadata:  # Only set if not already set by mutagen
                                for tag_key in tag_keys:
                                    if tag_key in ffmpeg_tags:
                                        metadata[meta_key] = ffmpeg_tags[tag_key]
                                        break
            except Exception as e:
                logger.error(f"Error extracting audio metadata with ffmpeg: {e}")
                metadata['ffmpeg_error'] = str(e)
        
        # Calculate quality rating based on metadata
        quality_rating = self._calculate_quality_rating(metadata)
        metadata['quality_rating'] = quality_rating
        
        return metadata
    
    def _calculate_quality_rating(self, metadata: Dict[str, Any]) -> float:
        """
        Calculate audio quality rating based on metadata.
        
        Args:
            metadata: Dictionary with audio metadata
            
        Returns:
            Quality rating between 0 and 10
        """
        # Default medium rating
        rating = 5.0
        
        # Adjust rating based on available metadata
        if metadata.get('bit_rate'):
            bit_rate = metadata['bit_rate']
            if isinstance(bit_rate, str):
                try:
                    bit_rate = int(bit_rate)
                except ValueError:
                    bit_rate = 0
            
            # Adjust rating based on bit rate
            if bit_rate > 320000:  # > 320 kbps
                rating += 2.5
            elif bit_rate > 256000:  # > 256 kbps
                rating += 2.0
            elif bit_rate > 192000:  # > 192 kbps
                rating += 1.5
            elif bit_rate > 128000:  # > 128 kbps
                rating += 0.5
            elif bit_rate < 96000:  # < 96 kbps
                rating -= 1.0
            elif bit_rate < 64000:  # < 64 kbps
                rating -= 2.0
        
        # Adjust rating based on sample rate
        if metadata.get('sample_rate'):
            sample_rate = metadata['sample_rate']
            if isinstance(sample_rate, str):
                try:
                    sample_rate = int(sample_rate)
                except ValueError:
                    sample_rate = 0
            
            if sample_rate >= 96000:  # 96 kHz
                rating += 1.5
            elif sample_rate >= 48000:  # 48 kHz
                rating += 1.0
            elif sample_rate >= 44100:  # 44.1 kHz
                rating += 0.5
            elif sample_rate < 44100:  # < 44.1 kHz
                rating -= 0.5
            elif sample_rate < 32000:  # < 32 kHz
                rating -= 1.0
        
        # Adjust rating based on bit depth
        if metadata.get('bit_depth'):
            bit_depth = metadata['bit_depth']
            if isinstance(bit_depth, str):
                try:
                    bit_depth = int(bit_depth)
                except ValueError:
                    bit_depth = 0
            
            if bit_depth >= 24:  # 24-bit
                rating += 1.0
            elif bit_depth >= 16:  # 16-bit
                rating += 0.5
            elif bit_depth < 16:  # < 16-bit
                rating -= 0.5
        
        # Adjust rating based on format
        file_type = metadata.get('file_type', '').lower()
        if file_type == 'flac':
            rating += 1.0
        elif file_type == 'wav':
            rating += 0.5
        elif file_type == 'mp3':
            # Rating already adjusted by bit rate
            pass
        
        # Cap the rating between 0 and 10
        rating = max(0.0, min(10.0, rating))
        
        return round(rating, 1)
    
    def _generate_waveform(self, file_path: str, output_path: Optional[str] = None) -> Optional[str]:
        """
        Generate a waveform visualization for the audio file.
        
        Args:
            file_path: Path to the audio file
            output_path: Optional path to save the waveform image
            
        Returns:
            Path to the generated waveform image or None if generation failed
        """
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return None
        
        try:
            # Get waveform settings
            width = self.get_setting("audio_analyzer.waveform_width", 800)
            height = self.get_setting("audio_analyzer.waveform_height", 240)
            color = self.get_setting("audio_analyzer.waveform_color", "#1E90FF")
            bg_color = self.get_setting("audio_analyzer.waveform_bg_color", "#F5F5F5")
            dpi = self.get_setting("audio_analyzer.waveform_dpi", 100)
            
            # Create output path if not provided
            if output_path is None:
                base_name = os.path.splitext(os.path.basename(file_path))[0]
                output_dir = os.path.join(tempfile.gettempdir(), "audio_analyzer_waveforms")
                os.makedirs(output_dir, exist_ok=True)
                output_path = os.path.join(output_dir, f"{base_name}_waveform.png")
            
            if not self.ffmpeg_available:
                logger.warning(f"Cannot generate waveform: ffmpeg-python not available")
                return None
            
            # Use ffmpeg to extract the audio data
            try:
                out, err = (
                    ffmpeg
                    .input(file_path)
                    .output('pipe:', format='f32le', acodec='pcm_f32le', ac=1, ar=8000)
                    .run(capture_stdout=True, capture_stderr=True)
                )
            except ffmpeg.Error as e:
                logger.error(f"FFmpeg error: {e.stderr.decode()}")
                return None
            
            # Convert to numpy array of 32-bit float values
            audio_array = np.frombuffer(out, np.float32)
            
            # Create the waveform visualization
            fig, ax = plt.subplots(figsize=(width/dpi, height/dpi), dpi=dpi)
            
            # Calculate number of samples to show (downsample for performance)
            max_samples = 10000  # Max number of samples to plot
            if len(audio_array) > max_samples:
                step = len(audio_array) // max_samples
                audio_array = audio_array[::step]
            
            # Plot the waveform
            ax.plot(audio_array, color=color, linewidth=0.5)
            ax.set_xlim(0, len(audio_array))
            ax.set_ylim(-1, 1)
            
            # Remove axes and set background color
            ax.set_axis_off()
            fig.patch.set_facecolor(bg_color)
            ax.set_facecolor(bg_color)
            
            # Tight layout
            plt.tight_layout(pad=0)
            
            # Save the figure
            plt.savefig(output_path, dpi=dpi, bbox_inches='tight', pad_inches=0)
            plt.close(fig)
            
            if os.path.exists(output_path):
                logger.info(f"Generated waveform visualization: {output_path}")
                return output_path
            else:
                logger.error(f"Failed to save waveform visualization: {output_path}")
                return None
            
        except Exception as e:
            logger.error(f"Error generating waveform visualization: {e}")
            return None
    
    def get_config_schema(self) -> Dict[str, Any]:
        """
        Get JSON schema for plugin configuration.
        
        Returns:
            Dictionary with JSON schema for plugin configuration
        """
        return {
            "type": "object",
            "properties": {
                "waveform_enabled": {
                    "type": "boolean",
                    "title": "Enable Waveform Generation",
                    "description": "Generate waveform visualizations for audio files",
                    "default": True
                },
                "waveform_width": {
                    "type": "integer",
                    "title": "Waveform Width",
                    "description": "Width of the waveform visualization in pixels",
                    "default": 800,
                    "minimum": 100,
                    "maximum": 2000
                },
                "waveform_height": {
                    "type": "integer",
                    "title": "Waveform Height",
                    "description": "Height of the waveform visualization in pixels",
                    "default": 240,
                    "minimum": 50,
                    "maximum": 1000
                },
                "waveform_color": {
                    "type": "string",
                    "title": "Waveform Color",
                    "description": "Color of the waveform line (CSS color code)",
                    "default": "#1E90FF",
                    "format": "color"
                },
                "waveform_bg_color": {
                    "type": "string",
                    "title": "Waveform Background Color",
                    "description": "Background color of the waveform visualization (CSS color code)",
                    "default": "#F5F5F5",
                    "format": "color"
                },
                "waveform_dpi": {
                    "type": "integer",
                    "title": "Waveform DPI",
                    "description": "DPI (dots per inch) for the waveform visualization",
                    "default": 100,
                    "minimum": 72,
                    "maximum": 300
                }
            }
        }