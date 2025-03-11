"""
Settings Manager Module for AI Document Organizer V2.

This module provides a central settings management system for the application,
allowing for persistent configuration across sessions and components.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List, Union
from pathlib import Path

logger = logging.getLogger(__name__)

class SettingsManager:
    """
    Manages application settings and configuration.
    
    This class provides methods for loading, saving, and accessing application
    settings from a JSON file, with support for plugin-specific settings.
    """
    
    DEFAULT_SETTINGS_FILE = "settings.json"
    
    def __init__(self, settings_file: Optional[str] = None):
        """
        Initialize the settings manager.
        
        Args:
            settings_file: Optional path to the settings file
        """
        self.settings_file = settings_file or SettingsManager.DEFAULT_SETTINGS_FILE
        self._settings = {}
        self._load_settings()
    
    def _load_settings(self) -> bool:
        """
        Load settings from the settings file.
        
        Returns:
            True if settings were loaded successfully, False otherwise
        """
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    self._settings = json.load(f)
                logger.info(f"Settings loaded from {self.settings_file}")
                return True
            else:
                logger.info(f"Settings file {self.settings_file} not found, using defaults")
                self._settings = self._get_default_settings()
                return False
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
            self._settings = self._get_default_settings()
            return False
    
    def save_settings(self) -> bool:
        """
        Save settings to the settings file.
        
        Returns:
            True if settings were saved successfully, False otherwise
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(os.path.abspath(self.settings_file)), exist_ok=True)
            
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self._settings, f, indent=2)
            logger.info(f"Settings saved to {self.settings_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            return False
    
    def _get_default_settings(self) -> Dict[str, Any]:
        """
        Get default settings.
        
        Returns:
            Dictionary containing default settings
        """
        return {
            "general": {
                "theme": "system",
                "language": "en",
                "debug_mode": False,
                "auto_update": True,
                "startup_check": True,
                "max_threads": 4,
                "memory_limit_mb": 1024,
                "log_level": "INFO"
            },
            "file_analyzer": {
                "batch_size": 10,
                "batch_delay": 0.1,
                "exclude_hidden": True,
                "exclude_system": True,
                "exclude_extensions": [".tmp", ".bak", ".swp"],
                "max_file_size_mb": 100,
                "analyze_content": True,
                "generate_thumbnails": True,
                "thumbnail_size": 256
            },
            "ai_services": {
                "primary_service": "google",
                "google_api_key": "",
                "openai_api_key": "",
                "azure_api_key": "",
                "model_name": "models/gemini-1.5-pro",
                "max_tokens": 1024,
                "temperature": 0.7,
                "enable_content_safety": True
            },
            "organizer": {
                "create_category_folders": True,
                "generate_summaries": True,
                "include_metadata": True,
                "copy_instead_of_move": True,
                "handle_duplicates": "ask",
                "apply_tags": False,
                "suggest_tags": False,
                "folder_structure": "category/date"
            },
            "media": {
                "extract_audio_from_video": True,
                "generate_video_thumbnails": True,
                "generate_audio_waveforms": True,
                "video_thumbnail_interval": 10,
                "audio_analysis_detail": "medium",
                "transcribe_audio": False,
                "transcription_service": "whisper",
                "max_audio_duration": 600,
                "max_video_duration": 3600
            },
            "database": {
                "connector": "sqlite",
                "sqlite": {
                    "database_path": "document_organizer.db",
                    "create_db_dir": True,
                    "timeout": 5.0
                },
                "mysql": {
                    "host": "localhost",
                    "port": 3306,
                    "database": "document_organizer",
                    "user": "",
                    "password": "",
                    "charset": "utf8mb4"
                },
                "postgresql": {
                    "host": "localhost",
                    "port": 5432,
                    "database": "document_organizer",
                    "user": "",
                    "password": "",
                    "sslmode": "prefer"
                },
                "mongodb": {
                    "uri": "mongodb://localhost:27017/",
                    "database": "document_organizer",
                    "collection_prefix": "doc_org_"
                }
            },
            "cloud_storage": {
                "provider": "google_drive",
                "google_drive": {
                    "credentials_file": "credentials.json",
                    "token_file": "token.json",
                    "client_id": "",
                    "client_secret": "",
                    "scopes": ["https://www.googleapis.com/auth/drive"],
                    "cache_size_mb": 100,
                    "upload_chunk_size_mb": 5,
                    "download_chunk_size_mb": 5
                },
                "onedrive": {
                    "client_id": "",
                    "client_secret": "",
                    "redirect_uri": "http://localhost:8000/callback",
                    "scopes": ["Files.ReadWrite.All"],
                    "token_file": "onedrive_token.json"
                },
                "dropbox": {
                    "app_key": "",
                    "app_secret": "",
                    "refresh_token": "",
                    "token_file": "dropbox_token.json"
                },
                "s3": {
                    "access_key": "",
                    "secret_key": "",
                    "region": "us-east-1",
                    "bucket": "document-organizer",
                    "endpoint_url": ""
                }
            },
            "plugins": {
                "enabled_plugins": [],
                "plugin_directory": "plugins"
            }
        }
    
    def get_all_settings(self) -> Dict[str, Any]:
        """
        Get all settings.
        
        Returns:
            Dictionary containing all settings
        """
        return self._settings
    
    def get_setting(self, path: str, default: Any = None) -> Any:
        """
        Get a setting value using a dot-separated path.
        
        Args:
            path: Dot-separated path to the setting (e.g., "general.theme")
            default: Default value to return if the setting is not found
            
        Returns:
            Setting value or default if not found
        """
        parts = path.split('.')
        
        # Start with the root settings dictionary
        current = self._settings
        
        # Traverse the path
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return default
        
        return current
    
    def set_setting(self, path: str, value: Any) -> bool:
        """
        Set a setting value using a dot-separated path.
        
        Args:
            path: Dot-separated path to the setting (e.g., "general.theme")
            value: Value to set
            
        Returns:
            True if the setting was set successfully, False otherwise
        """
        parts = path.split('.')
        
        # Start with the root settings dictionary
        current = self._settings
        
        # Traverse the path, creating dictionaries as needed
        for i, part in enumerate(parts[:-1]):
            if part not in current or not isinstance(current[part], dict):
                current[part] = {}
            current = current[part]
        
        # Set the value
        current[parts[-1]] = value
        return True
    
    def delete_setting(self, path: str) -> bool:
        """
        Delete a setting using a dot-separated path.
        
        Args:
            path: Dot-separated path to the setting (e.g., "general.theme")
            
        Returns:
            True if the setting was deleted successfully, False otherwise
        """
        parts = path.split('.')
        
        # Start with the root settings dictionary
        current = self._settings
        
        # Traverse the path
        for i, part in enumerate(parts[:-1]):
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return False
        
        # Delete the setting
        if isinstance(current, dict) and parts[-1] in current:
            del current[parts[-1]]
            return True
        else:
            return False
    
    def get_plugin_settings(self, plugin_name: str) -> Dict[str, Any]:
        """
        Get settings for a specific plugin.
        
        Args:
            plugin_name: Name of the plugin
            
        Returns:
            Dictionary containing plugin settings
        """
        plugin_settings = self.get_setting(f"plugins.{plugin_name}", {})
        
        if not plugin_settings:
            # Create a new empty settings dictionary for this plugin
            self.set_setting(f"plugins.{plugin_name}", {})
            plugin_settings = {}
        
        return plugin_settings
    
    def set_plugin_setting(self, plugin_name: str, key: str, value: Any) -> bool:
        """
        Set a setting for a specific plugin.
        
        Args:
            plugin_name: Name of the plugin
            key: Setting key
            value: Setting value
            
        Returns:
            True if the setting was set successfully, False otherwise
        """
        return self.set_setting(f"plugins.{plugin_name}.{key}", value)
    
    def get_plugin_setting(self, plugin_name: str, key: str, default: Any = None) -> Any:
        """
        Get a setting for a specific plugin.
        
        Args:
            plugin_name: Name of the plugin
            key: Setting key
            default: Default value to return if the setting is not found
            
        Returns:
            Setting value or default if not found
        """
        return self.get_setting(f"plugins.{plugin_name}.{key}", default)
    
    def reset_to_defaults(self) -> bool:
        """
        Reset all settings to their default values.
        
        Returns:
            True if settings were reset successfully, False otherwise
        """
        self._settings = self._get_default_settings()
        return self.save_settings()
    
    def import_settings(self, file_path: str) -> bool:
        """
        Import settings from a JSON file.
        
        Args:
            file_path: Path to the JSON file
            
        Returns:
            True if settings were imported successfully, False otherwise
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
            
            # Merge with existing settings
            self._merge_settings(settings)
            
            logger.info(f"Settings imported from {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error importing settings: {e}")
            return False
    
    def export_settings(self, file_path: str) -> bool:
        """
        Export settings to a JSON file.
        
        Args:
            file_path: Path to save the JSON file
            
        Returns:
            True if settings were exported successfully, False otherwise
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self._settings, f, indent=2)
            
            logger.info(f"Settings exported to {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error exporting settings: {e}")
            return False
    
    def _merge_settings(self, settings: Dict[str, Any], target: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Recursively merge settings dictionaries.
        
        Args:
            settings: Settings dictionary to merge
            target: Target dictionary (defaults to self._settings)
            
        Returns:
            Merged settings dictionary
        """
        if target is None:
            target = self._settings
        
        for key, value in settings.items():
            if isinstance(value, dict) and isinstance(target.get(key), dict):
                # Recursively merge nested dictionaries
                self._merge_settings(value, target[key])
            else:
                # Replace or add the value
                target[key] = value
        
        return target