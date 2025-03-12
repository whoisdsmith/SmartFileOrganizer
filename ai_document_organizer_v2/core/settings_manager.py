"""
Settings manager for AI Document Organizer V2.

Provides management of application settings and user preferences.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional, Union


logger = logging.getLogger(__name__)


class SettingsManager:
    """
    Manages application settings and user preferences.
    
    This class is responsible for:
    - Loading settings from file
    - Saving settings to file
    - Providing access to settings values
    - Validating settings values
    """
    
    def __init__(self, settings_file: str = None):
        """
        Initialize the settings manager.
        
        Args:
            settings_file: Path to the settings file
        """
        # Default settings file location
        self.settings_file = settings_file or os.path.join(
            os.path.expanduser("~"),
            ".ai_document_organizer",
            "settings.json"
        )
        
        # Default settings
        self.settings = self._get_default_settings()
        
        # Load settings from file if it exists
        self.load_settings()
    
    def _get_default_settings(self) -> Dict[str, Any]:
        """
        Get default settings.
        
        Returns:
            Dictionary with default settings
        """
        return {
            "general": {
                "theme": "light",
                "language": "en",
                "debug_mode": False,
                "auto_update": True,
                "save_session": True
            },
            "files": {
                "default_source_dir": os.path.expanduser("~/Documents"),
                "default_target_dir": os.path.expanduser("~/Documents/Organized"),
                "create_category_folders": True,
                "copy_instead_of_move": True,
                "handle_duplicates": "ask",  # "ask", "keep_both", "keep_newest", "keep_oldest"
                "generate_summaries": True,
                "include_metadata": True
            },
            "batch_processing": {
                "batch_size": 10,
                "batch_delay": 0.5,
                "max_workers": 4,
                "adaptive_resources": True,
                "memory_limit_percent": 75,
                "cpu_limit_percent": 80
            },
            "ai": {
                "service": "gemini",  # "gemini", "openai", etc.
                "gemini_model": "gemini-1.5-pro",
                "openai_model": "gpt-4-turbo",
                "max_requests_per_minute": 50,
                "max_tokens": 8192,
                "temperature": 0.7,
                "generate_tags": True,
                "suggest_categories": True,
                "content_summary_length": "medium"  # "short", "medium", "long"
            },
            "plugins": {
                "enabled_plugins": [],
                "plugin_settings": {}
            },
            "advanced": {
                "logging_level": "INFO",  # "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"
                "cache_dir": os.path.join(
                    os.path.expanduser("~"),
                    ".ai_document_organizer",
                    "cache"
                ),
                "max_cache_size_mb": 1024,
                "clear_cache_on_exit": False,
                "encryption_enabled": False,
                "database_path": os.path.join(
                    os.path.expanduser("~"),
                    ".ai_document_organizer",
                    "database.db"
                )
            }
        }
    
    def load_settings(self, settings_file: str = None) -> bool:
        """
        Load settings from file.
        
        Args:
            settings_file: Optional path to the settings file
            
        Returns:
            True if settings were loaded successfully, False otherwise
        """
        file_path = settings_file or self.settings_file
        
        if not os.path.exists(file_path):
            logger.info(f"Settings file not found: {file_path}")
            return False
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                file_settings = json.load(f)
            
            # Merge with default settings
            self._merge_settings(file_settings)
            logger.info(f"Settings loaded from: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to load settings from {file_path}: {e}")
            return False
    
    def save_settings(self, settings_file: str = None) -> bool:
        """
        Save settings to file.
        
        Args:
            settings_file: Optional path to the settings file
            
        Returns:
            True if settings were saved successfully, False otherwise
        """
        file_path = settings_file or self.settings_file
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4)
            
            logger.info(f"Settings saved to: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save settings to {file_path}: {e}")
            return False
    
    def _merge_settings(self, new_settings: Dict[str, Any]) -> None:
        """
        Merge new settings with existing settings.
        
        Args:
            new_settings: New settings to merge
        """
        # Helper function to recursively merge dictionaries
        def merge_dicts(target, source):
            for key, value in source.items():
                if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                    merge_dicts(target[key], value)
                else:
                    target[key] = value
        
        merge_dicts(self.settings, new_settings)
    
    def get_setting(self, path: str, default: Any = None) -> Any:
        """
        Get a setting value by path.
        
        Args:
            path: Path to the setting (e.g., "general.theme")
            default: Default value to return if the setting is not found
            
        Returns:
            Setting value or default if not found
        """
        parts = path.split('.')
        current = self.settings
        
        try:
            for part in parts:
                current = current[part]
            return current
        except (KeyError, TypeError):
            return default
    
    def set_setting(self, path: str, value: Any) -> bool:
        """
        Set a setting value by path.
        
        Args:
            path: Path to the setting (e.g., "general.theme")
            value: Value to set
            
        Returns:
            True if the setting was set successfully, False otherwise
        """
        parts = path.split('.')
        current = self.settings
        
        try:
            # Navigate to the parent of the target setting
            for part in parts[:-1]:
                if part not in current or not isinstance(current[part], dict):
                    current[part] = {}
                current = current[part]
            
            # Set the value
            current[parts[-1]] = value
            return True
        except Exception as e:
            logger.error(f"Failed to set setting {path}: {e}")
            return False
    
    def delete_setting(self, path: str) -> bool:
        """
        Delete a setting by path.
        
        Args:
            path: Path to the setting (e.g., "general.theme")
            
        Returns:
            True if the setting was deleted successfully, False otherwise
        """
        parts = path.split('.')
        current = self.settings
        
        try:
            # Navigate to the parent of the target setting
            for part in parts[:-1]:
                current = current[part]
            
            # Delete the setting
            if parts[-1] in current:
                del current[parts[-1]]
                return True
            else:
                return False
        except (KeyError, TypeError):
            return False
    
    def reset_settings(self) -> None:
        """Reset settings to defaults."""
        self.settings = self._get_default_settings()
    
    def reset_section(self, section: str) -> bool:
        """
        Reset a settings section to defaults.
        
        Args:
            section: Section name to reset
            
        Returns:
            True if the section was reset successfully, False otherwise
        """
        if section in self._get_default_settings():
            self.settings[section] = self._get_default_settings()[section]
            return True
        else:
            return False
    
    def get_all_settings(self) -> Dict[str, Any]:
        """
        Get all settings.
        
        Returns:
            Dictionary with all settings
        """
        return self.settings
    
    def get_section(self, section: str) -> Optional[Dict[str, Any]]:
        """
        Get a settings section.
        
        Args:
            section: Section name
            
        Returns:
            Dictionary with section settings or None if not found
        """
        return self.settings.get(section)
    
    def validate_settings(self) -> Dict[str, List[str]]:
        """
        Validate all settings.
        
        Returns:
            Dictionary with validation errors by section
        """
        errors = {}
        
        # Validate general settings
        general_errors = []
        general = self.get_section("general")
        if general:
            if "theme" in general and general["theme"] not in ["light", "dark", "system"]:
                general_errors.append("Invalid theme value. Must be 'light', 'dark', or 'system'.")
            if "language" in general and not isinstance(general["language"], str):
                general_errors.append("Invalid language value. Must be a string.")
            if "debug_mode" in general and not isinstance(general["debug_mode"], bool):
                general_errors.append("Invalid debug_mode value. Must be a boolean.")
        
        if general_errors:
            errors["general"] = general_errors
        
        # Validate batch processing settings
        batch_errors = []
        batch = self.get_section("batch_processing")
        if batch:
            if "batch_size" in batch and (not isinstance(batch["batch_size"], int) or batch["batch_size"] <= 0):
                batch_errors.append("Invalid batch_size value. Must be a positive integer.")
            if "batch_delay" in batch and (not isinstance(batch["batch_delay"], (int, float)) or batch["batch_delay"] < 0):
                batch_errors.append("Invalid batch_delay value. Must be a non-negative number.")
            if "max_workers" in batch and (not isinstance(batch["max_workers"], int) or batch["max_workers"] <= 0):
                batch_errors.append("Invalid max_workers value. Must be a positive integer.")
        
        if batch_errors:
            errors["batch_processing"] = batch_errors
        
        # Validate AI settings
        ai_errors = []
        ai = self.get_section("ai")
        if ai:
            if "service" in ai and ai["service"] not in ["gemini", "openai", "local"]:
                ai_errors.append("Invalid service value. Must be 'gemini', 'openai', or 'local'.")
            if "temperature" in ai and (not isinstance(ai["temperature"], (int, float)) or 
                                     ai["temperature"] < 0 or ai["temperature"] > 1):
                ai_errors.append("Invalid temperature value. Must be a number between 0 and 1.")
        
        if ai_errors:
            errors["ai"] = ai_errors
        
        return errors
    
    def get_plugin_setting(self, plugin_name: str, key: str, default: Any = None) -> Any:
        """
        Get a plugin setting.
        
        Args:
            plugin_name: Name of the plugin
            key: Setting key
            default: Default value to return if the setting is not found
            
        Returns:
            Plugin setting value or default if not found
        """
        plugin_settings = self.get_setting(f"plugins.plugin_settings.{plugin_name}", {})
        return plugin_settings.get(key, default)
    
    def set_plugin_setting(self, plugin_name: str, key: str, value: Any) -> bool:
        """
        Set a plugin setting.
        
        Args:
            plugin_name: Name of the plugin
            key: Setting key
            value: Setting value
            
        Returns:
            True if the setting was set successfully, False otherwise
        """
        # Ensure plugin settings dict exists
        if "plugins" not in self.settings:
            self.settings["plugins"] = {}
        if "plugin_settings" not in self.settings["plugins"]:
            self.settings["plugins"]["plugin_settings"] = {}
        if plugin_name not in self.settings["plugins"]["plugin_settings"]:
            self.settings["plugins"]["plugin_settings"][plugin_name] = {}
        
        # Set the value
        self.settings["plugins"]["plugin_settings"][plugin_name][key] = value
        return True
    
    def is_plugin_enabled(self, plugin_name: str) -> bool:
        """
        Check if a plugin is enabled.
        
        Args:
            plugin_name: Name of the plugin
            
        Returns:
            True if the plugin is enabled, False otherwise
        """
        enabled_plugins = self.get_setting("plugins.enabled_plugins", [])
        return plugin_name in enabled_plugins
    
    def enable_plugin(self, plugin_name: str) -> bool:
        """
        Enable a plugin.
        
        Args:
            plugin_name: Name of the plugin
            
        Returns:
            True if the plugin was enabled successfully, False otherwise
        """
        enabled_plugins = self.get_setting("plugins.enabled_plugins", [])
        if plugin_name not in enabled_plugins:
            enabled_plugins.append(plugin_name)
            return self.set_setting("plugins.enabled_plugins", enabled_plugins)
        return True
    
    def disable_plugin(self, plugin_name: str) -> bool:
        """
        Disable a plugin.
        
        Args:
            plugin_name: Name of the plugin
            
        Returns:
            True if the plugin was disabled successfully, False otherwise
        """
        enabled_plugins = self.get_setting("plugins.enabled_plugins", [])
        if plugin_name in enabled_plugins:
            enabled_plugins.remove(plugin_name)
            return self.set_setting("plugins.enabled_plugins", enabled_plugins)
        return True
    
    def get_enabled_plugins(self) -> List[str]:
        """
        Get list of enabled plugins.
        
        Returns:
            List of enabled plugin names
        """
        return self.get_setting("plugins.enabled_plugins", [])