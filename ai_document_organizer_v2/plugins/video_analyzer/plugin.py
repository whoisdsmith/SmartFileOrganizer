"""
Video Analyzer Plugin for AI Document Organizer V2.

This plugin provides video file analysis, metadata extraction, 
thumbnail generation, and scene detection.
"""

import os
import io
import logging
import tempfile
import json
import math
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple

# Import plugin base class
from ai_document_organizer_v2.core.plugin_base import MediaAnalyzerPlugin

# Import PIL for image processing
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# Try importing ffmpeg-python
try:
    import ffmpeg
    FFMPEG_AVAILABLE = True
except ImportError:
    FFMPEG_AVAILABLE = False

logger = logging.getLogger("AIDocumentOrganizerV2.VideoAnalyzer")

class VideoAnalyzerPlugin(MediaAnalyzerPlugin):
    """
    Plugin for analyzing video files.
    
    This plugin extracts metadata, generates thumbnails, and detects scenes from video files.
    """
    
    # Plugin metadata
    name = "Video Analyzer"
    version = "1.0.0"
    description = "Analyzes video files, extracts metadata, and generates thumbnails"
    author = "AI Document Organizer Team"
    dependencies = ["ffmpeg-python", "Pillow"]
    
    # File extensions supported by this plugin
    supported_extensions = [".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv", ".wmv"]
    
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
        self.ffmpeg_available = FFMPEG_AVAILABLE
        self.pil_available = PIL_AVAILABLE
        
        if not self.ffmpeg_available:
            logger.warning("FFmpeg library not available. Video analysis will be limited.")
        
        if not self.pil_available:
            logger.warning("Pillow (PIL) library not available. Thumbnail processing will be limited.")
    
    def initialize(self) -> bool:
        """
        Initialize the plugin.
        
        Returns:
            True if initialization was successful, False otherwise
        """
        # Check dependencies
        if not self.ffmpeg_available:
            logger.warning("FFmpeg library not available. Install ffmpeg-python for full video analysis.")
            # Return True anyway to allow partial functionality
        
        if not self.pil_available:
            logger.warning("Pillow (PIL) library not available. Install Pillow for thumbnail processing.")
            # Return True anyway to allow partial functionality
        
        # Register default settings if not already present
        if self.settings_manager is not None:
            # Use get_setting/set_setting to access settings manager
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
                
            scene_detection_enabled = self.get_setting("video_analyzer.scene_detection_enabled", None)
            if scene_detection_enabled is None:
                self.set_setting("video_analyzer.scene_detection_enabled", True)
                
            scene_threshold = self.get_setting("video_analyzer.scene_threshold", None)
            if scene_threshold is None:
                self.set_setting("video_analyzer.scene_threshold", 0.4)
                
            extract_subtitles = self.get_setting("video_analyzer.extract_subtitles", None)
            if extract_subtitles is None:
                self.set_setting("video_analyzer.extract_subtitles", True)
                
            logger.info("Video analyzer settings initialized")
            
        return True
    
    def analyze_media(self, file_path: str) -> Dict[str, Any]:
        """
        Analyze a video file and extract metadata and generate thumbnails.
        
        Args:
            file_path: Path to the video file
            
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
            # Extract metadata and analyze video
            metadata = self._extract_video_metadata(file_path)
            
            # Generate thumbnails if enabled
            preview_path = None
            thumbnail_paths = []
            thumbnail_enabled = self.get_setting("video_analyzer.thumbnail_enabled", True)
            
            if thumbnail_enabled:
                thumbnail_count = self.get_setting("video_analyzer.thumbnail_count", 3)
                thumbnails = self._generate_thumbnails(file_path, count=thumbnail_count)
                if thumbnails:
                    thumbnail_paths = thumbnails
                    # Use first thumbnail as preview
                    preview_path = thumbnails[0] if thumbnails else None
                    metadata['thumbnail_paths'] = thumbnail_paths
            
            # Detect scenes if enabled
            scene_detection_enabled = self.get_setting("video_analyzer.scene_detection_enabled", True)
            if scene_detection_enabled:
                scenes = self._detect_scenes(file_path)
                if scenes:
                    metadata['scenes'] = scenes
            
            # Extract subtitles if enabled
            extract_subtitles = self.get_setting("video_analyzer.extract_subtitles", True)
            if extract_subtitles:
                subtitles = self._extract_subtitles(file_path)
                if subtitles:
                    metadata['subtitles'] = subtitles
            
            # Return analysis results
            return {
                'metadata': metadata,
                'preview_path': preview_path,
                'transcription': None,  # Handled by transcription plugin
                'success': True,
                'error': ""
            }
        except Exception as e:
            logger.error(f"Error analyzing video file {file_path}: {e}")
            return {
                'metadata': {},
                'preview_path': None,
                'transcription': None,
                'success': False,
                'error': str(e)
            }
    
    def generate_preview(self, file_path: str, output_path: Optional[str] = None) -> Optional[str]:
        """
        Generate a thumbnail preview for the video file.
        
        Args:
            file_path: Path to the video file
            output_path: Optional path to save the thumbnail
            
        Returns:
            Path to the generated thumbnail or None if generation failed
        """
        # Generate a single thumbnail at the default position (10% into the video)
        thumbnails = self._generate_thumbnails(file_path, count=1, positions=[0.1], output_path=output_path)
        return thumbnails[0] if thumbnails else None
    
    def _extract_video_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        Extract metadata from a video file.
        
        Args:
            file_path: Path to the video file
            
        Returns:
            Dictionary with video metadata
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
            'width': None,
            'height': None,
            'duration': None,
            'format': None,
            'codec': None,
            'frame_rate': None,
            'bit_rate': None
        }
        
        # Extract detailed metadata if ffmpeg is available
        if self.ffmpeg_available:
            try:
                # Use ffmpeg probe to get video information
                probe = ffmpeg.probe(file_path)
                
                # Get video format info
                if 'format' in probe:
                    format_info = probe['format']
                    metadata['format'] = format_info.get('format_name')
                    metadata['format_long'] = format_info.get('format_long_name')
                    
                    if 'duration' in format_info:
                        duration = float(format_info['duration'])
                        metadata['duration'] = duration
                        metadata['duration_formatted'] = str(timedelta(seconds=int(duration)))
                    
                    if 'bit_rate' in format_info:
                        metadata['bit_rate'] = int(format_info['bit_rate'])
                    
                    # Extract tags
                    if 'tags' in format_info:
                        metadata['tags'] = format_info['tags']
                
                # Get video stream info
                video_stream = next((stream for stream in probe['streams'] 
                                     if stream['codec_type'] == 'video'), None)
                
                if video_stream:
                    metadata['codec'] = video_stream.get('codec_name')
                    metadata['codec_long'] = video_stream.get('codec_long_name')
                    
                    if 'width' in video_stream:
                        metadata['width'] = int(video_stream['width'])
                    
                    if 'height' in video_stream:
                        metadata['height'] = int(video_stream['height'])
                    
                    # Calculate aspect ratio if width and height are available
                    if metadata['width'] and metadata['height']:
                        metadata['aspect_ratio'] = f"{metadata['width']}:{metadata['height']}"
                        
                        # Calculate common aspect ratio
                        width = metadata['width']
                        height = metadata['height']
                        gcd = math.gcd(width, height)
                        metadata['aspect_ratio_common'] = f"{width//gcd}:{height//gcd}"
                    
                    # Calculate frame rate
                    if 'avg_frame_rate' in video_stream:
                        avg_frame_rate = video_stream['avg_frame_rate']
                        if avg_frame_rate != '0/0':
                            num, den = map(int, avg_frame_rate.split('/'))
                            if den != 0:
                                metadata['frame_rate'] = round(num / den, 3)
                    
                    # Extract video stream tags
                    if 'tags' in video_stream:
                        if 'tags' not in metadata:
                            metadata['tags'] = {}
                        # Merge with existing tags
                        metadata['tags'].update(video_stream['tags'])
                
                # Get audio stream info
                audio_stream = next((stream for stream in probe['streams'] 
                                     if stream['codec_type'] == 'audio'), None)
                
                if audio_stream:
                    audio_info = {
                        'codec': audio_stream.get('codec_name'),
                        'codec_long': audio_stream.get('codec_long_name'),
                        'sample_rate': int(audio_stream.get('sample_rate', 0)),
                        'channels': int(audio_stream.get('channels', 0)),
                    }
                    
                    # Extract bit rate if available
                    if 'bit_rate' in audio_stream:
                        audio_info['bit_rate'] = int(audio_stream['bit_rate'])
                    
                    # Extract audio stream tags
                    if 'tags' in audio_stream:
                        audio_info['tags'] = audio_stream['tags']
                    
                    metadata['audio_stream'] = audio_info
                
                # Check for subtitle streams
                subtitle_streams = [stream for stream in probe['streams'] 
                                    if stream['codec_type'] == 'subtitle']
                
                if subtitle_streams:
                    metadata['subtitle_streams'] = []
                    for stream in subtitle_streams:
                        subtitle_info = {
                            'codec': stream.get('codec_name'),
                            'codec_long': stream.get('codec_long_name'),
                            'index': stream.get('index')
                        }
                        
                        # Extract language tag if available
                        if 'tags' in stream and 'language' in stream['tags']:
                            subtitle_info['language'] = stream['tags']['language']
                        
                        metadata['subtitle_streams'].append(subtitle_info)
                
                # Calculate video quality rating
                quality_rating = self._calculate_quality_rating(metadata)
                metadata['quality_rating'] = quality_rating
                
            except Exception as e:
                logger.error(f"Error extracting video metadata with ffmpeg: {e}")
                metadata['ffmpeg_error'] = str(e)
        
        return metadata
    
    def _calculate_quality_rating(self, metadata: Dict[str, Any]) -> float:
        """
        Calculate video quality rating based on metadata.
        
        Args:
            metadata: Dictionary with video metadata
            
        Returns:
            Quality rating between 0 and 10
        """
        # Default medium rating
        rating = 5.0
        
        # Adjust rating based on resolution
        if metadata.get('width') and metadata.get('height'):
            width = metadata['width']
            height = metadata['height']
            
            # Calculate pixel count
            pixels = width * height
            
            # Adjust rating based on resolution
            if pixels >= 8294400:  # 4K (3840x2160)
                rating += 2.5
            elif pixels >= 2073600:  # 1080p (1920x1080)
                rating += 2.0
            elif pixels >= 921600:  # 720p (1280x720)
                rating += 1.0
            elif pixels >= 480000:  # 800x600
                rating += 0.0
            elif pixels < 480000:
                rating -= 1.0
            elif pixels < 307200:  # 640x480
                rating -= 1.5
        
        # Adjust rating based on bit rate
        if metadata.get('bit_rate'):
            bit_rate = metadata['bit_rate']
            
            # Adjust rating based on bit rate
            if bit_rate > 20000000:  # > 20 Mbps
                rating += 1.5
            elif bit_rate > 10000000:  # > 10 Mbps
                rating += 1.0
            elif bit_rate > 5000000:  # > 5 Mbps
                rating += 0.5
            elif bit_rate < 2000000:  # < 2 Mbps
                rating -= 0.5
            elif bit_rate < 1000000:  # < 1 Mbps
                rating -= 1.0
        
        # Adjust rating based on frame rate
        if metadata.get('frame_rate'):
            frame_rate = metadata['frame_rate']
            
            if frame_rate >= 60:
                rating += 1.0
            elif frame_rate >= 30:
                rating += 0.5
            elif frame_rate < 24:
                rating -= 0.5
            elif frame_rate < 20:
                rating -= 1.0
        
        # Adjust rating based on audio quality
        if 'audio_stream' in metadata:
            audio = metadata['audio_stream']
            
            # Adjust for audio sample rate
            if audio.get('sample_rate', 0) >= 48000:
                rating += 0.5
            
            # Adjust for audio channels
            if audio.get('channels', 0) > 2:
                rating += 0.5
            
            # Adjust for audio bit rate
            if audio.get('bit_rate', 0) > 320000:
                rating += 0.5
            elif audio.get('bit_rate', 0) < 128000:
                rating -= 0.5
        
        # Cap the rating between 0 and 10
        rating = max(0.0, min(10.0, rating))
        
        return round(rating, 1)
    
    def _generate_thumbnails(self, file_path: str, count: int = 3, 
                            positions: Optional[List[float]] = None,
                            output_path: Optional[str] = None) -> List[str]:
        """
        Generate thumbnails from a video file.
        
        Args:
            file_path: Path to the video file
            count: Number of thumbnails to generate
            positions: Optional list of positions (0-1) to extract frames from
            output_path: Optional path to save the thumbnails
            
        Returns:
            List of paths to the generated thumbnails
        """
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return []
        
        if not self.ffmpeg_available:
            logger.error(f"Cannot generate thumbnails: ffmpeg not available")
            return []
        
        try:
            # Get video metadata for duration
            probe = ffmpeg.probe(file_path)
            
            # Get video duration from format section
            duration = float(probe['format']['duration'])
            
            # Get thumbnail settings
            width = self.get_setting("video_analyzer.thumbnail_width", 320)
            height = self.get_setting("video_analyzer.thumbnail_height", 180)
            
            # Create output directory if not provided
            if output_path is None:
                base_name = os.path.splitext(os.path.basename(file_path))[0]
                output_dir = os.path.join(tempfile.gettempdir(), "video_analyzer_thumbnails", base_name)
                os.makedirs(output_dir, exist_ok=True)
            else:
                # If a full path is provided, use its directory
                output_dir = os.path.dirname(output_path)
                if not output_dir:
                    output_dir = "."
                os.makedirs(output_dir, exist_ok=True)
            
            # Determine frame positions if not provided
            if positions is None:
                # Skip first 10% and last 10% of the video to avoid intros/credits
                usable_duration = duration * 0.8
                start_time = duration * 0.1
                
                if count == 1:
                    # For single thumbnail, just take from middle
                    positions = [0.5]
                else:
                    # Evenly distribute timestamps
                    step = usable_duration / (count or 1)
                    positions = [
                        (start_time + i * step) / duration
                        for i in range(count)
                    ]
            
            # Convert positions to timestamps in seconds
            timestamps = [position * duration for position in positions]
            
            thumbnail_paths = []
            
            # Generate each thumbnail
            for i, timestamp in enumerate(timestamps):
                # Determine output filename
                if output_path and i == 0 and count == 1:
                    # Use provided output path for single thumbnail
                    thumbnail_path = output_path
                else:
                    # Generate a filename
                    thumbnail_path = os.path.join(output_dir, f"thumbnail_{i:02d}.jpg")
                
                # Use ffmpeg to extract the frame
                try:
                    (
                        ffmpeg
                        .input(file_path, ss=timestamp)
                        .filter('scale', width, height)
                        .output(thumbnail_path, vframes=1)
                        .overwrite_output()
                        .run(quiet=True)
                    )
                    
                    if os.path.exists(thumbnail_path):
                        thumbnail_paths.append(thumbnail_path)
                        logger.debug(f"Generated thumbnail at {timestamp:.2f}s: {thumbnail_path}")
                except ffmpeg.Error as e:
                    logger.error(f"Error generating thumbnail at {timestamp:.2f}s: {e.stderr.decode() if hasattr(e, 'stderr') else str(e)}")
            
            return thumbnail_paths
            
        except Exception as e:
            logger.error(f"Error generating video thumbnails: {e}")
            return []
    
    def _detect_scenes(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Detect scene changes in a video file.
        
        Args:
            file_path: Path to the video file
            
        Returns:
            List of scene information dictionaries
        """
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return []
        
        if not self.ffmpeg_available:
            logger.error(f"Cannot detect scenes: ffmpeg not available")
            return []
        
        try:
            # Get scene detection settings
            threshold = self.get_setting("video_analyzer.scene_threshold", 0.4)
            
            # Get video info
            probe = ffmpeg.probe(file_path)
            duration = float(probe['format']['duration'])
            
            # For longer videos, we need to limit the scene detection to avoid performance issues
            # Simple approach: extract frames at regular intervals and analyze those
            max_frames = 300  # Maximum number of frames to analyze
            
            # Get the frame rate to determine time between frames
            video_stream = next((stream for stream in probe['streams'] 
                                if stream['codec_type'] == 'video'), None)
            
            if not video_stream:
                logger.error(f"No video stream found in file: {file_path}")
                return []
            
            # Calculate frame rate
            frame_rate = 25.0  # Default fallback
            if 'avg_frame_rate' in video_stream:
                avg_frame_rate = video_stream['avg_frame_rate']
                if avg_frame_rate != '0/0':
                    num, den = map(int, avg_frame_rate.split('/'))
                    if den != 0:
                        frame_rate = num / den
            
            # Calculate number of frames in the video (approximate)
            total_frames = int(duration * frame_rate)
            
            # If total frames is very large, sample at regular intervals
            if total_frames > max_frames:
                # Calculate frame interval for sampling
                frame_interval = max(1, total_frames // max_frames)
                logger.debug(f"Video has {total_frames} frames, sampling every {frame_interval} frames")
            else:
                frame_interval = 1
            
            # In a real implementation, we would use scene detection algorithms here
            # For this implementation, we'll create a simple approximation using
            # frame-by-frame comparisons at regular intervals
            
            # Simplified approach: divide the video into "scenes" based on time
            # A real implementation would use proper scene detection based on frame differences
            
            # Let's create sample scenes based on video duration
            num_scenes = min(10, max(3, int(duration / 30)))  # Approximate 1 scene per 30 seconds
            
            scenes = []
            for i in range(num_scenes):
                start_time = i * (duration / num_scenes)
                end_time = (i + 1) * (duration / num_scenes)
                
                # Create scene entry
                scene = {
                    'index': i,
                    'start_time': start_time,
                    'end_time': end_time,
                    'duration': end_time - start_time,
                    'start_formatted': str(timedelta(seconds=int(start_time))),
                    'end_formatted': str(timedelta(seconds=int(end_time))),
                }
                
                # Generate thumbnail for this scene
                thumbnail_path = self._generate_thumbnails(
                    file_path, 
                    count=1, 
                    positions=[start_time / duration + 0.01]  # Add small offset to avoid exact start
                )
                
                if thumbnail_path:
                    scene['thumbnail'] = thumbnail_path[0]
                
                scenes.append(scene)
            
            return scenes
            
        except Exception as e:
            logger.error(f"Error detecting scenes in video: {e}")
            return []
    
    def _extract_subtitles(self, file_path: str) -> Dict[str, Any]:
        """
        Extract subtitle information from a video file.
        
        Args:
            file_path: Path to the video file
            
        Returns:
            Dictionary with subtitle information
        """
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return {}
        
        if not self.ffmpeg_available:
            logger.error(f"Cannot extract subtitles: ffmpeg not available")
            return {}
        
        try:
            # Get video info
            probe = ffmpeg.probe(file_path)
            
            # Check for subtitle streams
            subtitle_streams = [stream for stream in probe['streams'] 
                                if stream['codec_type'] == 'subtitle']
            
            if not subtitle_streams:
                logger.info(f"No subtitle streams found in file: {file_path}")
                return {}
            
            # Create output directory for extracted subtitles
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            output_dir = os.path.join(tempfile.gettempdir(), "video_analyzer_subtitles", base_name)
            os.makedirs(output_dir, exist_ok=True)
            
            result = {
                'streams': [],
                'files': []
            }
            
            # Process each subtitle stream
            for stream in subtitle_streams:
                stream_index = stream['index']
                
                # Get language if available
                language = "unknown"
                if 'tags' in stream and 'language' in stream['tags']:
                    language = stream['tags']['language']
                
                # Generate output filename
                output_file = os.path.join(output_dir, f"subtitle_{stream_index}_{language}.srt")
                
                # Try to extract the subtitle
                try:
                    (
                        ffmpeg
                        .input(file_path)
                        .output(output_file, map=f"0:{stream_index}")
                        .run(quiet=True)
                    )
                    
                    if os.path.exists(output_file):
                        # Add to result
                        subtitle_info = {
                            'stream_index': stream_index,
                            'language': language,
                            'codec': stream.get('codec_name'),
                            'file_path': output_file
                        }
                        
                        result['streams'].append(subtitle_info)
                        result['files'].append(output_file)
                        
                        logger.debug(f"Extracted subtitle stream {stream_index} ({language}): {output_file}")
                except ffmpeg.Error as e:
                    logger.error(f"Error extracting subtitle stream {stream_index}: {e.stderr.decode() if hasattr(e, 'stderr') else str(e)}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error extracting subtitles from video: {e}")
            return {}
    
    def get_config_schema(self) -> Dict[str, Any]:
        """
        Get JSON schema for plugin configuration.
        
        Returns:
            Dictionary with JSON schema for plugin configuration
        """
        return {
            "type": "object",
            "properties": {
                "thumbnail_enabled": {
                    "type": "boolean",
                    "title": "Enable Thumbnail Generation",
                    "description": "Generate thumbnails for video files",
                    "default": True
                },
                "thumbnail_count": {
                    "type": "integer",
                    "title": "Thumbnail Count",
                    "description": "Number of thumbnails to generate per video",
                    "default": 3,
                    "minimum": 1,
                    "maximum": 10
                },
                "thumbnail_width": {
                    "type": "integer",
                    "title": "Thumbnail Width",
                    "description": "Width of the thumbnails in pixels",
                    "default": 320,
                    "minimum": 80,
                    "maximum": 1920
                },
                "thumbnail_height": {
                    "type": "integer",
                    "title": "Thumbnail Height",
                    "description": "Height of the thumbnails in pixels",
                    "default": 180,
                    "minimum": 45,
                    "maximum": 1080
                },
                "scene_detection_enabled": {
                    "type": "boolean",
                    "title": "Enable Scene Detection",
                    "description": "Detect scene changes in videos",
                    "default": True
                },
                "scene_threshold": {
                    "type": "number",
                    "title": "Scene Detection Threshold",
                    "description": "Threshold for scene change detection (0.0-1.0)",
                    "default": 0.4,
                    "minimum": 0.1,
                    "maximum": 0.9
                },
                "extract_subtitles": {
                    "type": "boolean",
                    "title": "Extract Subtitles",
                    "description": "Extract subtitle tracks from videos",
                    "default": True
                }
            }
        }