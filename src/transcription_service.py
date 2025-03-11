import os
import logging
import tempfile
import json
from typing import Dict, Any, Optional, List
from pathlib import Path
import time

# Import speech recognition library
try:
    import speech_recognition as sr
except ImportError:
    sr = None

logger = logging.getLogger("AIDocumentOrganizer")


class TranscriptionService:
    """
    Service for transcribing audio content from audio and video files.
    Supports multiple transcription providers and caching of results.
    """

    def __init__(self, cache_dir: Optional[str] = None):
        """
        Initialize the transcription service.

        Args:
            cache_dir: Directory to store transcription cache files
        """
        # Set up cache directory
        if cache_dir:
            self.cache_dir = cache_dir
        else:
            self.cache_dir = os.path.join(
                tempfile.gettempdir(), "transcription_cache")

        # Create cache directory if it doesn't exist
        os.makedirs(self.cache_dir, exist_ok=True)

        # Initialize speech recognition if available
        self.recognizer = sr.Recognizer() if sr else None

        # Available transcription providers
        self.providers = {
            'local': self._transcribe_local,
            'google': self._transcribe_google,
            'azure': self._transcribe_azure,
        }

        # Default provider
        self.default_provider = 'local'

    def transcribe(self, audio_path: str, provider: Optional[str] = None,
                   language: str = 'en-US', cache: bool = True) -> Dict[str, Any]:
        """
        Transcribe audio file using the specified provider.

        Args:
            audio_path: Path to the audio file
            provider: Transcription provider to use (default: local)
            language: Language code for transcription
            cache: Whether to use cached transcription if available

        Returns:
            Dictionary containing transcription results
        """
        # Check if audio file exists
        if not os.path.exists(audio_path):
            return {'error': f"Audio file not found: {audio_path}"}

        # Use default provider if none specified
        if not provider:
            provider = self.default_provider

        # Check if provider is available
        if provider not in self.providers:
            return {'error': f"Transcription provider not available: {provider}"}

        # Check cache if enabled
        if cache:
            cached_result = self._get_cached_transcription(
                audio_path, provider, language)
            if cached_result:
                logger.info(f"Using cached transcription for {audio_path}")
                return cached_result

        # Perform transcription
        try:
            transcription_func = self.providers[provider]
            result = transcription_func(audio_path, language)

            # Cache result if successful and caching is enabled
            if cache and 'text' in result and result['text']:
                self._cache_transcription(
                    audio_path, provider, language, result)

            return result

        except Exception as e:
            logger.error(
                f"Error transcribing audio {audio_path} with provider {provider}: {str(e)}")
            return {'error': str(e)}

    def _transcribe_local(self, audio_path: str, language: str) -> Dict[str, Any]:
        """
        Transcribe audio using local speech recognition.

        Args:
            audio_path: Path to the audio file
            language: Language code for transcription

        Returns:
            Dictionary containing transcription results
        """
        if not self.recognizer:
            return {'error': "Speech recognition library not available"}

        try:
            # Convert language code to recognizer format
            recognizer_language = language.split('-')[0]

            # Load audio file
            with sr.AudioFile(audio_path) as source:
                audio_data = self.recognizer.record(source)

                # Perform recognition
                start_time = time.time()
                text = self.recognizer.recognize_google(
                    audio_data, language=recognizer_language)
                end_time = time.time()

                return {
                    'text': text,
                    'provider': 'local',
                    'language': language,
                    'duration_seconds': end_time - start_time,
                    'confidence': 0.8,  # Default confidence value
                }

        except sr.UnknownValueError:
            return {'error': "Speech recognition could not understand audio"}
        except sr.RequestError as e:
            return {'error': f"Speech recognition service error: {str(e)}"}
        except Exception as e:
            return {'error': f"Error in local transcription: {str(e)}"}

    def _transcribe_google(self, audio_path: str, language: str) -> Dict[str, Any]:
        """
        Transcribe audio using Google Cloud Speech-to-Text API.

        Args:
            audio_path: Path to the audio file
            language: Language code for transcription

        Returns:
            Dictionary containing transcription results
        """
        # This is a placeholder for Google Cloud Speech-to-Text integration
        # In a real implementation, you would use the Google Cloud client library
        return {'error': "Google Cloud Speech-to-Text not implemented yet"}

    def _transcribe_azure(self, audio_path: str, language: str) -> Dict[str, Any]:
        """
        Transcribe audio using Azure Speech Service.

        Args:
            audio_path: Path to the audio file
            language: Language code for transcription

        Returns:
            Dictionary containing transcription results
        """
        # This is a placeholder for Azure Speech Service integration
        # In a real implementation, you would use the Azure Speech SDK
        return {'error': "Azure Speech Service not implemented yet"}

    def _get_cached_transcription(self, audio_path: str, provider: str,
                                  language: str) -> Optional[Dict[str, Any]]:
        """
        Get cached transcription result if available.

        Args:
            audio_path: Path to the audio file
            provider: Transcription provider
            language: Language code

        Returns:
            Cached transcription result or None if not available
        """
        cache_file = self._get_cache_file_path(audio_path, provider, language)

        if os.path.exists(cache_file):
            try:
                # Check if the audio file has been modified since the cache was created
                audio_mtime = os.path.getmtime(audio_path)
                cache_mtime = os.path.getmtime(cache_file)

                if audio_mtime > cache_mtime:
                    # Audio file has been modified, cache is invalid
                    return None

                # Load cache file
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)

            except Exception as e:
                logger.error(f"Error reading transcription cache: {str(e)}")

        return None

    def _cache_transcription(self, audio_path: str, provider: str,
                             language: str, result: Dict[str, Any]) -> None:
        """
        Cache transcription result.

        Args:
            audio_path: Path to the audio file
            provider: Transcription provider
            language: Language code
            result: Transcription result to cache
        """
        cache_file = self._get_cache_file_path(audio_path, provider, language)

        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"Error writing transcription cache: {str(e)}")

    def _get_cache_file_path(self, audio_path: str, provider: str, language: str) -> str:
        """
        Get the path to the cache file for a specific transcription.

        Args:
            audio_path: Path to the audio file
            provider: Transcription provider
            language: Language code

        Returns:
            Path to the cache file
        """
        # Create a unique cache file name based on the audio file path, provider, and language
        audio_path_hash = str(hash(audio_path))
        file_name = f"{os.path.basename(audio_path)}_{provider}_{language}_{audio_path_hash}.json"

        return os.path.join(self.cache_dir, file_name)

    def clear_cache(self, audio_path: Optional[str] = None) -> int:
        """
        Clear transcription cache.

        Args:
            audio_path: Optional path to clear cache for a specific file

        Returns:
            Number of cache files deleted
        """
        count = 0

        try:
            if audio_path:
                # Clear cache for a specific file
                for provider in self.providers:
                    for language in ['en-US', 'en-GB', 'fr-FR', 'de-DE', 'es-ES', 'it-IT', 'ja-JP']:
                        cache_file = self._get_cache_file_path(
                            audio_path, provider, language)
                        if os.path.exists(cache_file):
                            os.remove(cache_file)
                            count += 1
            else:
                # Clear all cache
                for file in os.listdir(self.cache_dir):
                    if file.endswith('.json'):
                        os.remove(os.path.join(self.cache_dir, file))
                        count += 1

            return count

        except Exception as e:
            logger.error(f"Error clearing transcription cache: {str(e)}")
            return count
