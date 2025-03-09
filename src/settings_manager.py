import os
import json
import logging
from pathlib import Path

logger = logging.getLogger("AIDocumentOrganizer")

class SettingsManager:
    """
    Manages application settings and user preferences
    """
    def __init__(self):
        """Initialize settings manager"""
        # Determine settings directory based on platform
        if os.name == 'nt':  # Windows
            self.settings_dir = os.path.join(os.path.expanduser("~"), "AppData", "Local", "AIDocumentOrganizer")
        else:  # macOS/Linux
            self.settings_dir = os.path.join(os.path.expanduser("~"), ".config", "AIDocumentOrganizer")
        
        # Create settings directory if it doesn't exist
        os.makedirs(self.settings_dir, exist_ok=True)
        
        # Path to settings file
        self.settings_file = os.path.join(self.settings_dir, "settings.json")
        
        # Default settings
        self.default_settings = {
            "batch_size": 20,
            "source_directory": os.path.expanduser(r"~\Documents"),
            "target_directory": os.path.expanduser(r"~\Documents\Organized"),
            "theme": "clam",
            "organization_rules": {
                "create_category_folders": True,
                "generate_summaries": True,
                "include_metadata": True,
                "copy_instead_of_move": True
            },
            "ai_service": {
                "service_type": "google",  # 'google' or 'openai'
                "google_api_key": "",      # Stored encrypted in actual implementation
                "openai_api_key": ""       # Stored encrypted in actual implementation
            }
        }
        
        # Load settings
        self.settings = self.load_settings()
    
    def load_settings(self):
        """Load settings from file"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)
                logger.info(f"Loaded settings from {self.settings_file}")
                
                # Merge with defaults in case new settings were added
                merged_settings = self.default_settings.copy()
                merged_settings.update(settings)
                return merged_settings
            else:
                logger.info("No settings file found, using defaults")
                return self.default_settings.copy()
        except Exception as e:
            logger.error(f"Error loading settings: {str(e)}")
            return self.default_settings.copy()
    
    def save_settings(self):
        """Save current settings to file"""
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(self.settings, f, indent=4)
            logger.info(f"Saved settings to {self.settings_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving settings: {str(e)}")
            return False
    
    def get_setting(self, key, default=None):
        """
        Get a setting value
        
        Args:
            key: Setting key (can use dot notation for nested settings)
            default: Default value if setting doesn't exist
            
        Returns:
            Setting value or default
        """
        try:
            # Handle nested settings with dot notation (e.g., "organization_rules.create_category_folders")
            if '.' in key:
                parts = key.split('.')
                value = self.settings
                for part in parts:
                    value = value.get(part, {})
                return value if value != {} else default
            else:
                return self.settings.get(key, default)
        except Exception as e:
            logger.error(f"Error getting setting {key}: {str(e)}")
            return default
    
    def set_setting(self, key, value):
        """
        Set a setting value
        
        Args:
            key: Setting key (can use dot notation for nested settings)
            value: Value to set
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Handle nested settings with dot notation
            if '.' in key:
                parts = key.split('.')
                setting_ref = self.settings
                for part in parts[:-1]:
                    if part not in setting_ref:
                        setting_ref[part] = {}
                    setting_ref = setting_ref[part]
                setting_ref[parts[-1]] = value
            else:
                self.settings[key] = value
            
            # Save settings immediately
            return self.save_settings()
        except Exception as e:
            logger.error(f"Error setting {key}: {str(e)}")
            return False