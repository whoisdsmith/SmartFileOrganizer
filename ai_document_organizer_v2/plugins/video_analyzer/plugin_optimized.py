"""
Optimized Video Analyzer Plugin for AI Document Organizer V2.

This enhanced version includes:
- Result caching to avoid redundant processing
- Progress reporting for long-running operations
- Adaptive processing based on available system resources
- Scene detection and frame extraction
- Integration with audio analysis
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
from ai_document_organizer_v2.plugins.video_analyzer.cache_manager import VideoAnalysisCache

# Import utilities
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import numpy as np

# System monitoring
import psutil

# Try importing required libraries
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

try:
    import ffmpeg
    FFMPEG_AVAILABLE = True
except ImportError:
    FFMPEG_AVAILABLE = False

try:
    from moviepy.editor import VideoFileClip
    MOVIEPY_AVAILABLE = True
except ImportError:
    MOVIEPY_AVAILABLE = False

logger = logging.getLogger("AIDocumentOrganizerV2.VideoAnalyzer")

class VideoAnalyzerPlugin(MediaAnalyzerPlugin):
    """
    Enhanced plugin for analyzing video files with performance optimizations.
    
    This plugin extracts metadata, generates thumbnails, and performs scene detection
    with improved performance through caching and adaptive processing.
    """
    
    # Plugin metadata
    name = "Video Analyzer"
    version = "1.1.0"
    description = "Analyzes video files with optimized performance and caching support"
    author = "AI Document Organizer Team"
    dependencies = ["ffmpeg-python", "opencv-python", "moviepy"]
    
    # File extensions supported by this plugin
    supported_extensions = [".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv", ".webm"]
    
    def __init__(self, plugin_id: str, name: Optional[str] = None, version: Optional[str] = None,
                 description: Optional[str] = None):
        """
        Initialize the video analyzer plugin.
        
        Args:
            plugin_id: Unique identifier for the plugin
            name: Plugin name (if None, uses class attribute)
            version: Plugin version (if None, uses class attribute)
            description: Plugin description (if None, uses class attribute)
        """
        super().__init__(plugin_id, name, version, description)
        
        # Check if required libraries are available
        self.cv2_available = CV2_AVAILABLE
        self.ffmpeg_available = FFMPEG_AVAILABLE
        self.moviepy_available = MOVIEPY_AVAILABLE
        
        if not self.cv2_available:
            logger.warning("OpenCV library not available. Scene detection will be limited.")
        
        if not self.ffmpeg_available:
            logger.warning("FFmpeg library not available. Video processing will be limited.")
            
        if not self.moviepy_available:
            logger.warning("MoviePy library not available. Video analysis will be limited.")
            
        # Initialize cache
        self.cache = VideoAnalysisCache()
        
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
            
        logger.info(f"Video analyzer default processing mode set to: {self.default_processing_mode}")
            
    def initialize(self) -> bool:
        """
        Initialize the plugin.
        
        Returns:
            True if initialization was successful, False otherwise
        """
        # Check dependencies
        if not self.cv2_available:
            logger.warning("OpenCV library not available. Install opencv-python for scene detection.")
            # Return True anyway to allow partial functionality
        
        if not self.ffmpeg_available:
            logger.warning("FFmpeg library not available. Install ffmpeg-python for video processing.")
            # Return True anyway to allow partial functionality
            
        if not self.moviepy_available:
            logger.warning("MoviePy library not available. Install moviepy for video analysis.")
            # Return True anyway to allow partial functionality
        
        # Register default settings if not already present
        if self.settings_manager is not None:
            # Cache settings
            cache_enabled = self.get_setting("video_analyzer.cache_enabled", None)
            if cache_enabled is None:
                self.set_setting("video_analyzer.cache_enabled", True)
                
            # Processing mode
            processing_mode = self.get_setting("video_analyzer.processing_mode", None)
            if processing_mode is None:
                self.set_setting("video_analyzer.processing_mode", self.default_processing_mode)
            
            # Adaptive processing
            adaptive_processing = self.get_setting("video_analyzer.adaptive_processing", None)
            if adaptive_processing is None:
                self.set_setting("video_analyzer.adaptive_processing", True)
            
            # Thumbnail settings
            thumbnail_enabled = self.get_setting("video_analyzer.thumbnail_enabled", None)
            if thumbnail_enabled is None:
                self.set_setting("video_analyzer.thumbnail_enabled", True)
                
            thumbnail_count = self.get_setting("video_analyzer.thumbnail_count", None)
            if thumbnail_count is None:
                self.set_setting("video_analyzer.thumbnail_count", 3)
                
            thumbnail_width = self.get_setting("video_analyzer.thumbnail_width", None)
            if thumbnail_width is None:
                self.set_setting("video_analyzer.thumbnail_width", 320)
                
            thumbnail_height = self.get_setting("video_analyzer.thumbnail_height", None)
            if thumbnail_height is None:
                self.set_setting("video_analyzer.thumbnail_height", 180)
                
            # Scene detection settings
            scene_detection_enabled = self.get_setting("video_analyzer.scene_detection_enabled", None)
            if scene_detection_enabled is None:
                self.set_setting("video_analyzer.scene_detection_enabled", True)
                
            scene_threshold = self.get_setting("video_analyzer.scene_threshold", None)
            if scene_threshold is None:
                self.set_setting("video_analyzer.scene_threshold", 30.0)
                
            min_scene_duration = self.get_setting("video_analyzer.min_scene_duration", None)
            if min_scene_duration is None:
                self.set_setting("video_analyzer.min_scene_duration", 1.0)
                
            # Frame extraction settings
            max_frames = self.get_setting("video_analyzer.max_frames", None)
            if max_frames is None:
                self.set_setting("video_analyzer.max_frames", 50)
                
            # Audio extraction settings
            extract_audio = self.get_setting("video_analyzer.extract_audio", None)
            if extract_audio is None:
                self.set_setting("video_analyzer.extract_audio", False)
                
            # Time limit settings
            time_limit_enabled = self.get_setting("video_analyzer.time_limit_enabled", None)
            if time_limit_enabled is None:
                self.set_setting("video_analyzer.time_limit_enabled", True)
                
            max_duration = self.get_setting("video_analyzer.max_duration", None)
            if max_duration is None:
                self.set_setting("video_analyzer.max_duration", 300)  # 5 minutes
                
            logger.info("Video analyzer settings initialized")
            
        # Update dependencies list based on available libraries
        dependencies = []
        if self.ffmpeg_available:
            dependencies.append("ffmpeg-python")
        if self.cv2_available:
            dependencies.append("opencv-python")
        if self.moviepy_available:
            dependencies.append("moviepy")
            
        # Update plugin description to reflect capabilities
        description = "Analyzes video files, extracts metadata, and generates thumbnails"
        if self.cv2_available:
            description += " with scene detection"
            
        # Update plugin info
        self.dependencies = dependencies
        self.description = description
            
        return True
    
    def analyze_media(self, file_path: str, callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        Analyze a video file and extract metadata, thumbnails, and scene information.
        
        Args:
            file_path: Path to the video file
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
            cache_enabled = self.get_setting("video_analyzer.cache_enabled", True)
            
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
            
            # Extract basic metadata from video file
            self.current_operation = "metadata"
            metadata = self._extract_video_metadata(file_path)
            
            # Get the processing mode
            processing_mode = self.get_setting("video_analyzer.processing_mode", self.default_processing_mode)
            
            # Use adaptive processing if enabled
            adaptive_processing = self.get_setting("video_analyzer.adaptive_processing", True)
            if adaptive_processing:
                # Adjust processing mode based on file duration and size
                processing_mode = self._get_adaptive_processing_mode(file_path, metadata, processing_mode)
            
            # Generate thumbnail if enabled
            preview_path = None
            thumbnail_enabled = self.get_setting("video_analyzer.thumbnail_enabled", True)
            
            if thumbnail_enabled:
                self.current_operation = "thumbnails"
                preview_path = self._generate_thumbnails(file_path, metadata)
                if preview_path:
                    metadata['thumbnail_path'] = preview_path
            
            # Perform scene detection if enabled and not in minimal mode
            if self.cv2_available and processing_mode != "minimal":
                scene_detection_enabled = self.get_setting("video_analyzer.scene_detection_enabled", True)
                
                if scene_detection_enabled:
                    try:
                        # Check for potential time limit constraints
                        time_limit_enabled = self.get_setting("video_analyzer.time_limit_enabled", True)
                        max_duration = self.get_setting("video_analyzer.max_duration", 300)  # Default: 5 minutes
                        
                        # Apply duration limit if enabled and file is too long
                        duration = metadata.get('duration', 0)
                        if time_limit_enabled and duration and duration > max_duration:
                            logger.warning(f"Video file duration ({duration}s) exceeds max allowed ({max_duration}s). Using partial scene detection.")
                            self.current_operation = "scene detection (truncated)"
                            scene_info = self._detect_scenes(file_path, max_duration=max_duration)
                        else:
                            # Analyze without time limit
                            self.current_operation = "scene detection"
                            scene_info = self._detect_scenes(file_path)
                        
                        # Add scene information to metadata
                        if scene_info:
                            metadata['scenes'] = scene_info
                        
                    except Exception as e:
                        logger.warning(f"Error in scene detection: {e}")
                        metadata['scene_detection_error'] = str(e)
            
            # Extract audio if enabled and in full mode
            if self.moviepy_available and processing_mode == "full":
                extract_audio = self.get_setting("video_analyzer.extract_audio", False)
                
                if extract_audio:
                    try:
                        self.current_operation = "audio extraction"
                        audio_path = self._extract_audio(file_path)
                        
                        if audio_path:
                            metadata['audio_path'] = audio_path
                            
                    except Exception as e:
                        logger.warning(f"Error in audio extraction: {e}")
                        metadata['audio_extraction_error'] = str(e)
            
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
            
            logger.error(f"Error analyzing video file {file_path}: {e}")
            return {
                'metadata': {},
                'preview_path': None,
                'transcription': None,
                'success': False,
                'error': str(e)
            }
    
    def _get_adaptive_processing_mode(self, file_path: str, metadata: Dict[str, Any], default_mode: str) -> str:
        """
        Determine the appropriate processing mode based on file characteristics and system resources.
        
        Args:
            file_path: Path to the video file
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
        # Video processing typically needs ~5x the file size in memory for full processing
        estimated_memory_needed = file_size * 5
        
        # For very large files or low memory conditions
        if duration > 600 or file_size > 500 * 1024 * 1024 or estimated_memory_needed > available_memory * 0.7:
            logger.info(f"Using minimal processing mode for large file: {file_path}")
            return "minimal"
        
        # For medium duration files
        if duration > 180 or file_size > 100 * 1024 * 1024 or estimated_memory_needed > available_memory * 0.5:
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
        stages = ["metadata", "thumbnails", "scene detection", "scene detection (truncated)", "audio extraction"]
        
        # Estimate stage weights (time proportions)
        weights = {
            "metadata": 10,
            "thumbnails": 20,
            "scene detection": 60,
            "scene detection (truncated)": 40,
            "audio extraction": 30
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
            
    def _extract_video_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        Extract metadata from a video file.
        
        Args:
            file_path: Path to the video file
            
        Returns:
            Dictionary containing video metadata
        """
        metadata = {
            'file_name': os.path.basename(file_path),
            'file_path': file_path,
            'file_size': os.path.getsize(file_path),
            'file_extension': os.path.splitext(file_path)[1].lower(),
            'last_modified': datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
        }
        
        # Extract video metadata using ffmpeg
        if self.ffmpeg_available:
            try:
                # Get video information
                probe = ffmpeg.probe(file_path)
                
                # Extract video stream information
                video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
                
                if video_stream:
                    # Basic video properties
                    metadata['width'] = int(video_stream.get('width', 0))
                    metadata['height'] = int(video_stream.get('height', 0))
                    metadata['codec'] = video_stream.get('codec_name', 'unknown')
                    metadata['pixel_format'] = video_stream.get('pix_fmt', 'unknown')
                    
                    # Calculate aspect ratio
                    if metadata['width'] > 0 and metadata['height'] > 0:
                        gcd = self._calculate_gcd(metadata['width'], metadata['height'])
                        metadata['aspect_ratio'] = f"{metadata['width'] // gcd}:{metadata['height'] // gcd}"
                    
                    # Get framerate
                    if 'avg_frame_rate' in video_stream:
                        frame_rate_parts = video_stream['avg_frame_rate'].split('/')
                        if len(frame_rate_parts) == 2 and int(frame_rate_parts[1]) != 0:
                            metadata['frame_rate'] = round(int(frame_rate_parts[0]) / int(frame_rate_parts[1]), 2)
                    
                    # Calculate duration
                    if 'duration' in video_stream:
                        metadata['duration'] = float(video_stream['duration'])
                        metadata['duration_formatted'] = str(timedelta(seconds=int(float(video_stream['duration']))))
                    
                    # Calculate bitrate
                    if 'bit_rate' in video_stream:
                        metadata['video_bitrate'] = int(video_stream['bit_rate'])
                    
                    # Get total frames if available
                    if 'nb_frames' in video_stream:
                        metadata['frame_count'] = int(video_stream['nb_frames'])
                    
                # Extract audio stream information
                audio_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'audio'), None)
                
                if audio_stream:
                    # Basic audio properties
                    metadata['audio_codec'] = audio_stream.get('codec_name', 'unknown')
                    metadata['audio_channels'] = int(audio_stream.get('channels', 0))
                    metadata['audio_sample_rate'] = int(audio_stream.get('sample_rate', 0))
                    
                    # Calculate audio bitrate
                    if 'bit_rate' in audio_stream:
                        metadata['audio_bitrate'] = int(audio_stream['bit_rate'])
                    
                    # Calculate audio duration
                    if 'duration' in audio_stream:
                        metadata['audio_duration'] = float(audio_stream['duration'])
                        
                # Get general information from format section
                if 'format' in probe:
                    format_info = probe['format']
                    
                    # Override duration if not set in video stream
                    if 'duration' in format_info and 'duration' not in metadata:
                        metadata['duration'] = float(format_info['duration'])
                        metadata['duration_formatted'] = str(timedelta(seconds=int(float(format_info['duration']))))
                    
                    # Get container format
                    if 'format_name' in format_info:
                        metadata['container_format'] = format_info['format_name']
                        
                    # Get overall bitrate
                    if 'bit_rate' in format_info:
                        metadata['bitrate'] = int(format_info['bit_rate'])
                        
                    # Get tags if available
                    if 'tags' in format_info:
                        for key, value in format_info['tags'].items():
                            metadata[f"tag_{key.lower()}"] = value
                
                # Try to determine if the video has audio
                metadata['has_audio'] = audio_stream is not None
                
                # Try to determine video quality
                quality_rating = 5.0  # Default middle rating
                
                # Adjust based on resolution
                if metadata.get('width', 0) >= 1920 and metadata.get('height', 0) >= 1080:
                    quality_rating += 2.0  # Full HD or better
                elif metadata.get('width', 0) >= 1280 and metadata.get('height', 0) >= 720:
                    quality_rating += 1.0  # HD
                elif metadata.get('width', 0) < 640 or metadata.get('height', 0) < 480:
                    quality_rating -= 1.0  # Less than SD
                
                # Adjust based on video bitrate
                video_bitrate = metadata.get('video_bitrate', 0)
                if video_bitrate > 8000000:  # > 8 Mbps
                    quality_rating += 1.5
                elif video_bitrate > 4000000:  # > 4 Mbps
                    quality_rating += 1.0
                elif video_bitrate > 2000000:  # > 2 Mbps
                    quality_rating += 0.5
                elif video_bitrate < 1000000:  # < 1 Mbps
                    quality_rating -= 1.0
                
                # Cap rating at 10.0
                metadata['quality_rating'] = min(10.0, quality_rating)
                
                # Add quality assessment text
                if metadata['quality_rating'] >= 9.0:
                    metadata['quality_assessment'] = "Excellent video quality"
                elif metadata['quality_rating'] >= 7.5:
                    metadata['quality_assessment'] = "Very good video quality"
                elif metadata['quality_rating'] >= 6.0:
                    metadata['quality_assessment'] = "Good video quality"
                elif metadata['quality_rating'] >= 4.0:
                    metadata['quality_assessment'] = "Average video quality"
                else:
                    metadata['quality_assessment'] = "Below average video quality"
                    
            except Exception as e:
                logger.warning(f"Error extracting metadata with ffmpeg: {e}")
        
        # If ffmpeg failed or is not available, try moviepy
        if self.moviepy_available and 'duration' not in metadata:
            try:
                # Open the video file
                with VideoFileClip(file_path) as clip:
                    # Get basic properties
                    metadata['duration'] = clip.duration
                    metadata['duration_formatted'] = str(timedelta(seconds=int(clip.duration)))
                    metadata['width'] = clip.size[0]
                    metadata['height'] = clip.size[1]
                    metadata['frame_rate'] = clip.fps
                    metadata['has_audio'] = clip.audio is not None
                    
                    # Calculate aspect ratio
                    if metadata['width'] > 0 and metadata['height'] > 0:
                        gcd = self._calculate_gcd(metadata['width'], metadata['height'])
                        metadata['aspect_ratio'] = f"{metadata['width'] // gcd}:{metadata['height'] // gcd}"
                    
                    # Rough quality assessment based on resolution
                    quality_rating = 5.0  # Default middle rating
                    
                    # Adjust based on resolution
                    if metadata['width'] >= 1920 and metadata['height'] >= 1080:
                        quality_rating += 2.0  # Full HD or better
                    elif metadata['width'] >= 1280 and metadata['height'] >= 720:
                        quality_rating += 1.0  # HD
                    elif metadata['width'] < 640 or metadata['height'] < 480:
                        quality_rating -= 1.0  # Less than SD
                        
                    # Cap rating at 10.0
                    metadata['quality_rating'] = min(10.0, quality_rating)
                    
            except Exception as e:
                logger.warning(f"Error extracting metadata with moviepy: {e}")
                
        return metadata
    
    def _calculate_gcd(self, a: int, b: int) -> int:
        """
        Calculate the greatest common divisor of two numbers.
        
        Args:
            a: First number
            b: Second number
            
        Returns:
            Greatest common divisor
        """
        while b:
            a, b = b, a % b
        return a
    
    def _generate_thumbnails(self, file_path: str, metadata: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Generate thumbnails from a video file.
        
        Args:
            file_path: Path to the video file
            metadata: Optional metadata dictionary (to avoid re-extraction)
            
        Returns:
            Path to the primary thumbnail image or None if failed
        """
        # Try using ffmpeg first (faster)
        if self.ffmpeg_available:
            try:
                # Get thumbnail settings
                thumbnail_count = self.get_setting("video_analyzer.thumbnail_count", 3)
                width = self.get_setting("video_analyzer.thumbnail_width", 320)
                height = self.get_setting("video_analyzer.thumbnail_height", 180)
                
                # Get video duration
                duration = metadata.get('duration') if metadata else None
                
                if duration is None:
                    # Extract duration if not provided
                    probe = ffmpeg.probe(file_path)
                    video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
                    if video_stream and 'duration' in video_stream:
                        duration = float(video_stream['duration'])
                    elif 'format' in probe and 'duration' in probe['format']:
                        duration = float(probe['format']['duration'])
                    else:
                        duration = 60  # Default 1 minute if unknown
                
                # Create a temporary directory for the output
                with tempfile.TemporaryDirectory() as temp_dir:
                    # Generate multiple thumbnails at different points in the video
                    thumbnail_paths = []
                    
                    for i in range(thumbnail_count):
                        # Calculate time offset
                        if duration <= 10:  # For very short videos
                            time_offset = duration / 2 if i == 0 else duration * i / (thumbnail_count * 2)
                        else:
                            # Skip intro/credits (10% from start, 10% from end)
                            usable_duration = duration * 0.8
                            start_offset = duration * 0.1
                            time_offset = start_offset + (usable_duration * i / (thumbnail_count - 1 or 1))
                        
                        # Ensure time_offset is not beyond video duration
                        time_offset = min(time_offset, duration - 0.1)
                        time_offset = max(time_offset, 0)
                        
                        output_path = os.path.join(temp_dir, f"thumbnail_{i}.jpg")
                        
                        # Extract frame at the calculated time offset
                        (
                            ffmpeg
                            .input(file_path, ss=time_offset)
                            .filter('scale', width, height)
                            .output(output_path, vframes=1)
                            .overwrite_output()
                            .run(quiet=True)
                        )
                        
                        thumbnail_paths.append(output_path)
                    
                    # Get user's document folder
                    if 'USERPROFILE' in os.environ:
                        docs_folder = os.path.join(os.environ['USERPROFILE'], 'Documents')
                    else:
                        docs_folder = os.path.expanduser("~/Documents")
                    
                    # Create a folder for thumbnail images if it doesn't exist
                    thumbnail_folder = os.path.join(docs_folder, "AI Document Organizer", "thumbnails")
                    os.makedirs(thumbnail_folder, exist_ok=True)
                    
                    # Create a unique filename based on the original file
                    base_name = os.path.splitext(os.path.basename(file_path))[0]
                    
                    # Save the thumbnails
                    saved_paths = []
                    import shutil
                    
                    for i, tmp_path in enumerate(thumbnail_paths):
                        final_path = os.path.join(thumbnail_folder, f"{base_name}_thumbnail_{i}.jpg")
                        
                        # Ensure the filename is unique
                        counter = 1
                        while os.path.exists(final_path):
                            final_path = os.path.join(thumbnail_folder, f"{base_name}_thumbnail_{i}_{counter}.jpg")
                            counter += 1
                        
                        # Copy the temporary file to the final location
                        shutil.copy2(tmp_path, final_path)
                        saved_paths.append(final_path)
                    
                    # Return the path to the main thumbnail (middle one)
                    if saved_paths:
                        main_thumbnail = saved_paths[len(saved_paths) // 2]
                        return main_thumbnail
                    
            except Exception as e:
                logger.warning(f"Error generating thumbnails with ffmpeg: {e}")
        
        # If ffmpeg failed or is not available, try moviepy
        if self.moviepy_available:
            try:
                # Get thumbnail settings
                thumbnail_count = self.get_setting("video_analyzer.thumbnail_count", 3)
                width = self.get_setting("video_analyzer.thumbnail_width", 320)
                height = self.get_setting("video_analyzer.thumbnail_height", 180)
                
                # Open the video file
                with VideoFileClip(file_path) as clip:
                    # Get video duration
                    duration = clip.duration
                    
                    # Create a temporary directory for the output
                    with tempfile.TemporaryDirectory() as temp_dir:
                        # Generate multiple thumbnails at different points in the video
                        thumbnail_paths = []
                        
                        for i in range(thumbnail_count):
                            # Calculate time offset
                            if duration <= 10:  # For very short videos
                                time_offset = duration / 2 if i == 0 else duration * i / (thumbnail_count * 2)
                            else:
                                # Skip intro/credits (10% from start, 10% from end)
                                usable_duration = duration * 0.8
                                start_offset = duration * 0.1
                                time_offset = start_offset + (usable_duration * i / (thumbnail_count - 1 or 1))
                            
                            # Ensure time_offset is not beyond video duration
                            time_offset = min(time_offset, duration - 0.1)
                            time_offset = max(time_offset, 0)
                            
                            output_path = os.path.join(temp_dir, f"thumbnail_{i}.jpg")
                            
                            # Extract frame at the calculated time offset
                            frame = clip.get_frame(time_offset)
                            
                            # Resize the frame
                            from PIL import Image
                            image = Image.fromarray(frame)
                            image = image.resize((width, height), Image.LANCZOS)
                            image.save(output_path)
                            
                            thumbnail_paths.append(output_path)
                        
                        # Get user's document folder
                        if 'USERPROFILE' in os.environ:
                            docs_folder = os.path.join(os.environ['USERPROFILE'], 'Documents')
                        else:
                            docs_folder = os.path.expanduser("~/Documents")
                        
                        # Create a folder for thumbnail images if it doesn't exist
                        thumbnail_folder = os.path.join(docs_folder, "AI Document Organizer", "thumbnails")
                        os.makedirs(thumbnail_folder, exist_ok=True)
                        
                        # Create a unique filename based on the original file
                        base_name = os.path.splitext(os.path.basename(file_path))[0]
                        
                        # Save the thumbnails
                        saved_paths = []
                        import shutil
                        
                        for i, tmp_path in enumerate(thumbnail_paths):
                            final_path = os.path.join(thumbnail_folder, f"{base_name}_thumbnail_{i}.jpg")
                            
                            # Ensure the filename is unique
                            counter = 1
                            while os.path.exists(final_path):
                                final_path = os.path.join(thumbnail_folder, f"{base_name}_thumbnail_{i}_{counter}.jpg")
                                counter += 1
                            
                            # Copy the temporary file to the final location
                            shutil.copy2(tmp_path, final_path)
                            saved_paths.append(final_path)
                        
                        # Return the path to the main thumbnail (middle one)
                        if saved_paths:
                            main_thumbnail = saved_paths[len(saved_paths) // 2]
                            return main_thumbnail
                
            except Exception as e:
                logger.warning(f"Error generating thumbnails with moviepy: {e}")
        
        # If all methods failed
        return None
    
    def _detect_scenes(self, file_path: str, max_duration: Optional[float] = None) -> List[Dict[str, Any]]:
        """
        Detect scene changes in a video file.
        
        Args:
            file_path: Path to the video file
            max_duration: Optional maximum duration to analyze (in seconds)
            
        Returns:
            List of dictionaries containing scene information
        """
        if not self.cv2_available:
            return []
            
        try:
            # Get scene detection settings
            threshold = self.get_setting("video_analyzer.scene_threshold", 30.0)
            min_scene_duration = self.get_setting("video_analyzer.min_scene_duration", 1.0)
            max_frames = self.get_setting("video_analyzer.max_frames", 50)
            
            # Open the video
            cap = cv2.VideoCapture(file_path)
            
            # Check if the video opened successfully
            if not cap.isOpened():
                logger.warning(f"Could not open video file: {file_path}")
                return []
            
            # Get video properties
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = frame_count / fps if fps > 0 else 0
            
            # Apply duration limit if specified
            if max_duration and duration > max_duration:
                frame_count = int(max_duration * fps)
            
            # Calculate frame sampling rate (to avoid processing every frame)
            # For long videos, we process fewer frames for efficiency
            if frame_count > max_frames * 2:
                sampling_rate = frame_count // max_frames
            else:
                sampling_rate = 1
            
            # Initialize variables
            prev_frame = None
            scenes = []
            current_scene_start = 0
            frame_index = 0
            
            # Process frames to detect scene changes
            while frame_index < frame_count:
                # Read frame
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
                ret, frame = cap.read()
                
                if not ret:
                    break
                
                # Convert to grayscale
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                
                # If this is the first frame
                if prev_frame is None:
                    prev_frame = gray
                    frame_index += sampling_rate
                    continue
                
                # Calculate difference between frames
                frame_diff = cv2.absdiff(prev_frame, gray)
                diff_score = frame_diff.mean()
                
                # If difference is above threshold, mark as scene change
                if diff_score > threshold:
                    scene_time = frame_index / fps
                    scene_duration = scene_time - current_scene_start
                    
                    # Only add if scene is long enough
                    if scene_duration >= min_scene_duration:
                        scenes.append({
                            'start_time': current_scene_start,
                            'end_time': scene_time,
                            'duration': scene_duration,
                            'frame_start': frame_index - int(sampling_rate),
                            'diff_score': diff_score
                        })
                        current_scene_start = scene_time
                
                # Update previous frame
                prev_frame = gray
                frame_index += sampling_rate
            
            # Add the final scene
            final_time = min(frame_count / fps, duration)
            if final_time > current_scene_start:
                scenes.append({
                    'start_time': current_scene_start,
                    'end_time': final_time,
                    'duration': final_time - current_scene_start,
                    'frame_start': frame_index - sampling_rate,
                    'diff_score': 0  # Unknown for the last scene
                })
            
            # Release the video capture
            cap.release()
            
            return scenes
            
        except Exception as e:
            logger.error(f"Error in scene detection: {e}")
            return []
    
    def _extract_audio(self, file_path: str) -> Optional[str]:
        """
        Extract audio track from a video file.
        
        Args:
            file_path: Path to the video file
            
        Returns:
            Path to the extracted audio file or None if failed
        """
        if not self.moviepy_available and not self.ffmpeg_available:
            return None
            
        try:
            # Get user's document folder
            if 'USERPROFILE' in os.environ:
                docs_folder = os.path.join(os.environ['USERPROFILE'], 'Documents')
            else:
                docs_folder = os.path.expanduser("~/Documents")
            
            # Create a folder for extracted audio files if it doesn't exist
            audio_folder = os.path.join(docs_folder, "AI Document Organizer", "extracted_audio")
            os.makedirs(audio_folder, exist_ok=True)
            
            # Create a unique filename based on the original file
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            output_path = os.path.join(audio_folder, f"{base_name}_audio.wav")
            
            # Ensure the filename is unique
            counter = 1
            while os.path.exists(output_path):
                output_path = os.path.join(audio_folder, f"{base_name}_audio_{counter}.wav")
                counter += 1
            
            # Try using moviepy first
            if self.moviepy_available:
                try:
                    # Extract audio using moviepy
                    with VideoFileClip(file_path) as video:
                        if video.audio is not None:
                            video.audio.write_audiofile(output_path, logger=None)
                            return output_path
                        else:
                            logger.warning(f"No audio track found in video: {file_path}")
                            return None
                            
                except Exception as e:
                    logger.warning(f"Error extracting audio with moviepy: {e}")
            
            # If moviepy failed or is not available, try ffmpeg
            if self.ffmpeg_available:
                try:
                    # Extract audio using ffmpeg
                    (
                        ffmpeg
                        .input(file_path)
                        .output(output_path, acodec='pcm_s16le')
                        .overwrite_output()
                        .run(quiet=True)
                    )
                    
                    # Check if the file was created
                    if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                        return output_path
                    else:
                        logger.warning(f"Failed to extract audio with ffmpeg: {file_path}")
                        return None
                        
                except Exception as e:
                    logger.warning(f"Error extracting audio with ffmpeg: {e}")
            
            # If all methods failed
            return None
            
        except Exception as e:
            logger.error(f"Error extracting audio: {e}")
            return None