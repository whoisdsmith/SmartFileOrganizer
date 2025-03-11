"""
Optimized Transcription Service Plugin for AI Document Organizer V2.

This enhanced version includes:
- Result caching to avoid redundant processing
- Progress reporting for long-running operations
- Support for multiple transcription providers
- Language detection and support for multiple languages
- Optimization for different file types and durations
"""

import os
import io
import time
import logging
import tempfile
import threading
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Callable

# Import plugin base class
from ai_document_organizer_v2.core.plugin_base import MediaProcessorPlugin

# Import cache manager
from ai_document_organizer_v2.plugins.transcription_service.cache_manager import TranscriptionCache

# System monitoring
import psutil

# Try importing required libraries
try:
    import ffmpeg
    FFMPEG_AVAILABLE = True
except ImportError:
    FFMPEG_AVAILABLE = False

# Try importing whisper for advanced transcription
try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False

# Try importing pydub for audio processing
try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False

# Try importing speech recognition
try:
    import speech_recognition as sr
    SR_AVAILABLE = True
except ImportError:
    SR_AVAILABLE = False

logger = logging.getLogger("AIDocumentOrganizerV2.TranscriptionService")

class TranscriptionServicePlugin(MediaProcessorPlugin):
    """
    Enhanced plugin for transcribing audio and video files with performance optimizations.
    
    This plugin provides transcription services with multiple providers,
    caching support, and progress reporting.
    """
    
    # Plugin metadata
    name = "Transcription Service"
    version = "1.1.0"
    description = "Transcribes audio and video files with optimized performance and caching support"
    author = "AI Document Organizer Team"
    dependencies = ["ffmpeg-python", "pydub", "SpeechRecognition", "whisper"]
    
    # File extensions supported by this plugin
    supported_extensions = [
        # Audio formats
        ".mp3", ".wav", ".flac", ".ogg", ".aac", ".m4a",
        # Video formats
        ".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv", ".webm"
    ]
    
    def __init__(self, plugin_id: str, name: Optional[str] = None, version: Optional[str] = None,
                 description: Optional[str] = None):
        """
        Initialize the transcription service plugin.
        
        Args:
            plugin_id: Unique identifier for the plugin
            name: Plugin name (if None, uses class attribute)
            version: Plugin version (if None, uses class attribute)
            description: Plugin description (if None, uses class attribute)
        """
        super().__init__(plugin_id, name, version, description)
        
        # Check if required libraries are available
        self.ffmpeg_available = FFMPEG_AVAILABLE
        self.whisper_available = WHISPER_AVAILABLE
        self.pydub_available = PYDUB_AVAILABLE
        self.sr_available = SR_AVAILABLE
        
        if not self.ffmpeg_available:
            logger.warning("FFmpeg library not available. Audio conversion will be limited.")
            
        if not self.whisper_available:
            logger.warning("Whisper library not available. Advanced transcription will be disabled.")
            
        if not self.pydub_available:
            logger.warning("Pydub library not available. Audio processing will be limited.")
            
        if not self.sr_available:
            logger.warning("SpeechRecognition library not available. Basic transcription will be disabled.")
            
        # Initialize cache
        self.cache = TranscriptionCache()
        
        # Initialize whisper model (if available)
        self.whisper_model = None
        
        # Progress tracking variables
        self.progress_callback = None
        self.progress_thread = None
        self.progress_abort = threading.Event()
        self.current_operation = None
        
    def initialize(self) -> bool:
        """
        Initialize the plugin.
        
        Returns:
            True if initialization was successful, False otherwise
        """
        # Check dependencies
        if not self.ffmpeg_available:
            logger.warning("FFmpeg library not available. Install ffmpeg-python for audio conversion.")
            # Return True anyway to allow partial functionality
            
        if not self.whisper_available and not self.sr_available:
            logger.warning("Neither Whisper nor SpeechRecognition library is available. Transcription will be disabled.")
            # Return True anyway to allow partial functionality
        
        # Register default settings if not already present
        if self.settings_manager is not None:
            # Cache settings
            cache_enabled = self.get_setting("transcription.cache_enabled", None)
            if cache_enabled is None:
                self.set_setting("transcription.cache_enabled", True)
                
            # Provider settings
            default_provider = self.get_setting("transcription.default_provider", None)
            if default_provider is None:
                if self.whisper_available:
                    default_provider = "whisper"
                elif self.sr_available:
                    default_provider = "google"
                else:
                    default_provider = "mock"
                self.set_setting("transcription.default_provider", default_provider)
            
            # Language settings
            default_language = self.get_setting("transcription.default_language", None)
            if default_language is None:
                self.set_setting("transcription.default_language", "en-US")
                
            # Whisper model settings (if whisper is available)
            if self.whisper_available:
                whisper_model = self.get_setting("transcription.whisper_model", None)
                if whisper_model is None:
                    self.set_setting("transcription.whisper_model", "base")
                    
                auto_language_detection = self.get_setting("transcription.auto_language_detection", None)
                if auto_language_detection is None:
                    self.set_setting("transcription.auto_language_detection", True)
            
            # Audio conversion settings
            max_audio_length = self.get_setting("transcription.max_audio_length", None)
            if max_audio_length is None:
                self.set_setting("transcription.max_audio_length", 600)  # 10 minutes
                
            segment_long_audio = self.get_setting("transcription.segment_long_audio", None)
            if segment_long_audio is None:
                self.set_setting("transcription.segment_long_audio", True)
                
            segment_length = self.get_setting("transcription.segment_length", None)
            if segment_length is None:
                self.set_setting("transcription.segment_length", 60)  # 1 minute
            
            # Output format settings
            output_format = self.get_setting("transcription.output_format", None)
            if output_format is None:
                self.set_setting("transcription.output_format", "text")  # text, srt, vtt, json
                
            include_timestamps = self.get_setting("transcription.include_timestamps", None)
            if include_timestamps is None:
                self.set_setting("transcription.include_timestamps", True)
                
            # Confidence settings
            min_confidence = self.get_setting("transcription.min_confidence", None)
            if min_confidence is None:
                self.set_setting("transcription.min_confidence", 0.6)  # 0.0 to 1.0
                
            logger.info("Transcription service settings initialized")
            
            # Initialize whisper model if enabled
            if self.whisper_available:
                try:
                    whisper_model = self.get_setting("transcription.whisper_model", "base")
                    self.current_operation = "loading whisper model"
                    
                    # Lazy loading - we'll load the model on first use
                    self.whisper_model = None
                    logger.info(f"Whisper model '{whisper_model}' will be loaded on first use")
                    
                except Exception as e:
                    logger.warning(f"Error initializing Whisper model: {e}")
        
        # Update dependencies list based on available libraries
        dependencies = []
        if self.ffmpeg_available:
            dependencies.append("ffmpeg-python")
        if self.pydub_available:
            dependencies.append("pydub")
        if self.sr_available:
            dependencies.append("SpeechRecognition")
        if self.whisper_available:
            dependencies.append("whisper")
            
        # Update plugin description to reflect capabilities
        description = "Transcribes audio and video files"
        if self.whisper_available:
            description += " with advanced AI-powered transcription"
        elif self.sr_available:
            description += " with cloud-based transcription services"
            
        # Update plugin info
        self.dependencies = dependencies
        self.description = description
            
        return True
    
    def transcribe(self, audio_path: str, provider: Optional[str] = None, 
                 language: Optional[str] = None, callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        Transcribe an audio file using the specified provider.
        
        Args:
            audio_path: Path to the audio file
            provider: Optional transcription provider to use
            language: Optional language code (e.g., 'en-US')
            callback: Optional progress callback function
            
        Returns:
            Dictionary containing transcription results
        """
        # Set the progress callback
        self.progress_callback = callback
        
        if not os.path.exists(audio_path):
            return {
                'text': "",
                'segments': [],
                'language': None,
                'success': False,
                'error': f"File not found: {audio_path}"
            }
        
        # Extract file extension
        _, file_ext = os.path.splitext(audio_path)
        file_ext = file_ext.lower()
        
        if file_ext not in [ext.lower() for ext in self.supported_extensions]:
            return {
                'text': "",
                'segments': [],
                'language': None,
                'success': False,
                'error': f"Unsupported file extension: {file_ext}"
            }
        
        try:
            # Get default provider if not specified
            if provider is None:
                provider = self.get_setting("transcription.default_provider", "whisper" if self.whisper_available else "google")
            
            # Get default language if not specified
            if language is None:
                language = self.get_setting("transcription.default_language", "en-US")
            
            # Check if cache is enabled
            cache_enabled = self.get_setting("transcription.cache_enabled", True)
            
            # Try to get cached results if caching is enabled
            if cache_enabled:
                cached_results = self.cache.get(audio_path, provider, language)
                if cached_results:
                    logger.info(f"Using cached transcription results for: {audio_path}")
                    if self.progress_callback:
                        self.progress_callback(100, 100, "Retrieved cached results")
                    return cached_results
            
            # Start progress reporting
            self._start_progress_reporting(audio_path)
            
            # Check if the file is a video file
            is_video = file_ext in [".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv", ".webm"]
            
            # Extract audio from video if necessary
            audio_file_path = audio_path
            temp_audio = None
            
            if is_video:
                self.current_operation = "extracting audio"
                audio_file_path = self._extract_audio_from_video(audio_path)
                if not audio_file_path:
                    self._stop_progress_reporting()
                    return {
                        'text': "",
                        'segments': [],
                        'language': None,
                        'success': False,
                        'error': f"Failed to extract audio from video: {audio_path}"
                    }
                temp_audio = audio_file_path
            
            # Process audio
            self.current_operation = "transcribing"
            
            # Check for auto language detection
            auto_language_detection = self.get_setting("transcription.auto_language_detection", True)
            detected_language = None
            
            if auto_language_detection and provider == "whisper" and self.whisper_available:
                # Whisper will auto-detect language
                pass
                
            # Perform transcription based on provider
            if provider == "whisper" and self.whisper_available:
                transcription = self._transcribe_with_whisper(audio_file_path, language)
            elif provider == "google" and self.sr_available:
                transcription = self._transcribe_with_google(audio_file_path, language)
            elif provider == "azure" and self.sr_available:
                transcription = self._transcribe_with_azure(audio_file_path, language)
            elif provider == "mock":
                transcription = self._transcribe_with_mock(audio_file_path, language)
            else:
                transcription = {
                    'text': "",
                    'segments': [],
                    'language': language,
                    'success': False,
                    'error': f"Unsupported provider: {provider}"
                }
            
            # Clean up temporary audio file
            if temp_audio and os.path.exists(temp_audio):
                try:
                    os.remove(temp_audio)
                except Exception as e:
                    logger.warning(f"Failed to remove temporary audio file: {e}")
            
            # Stop progress reporting
            self._stop_progress_reporting()
            
            # Format the transcription according to the requested output format
            output_format = self.get_setting("transcription.output_format", "text")
            include_timestamps = self.get_setting("transcription.include_timestamps", True)
            
            if output_format == "srt":
                transcription['formatted_output'] = self._format_as_srt(transcription['segments'])
            elif output_format == "vtt":
                transcription['formatted_output'] = self._format_as_vtt(transcription['segments'])
            elif output_format == "json":
                transcription['formatted_output'] = json.dumps(transcription, ensure_ascii=False, indent=2)
            else:  # Default to text
                if include_timestamps and transcription['segments']:
                    lines = []
                    for segment in transcription['segments']:
                        start_time = segment.get('start', 0)
                        start_formatted = self._format_timestamp(start_time)
                        lines.append(f"[{start_formatted}] {segment.get('text', '')}")
                    transcription['formatted_output'] = "\n".join(lines)
                else:
                    transcription['formatted_output'] = transcription['text']
            
            # Mark as successful if we have text
            if transcription['text']:
                transcription['success'] = True
                transcription['error'] = ""
            
            # Cache the results if caching is enabled and transcription was successful
            if cache_enabled and transcription.get('success', False):
                self.cache.put(audio_path, transcription, provider, language)
            
            return transcription
            
        except Exception as e:
            # Stop progress reporting
            self._stop_progress_reporting()
            
            logger.error(f"Error transcribing audio file {audio_path}: {e}")
            return {
                'text': "",
                'segments': [],
                'language': language,
                'success': False,
                'error': str(e)
            }
    
    def process_media(self, file_path: str, callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        Process a media file to extract transcription.
        
        Args:
            file_path: Path to the media file
            callback: Optional progress callback function
            
        Returns:
            Dictionary containing processing results
        """
        # This is a wrapper around transcribe to comply with the MediaProcessorPlugin interface
        return self.transcribe(file_path, callback=callback)
        
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
        stages = ["extracting audio", "transcribing", "loading whisper model"]
        
        # Estimate stage weights (time proportions)
        weights = {
            "extracting audio": 10,
            "transcribing": 85,
            "loading whisper model": 5
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
            
    def _extract_audio_from_video(self, video_path: str) -> Optional[str]:
        """
        Extract audio track from a video file.
        
        Args:
            video_path: Path to the video file
            
        Returns:
            Path to the extracted audio file or None if failed
        """
        if not self.ffmpeg_available:
            return None
            
        try:
            # Create a temporary file for the extracted audio
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_path = temp_file.name
                
            # Extract audio using ffmpeg
            (
                ffmpeg
                .input(video_path)
                .output(temp_path, acodec='pcm_s16le', ar=16000, ac=1)
                .overwrite_output()
                .run(quiet=True)
            )
            
            # Check if the file was created successfully
            if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
                return temp_path
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error extracting audio from video: {e}")
            return None
    
    def _transcribe_with_whisper(self, audio_path: str, language: str) -> Dict[str, Any]:
        """
        Transcribe audio using OpenAI's Whisper model.
        
        Args:
            audio_path: Path to the audio file
            language: Language code
            
        Returns:
            Dictionary with transcription results
        """
        if not self.whisper_available:
            return {
                'text': "",
                'segments': [],
                'language': language,
                'success': False,
                'error': "Whisper library not available"
            }
            
        try:
            # Load the model if not already loaded
            if self.whisper_model is None:
                whisper_model = self.get_setting("transcription.whisper_model", "base")
                self.current_operation = "loading whisper model"
                self.whisper_model = whisper.load_model(whisper_model)
                logger.info(f"Loaded Whisper model: {whisper_model}")
            
            # Set transcription options
            auto_language_detection = self.get_setting("transcription.auto_language_detection", True)
            
            options = {
                "verbose": False,
                "fp16": False
            }
            
            # Set language if specified and not auto-detecting
            if not auto_language_detection and language:
                # Convert language code format if needed (e.g., en-US to en)
                lang_code = language.split('-')[0] if '-' in language else language
                options["language"] = lang_code
            
            # Perform transcription
            self.current_operation = "transcribing"
            result = self.whisper_model.transcribe(audio_path, **options)
            
            # Extract text and segments
            text = result.get('text', '')
            segments = []
            
            if 'segments' in result:
                for segment in result['segments']:
                    segments.append({
                        'id': segment.get('id', 0),
                        'start': segment.get('start', 0),
                        'end': segment.get('end', 0),
                        'text': segment.get('text', ''),
                        'confidence': segment.get('confidence', 1.0)
                    })
            
            # Get detected language
            detected_language = result.get('language')
            
            return {
                'text': text,
                'segments': segments,
                'language': detected_language,
                'success': bool(text),
                'error': "" if text else "Failed to transcribe audio"
            }
            
        except Exception as e:
            logger.error(f"Error transcribing with Whisper: {e}")
            return {
                'text': "",
                'segments': [],
                'language': language,
                'success': False,
                'error': str(e)
            }
    
    def _transcribe_with_google(self, audio_path: str, language: str) -> Dict[str, Any]:
        """
        Transcribe audio using Google Speech Recognition.
        
        Args:
            audio_path: Path to the audio file
            language: Language code
            
        Returns:
            Dictionary with transcription results
        """
        if not self.sr_available:
            return {
                'text': "",
                'segments': [],
                'language': language,
                'success': False,
                'error': "SpeechRecognition library not available"
            }
            
        try:
            # Initialize recognizer
            recognizer = sr.Recognizer()
            
            # Load audio file
            with sr.AudioFile(audio_path) as source:
                audio_data = recognizer.record(source)
            
            # Recognize speech using Google Speech Recognition
            text = recognizer.recognize_google(audio_data, language=language)
            
            # Create a simple segment for the full audio
            segments = [{
                'id': 0,
                'start': 0,
                'end': 0,  # We don't know the duration
                'text': text,
                'confidence': 1.0  # Google doesn't provide confidence scores
            }]
            
            return {
                'text': text,
                'segments': segments,
                'language': language,
                'success': bool(text),
                'error': "" if text else "Failed to transcribe audio"
            }
            
        except sr.UnknownValueError:
            return {
                'text': "",
                'segments': [],
                'language': language,
                'success': False,
                'error': "Google Speech Recognition could not understand audio"
            }
            
        except sr.RequestError as e:
            return {
                'text': "",
                'segments': [],
                'language': language,
                'success': False,
                'error': f"Could not request results from Google Speech Recognition service: {e}"
            }
            
        except Exception as e:
            logger.error(f"Error transcribing with Google: {e}")
            return {
                'text': "",
                'segments': [],
                'language': language,
                'success': False,
                'error': str(e)
            }
    
    def _transcribe_with_azure(self, audio_path: str, language: str) -> Dict[str, Any]:
        """
        Transcribe audio using Microsoft Azure Speech Services.
        
        Args:
            audio_path: Path to the audio file
            language: Language code
            
        Returns:
            Dictionary with transcription results
        """
        if not self.sr_available:
            return {
                'text': "",
                'segments': [],
                'language': language,
                'success': False,
                'error': "SpeechRecognition library not available"
            }
            
        try:
            # Get Azure API key
            azure_key = self.get_setting("transcription.azure_key", "")
            azure_region = self.get_setting("transcription.azure_region", "westus")
            
            if not azure_key:
                return {
                    'text': "",
                    'segments': [],
                    'language': language,
                    'success': False,
                    'error': "Azure Speech API key not configured"
                }
            
            # Initialize recognizer
            recognizer = sr.Recognizer()
            
            # Load audio file
            with sr.AudioFile(audio_path) as source:
                audio_data = recognizer.record(source)
            
            # Recognize speech using Microsoft Azure Speech
            text = recognizer.recognize_azure(audio_data, key=azure_key, 
                                            location=azure_region, language=language)
            
            # Create a simple segment for the full audio
            segments = [{
                'id': 0,
                'start': 0,
                'end': 0,  # We don't know the duration
                'text': text,
                'confidence': 1.0  # Default confidence
            }]
            
            return {
                'text': text,
                'segments': segments,
                'language': language,
                'success': bool(text),
                'error': "" if text else "Failed to transcribe audio"
            }
            
        except sr.UnknownValueError:
            return {
                'text': "",
                'segments': [],
                'language': language,
                'success': False,
                'error': "Microsoft Azure Speech could not understand audio"
            }
            
        except sr.RequestError as e:
            return {
                'text': "",
                'segments': [],
                'language': language,
                'success': False,
                'error': f"Could not request results from Microsoft Azure Speech service: {e}"
            }
            
        except Exception as e:
            logger.error(f"Error transcribing with Azure: {e}")
            return {
                'text': "",
                'segments': [],
                'language': language,
                'success': False,
                'error': str(e)
            }
    
    def _transcribe_with_mock(self, audio_path: str, language: str) -> Dict[str, Any]:
        """
        Mock transcription for testing purposes.
        
        Args:
            audio_path: Path to the audio file
            language: Language code
            
        Returns:
            Dictionary with mock transcription results
        """
        try:
            # Create mock transcription
            file_name = os.path.basename(audio_path)
            
            text = f"This is a mock transcription for the file '{file_name}' " + \
                   f"using language code '{language}'. " + \
                   f"Mock transcription generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}."
            
            # Create mock segments
            segments = [
                {
                    'id': 0,
                    'start': 0,
                    'end': 5,
                    'text': f"This is a mock transcription for the file '{file_name}'",
                    'confidence': 0.95
                },
                {
                    'id': 1,
                    'start': 5,
                    'end': 10,
                    'text': f"using language code '{language}'.",
                    'confidence': 0.93
                },
                {
                    'id': 2,
                    'start': 10,
                    'end': 15,
                    'text': f"Mock transcription generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.",
                    'confidence': 0.91
                }
            ]
            
            return {
                'text': text,
                'segments': segments,
                'language': language,
                'success': True,
                'error': "",
                'mock': True
            }
            
        except Exception as e:
            logger.error(f"Error creating mock transcription: {e}")
            return {
                'text': "",
                'segments': [],
                'language': language,
                'success': False,
                'error': str(e)
            }
    
    def _format_as_srt(self, segments: List[Dict[str, Any]]) -> str:
        """
        Format segments as SRT subtitle format.
        
        Args:
            segments: List of transcription segments
            
        Returns:
            String in SRT format
        """
        if not segments:
            return ""
            
        srt_lines = []
        
        for i, segment in enumerate(segments):
            # Get segment info
            segment_id = i + 1
            start_time = segment.get('start', 0)
            end_time = segment.get('end', start_time + 5)  # Default 5 seconds if end not specified
            text = segment.get('text', '').strip()
            
            # Format times
            start_formatted = self._format_srt_timestamp(start_time)
            end_formatted = self._format_srt_timestamp(end_time)
            
            # Add to SRT
            srt_lines.append(str(segment_id))
            srt_lines.append(f"{start_formatted} --> {end_formatted}")
            srt_lines.append(text)
            srt_lines.append("")  # Empty line between segments
        
        return "\n".join(srt_lines)
    
    def _format_as_vtt(self, segments: List[Dict[str, Any]]) -> str:
        """
        Format segments as WebVTT subtitle format.
        
        Args:
            segments: List of transcription segments
            
        Returns:
            String in WebVTT format
        """
        if not segments:
            return ""
            
        vtt_lines = ["WEBVTT", ""]  # Header and empty line
        
        for i, segment in enumerate(segments):
            # Get segment info
            segment_id = i + 1
            start_time = segment.get('start', 0)
            end_time = segment.get('end', start_time + 5)  # Default 5 seconds if end not specified
            text = segment.get('text', '').strip()
            
            # Format times
            start_formatted = self._format_vtt_timestamp(start_time)
            end_formatted = self._format_vtt_timestamp(end_time)
            
            # Add to VTT
            vtt_lines.append(f"{segment_id}")
            vtt_lines.append(f"{start_formatted} --> {end_formatted}")
            vtt_lines.append(text)
            vtt_lines.append("")  # Empty line between segments
        
        return "\n".join(vtt_lines)
    
    def _format_srt_timestamp(self, seconds: float) -> str:
        """
        Format seconds as SRT timestamp (HH:MM:SS,mmm).
        
        Args:
            seconds: Time in seconds
            
        Returns:
            Formatted timestamp string
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = seconds % 60
        milliseconds = int((seconds - int(seconds)) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{int(seconds):02d},{milliseconds:03d}"
    
    def _format_vtt_timestamp(self, seconds: float) -> str:
        """
        Format seconds as WebVTT timestamp (HH:MM:SS.mmm).
        
        Args:
            seconds: Time in seconds
            
        Returns:
            Formatted timestamp string
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = seconds % 60
        milliseconds = int((seconds - int(seconds)) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{int(seconds):02d}.{milliseconds:03d}"
    
    def _format_timestamp(self, seconds: float) -> str:
        """
        Format seconds as simple timestamp (HH:MM:SS).
        
        Args:
            seconds: Time in seconds
            
        Returns:
            Formatted timestamp string
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = int(seconds % 60)
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"