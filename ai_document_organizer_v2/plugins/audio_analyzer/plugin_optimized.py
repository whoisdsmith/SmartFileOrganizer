"""
Optimized Audio Analyzer Plugin for AI Document Organizer V2.

This enhanced version includes:
- Result caching to avoid redundant processing
- Progress reporting for long-running operations
- Adaptive processing based on available system resources
- Optional feature toggles for intensive operations
- Integration with advanced audio features module
"""

import os
import io
import time
import logging
import tempfile
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Callable

# Import plugin base class
from ai_document_organizer_v2.core.plugin_base import MediaAnalyzerPlugin

# Import cache manager
from ai_document_organizer_v2.plugins.audio_analyzer.cache_manager import AudioAnalysisCache

# Import advanced features module
try:
    from ai_document_organizer_v2.plugins.audio_analyzer.advanced_features import (
        analyze_advanced_features,
        detect_musical_key,
        analyze_harmonic_content,
        detect_voice_instrumental,
        segment_audio
    )
    ADVANCED_FEATURES_AVAILABLE = True
except ImportError:
    ADVANCED_FEATURES_AVAILABLE = False

# Import utilities
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import numpy as np

# System monitoring
import psutil

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
    Enhanced plugin for analyzing audio files with performance optimizations.
    
    This plugin extracts metadata and generates waveform visualizations from audio files
    with improved performance through caching and adaptive processing.
    """
    
    # Plugin metadata
    name = "Audio Analyzer"
    version = "1.1.0"
    description = "Analyzes audio files with optimized performance and caching support"
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
            
        # Initialize cache
        self.cache = AudioAnalysisCache()
        
        # Progress tracking variables
        self.progress_callback = None
        self.progress_thread = None
        self.progress_abort = threading.Event()
        self.current_operation = None
        
        # Set default processing mode based on system resources
        self._set_default_processing_mode()
    
    def _set_default_processing_mode(self):
        """Set the default processing mode based on available system resources"""
        total_memory = psutil.virtual_memory().total
        cpu_count = psutil.cpu_count(logical=False) or 1
        
        # Determine processing mode based on available resources
        if total_memory < 2 * 1024 * 1024 * 1024:  # Less than 2GB RAM
            self.default_processing_mode = "minimal"
        elif total_memory < 8 * 1024 * 1024 * 1024:  # Less than 8GB RAM
            self.default_processing_mode = "standard"
        else:
            self.default_processing_mode = "full"
            
        logger.info(f"Audio analyzer default processing mode set to: {self.default_processing_mode}")
            
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
            # Cache settings
            cache_enabled = self.get_setting("audio_analyzer.cache_enabled", None)
            if cache_enabled is None:
                self.set_setting("audio_analyzer.cache_enabled", True)
                
            # Processing mode
            processing_mode = self.get_setting("audio_analyzer.processing_mode", None)
            if processing_mode is None:
                self.set_setting("audio_analyzer.processing_mode", self.default_processing_mode)
            
            # Adaptive processing
            adaptive_processing = self.get_setting("audio_analyzer.adaptive_processing", None)
            if adaptive_processing is None:
                self.set_setting("audio_analyzer.adaptive_processing", True)
            
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
                    
                # Add new time limit settings
                time_limit_enabled = self.get_setting("audio_analyzer.time_limit_enabled", None)
                if time_limit_enabled is None:
                    self.set_setting("audio_analyzer.time_limit_enabled", True)
                    
                max_duration = self.get_setting("audio_analyzer.max_duration", None)
                if max_duration is None:
                    self.set_setting("audio_analyzer.max_duration", 300)  # 5 minutes
                
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
    
    def analyze_media(self, file_path: str, callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        Analyze an audio file and extract metadata and generate waveform.
        
        Args:
            file_path: Path to the audio file
            callback: Optional progress callback function
            
        Returns:
            Dictionary containing analysis results
        """
        # Set the progress callback
        self.progress_callback = callback
        
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
            # Check if cache is enabled
            cache_enabled = self.get_setting("audio_analyzer.cache_enabled", True)
            
            # Try to get cached results if caching is enabled
            if cache_enabled:
                cached_results = self.cache.get(file_path)
                if cached_results:
                    logger.info(f"Using cached analysis results for: {file_path}")
                    if self.progress_callback:
                        self.progress_callback(100, 100, "Retrieved cached results")
                    return cached_results
            
            # Start progress reporting
            self._start_progress_reporting(file_path)
            
            # Extract basic metadata from audio file
            self.current_operation = "metadata"
            metadata = self._extract_audio_metadata(file_path)
            
            # Get the processing mode
            processing_mode = self.get_setting("audio_analyzer.processing_mode", self.default_processing_mode)
            
            # Use adaptive processing if enabled
            adaptive_processing = self.get_setting("audio_analyzer.adaptive_processing", True)
            if adaptive_processing:
                # Adjust processing mode based on file duration and size
                processing_mode = self._get_adaptive_processing_mode(file_path, metadata, processing_mode)
            
            # Generate waveform visualization if enabled
            preview_path = None
            waveform_enabled = self.get_setting("audio_analyzer.waveform_enabled", True)
            
            if waveform_enabled:
                self.current_operation = "waveform"
                preview_path = self._generate_waveform(file_path)
                if preview_path:
                    metadata['waveform_path'] = preview_path
            
            # Perform advanced audio analysis if librosa is available and not in minimal mode
            if LIBROSA_AVAILABLE and processing_mode != "minimal":
                try:
                    # Check for potential time limit constraints
                    time_limit_enabled = self.get_setting("audio_analyzer.time_limit_enabled", True)
                    max_duration = self.get_setting("audio_analyzer.max_duration", 300)  # Default: 5 minutes
                    
                    # Apply duration limit if enabled and file is too long
                    duration = metadata.get('duration')
                    if time_limit_enabled and duration and duration > max_duration:
                        logger.warning(f"Audio file duration ({duration}s) exceeds max allowed ({max_duration}s). Using first {max_duration} seconds.")
                        # Skip detailed analysis if in standard mode
                        if processing_mode == "standard":
                            logger.info("Skipping detailed analysis due to file duration and 'standard' mode.")
                        else:
                            # In full mode, analyze first max_duration seconds
                            self.current_operation = "advanced analysis (truncated)"
                            advanced_features = self.analyze_audio_features(file_path, max_duration=max_duration)
                            if advanced_features.get('success', False):
                                self._update_metadata_with_advanced_features(metadata, advanced_features)
                    else:
                        # Analyze within limits
                        self.current_operation = "advanced analysis"
                        advanced_features = self.analyze_audio_features(file_path)
                        
                        if advanced_features.get('success', False):
                            self._update_metadata_with_advanced_features(metadata, advanced_features)
                    
                except Exception as e:
                    logger.warning(f"Error in advanced audio analysis: {e}")
                    metadata['advanced_analysis_error'] = str(e)
            
            # Stop progress reporting
            self._stop_progress_reporting()
            
            # Create final result
            result = {
                'metadata': metadata,
                'preview_path': preview_path,
                'transcription': None,  # Handled by transcription plugin
                'success': True,
                'error': ""
            }
            
            # Cache the results if caching is enabled
            if cache_enabled:
                self.cache.put(file_path, result)
            
            return result
            
        except Exception as e:
            # Stop progress reporting
            self._stop_progress_reporting()
            
            logger.error(f"Error analyzing audio file {file_path}: {e}")
            return {
                'metadata': {},
                'preview_path': None,
                'transcription': None,
                'success': False,
                'error': str(e)
            }
    
    def _update_metadata_with_advanced_features(self, metadata: Dict[str, Any], advanced_features: Dict[str, Any]):
        """Update metadata dictionary with advanced feature data"""
        # Add main feature data to metadata
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
                
    def _get_adaptive_processing_mode(self, file_path: str, metadata: Dict[str, Any], default_mode: str) -> str:
        """
        Determine the appropriate processing mode based on file characteristics and system resources.
        
        Args:
            file_path: Path to the audio file
            metadata: Extracted metadata
            default_mode: Default processing mode
            
        Returns:
            Processing mode to use ('minimal', 'standard', or 'full')
        """
        # Get file size and duration
        file_size = metadata.get('file_size', 0)
        duration = metadata.get('duration', 0)
        
        # Check memory availability
        available_memory = psutil.virtual_memory().available
        
        # Calculate memory requirements (rough estimate)
        # Librosa typically needs ~10x the file size in memory
        estimated_memory_needed = file_size * 10
        
        # For very large files or low memory conditions
        if duration > 600 or file_size > 100 * 1024 * 1024 or estimated_memory_needed > available_memory * 0.7:
            logger.info(f"Using minimal processing mode for large file: {file_path}")
            return "minimal"
        
        # For medium duration files
        if duration > 180 or file_size > 50 * 1024 * 1024 or estimated_memory_needed > available_memory * 0.5:
            logger.info(f"Using standard processing mode for medium file: {file_path}")
            return "standard"
        
        # For small files, use the default mode
        return default_mode
        
    def _start_progress_reporting(self, file_path: str):
        """
        Start a thread for progress reporting.
        
        Args:
            file_path: Path to the file being processed
        """
        if self.progress_callback:
            self.progress_abort.clear()
            self.progress_thread = threading.Thread(
                target=self._progress_reporter, 
                args=(file_path,)
            )
            self.progress_thread.daemon = True
            self.progress_thread.start()
    
    def _stop_progress_reporting(self):
        """Stop the progress reporting thread"""
        if self.progress_thread:
            self.progress_abort.set()
            self.progress_thread.join(timeout=1.0)
            self.progress_thread = None
    
    def _progress_reporter(self, file_path: str):
        """
        Thread function for reporting progress.
        
        Args:
            file_path: Path to the file being processed
        """
        start_time = time.time()
        stages = ["metadata", "waveform", "advanced analysis", "advanced analysis (truncated)"]
        
        # Estimate stage weights (time proportions)
        weights = {
            "metadata": 10,
            "waveform": 20,
            "advanced analysis": 70,
            "advanced analysis (truncated)": 40
        }
        
        total_weight = sum(weights.values())
        completed_weight = 0
        
        while not self.progress_abort.is_set():
            current_op = self.current_operation
            
            if current_op in stages:
                stage_index = stages.index(current_op)
                
                # Calculate completed weight
                completed_weight = sum(weights[stage] for stage in stages[:stage_index])
                
                # Estimate progress within current stage (time-based)
                elapsed_time = time.time() - start_time
                stage_progress = min(95, int(elapsed_time * 10)) / 100
                
                current_weight = weights[current_op] * stage_progress
                total_progress = int((completed_weight + current_weight) / total_weight * 100)
                
                # Ensure progress is within bounds
                total_progress = max(1, min(99, total_progress))
                
                # Report progress
                if self.progress_callback:
                    self.progress_callback(total_progress, 100, f"Processing {current_op}")
            
            # Wait a bit
            time.sleep(0.2)
        
        # Final progress report
        if self.progress_callback:
            self.progress_callback(100, 100, "Processing complete")
            
    def _extract_audio_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        Extract metadata from an audio file.
        
        Args:
            file_path: Path to the audio file
            
        Returns:
            Dictionary containing audio metadata
        """
        metadata = {
            'file_name': os.path.basename(file_path),
            'file_path': file_path,
            'file_size': os.path.getsize(file_path),
            'file_extension': os.path.splitext(file_path)[1].lower(),
            'last_modified': datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
        }
        
        # Try to extract metadata using mutagen if available
        if self.mutagen_available:
            try:
                audio = mutagen.File(file_path)
                
                if audio is not None:
                    # Get basic properties
                    metadata['duration'] = audio.info.length
                    metadata['sample_rate'] = getattr(audio.info, 'sample_rate', None)
                    metadata['channels'] = getattr(audio.info, 'channels', None)
                    metadata['bitrate'] = getattr(audio.info, 'bitrate', None)
                    
                    # Extract tags based on file format
                    if isinstance(audio, MP3):
                        metadata['format'] = 'MP3'
                        metadata['bit_depth'] = None  # MP3 doesn't have bit depth
                        metadata['encoder'] = getattr(audio.info, 'encoder_info', None)
                        
                        # ID3 tags
                        if audio.tags:
                            self._extract_id3_tags(audio, metadata)
                            
                    elif isinstance(audio, FLAC):
                        metadata['format'] = 'FLAC'
                        metadata['bit_depth'] = getattr(audio.info, 'bits_per_sample', None)
                        
                        # FLAC tags
                        for key, value in audio.items():
                            metadata[key.lower()] = value[0]
                            
                    elif isinstance(audio, OggVorbis):
                        metadata['format'] = 'Ogg Vorbis'
                        metadata['bit_depth'] = None  # Ogg doesn't expose bit depth
                        
                        # Vorbis comments
                        for key, value in audio.items():
                            metadata[key.lower()] = value[0]
                            
                    elif isinstance(audio, WAVE):
                        metadata['format'] = 'WAV'
                        metadata['bit_depth'] = getattr(audio.info, 'bits_per_sample', None)
                        
                        # WAV tags
                        if hasattr(audio, 'tags'):
                            for key, value in audio.tags.items():
                                metadata[key.lower()] = value[0]
                                
                    elif isinstance(audio, AAC):
                        metadata['format'] = 'AAC'
                        metadata['bit_depth'] = None  # AAC doesn't have bit depth
                    
                    else:
                        metadata['format'] = audio.__class__.__name__
                        
                        # Generic tag extraction attempt
                        if hasattr(audio, 'tags') and audio.tags:
                            for key, value in audio.tags.items():
                                if isinstance(value, list) and len(value) > 0:
                                    metadata[key.lower()] = value[0]
                                else:
                                    metadata[key.lower()] = value
            except Exception as e:
                logger.warning(f"Error extracting metadata with mutagen: {e}")
        
        # Add inferred metadata
        if 'duration' in metadata and metadata['duration']:
            metadata['duration_formatted'] = str(timedelta(seconds=int(metadata['duration'])))
            
        # Estimate quality rating
        quality_rating = 5.0  # Default middle rating
        
        # Adjust based on bitrate
        if 'bitrate' in metadata and metadata['bitrate']:
            bitrate = metadata['bitrate']
            if isinstance(bitrate, int):
                # Adjust quality rating based on bitrate (very simplified model)
                if bitrate >= 320000:
                    quality_rating = 9.0
                elif bitrate >= 256000:
                    quality_rating = 8.0
                elif bitrate >= 192000:
                    quality_rating = 7.0
                elif bitrate >= 128000:
                    quality_rating = 6.0
                elif bitrate < 96000:
                    quality_rating = 4.0
            
        # Adjust based on format
        if 'format' in metadata:
            format_name = metadata['format']
            if format_name == 'FLAC':
                quality_rating += 1.0
            elif format_name == 'WAV':
                quality_rating += 0.5
            elif format_name == 'MP3' and metadata.get('bitrate', 0) < 128000:
                quality_rating -= 0.5
        
        # Cap rating at 10.0
        metadata['quality_rating'] = min(10.0, quality_rating)
        
        return metadata
    
    def _extract_id3_tags(self, audio, metadata):
        """
        Extract ID3 tags from an MP3 file.
        
        Args:
            audio: Mutagen audio object
            metadata: Metadata dictionary to update
        """
        if not audio.tags:
            return
            
        # Common ID3 tags mapping
        tag_mapping = {
            'TIT2': 'title',
            'TPE1': 'artist',
            'TALB': 'album',
            'TDRC': 'year',
            'TCON': 'genre',
            'TRCK': 'track',
            'TPOS': 'disc',
            'COMM': 'comment',
            'TCOM': 'composer',
            'TPUB': 'publisher',
            'TBPM': 'bpm',
            'TKEY': 'key',
            'TLAN': 'language',
            'TCOP': 'copyright',
            'TENC': 'encoded_by',
            'TCMP': 'compilation'
        }
        
        # Extract tags
        for tag, name in tag_mapping.items():
            if tag in audio.tags:
                metadata[name] = str(audio.tags[tag].text[0])
                
        # Extract cover art if present
        if 'APIC:' in audio.tags:
            try:
                # Don't store the actual image data in metadata
                metadata['has_cover_art'] = True
            except:
                pass
    
    def _generate_waveform(self, file_path: str) -> Optional[str]:
        """
        Generate a waveform visualization from an audio file.
        
        Args:
            file_path: Path to the audio file
            
        Returns:
            Path to the generated waveform image or None if failed
        """
        # Check if librosa should be used for waveform generation
        use_librosa = LIBROSA_AVAILABLE and self.get_setting("audio_analyzer.use_librosa_waveform", True)
        
        if use_librosa:
            try:
                return self._generate_librosa_waveform(file_path)
            except Exception as e:
                logger.warning(f"Error generating waveform with librosa: {e}")
                # Fall back to ffmpeg method
                use_librosa = False
        
        # If librosa is not available or failed, try ffmpeg
        if self.ffmpeg_available:
            try:
                # Get waveform settings
                width = self.get_setting("audio_analyzer.waveform_width", 800)
                height = self.get_setting("audio_analyzer.waveform_height", 240)
                color = self.get_setting("audio_analyzer.waveform_color", "#1E90FF")
                bg_color = self.get_setting("audio_analyzer.waveform_bg_color", "#F5F5F5")
                
                # Create a temporary directory for the output
                with tempfile.TemporaryDirectory() as temp_dir:
                    output_path = os.path.join(temp_dir, "waveform.png")
                    
                    # Use ffmpeg to generate a waveform visualization
                    (
                        ffmpeg
                        .input(file_path)
                        .filter('showwavespic', s=f'{width}x{height}', colors=color)
                        .output(output_path)
                        .overwrite_output()
                        .run(quiet=True)
                    )
                    
                    # Get user's document folder
                    if 'USERPROFILE' in os.environ:
                        docs_folder = os.path.join(os.environ['USERPROFILE'], 'Documents')
                    else:
                        docs_folder = os.path.expanduser("~/Documents")
                    
                    # Create a folder for waveform images if it doesn't exist
                    waveform_folder = os.path.join(docs_folder, "AI Document Organizer", "waveforms")
                    os.makedirs(waveform_folder, exist_ok=True)
                    
                    # Create a unique filename based on the original file
                    base_name = os.path.splitext(os.path.basename(file_path))[0]
                    final_path = os.path.join(waveform_folder, f"{base_name}_waveform.png")
                    
                    # Ensure the filename is unique
                    counter = 1
                    while os.path.exists(final_path):
                        final_path = os.path.join(waveform_folder, f"{base_name}_waveform_{counter}.png")
                        counter += 1
                    
                    # Copy the temporary file to the final location
                    import shutil
                    shutil.copy2(output_path, final_path)
                    
                    return final_path
                    
            except Exception as e:
                logger.warning(f"Error generating waveform with ffmpeg: {e}")
        
        # If all methods failed
        return None
    
    def _generate_librosa_waveform(self, file_path: str) -> Optional[str]:
        """
        Generate a waveform visualization using librosa for higher quality.
        
        Args:
            file_path: Path to the audio file
            
        Returns:
            Path to the generated waveform image or None if failed
        """
        if not LIBROSA_AVAILABLE:
            return None
            
        try:
            # Get waveform settings
            width = self.get_setting("audio_analyzer.waveform_width", 800)
            height = self.get_setting("audio_analyzer.waveform_height", 240)
            color = self.get_setting("audio_analyzer.waveform_color", "#1E90FF")
            bg_color = self.get_setting("audio_analyzer.waveform_bg_color", "#F5F5F5")
            
            # For long files, use a duration limit
            time_limit_enabled = self.get_setting("audio_analyzer.time_limit_enabled", True)
            max_duration = self.get_setting("audio_analyzer.max_duration", 300)  # 5 minutes
            
            # Load audio file
            if time_limit_enabled:
                # Limit duration for very long files
                y, sr = librosa.load(file_path, sr=None, duration=max_duration)
            else:
                y, sr = librosa.load(file_path, sr=None)
            
            # Set up the figure
            plt.figure(figsize=(width/100, height/100), dpi=100)
            plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
            plt.axis('off')
            plt.box(False)
            plt.margins(0,0)
            plt.gca().xaxis.set_major_locator(plt.NullLocator())
            plt.gca().yaxis.set_major_locator(plt.NullLocator())
            
            # Set background color
            plt.gca().set_facecolor(bg_color)
            
            # Plot the waveform
            librosa.display.waveshow(y, sr=sr, color=color)
            
            # Get user's document folder
            if 'USERPROFILE' in os.environ:
                docs_folder = os.path.join(os.environ['USERPROFILE'], 'Documents')
            else:
                docs_folder = os.path.expanduser("~/Documents")
            
            # Create a folder for waveform images if it doesn't exist
            waveform_folder = os.path.join(docs_folder, "AI Document Organizer", "waveforms")
            os.makedirs(waveform_folder, exist_ok=True)
            
            # Create a unique filename based on the original file
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            final_path = os.path.join(waveform_folder, f"{base_name}_waveform.png")
            
            # Ensure the filename is unique
            counter = 1
            while os.path.exists(final_path):
                final_path = os.path.join(waveform_folder, f"{base_name}_waveform_{counter}.png")
                counter += 1
            
            # Save the figure
            plt.savefig(final_path, bbox_inches='tight', pad_inches=0)
            plt.close()
            
            return final_path
            
        except Exception as e:
            logger.warning(f"Error generating waveform with librosa: {e}")
            return None
    
    def analyze_audio_features(self, file_path: str, max_duration: Optional[float] = None) -> Dict[str, Any]:
        """
        Perform advanced audio analysis using librosa.
        
        Args:
            file_path: Path to the audio file
            max_duration: Optional maximum duration to analyze (in seconds)
            
        Returns:
            Dictionary with analysis results
        """
        if not LIBROSA_AVAILABLE:
            return {'success': False, 'error': "Librosa library not available"}
            
        try:
            # Load audio file
            y, sr = librosa.load(file_path, sr=None, duration=max_duration)
            
            # Initialize result dictionary
            result = {'success': True}
            
            # Feature extraction enabled checks
            tempo_enabled = self.get_setting("audio_analyzer.tempo_enabled", True)
            spectral_enabled = self.get_setting("audio_analyzer.spectral_enabled", True)
            chroma_enabled = self.get_setting("audio_analyzer.chroma_enabled", True)
            
            # Extract tempo and beats if enabled
            if tempo_enabled:
                try:
                    # Get tempo and beat frames
                    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
                    result['tempo'] = float(tempo)
                    
                    # Convert beat frames to time
                    beat_times = librosa.frames_to_time(beat_frames, sr=sr)
                    result['beat_times'] = beat_times.tolist()
                    result['beat_count'] = len(beat_times)
                    
                    # Calculate beat regularity (standard deviation of beat intervals)
                    if len(beat_times) > 1:
                        beat_intervals = np.diff(beat_times)
                        beat_regularity = 1.0 - min(1.0, np.std(beat_intervals) / np.mean(beat_intervals))
                        result['beat_regularity'] = float(beat_regularity)
                    else:
                        result['beat_regularity'] = 0
                        
                    # Calculate average beat strength
                    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
                    result['avg_beat_strength'] = float(np.mean(onset_env[beat_frames]))
                    
                except Exception as e:
                    result['tempo_error'] = str(e)
                    result['tempo'] = 0
                    result['beat_times'] = []
                    result['beat_count'] = 0
                    result['beat_regularity'] = 0
                    result['avg_beat_strength'] = 0
            
            # Extract spectral features if enabled
            if spectral_enabled:
                try:
                    # Spectral centroid (brightness)
                    spec_cent = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
                    result['spectral_centroid'] = float(np.mean(spec_cent))
                    
                    # Spectral bandwidth (width of the spectrum)
                    spec_bw = librosa.feature.spectral_bandwidth(y=y, sr=sr)[0]
                    result['spectral_bandwidth'] = float(np.mean(spec_bw))
                    
                    # Spectral contrast (valley vs. peak energy)
                    spec_contrast = librosa.feature.spectral_contrast(y=y, sr=sr)
                    result['spectral_contrast'] = float(np.mean(spec_contrast))
                    
                    # Spectral rolloff (frequency below which 85% of the energy lies)
                    rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)[0]
                    result['spectral_rolloff'] = float(np.mean(rolloff))
                    
                    # Zero crossing rate (noise vs. harmonic content)
                    zcr = librosa.feature.zero_crossing_rate(y)[0]
                    result['zero_crossing_rate'] = float(np.mean(zcr))
                    
                    # RMS energy (loudness)
                    rms = librosa.feature.rms(y=y)[0]
                    result['rms_energy'] = float(np.mean(rms))
                    
                except Exception as e:
                    result['spectral_error'] = str(e)
            
            # Extract tonal features if enabled
            if chroma_enabled:
                try:
                    # Chroma features (pitch content)
                    chroma = librosa.feature.chroma_stft(y=y, sr=sr)
                    
                    # Calculate dominant pitch class
                    chroma_avg = np.mean(chroma, axis=1)
                    pitch_classes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
                    dominant_idx = np.argmax(chroma_avg)
                    
                    result['dominant_pitch'] = pitch_classes[dominant_idx]
                    result['tonal_strength'] = float(chroma_avg[dominant_idx] / np.sum(chroma_avg))
                    result['tonal_spread'] = float(np.std(chroma_avg))
                    
                    # Extract limited chroma features for analysis results
                    result['chroma_features'] = {
                        'mean': chroma_avg.tolist(),
                        'dominant_idx': int(dominant_idx)
                    }
                    
                except Exception as e:
                    result['chroma_error'] = str(e)
                    result['dominant_pitch'] = "Unknown"
                    result['tonal_strength'] = 0
            
            # Extract MFCCs if enabled
            try:
                mfcc_count = self.get_setting("audio_analyzer.mfcc_count", 13)
                
                # Extract MFCCs
                mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=mfcc_count)
                
                # Calculate statistics of MFCCs
                result['mfcc_features'] = {
                    'mean': np.mean(mfccs, axis=1).tolist(),
                    'std': np.std(mfccs, axis=1).tolist()
                }
                
            except Exception as e:
                result['mfcc_error'] = str(e)
            
            return result
            
        except Exception as e:
            logger.error(f"Error in advanced audio analysis: {e}")
            return {'success': False, 'error': str(e)}