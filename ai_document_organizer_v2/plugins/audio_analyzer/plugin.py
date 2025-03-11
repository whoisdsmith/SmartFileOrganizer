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
    
# Try importing librosa for advanced audio analysis
try:
    import librosa
    import librosa.feature
    import librosa.beat
    import librosa.display
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False

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
            
        # Check for librosa (advanced audio analysis)
        if not LIBROSA_AVAILABLE:
            logger.warning("Librosa library not available. Advanced audio analysis features will be disabled.")
            # Return True anyway to allow partial functionality
        else:
            logger.info("Librosa found. Advanced audio analysis features are available.")
        
        # Register default settings if not already present
        if self.settings_manager is not None:
            # Waveform visualization settings
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
            
            # Advanced audio analysis settings
            if LIBROSA_AVAILABLE:
                tempo_enabled = self.get_setting("audio_analyzer.tempo_enabled", None)
                if tempo_enabled is None:
                    self.set_setting("audio_analyzer.tempo_enabled", True)
                    
                spectral_enabled = self.get_setting("audio_analyzer.spectral_enabled", None)
                if spectral_enabled is None:
                    self.set_setting("audio_analyzer.spectral_enabled", True)
                    
                chroma_enabled = self.get_setting("audio_analyzer.chroma_enabled", None)
                if chroma_enabled is None:
                    self.set_setting("audio_analyzer.chroma_enabled", True)
                    
                mfcc_count = self.get_setting("audio_analyzer.mfcc_count", None)
                if mfcc_count is None:
                    self.set_setting("audio_analyzer.mfcc_count", 13)
                    
                use_librosa_waveform = self.get_setting("audio_analyzer.use_librosa_waveform", None)
                if use_librosa_waveform is None:
                    self.set_setting("audio_analyzer.use_librosa_waveform", True)
                
            logger.info("Audio analyzer settings initialized")
            
        # Update dependencies list based on available libraries
        dependencies = ["mutagen", "matplotlib", "ffmpeg-python"]
        if LIBROSA_AVAILABLE:
            dependencies.append("librosa")
            
        # Update plugin description to reflect capabilities
        description = "Analyzes audio files, extracts metadata, and generates waveform visualizations"
        if LIBROSA_AVAILABLE:
            description += " with advanced beat detection and tempo analysis"
            
        # Update plugin info
        self.dependencies = dependencies
        self.description = description
            
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
            # Extract basic metadata from audio file
            metadata = self._extract_audio_metadata(file_path)
            
            # Generate waveform visualization if enabled
            preview_path = None
            waveform_enabled = self.get_setting("audio_analyzer.waveform_enabled", True)
            
            if waveform_enabled:
                preview_path = self._generate_waveform(file_path)
                if preview_path:
                    metadata['waveform_path'] = preview_path
            
            # Perform advanced audio analysis if librosa is available
            if LIBROSA_AVAILABLE:
                try:
                    # Check if user settings have disabled any analysis
                    advanced_analysis_enabled = True
                    
                    # Perform advanced audio analysis and update metadata
                    if advanced_analysis_enabled:
                        advanced_features = self.analyze_audio_features(file_path)
                        
                        if advanced_features.get('success', False):
                            # Add advanced feature data to metadata
                            metadata['tempo'] = advanced_features.get('tempo')
                            metadata['beat_count'] = advanced_features.get('beat_count')
                            metadata['beat_regularity'] = advanced_features.get('beat_regularity')
                            metadata['dominant_pitch'] = advanced_features.get('dominant_pitch')
                            metadata['tonal_strength'] = advanced_features.get('tonal_strength')
                            metadata['spectral_centroid'] = advanced_features.get('spectral_centroid')
                            
                            # Add detailed analysis to a separate field
                            metadata['advanced_analysis'] = {
                                'beat_times': advanced_features.get('beat_times'),
                                'avg_beat_strength': advanced_features.get('avg_beat_strength'),
                                'spectral_bandwidth': advanced_features.get('spectral_bandwidth'),
                                'spectral_contrast': advanced_features.get('spectral_contrast'),
                                'spectral_rolloff': advanced_features.get('spectral_rolloff'),
                                'zero_crossing_rate': advanced_features.get('zero_crossing_rate'),
                                'rms_energy': advanced_features.get('rms_energy'),
                                'mfcc_features': advanced_features.get('mfcc_features'),
                                'chroma_features': advanced_features.get('chroma_features'),
                                'tonal_spread': advanced_features.get('tonal_spread')
                            }
                            
                            # Add audio quality assessment based on spectral features
                            if 'quality_rating' in metadata:
                                # Adjust quality rating based on advanced analysis
                                quality_rating = metadata['quality_rating']
                                
                                # Adjust for beat regularity (well-produced music tends to have regular beats)
                                if advanced_features.get('beat_regularity', 0) > 0.8:
                                    quality_rating += 0.5
                                
                                # Adjust for spectral balance
                                if advanced_features.get('spectral_contrast', 0) > 30:
                                    quality_rating += 0.5
                                
                                # Cap rating at 10.0
                                metadata['quality_rating'] = min(10.0, quality_rating)
                                
                                # Add quality assessment text
                                if metadata['quality_rating'] >= 9.0:
                                    metadata['quality_assessment'] = "Excellent audio quality with well-balanced frequency response"
                                elif metadata['quality_rating'] >= 7.5:
                                    metadata['quality_assessment'] = "Very good audio quality"
                                elif metadata['quality_rating'] >= 6.0:
                                    metadata['quality_assessment'] = "Good audio quality"
                                elif metadata['quality_rating'] >= 4.0:
                                    metadata['quality_assessment'] = "Average audio quality"
                                else:
                                    metadata['quality_assessment'] = "Below average audio quality"
                except Exception as e:
                    logger.warning(f"Error in advanced audio analysis: {e}")
                    metadata['advanced_analysis_error'] = str(e)
            
            # Return final analysis results
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
            'format': None,
            # Audio analysis fields
            'tempo': None,
            'beats': None,
            'beat_times': None,
            'spectral_centroid': None,
            'spectral_bandwidth': None,
            'spectral_contrast': None,
            'spectral_rolloff': None,
            'zero_crossing_rate': None,
            'chroma_features': None,
            'mfcc_features': None,
            'rms_energy': None
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
            
            # Try using librosa first if available (better quality)
            if LIBROSA_AVAILABLE:
                try:
                    return self._generate_librosa_waveform(file_path, output_path, width, height, color, bg_color, dpi)
                except Exception as e:
                    logger.warning(f"Error generating waveform with librosa, falling back to ffmpeg: {e}")
                    # Fall back to ffmpeg method
            
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
    
    def _generate_librosa_waveform(self, file_path: str, output_path: str, 
                                 width: int, height: int, color: str, 
                                 bg_color: str, dpi: int) -> Optional[str]:
        """
        Generate a waveform visualization using librosa (higher quality).
        
        Args:
            file_path: Path to the audio file
            output_path: Path to save the waveform image
            width: Width of the waveform in pixels
            height: Height of the waveform in pixels
            color: Waveform color
            bg_color: Background color
            dpi: DPI for the output image
            
        Returns:
            Path to the generated waveform image or None if generation failed
        """
        # Load the audio file with librosa
        y, sr = librosa.load(file_path, sr=None)
        
        # Create the figure
        fig, ax = plt.subplots(figsize=(width/dpi, height/dpi), dpi=dpi)
        
        # Plot the waveform
        librosa.display.waveshow(y, sr=sr, ax=ax, color=color)
        
        # Remove axes and set background color
        ax.set_axis_off()
        fig.patch.set_facecolor(bg_color)
        ax.set_facecolor(bg_color)
        
        # Tight layout
        plt.tight_layout(pad=0)
        
        # Save the figure
        plt.savefig(output_path, dpi=dpi, bbox_inches='tight', pad_inches=0)
        plt.close(fig)
        
        return output_path if os.path.exists(output_path) else None
    
    def analyze_audio_features(self, file_path: str) -> Dict[str, Any]:
        """
        Perform advanced audio analysis using librosa.
        
        Args:
            file_path: Path to the audio file
            
        Returns:
            Dictionary with audio analysis results
        """
        if not LIBROSA_AVAILABLE:
            logger.warning("Cannot perform advanced audio analysis: librosa not available")
            return {
                'success': False,
                'error': "Librosa library not available"
            }
        
        try:
            # Load the audio file with librosa
            y, sr = librosa.load(file_path, sr=None)
            
            # Initialize results dictionary
            results = {
                'success': True,
                'sample_rate': sr,
                'duration': librosa.get_duration(y=y, sr=sr)
            }
            
            # Extract tempo and beat information
            tempo_enabled = self.get_setting("audio_analyzer.tempo_enabled", True)
            if tempo_enabled:
                try:
                    tempo_result = self._analyze_tempo_and_beats(y, sr)
                    results.update(tempo_result)
                except Exception as e:
                    logger.warning(f"Error analyzing tempo and beats: {e}")
                    results['tempo_error'] = str(e)
            
            # Extract spectral features
            spectral_enabled = self.get_setting("audio_analyzer.spectral_enabled", True)
            if spectral_enabled:
                try:
                    spectral_result = self._analyze_spectral_features(y, sr)
                    results.update(spectral_result)
                except Exception as e:
                    logger.warning(f"Error analyzing spectral features: {e}")
                    results['spectral_error'] = str(e)
            
            # Extract chromagram features
            chroma_enabled = self.get_setting("audio_analyzer.chroma_enabled", True)
            if chroma_enabled:
                try:
                    chroma_result = self._analyze_chroma_features(y, sr)
                    results.update(chroma_result)
                except Exception as e:
                    logger.warning(f"Error analyzing chroma features: {e}")
                    results['chroma_error'] = str(e)
            
            return results
        
        except Exception as e:
            logger.error(f"Error performing advanced audio analysis: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _analyze_tempo_and_beats(self, y: np.ndarray, sr: int) -> Dict[str, Any]:
        """
        Analyze tempo and beat information.
        
        Args:
            y: Audio time series
            sr: Sample rate
            
        Returns:
            Dictionary with tempo and beat analysis results
        """
        # Get tempo (BPM)
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        tempo = librosa.beat.tempo(onset_envelope=onset_env, sr=sr)[0]
        
        # Beat tracking
        beat_frames = librosa.beat.beat_track(y=y, sr=sr)[1]
        beat_times = librosa.frames_to_time(beat_frames, sr=sr)
        
        # Count beats
        beat_count = len(beat_times)
        
        # Calculate average beat strength
        beat_strengths = onset_env[beat_frames] if len(beat_frames) > 0 else []
        avg_beat_strength = float(np.mean(beat_strengths)) if len(beat_strengths) > 0 else 0
        
        # Calculate beat regularity
        if len(beat_times) > 1:
            beat_intervals = np.diff(beat_times)
            beat_regularity = 1.0 - float(np.std(beat_intervals) / np.mean(beat_intervals))
            beat_regularity = max(0.0, min(1.0, beat_regularity))  # Clamp between 0 and 1
        else:
            beat_regularity = 0.0
        
        return {
            'tempo': float(tempo),
            'beat_count': beat_count,
            'beat_times': beat_times.tolist(),
            'avg_beat_strength': avg_beat_strength,
            'beat_regularity': beat_regularity
        }
    
    def _analyze_spectral_features(self, y: np.ndarray, sr: int) -> Dict[str, Any]:
        """
        Analyze spectral features.
        
        Args:
            y: Audio time series
            sr: Sample rate
            
        Returns:
            Dictionary with spectral analysis results
        """
        # Extract various spectral features
        
        # Spectral centroid (brightness)
        cent = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
        avg_cent = float(np.mean(cent))
        
        # Spectral bandwidth
        bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr)[0]
        avg_bandwidth = float(np.mean(bandwidth))
        
        # Spectral contrast
        contrast = librosa.feature.spectral_contrast(y=y, sr=sr)
        avg_contrast = float(np.mean(contrast))
        
        # Spectral rolloff
        rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)[0]
        avg_rolloff = float(np.mean(rolloff))
        
        # Zero crossing rate (noisiness)
        zcr = librosa.feature.zero_crossing_rate(y)[0]
        avg_zcr = float(np.mean(zcr))
        
        # Root mean square energy
        rms = librosa.feature.rms(y=y)[0]
        avg_rms = float(np.mean(rms))
        
        # Mel-frequency cepstral coefficients (MFCCs)
        mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
        avg_mfccs = [float(np.mean(mfcc)) for mfcc in mfccs]
        
        return {
            'spectral_centroid': avg_cent,
            'spectral_bandwidth': avg_bandwidth,
            'spectral_contrast': avg_contrast,
            'spectral_rolloff': avg_rolloff,
            'zero_crossing_rate': avg_zcr,
            'rms_energy': avg_rms,
            'mfcc_features': avg_mfccs
        }
    
    def _analyze_chroma_features(self, y: np.ndarray, sr: int) -> Dict[str, Any]:
        """
        Analyze chroma features (tonal content).
        
        Args:
            y: Audio time series
            sr: Sample rate
            
        Returns:
            Dictionary with chroma analysis results
        """
        # Compute chromagram
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
        
        # Average values for each pitch class
        avg_chroma = [float(np.mean(pitch)) for pitch in chroma]
        
        # Get the dominant pitch class (0=C, 1=C#, ..., 11=B)
        dominant_pitch_idx = int(np.argmax(avg_chroma))
        pitch_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        dominant_pitch = pitch_names[dominant_pitch_idx]
        
        # Calculate tonal strength (max chroma value)
        tonal_strength = float(np.max(avg_chroma))
        
        # Calculate tonal spread (entropy of distribution)
        normalized_chroma = np.array(avg_chroma) / np.sum(avg_chroma)
        tonal_spread = float(-np.sum(normalized_chroma * np.log2(normalized_chroma + 1e-10)))
        
        return {
            'chroma_features': avg_chroma,
            'dominant_pitch': dominant_pitch,
            'dominant_pitch_idx': dominant_pitch_idx,
            'tonal_strength': tonal_strength,
            'tonal_spread': tonal_spread
        }
    
    def get_config_schema(self) -> Dict[str, Any]:
        """
        Get JSON schema for plugin configuration.
        
        Returns:
            Dictionary with JSON schema for plugin configuration
        """
        return {
            "type": "object",
            "properties": {
                # Waveform visualization settings
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
                },
                
                # Advanced audio analysis settings
                "tempo_enabled": {
                    "type": "boolean",
                    "title": "Enable Tempo Analysis",
                    "description": "Enable tempo and beat detection analysis",
                    "default": True
                },
                "spectral_enabled": {
                    "type": "boolean",
                    "title": "Enable Spectral Analysis",
                    "description": "Enable spectral feature analysis",
                    "default": True
                },
                "chroma_enabled": {
                    "type": "boolean",
                    "title": "Enable Chroma Analysis",
                    "description": "Enable chroma feature (tonal content) analysis",
                    "default": True
                },
                "mfcc_count": {
                    "type": "integer",
                    "title": "MFCC Count",
                    "description": "Number of Mel-frequency cepstral coefficients to extract",
                    "default": 13,
                    "minimum": 5,
                    "maximum": 40
                },
                "use_librosa_waveform": {
                    "type": "boolean",
                    "title": "Use Librosa for Waveforms",
                    "description": "Use librosa for generating higher quality waveforms (requires more processing power)",
                    "default": True
                }
            }
        }