"""
Settings Manager Module for AI Document Organizer V2.

This module provides functionality to load, save, and manage application settings.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List, Union

logger = logging.getLogger("AIDocumentOrganizerV2.Settings")

class SettingsManager:
    """
    Class for managing application settings.
    
    This class provides functionality to:
    - Load settings from a file
    - Save settings to a file
    - Manage settings with dot notation access
    - Provide defaults for missing settings
    """
    
    def __init__(self, settings_file: Optional[str] = None):
        """
        Initialize the settings manager.
        
        Args:
            settings_file: Optional path to the settings file. If None, uses default location.
        """
        # Use the provided settings file or default to a standard location
        if settings_file is None:
            self.settings_dir = os.path.join(os.path.expanduser("~"), ".ai_document_organizer")
            os.makedirs(self.settings_dir, exist_ok=True)
            self.settings_file = os.path.join(self.settings_dir, "settings.json")
        else:
            self.settings_file = settings_file
            self.settings_dir = os.path.dirname(os.path.abspath(settings_file))
            os.makedirs(self.settings_dir, exist_ok=True)
        
        # Default settings
        self.settings = self._get_default_settings()
        
        # Load settings from file if it exists
        self._load_settings()
    
    def _get_default_settings(self) -> Dict[str, Any]:
        """
        Get default settings.
        
        Returns:
            Dictionary with default settings
        """
        return {
            "version": "2.0.0",
            "last_source_dir": os.path.expanduser("~/Documents"),
            "last_target_dir": os.path.expanduser("~/Documents/Organized"),
            "theme": "default",
            "plugins": {
                "enabled_plugins": [],
                "plugin_settings": {}
            },
            "batch_processing": {
                "batch_size": 10,
                "batch_delay": 0.1,
                "use_process_pool": True,
                "adaptive_workers": True,
                "max_workers": 4,
                "memory_limit_percent": 80,
                "enable_pause_resume": True,
                "save_job_state": True
            },
            "file_organization": {
                "create_category_folders": True,
                "generate_summaries": True,
                "include_metadata": True,
                "copy_instead_of_move": True,
                "detect_duplicates": False,
                "duplicate_action": "report",
                "duplicate_strategy": "newest",
                "apply_tags": False,
                "suggest_tags": False
            },
            "ai_service": {
                "provider": "google",
                "google_model": "models/gemini-2.0-flash",
                "openai_model": "gpt-4-turbo-preview",
                "request_rate_limit": 30
            }
        }
    
    def _load_settings(self) -> bool:
        """
        Load settings from file.
        
        Returns:
            True if settings were loaded successfully, False otherwise
        """
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    loaded_settings = json.load(f)
                
                # Update default settings with loaded values
                self._update_dict_recursive(self.settings, loaded_settings)
                logger.debug(f"Settings loaded from {self.settings_file}")
                return True
            else:
                logger.info("Settings file not found, using defaults")
                self.save_settings()  # Create the settings file
                return False
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
            # Save current settings to repair corrupted file
            self.save_settings()
            return False
    
    def save_settings(self) -> bool:
        """
        Save settings to file.
        
        Returns:
            True if settings were saved successfully, False otherwise
        """
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2)
            logger.info(f"Saved settings to {self.settings_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            return False
    
    def _update_dict_recursive(self, target: Dict, source: Dict) -> None:
        """
        Update target dictionary with values from source dictionary recursively.
        
        Args:
            target: Target dictionary to update
            source: Source dictionary with new values
        """
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._update_dict_recursive(target[key], value)
            else:
                target[key] = value
    
    def get_setting(self, key_path: str, default: Any = None) -> Any:
        """
        Get a setting value using dot notation.
        
        Args:
            key_path: Setting key path using dot notation (e.g., "plugins.enabled_plugins")
            default: Default value to return if setting not found
            
        Returns:
            Setting value or default if not found
        """
        keys = key_path.split('.')
        value = self.settings
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def set_setting(self, key_path: str, value: Any) -> bool:
        """
        Set a setting value using dot notation.
        
        Args:
            key_path: Setting key path using dot notation (e.g., "plugins.enabled_plugins")
            value: Value to set
            
        Returns:
            True if setting was set successfully, False otherwise
        """
        keys = key_path.split('.')
        target = self.settings
        
        try:
            # Navigate to the innermost dictionary
            for key in keys[:-1]:
                if key not in target:
                    target[key] = {}
                target = target[key]
            
            # Set the value
            target[keys[-1]] = value
            return True
        except Exception as e:
            logger.error(f"Error setting {key_path}: {e}")
            return False
    
    def get_plugin_setting(self, plugin_id: str, key: str, default: Any = None) -> Any:
        """
        Get a plugin-specific setting.
        
        Args:
            plugin_id: Plugin identifier
            key: Setting key
            default: Default value if setting not found
            
        Returns:
            Setting value or default if not found
        """
        plugin_settings = self.settings.get("plugins", {}).get("plugin_settings", {})
        if plugin_id in plugin_settings and key in plugin_settings[plugin_id]:
            return plugin_settings[plugin_id][key]
        return default
    
    def set_plugin_setting(self, plugin_id: str, key: str, value: Any) -> bool:
        """
        Set a plugin-specific setting.
        
        Args:
            plugin_id: Plugin identifier
            key: Setting key
            value: Setting value
            
        Returns:
            True if setting was set successfully, False otherwise
        """
        if "plugins" not in self.settings:
            self.settings["plugins"] = {}
        
        if "plugin_settings" not in self.settings["plugins"]:
            self.settings["plugins"]["plugin_settings"] = {}
        
        if plugin_id not in self.settings["plugins"]["plugin_settings"]:
            self.settings["plugins"]["plugin_settings"][plugin_id] = {}
        
        self.settings["plugins"]["plugin_settings"][plugin_id][key] = value
        return True
    
    def get_enabled_plugins(self) -> List[str]:
        """
        Get list of enabled plugin IDs.
        
        Returns:
            List of enabled plugin IDs
        """
        return self.settings.get("plugins", {}).get("enabled_plugins", [])
    
    def enable_plugin(self, plugin_id: str) -> bool:
        """
        Enable a plugin.
        
        Args:
            plugin_id: Plugin identifier
            
        Returns:
            True if plugin was enabled successfully, False otherwise
        """
        if "plugins" not in self.settings:
            self.settings["plugins"] = {}
        
        if "enabled_plugins" not in self.settings["plugins"]:
            self.settings["plugins"]["enabled_plugins"] = []
        
        if plugin_id not in self.settings["plugins"]["enabled_plugins"]:
            self.settings["plugins"]["enabled_plugins"].append(plugin_id)
        
        return True
    
    def disable_plugin(self, plugin_id: str) -> bool:
        """
        Disable a plugin.
        
        Args:
            plugin_id: Plugin identifier
            
        Returns:
            True if plugin was disabled successfully, False otherwise
        """
        if "plugins" in self.settings and "enabled_plugins" in self.settings["plugins"]:
            if plugin_id in self.settings["plugins"]["enabled_plugins"]:
                self.settings["plugins"]["enabled_plugins"].remove(plugin_id)
        
        return True
    
    def is_plugin_enabled(self, plugin_id: str) -> bool:
        """
        Check if a plugin is enabled.
        
        Args:
            plugin_id: Plugin identifier
            
        Returns:
            True if the plugin is enabled, False otherwise
        """
        enabled_plugins = self.get_enabled_plugins()
        return plugin_id in enabled_plugins