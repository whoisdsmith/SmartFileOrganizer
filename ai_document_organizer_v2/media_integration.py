"""
Media Integration Module for AI Document Organizer V2.

This module integrates all media processing plugins (audio analyzer, video analyzer,
transcription service) to provide comprehensive media analysis capabilities.
"""

import os
import logging
import threading
from typing import Dict, Any, List, Optional, Callable, Tuple

# Import plugin management
from ai_document_organizer_v2.core.plugin_manager import PluginManager

logger = logging.getLogger("AIDocumentOrganizerV2.MediaIntegration")

class MediaIntegration:
    """
    Integrates all media processing plugins to provide comprehensive media analysis.
    
    This class coordinates the use of multiple media plugins to analyze media files,
    handling plugin discovery, initialization, and coordinated processing.
    """
    
    def __init__(self, settings_manager=None):
        """
        Initialize the media integration module.
        
        Args:
            settings_manager: Optional settings manager instance
        """
        self.settings_manager = settings_manager
        self.plugin_manager = PluginManager(settings_manager)
        
        # Initialize plugins dictionary
        self.plugins = {}
        
        # Media type mappings
        self.audio_extensions = ['.mp3', '.wav', '.flac', '.ogg', '.aac', '.m4a']
        self.video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm']
        
        # Current operation tracking
        self.current_operations = {}
        
    def initialize(self) -> bool:
        """
        Initialize all media plugins.
        
        Returns:
            True if at least one plugin was initialized successfully, False otherwise
        """
        # Discover and initialize all media plugins
        try:
            # Discover plugins
            self.plugin_manager.discover_plugins()
            
            # Filter for media processing plugins
            audio_plugins = self.plugin_manager.get_plugins_by_type('audio_analyzer')
            video_plugins = self.plugin_manager.get_plugins_by_type('video_analyzer')
            transcription_plugins = self.plugin_manager.get_plugins_by_type('transcription_service')
            
            # Initialize audio analyzer plugin
            if audio_plugins:
                self.plugins['audio_analyzer'] = audio_plugins[0]
                logger.info(f"Using audio analyzer plugin: {self.plugins['audio_analyzer'].name}")
            else:
                logger.warning("No audio analyzer plugin found")
            
            # Initialize video analyzer plugin
            if video_plugins:
                self.plugins['video_analyzer'] = video_plugins[0]
                logger.info(f"Using video analyzer plugin: {self.plugins['video_analyzer'].name}")
            else:
                logger.warning("No video analyzer plugin found")
            
            # Initialize transcription service plugin
            if transcription_plugins:
                self.plugins['transcription_service'] = transcription_plugins[0]
                logger.info(f"Using transcription service plugin: {self.plugins['transcription_service'].name}")
            else:
                logger.warning("No transcription service plugin found")
            
            return len(self.plugins) > 0
            
        except Exception as e:
            logger.error(f"Error initializing media plugins: {e}")
            return False
            
    def analyze_media(self, file_path: str, options: Optional[Dict[str, Any]] = None, 
                   callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        Analyze a media file using appropriate plugins.
        
        Args:
            file_path: Path to the media file
            options: Optional dictionary with analysis options
            callback: Optional progress callback function
            
        Returns:
            Dictionary with analysis results
        """
        if not os.path.exists(file_path):
            return {
                'success': False,
                'error': f"File not found: {file_path}"
            }
        
        # Extract file extension
        _, file_ext = os.path.splitext(file_path)
        file_ext = file_ext.lower()
        
        # Determine file type and use appropriate plugin
        if file_ext in self.audio_extensions:
            media_type = 'audio'
            plugin_key = 'audio_analyzer'
        elif file_ext in self.video_extensions:
            media_type = 'video'
            plugin_key = 'video_analyzer'
        else:
            return {
                'success': False,
                'error': f"Unsupported file extension: {file_ext}"
            }
        
        # Check if needed plugin is available
        if plugin_key not in self.plugins:
            return {
                'success': False,
                'error': f"No {plugin_key} plugin available"
            }
        
        # Process options
        if options is None:
            options = {}
        
        # Extract specific options
        transcribe = options.get('transcribe', False)
        analyze_content = options.get('analyze_content', True)
        
        # Initialize results
        result = {
            'media_type': media_type,
            'file_path': file_path,
            'file_ext': file_ext
        }
        
        # Track current operation for this file
        file_id = os.path.basename(file_path)
        self.current_operations[file_id] = {'status': 'starting', 'progress': 0}
        
        try:
            # Define progress callback wrapper
            progress_data = {'last_progress': 0, 'stage': 'analysis'}
            
            def progress_wrapper(current, total, message):
                """Wrapper for progress callback to handle multi-stage processing"""
                if not callback:
                    return
                    
                stage = progress_data['stage']
                stage_weight = 0.5 if transcribe else 1.0  # Analysis is 50% if transcribing
                
                if stage == 'analysis':
                    # Analysis phase
                    progress = current / total * 100 * stage_weight
                elif stage == 'transcription':
                    # Transcription phase (only if requested)
                    progress = 50 + (current / total * 100 * 0.5)  # Start at 50%
                
                # Update progress tracking
                progress_data['last_progress'] = progress
                self.current_operations[file_id] = {'status': message, 'progress': progress}
                
                # Call the original callback
                callback(progress, 100, message)
            
            # Analyze media content
            if analyze_content:
                logger.info(f"Analyzing {media_type} file: {file_path}")
                
                # Call the appropriate plugin
                analysis_result = self.plugins[plugin_key].analyze_media(file_path, progress_wrapper)
                
                # Update result with analysis data
                result.update(analysis_result)
            
            # Perform transcription if requested
            if transcribe and 'transcription_service' in self.plugins:
                progress_data['stage'] = 'transcription'
                logger.info(f"Transcribing {media_type} file: {file_path}")
                
                # Call the transcription plugin
                transcription_result = self.plugins['transcription_service'].transcribe(
                    file_path, callback=progress_wrapper)
                
                # Update result with transcription data
                result['transcription'] = transcription_result
            
            # Mark as successful if we have metadata
            if 'metadata' in result:
                result['success'] = True
            else:
                result['success'] = False
                result['error'] = "Failed to analyze media"
                
            # Update operation status
            self.current_operations[file_id] = {'status': 'completed', 'progress': 100}
            
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing media file {file_path}: {e}")
            
            # Update operation status
            self.current_operations[file_id] = {'status': 'error', 'progress': 0, 'error': str(e)}
            
            return {
                'media_type': media_type,
                'file_path': file_path,
                'file_ext': file_ext,
                'success': False,
                'error': str(e)
            }
    
    def transcribe_media(self, file_path: str, provider: Optional[str] = None, 
                       language: Optional[str] = None, callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        Transcribe a media file using the transcription service plugin.
        
        Args:
            file_path: Path to the media file
            provider: Optional transcription provider to use
            language: Optional language code
            callback: Optional progress callback function
            
        Returns:
            Dictionary with transcription results
        """
        if 'transcription_service' not in self.plugins:
            return {
                'success': False,
                'error': "No transcription service plugin available"
            }
        
        if not os.path.exists(file_path):
            return {
                'success': False,
                'error': f"File not found: {file_path}"
            }
        
        # Extract file extension
        _, file_ext = os.path.splitext(file_path)
        file_ext = file_ext.lower()
        
        # Check if file type is supported
        if file_ext not in self.audio_extensions and file_ext not in self.video_extensions:
            return {
                'success': False,
                'error': f"Unsupported file extension for transcription: {file_ext}"
            }
        
        try:
            # Track current operation for this file
            file_id = os.path.basename(file_path)
            self.current_operations[file_id] = {'status': 'transcribing', 'progress': 0}
            
            # Define progress callback wrapper
            def progress_wrapper(current, total, message):
                if callback:
                    self.current_operations[file_id] = {'status': message, 'progress': current}
                    callback(current, total, message)
            
            # Call the transcription plugin
            result = self.plugins['transcription_service'].transcribe(
                file_path, provider=provider, language=language, callback=progress_wrapper)
            
            # Update operation status
            self.current_operations[file_id] = {'status': 'completed', 'progress': 100}
            
            return result
            
        except Exception as e:
            logger.error(f"Error transcribing media file {file_path}: {e}")
            
            # Update operation status
            self.current_operations[file_id] = {'status': 'error', 'progress': 0, 'error': str(e)}
            
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_operation_status(self, file_id: str) -> Dict[str, Any]:
        """
        Get the status of a current operation.
        
        Args:
            file_id: File identifier (typically the filename)
            
        Returns:
            Dictionary with operation status information
        """
        if file_id in self.current_operations:
            return self.current_operations[file_id]
        else:
            return {'status': 'unknown', 'progress': 0}
    
    def get_available_providers(self) -> Dict[str, List[str]]:
        """
        Get available providers for each plugin type.
        
        Returns:
            Dictionary mapping plugin types to lists of available providers
        """
        providers = {}
        
        # Check transcription providers
        if 'transcription_service' in self.plugins:
            # Build list of available providers based on available libraries
            available_providers = []
            
            if hasattr(self.plugins['transcription_service'], 'whisper_available') and \
               self.plugins['transcription_service'].whisper_available:
                available_providers.append('whisper')
                
            if hasattr(self.plugins['transcription_service'], 'sr_available') and \
               self.plugins['transcription_service'].sr_available:
                available_providers.extend(['google', 'azure'])
            
            # Always add mock provider for testing
            available_providers.append('mock')
            
            providers['transcription'] = available_providers
        
        return providers
    
    def get_supported_extensions(self) -> Dict[str, List[str]]:
        """
        Get supported file extensions for each media type.
        
        Returns:
            Dictionary mapping media types to lists of supported extensions
        """
        return {
            'audio': self.audio_extensions,
            'video': self.video_extensions,
            'media': self.audio_extensions + self.video_extensions
        }
    
    def get_cache_statistics(self) -> Dict[str, Dict[str, Any]]:
        """
        Get cache statistics for all plugins.
        
        Returns:
            Dictionary mapping plugin names to cache statistics
        """
        stats = {}
        
        for plugin_key, plugin in self.plugins.items():
            if hasattr(plugin, 'cache') and hasattr(plugin.cache, 'get_stats'):
                stats[plugin_key] = plugin.cache.get_stats()
        
        return stats
    
    def clear_caches(self) -> Dict[str, bool]:
        """
        Clear all plugin caches.
        
        Returns:
            Dictionary mapping plugin names to cache clear success status
        """
        results = {}
        
        for plugin_key, plugin in self.plugins.items():
            if hasattr(plugin, 'cache') and hasattr(plugin.cache, 'clear'):
                results[plugin_key] = plugin.cache.clear()
        
        return results