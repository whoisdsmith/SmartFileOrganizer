"""
Transcription Service Plugin for AI Document Organizer V2.

This plugin provides speech-to-text capabilities for audio and video files
using multiple transcription engines: local Whisper, SpeechRecognition, and
optionally cloud transcription services.
"""

import os
import io
import json
import logging
import tempfile
import hashlib
import time
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

# Import plugin base class
from ai_document_organizer_v2.core.plugin_base import TranscriptionPlugin

# Set up logger
logger = logging.getLogger("AIDocumentOrganizerV2.TranscriptionService")

# Try importing ffmpeg for audio extraction
try:
    import ffmpeg
    FFMPEG_AVAILABLE = True
except ImportError:
    FFMPEG_AVAILABLE = False
    logger.warning("FFmpeg library not available")

# Try importing whisper for local transcription
try:
    import whisper
    # Check if the required function is available
    if hasattr(whisper, 'load_model'):
        WHISPER_AVAILABLE = True
    else:
        WHISPER_AVAILABLE = False
        logger.warning("Whisper library found but missing load_model function")
except ImportError:
    WHISPER_AVAILABLE = False
    logger.warning("Whisper library not available")

# Try importing speech_recognition
try:
    import speech_recognition as sr
    SR_AVAILABLE = True
except ImportError:
    SR_AVAILABLE = False
    logger.warning("SpeechRecognition library not available")

class TranscriptionServicePlugin(TranscriptionPlugin):
    """
    Plugin for transcribing audio and video files.
    
    This plugin provides speech-to-text capabilities using multiple engines:
    - Local Whisper model (if available)
    - SpeechRecognition library (if available)
    - Cloud services (if configured)
    """
    
    # Plugin metadata
    name = "Transcription Service"
    version = "1.0.0"
    description = "Provides speech-to-text capabilities for audio and video files"
    author = "AI Document Organizer Team"
    dependencies = ["whisper", "SpeechRecognition", "ffmpeg-python"]
    
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
        self.whisper_available = WHISPER_AVAILABLE
        self.sr_available = SR_AVAILABLE
        self.ffmpeg_available = FFMPEG_AVAILABLE
        
        # Initialize properties
        self.whisper_model = None
        self.whisper_model_name = None
        self.cache_dir = None
        
        if not self.whisper_available:
            logger.warning("Whisper library not available. Local transcription will be limited.")
        
        if not self.sr_available:
            logger.warning("SpeechRecognition library not available. Speech recognition will be limited.")
        
        if not self.ffmpeg_available:
            logger.warning("FFmpeg library not available. Audio extraction will be limited.")
    
    def initialize(self) -> bool:
        """
        Initialize the plugin.
        
        Returns:
            True if initialization was successful, False otherwise
        """
        # Register default settings if not already present
        if self.settings_manager is not None:
            # Use get_setting/set_setting to access settings manager
            
            # Transcription engine settings
            engine = self.get_setting("transcription.default_engine", None)
            if engine is None:
                # Default to Whisper if available, otherwise SpeechRecognition
                default_engine = "whisper" if self.whisper_available else "speechrecognition"
                self.set_setting("transcription.default_engine", default_engine)
            
            # Whisper settings
            whisper_model_size = self.get_setting("transcription.whisper_model_size", None)
            if whisper_model_size is None:
                self.set_setting("transcription.whisper_model_size", "base")
            
            # SpeechRecognition settings
            sr_engine = self.get_setting("transcription.sr_engine", None)
            if sr_engine is None:
                self.set_setting("transcription.sr_engine", "google")
            
            # Cloud service settings
            use_cloud = self.get_setting("transcription.use_cloud_services", None)
            if use_cloud is None:
                self.set_setting("transcription.use_cloud_services", False)
            
            # Cache settings
            use_cache = self.get_setting("transcription.use_cache", None)
            if use_cache is None:
                self.set_setting("transcription.use_cache", True)
            
            cache_dir = self.get_setting("transcription.cache_directory", None)
            if cache_dir is None:
                default_cache_dir = os.path.join(tempfile.gettempdir(), "transcription_cache")
                self.set_setting("transcription.cache_directory", default_cache_dir)
                self.cache_dir = default_cache_dir
            else:
                self.cache_dir = cache_dir
            
            # Create cache directory if it doesn't exist
            if self.cache_dir:
                os.makedirs(self.cache_dir, exist_ok=True)
        
        # Initialize Whisper model if available and enabled
        if self.whisper_available:
            try:
                model_size = self.get_setting("transcription.whisper_model_size", "base")
                self.whisper_model_name = model_size
                
                # Only load the model if we're going to use it
                if self.get_setting("transcription.default_engine", "") == "whisper":
                    logger.info(f"Loading Whisper model: {model_size}")
                    self.whisper_model = whisper.load_model(model_size)
                    logger.info(f"Whisper model loaded successfully")
            except Exception as e:
                logger.error(f"Error loading Whisper model: {e}")
                # Don't fail initialization, we'll use fallback methods
        
        logger.info("Transcription service initialized")
        return True
    
    def transcribe(self, audio_path: str, language: str = 'en-US', 
                  options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Transcribe audio content from a file.
        
        Args:
            audio_path: Path to the audio or video file
            language: Language code for transcription (ISO 639-1)
            options: Optional dictionary with transcription options
            
        Returns:
            Dictionary containing transcription results
        """
        if not os.path.exists(audio_path):
            return {
                'text': '',
                'segments': [],
                'confidence': 0.0,
                'language': language,
                'success': False,
                'error': f"File not found: {audio_path}"
            }
        
        # Default options
        if options is None:
            options = {}
        
        # Merge with settings
        engine = options.get('engine', self.get_setting("transcription.default_engine", "whisper"))
        use_cache = options.get('use_cache', self.get_setting("transcription.use_cache", True))
        
        # Check cache first if enabled
        if use_cache:
            cache_result = self._check_cache(audio_path, language, engine)
            if cache_result:
                logger.info(f"Using cached transcription for {audio_path}")
                return cache_result
        
        # Extract audio from video if needed
        _, file_ext = os.path.splitext(audio_path)
        file_ext = file_ext.lower()
        
        audio_file = audio_path
        extracted_audio = None
        
        # If file is video, extract audio
        if file_ext in ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv']:
            if not self.ffmpeg_available:
                return {
                    'text': '',
                    'segments': [],
                    'confidence': 0.0,
                    'language': language,
                    'success': False,
                    'error': "Cannot extract audio: ffmpeg not available"
                }
            
            # Extract audio to a temporary file
            try:
                extracted_audio = self._extract_audio(audio_path)
                if extracted_audio:
                    audio_file = extracted_audio
                else:
                    return {
                        'text': '',
                        'segments': [],
                        'confidence': 0.0,
                        'language': language,
                        'success': False,
                        'error': "Failed to extract audio from video"
                    }
            except Exception as e:
                logger.error(f"Error extracting audio from video: {e}")
                return {
                    'text': '',
                    'segments': [],
                    'confidence': 0.0,
                    'language': language,
                    'success': False,
                    'error': f"Error extracting audio: {str(e)}"
                }
        
        try:
            # Choose transcription engine
            result = None
            
            if engine == "whisper" and self.whisper_available:
                result = self._transcribe_with_whisper(audio_file, language, options)
            elif engine == "speechrecognition" and self.sr_available:
                result = self._transcribe_with_sr(audio_file, language, options)
            elif engine == "cloud" and self.get_setting("transcription.use_cloud_services", False):
                result = self._transcribe_with_cloud(audio_file, language, options)
            else:
                # Try all available engines in order
                if self.whisper_available:
                    result = self._transcribe_with_whisper(audio_file, language, options)
                elif self.sr_available:
                    result = self._transcribe_with_sr(audio_file, language, options)
                elif self.get_setting("transcription.use_cloud_services", False):
                    result = self._transcribe_with_cloud(audio_file, language, options)
                else:
                    return {
                        'text': '',
                        'segments': [],
                        'confidence': 0.0,
                        'language': language,
                        'success': False,
                        'error': "No transcription engines available"
                    }
            
            # If transcription was successful, cache the result
            if result and result.get('success', False) and use_cache:
                self._save_to_cache(audio_path, language, engine, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            return {
                'text': '',
                'segments': [],
                'confidence': 0.0,
                'language': language,
                'success': False,
                'error': str(e)
            }
        finally:
            # Clean up extracted audio file if created
            if extracted_audio and os.path.exists(extracted_audio):
                try:
                    os.unlink(extracted_audio)
                except Exception:
                    pass
    
    def get_supported_languages(self) -> List[Dict[str, str]]:
        """
        Get list of supported languages for transcription.
        
        Returns:
            List of dictionaries with language information
        """
        # Common languages supported by most transcription services
        common_languages = [
            {'code': 'en-US', 'name': 'English (US)'},
            {'code': 'en-GB', 'name': 'English (UK)'},
            {'code': 'es-ES', 'name': 'Spanish'},
            {'code': 'fr-FR', 'name': 'French'},
            {'code': 'de-DE', 'name': 'German'},
            {'code': 'it-IT', 'name': 'Italian'},
            {'code': 'ja-JP', 'name': 'Japanese'},
            {'code': 'ko-KR', 'name': 'Korean'},
            {'code': 'pt-BR', 'name': 'Portuguese (Brazil)'},
            {'code': 'zh-CN', 'name': 'Chinese (Simplified)'},
            {'code': 'ru-RU', 'name': 'Russian'},
            {'code': 'ar-SA', 'name': 'Arabic'},
            {'code': 'hi-IN', 'name': 'Hindi'},
            {'code': 'nl-NL', 'name': 'Dutch'},
            {'code': 'sv-SE', 'name': 'Swedish'},
            {'code': 'tr-TR', 'name': 'Turkish'}
        ]
        
        # Add additional languages if using Whisper
        if self.whisper_available and self.get_setting("transcription.default_engine", "") == "whisper":
            additional_languages = [
                {'code': 'cs-CZ', 'name': 'Czech'},
                {'code': 'da-DK', 'name': 'Danish'},
                {'code': 'fi-FI', 'name': 'Finnish'},
                {'code': 'el-GR', 'name': 'Greek'},
                {'code': 'hu-HU', 'name': 'Hungarian'},
                {'code': 'id-ID', 'name': 'Indonesian'},
                {'code': 'pl-PL', 'name': 'Polish'},
                {'code': 'ro-RO', 'name': 'Romanian'},
                {'code': 'sk-SK', 'name': 'Slovak'},
                {'code': 'th-TH', 'name': 'Thai'},
                {'code': 'uk-UA', 'name': 'Ukrainian'},
                {'code': 'vi-VN', 'name': 'Vietnamese'}
            ]
            
            return common_languages + additional_languages
        
        return common_languages
    
    def _extract_audio(self, video_path: str) -> Optional[str]:
        """
        Extract audio from a video file.
        
        Args:
            video_path: Path to the video file
            
        Returns:
            Path to the extracted audio file or None if extraction failed
        """
        if not self.ffmpeg_available:
            logger.error("Cannot extract audio: ffmpeg not available")
            return None
        
        try:
            # Create output path
            output_dir = os.path.join(tempfile.gettempdir(), "transcription_audio")
            os.makedirs(output_dir, exist_ok=True)
            
            # Create a filename hash based on the input path
            file_hash = hashlib.md5(video_path.encode()).hexdigest()[:10]
            base_name = os.path.splitext(os.path.basename(video_path))[0]
            output_path = os.path.join(output_dir, f"{base_name}_{file_hash}.wav")
            
            # Use ffmpeg to extract audio
            (
                ffmpeg
                .input(video_path)
                .output(output_path, acodec='pcm_s16le', ac=1, ar='16k')
                .overwrite_output()
                .run(quiet=True)
            )
            
            if os.path.exists(output_path):
                logger.debug(f"Extracted audio from video: {output_path}")
                return output_path
            else:
                logger.error(f"Failed to extract audio: {output_path} not created")
                return None
                
        except Exception as e:
            logger.error(f"Error extracting audio from video: {e}")
            return None
    
    def _transcribe_with_whisper(self, audio_path: str, language: str, 
                               options: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transcribe audio using the local Whisper model.
        
        Args:
            audio_path: Path to the audio file
            language: Language code for transcription
            options: Transcription options
            
        Returns:
            Dictionary with transcription results
        """
        if not self.whisper_available:
            return {
                'text': '',
                'segments': [],
                'confidence': 0.0,
                'language': language,
                'success': False,
                'error': "Whisper library not available"
            }
        
        try:
            # Load model if not already loaded
            if self.whisper_model is None:
                model_size = self.get_setting("transcription.whisper_model_size", "base")
                self.whisper_model_name = model_size
                logger.info(f"Loading Whisper model: {model_size}")
                self.whisper_model = whisper.load_model(model_size)
            
            # Convert language code format (e.g., 'en-US' to 'en')
            if '-' in language:
                whisper_lang = language.split('-')[0]
            else:
                whisper_lang = language
            
            # Transcribe audio
            start_time = time.time()
            
            # Get transcription options
            beam_size = options.get('beam_size', 5)
            temperature = options.get('temperature', 0.0)
            
            logger.info(f"Transcribing audio with Whisper ({self.whisper_model_name}): {audio_path}")
            
            result = self.whisper_model.transcribe(
                audio_path,
                language=whisper_lang,
                task="transcribe",
                beam_size=beam_size,
                temperature=temperature
            )
            
            elapsed_time = time.time() - start_time
            logger.info(f"Transcription completed in {elapsed_time:.2f} seconds")
            
            # Process result
            text = result.get('text', '')
            segments = []
            
            # Process segments if available
            if 'segments' in result:
                for seg in result['segments']:
                    segment = {
                        'start': seg.get('start', 0),
                        'end': seg.get('end', 0),
                        'text': seg.get('text', ''),
                    }
                    
                    # Convert to milliseconds for consistency
                    segment['start_ms'] = int(segment['start'] * 1000)
                    segment['end_ms'] = int(segment['end'] * 1000)
                    
                    # Add formatted time for display
                    segment['start_formatted'] = self._format_time(segment['start'])
                    segment['end_formatted'] = self._format_time(segment['end'])
                    
                    segments.append(segment)
            
            # Estimate confidence (Whisper doesn't provide per-token confidence)
            # This is a very rough approximation
            confidence = 0.8  # Default medium-high confidence for Whisper
            
            return {
                'text': text,
                'segments': segments,
                'confidence': confidence,
                'language': language,
                'detected_language': result.get('language', whisper_lang),
                'provider': f"whisper_{self.whisper_model_name}",
                'processing_time': elapsed_time,
                'success': True,
                'error': ""
            }
            
        except Exception as e:
            logger.error(f"Error transcribing with Whisper: {e}")
            return {
                'text': '',
                'segments': [],
                'confidence': 0.0,
                'language': language,
                'success': False,
                'error': f"Whisper transcription error: {str(e)}"
            }
    
    def _transcribe_with_sr(self, audio_path: str, language: str, 
                          options: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transcribe audio using the SpeechRecognition library.
        
        Args:
            audio_path: Path to the audio file
            language: Language code for transcription
            options: Transcription options
            
        Returns:
            Dictionary with transcription results
        """
        if not self.sr_available:
            return {
                'text': '',
                'segments': [],
                'confidence': 0.0,
                'language': language,
                'success': False,
                'error': "SpeechRecognition library not available"
            }
        
        try:
            # Initialize recognizer
            recognizer = sr.Recognizer()
            
            # Get options
            sr_engine = options.get('sr_engine', self.get_setting("transcription.sr_engine", "google"))
            
            # Split long audio into chunks (SpeechRecognition works best with shorter clips)
            max_duration = 60  # seconds
            
            # Get audio duration using ffmpeg if available
            duration = None
            if self.ffmpeg_available:
                try:
                    probe = ffmpeg.probe(audio_path)
                    duration = float(probe['format']['duration'])
                except Exception as e:
                    logger.warning(f"Error getting audio duration: {e}")
            
            # Start timing
            start_time = time.time()
            
            # Open the audio file
            with sr.AudioFile(audio_path) as source:
                # If duration is known and longer than max_duration, process in chunks
                if duration and duration > max_duration:
                    logger.info(f"Processing audio in chunks (total duration: {duration:.2f}s)")
                    
                    texts = []
                    segments = []
                    overall_confidence = 0.0
                    segment_count = 0
                    
                    # Process audio in chunks
                    for chunk_start in range(0, int(duration), max_duration):
                        chunk_end = min(chunk_start + max_duration, duration)
                        
                        logger.debug(f"Processing audio chunk: {chunk_start}s to {chunk_end}s")
                        
                        # Get audio chunk
                        audio_data = recognizer.record(source, duration=chunk_end - chunk_start, offset=chunk_start)
                        
                        # Recognize speech in chunk
                        chunk_result = self._recognize_speech(recognizer, audio_data, language, sr_engine)
                        
                        if chunk_result['success']:
                            texts.append(chunk_result['text'])
                            
                            # Add segment
                            segment = {
                                'start': chunk_start,
                                'end': chunk_end,
                                'text': chunk_result['text'],
                                'start_ms': int(chunk_start * 1000),
                                'end_ms': int(chunk_end * 1000),
                                'start_formatted': self._format_time(chunk_start),
                                'end_formatted': self._format_time(chunk_end),
                            }
                            
                            if 'confidence' in chunk_result:
                                segment['confidence'] = chunk_result['confidence']
                                overall_confidence += chunk_result['confidence']
                                segment_count += 1
                            
                            segments.append(segment)
                    
                    # Calculate average confidence
                    if segment_count > 0:
                        overall_confidence /= segment_count
                    
                    # Join all texts
                    text = ' '.join(texts)
                    
                else:
                    # Process the entire audio file at once
                    audio_data = recognizer.record(source)
                    
                    # Recognize speech
                    result = self._recognize_speech(recognizer, audio_data, language, sr_engine)
                    
                    if result['success']:
                        text = result['text']
                        overall_confidence = result.get('confidence', 0.0)
                        
                        # Create a single segment for the entire audio
                        segments = [{
                            'start': 0,
                            'end': duration if duration else 0,
                            'text': text,
                            'start_ms': 0,
                            'end_ms': int(duration * 1000) if duration else 0,
                            'start_formatted': self._format_time(0),
                            'end_formatted': self._format_time(duration) if duration else "00:00:00",
                            'confidence': overall_confidence
                        }]
                    else:
                        return result  # Return the error result
                
            elapsed_time = time.time() - start_time
            
            return {
                'text': text,
                'segments': segments,
                'confidence': overall_confidence,
                'language': language,
                'provider': f"speechrecognition_{sr_engine}",
                'processing_time': elapsed_time,
                'success': True,
                'error': ""
            }
            
        except Exception as e:
            logger.error(f"Error transcribing with SpeechRecognition: {e}")
            return {
                'text': '',
                'segments': [],
                'confidence': 0.0,
                'language': language,
                'success': False,
                'error': f"SpeechRecognition error: {str(e)}"
            }
    
    def _recognize_speech(self, recognizer, audio_data, language, engine):
        """
        Recognize speech using the specified engine.
        
        Args:
            recognizer: SpeechRecognition recognizer instance
            audio_data: Audio data to recognize
            language: Language code
            engine: Recognition engine name
            
        Returns:
            Dictionary with recognition results
        """
        try:
            result = {
                'text': '',
                'confidence': 0.0,
                'success': False,
                'error': ""
            }
            
            if engine == "google":
                # Use Google Speech Recognition
                google_result = recognizer.recognize_google(
                    audio_data, 
                    language=language,
                    show_all=True
                )
                
                if google_result and 'alternative' in google_result:
                    result['text'] = google_result['alternative'][0]['transcript']
                    if 'confidence' in google_result['alternative'][0]:
                        result['confidence'] = google_result['alternative'][0]['confidence']
                    result['success'] = True
                else:
                    result['error'] = "Google Speech Recognition could not understand audio"
            
            elif engine == "sphinx":
                # Use CMU Sphinx (offline)
                text = recognizer.recognize_sphinx(audio_data, language=language)
                result['text'] = text
                result['confidence'] = 0.6  # Sphinx doesn't provide confidence scores
                result['success'] = True
            
            else:
                result['error'] = f"Unsupported recognition engine: {engine}"
            
            return result
            
        except sr.UnknownValueError:
            return {
                'text': '',
                'confidence': 0.0,
                'success': False,
                'error': "Speech Recognition could not understand audio"
            }
        except sr.RequestError as e:
            return {
                'text': '',
                'confidence': 0.0,
                'success': False,
                'error': f"Speech Recognition service error: {e}"
            }
        except Exception as e:
            return {
                'text': '',
                'confidence': 0.0,
                'success': False,
                'error': f"Speech Recognition error: {e}"
            }
    
    def _transcribe_with_cloud(self, audio_path: str, language: str, 
                             options: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transcribe audio using a cloud service.
        
        Args:
            audio_path: Path to the audio file
            language: Language code for transcription
            options: Transcription options
            
        Returns:
            Dictionary with transcription results
        """
        # Get cloud service settings
        cloud_provider = options.get('cloud_provider', 
                                   self.get_setting("transcription.cloud_provider", "googlecloud"))
        
        # Check if API keys/credentials are available for the cloud provider
        if cloud_provider == "googlecloud":
            api_key = self.get_setting("transcription.google_api_key", None)
            if not api_key:
                return {
                    'text': '',
                    'segments': [],
                    'confidence': 0.0,
                    'language': language,
                    'success': False,
                    'error': "Google Cloud API key not configured"
                }
        elif cloud_provider == "azure":
            api_key = self.get_setting("transcription.azure_api_key", None)
            region = self.get_setting("transcription.azure_region", None)
            if not api_key or not region:
                return {
                    'text': '',
                    'segments': [],
                    'confidence': 0.0,
                    'language': language,
                    'success': False,
                    'error': "Azure Speech API key or region not configured"
                }
        else:
            return {
                'text': '',
                'segments': [],
                'confidence': 0.0,
                'language': language,
                'success': False,
                'error': f"Unsupported cloud provider: {cloud_provider}"
            }
        
        # Note: For a real implementation, we would integrate with the actual cloud APIs here
        # For this implementation, we'll return a message indicating that cloud transcription
        # requires API key configuration
        
        return {
            'text': '',
            'segments': [],
            'confidence': 0.0,
            'language': language,
            'success': False,
            'error': f"Cloud transcription with {cloud_provider} requires proper API configuration"
        }
    
    def _check_cache(self, file_path: str, language: str, engine: str) -> Optional[Dict[str, Any]]:
        """
        Check if transcription is cached for the file.
        
        Args:
            file_path: Path to the file
            language: Language code used for transcription
            engine: Transcription engine
            
        Returns:
            Cached transcription result or None if not found
        """
        if not self.cache_dir or not os.path.exists(self.cache_dir):
            return None
        
        try:
            # Create cache key from file path, modification time, language, and engine
            file_stat = os.stat(file_path)
            mtime = file_stat.st_mtime
            file_size = file_stat.st_size
            
            cache_key = f"{file_path}_{mtime}_{file_size}_{language}_{engine}"
            cache_hash = hashlib.md5(cache_key.encode()).hexdigest()
            cache_file = os.path.join(self.cache_dir, f"transcription_{cache_hash}.json")
            
            if os.path.exists(cache_file):
                with open(cache_file, 'r', encoding='utf-8') as f:
                    result = json.load(f)
                    # Add the source information
                    result['cached'] = True
                    result['cache_date'] = datetime.fromtimestamp(
                        os.path.getmtime(cache_file)).isoformat()
                    return result
        except Exception as e:
            logger.warning(f"Error checking transcription cache: {e}")
        
        return None
    
    def _save_to_cache(self, file_path: str, language: str, engine: str, result: Dict[str, Any]) -> bool:
        """
        Save transcription result to cache.
        
        Args:
            file_path: Path to the file
            language: Language code used for transcription
            engine: Transcription engine
            result: Transcription result to cache
            
        Returns:
            True if saved successfully, False otherwise
        """
        if not self.cache_dir:
            return False
        
        try:
            # Create cache directory if it doesn't exist
            os.makedirs(self.cache_dir, exist_ok=True)
            
            # Create cache key from file path, modification time, language, and engine
            file_stat = os.stat(file_path)
            mtime = file_stat.st_mtime
            file_size = file_stat.st_size
            
            cache_key = f"{file_path}_{mtime}_{file_size}_{language}_{engine}"
            cache_hash = hashlib.md5(cache_key.encode()).hexdigest()
            cache_file = os.path.join(self.cache_dir, f"transcription_{cache_hash}.json")
            
            # Remove cached flag if present
            result_copy = result.copy()
            result_copy.pop('cached', None)
            result_copy.pop('cache_date', None)
            
            # Save result to cache file
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(result_copy, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            logger.warning(f"Error saving transcription to cache: {e}")
            return False
    
    def _format_time(self, seconds: float) -> str:
        """
        Format time in seconds to HH:MM:SS format.
        
        Args:
            seconds: Time in seconds
            
        Returns:
            Formatted time string
        """
        if seconds is None:
            return "00:00:00"
        
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = int(seconds % 60)
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    def clear_cache(self) -> int:
        """
        Clear the transcription cache.
        
        Returns:
            Number of cache files deleted
        """
        if not self.cache_dir or not os.path.exists(self.cache_dir):
            return 0
        
        try:
            count = 0
            for filename in os.listdir(self.cache_dir):
                if filename.startswith("transcription_") and filename.endswith(".json"):
                    file_path = os.path.join(self.cache_dir, filename)
                    os.unlink(file_path)
                    count += 1
            
            return count
        except Exception as e:
            logger.error(f"Error clearing transcription cache: {e}")
            return 0
    
    def get_config_schema(self) -> Dict[str, Any]:
        """
        Get JSON schema for plugin configuration.
        
        Returns:
            Dictionary with JSON schema for plugin configuration
        """
        engines = ["whisper", "speechrecognition", "cloud"]
        if not self.whisper_available:
            engines.remove("whisper")
        if not self.sr_available:
            engines.remove("speechrecognition")
        
        # Default to first available engine
        default_engine = engines[0] if engines else ""
        
        return {
            "type": "object",
            "properties": {
                "default_engine": {
                    "type": "string",
                    "title": "Default Transcription Engine",
                    "description": "The default engine to use for transcription",
                    "enum": engines,
                    "default": default_engine
                },
                "whisper_model_size": {
                    "type": "string",
                    "title": "Whisper Model Size",
                    "description": "Size of the Whisper model to use (larger models are more accurate but slower)",
                    "enum": ["tiny", "base", "small", "medium", "large"],
                    "default": "base"
                },
                "sr_engine": {
                    "type": "string",
                    "title": "SpeechRecognition Engine",
                    "description": "Engine to use with SpeechRecognition library",
                    "enum": ["google", "sphinx"],
                    "default": "google"
                },
                "use_cloud_services": {
                    "type": "boolean",
                    "title": "Use Cloud Services",
                    "description": "Enable cloud-based transcription services",
                    "default": False
                },
                "cloud_provider": {
                    "type": "string",
                    "title": "Cloud Provider",
                    "description": "Cloud provider to use for transcription",
                    "enum": ["googlecloud", "azure"],
                    "default": "googlecloud"
                },
                "use_cache": {
                    "type": "boolean",
                    "title": "Use Transcription Cache",
                    "description": "Cache transcription results to avoid re-processing the same files",
                    "default": True
                },
                "cache_directory": {
                    "type": "string",
                    "title": "Cache Directory",
                    "description": "Directory to store cached transcription results",
                    "default": ""
                }
            }
        }