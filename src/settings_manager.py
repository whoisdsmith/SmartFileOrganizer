import os
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("AIDocumentOrganizer")


class SettingsManager:
    """
    Manages application settings and user preferences
    """

    DEFAULT_SETTINGS = {
        "batch_size": 5,
        "batch_delay": 10,
        "source_directory": os.path.expanduser(r"~\Documents"),
        "target_directory": os.path.expanduser(r"~\Documents\Organized"),
        "theme": "clam",
        "organization_rules": {
            "create_category_folders": True,
            "generate_summaries": True,
            "include_metadata": True,
            "copy_instead_of_move": True,
            "use_custom_rules": False,
            "rules_file": "",
            "detect_duplicates": False,
            "duplicate_action": "report",  # 'report', 'move', 'delete', 'keep_newest'
            "apply_tags": False,
            "suggest_tags": False
        },
        "ai_service": {
            "service_type": "google",  # 'google' or 'openai'
            "google_api_key": "",      # Stored encrypted in actual implementation
            "openai_api_key": "",      # Stored encrypted in actual implementation
            "google_model": "models/gemini-2.0-flash",  # Default Google model
            "openai_model": "gpt-4-turbo-preview",      # Default OpenAI model
            "requests_per_minute": 30,   # Default API rate limit
            "max_retries": 5            # Maximum number of retries for rate limit errors
        },
        "batch_processing": {
            "use_process_pool": True,     # Use process pool instead of thread pool
            "adaptive_workers": True,     # Adapt worker count based on system resources
            "max_workers": 4,             # Maximum number of workers
            "memory_limit_percent": 80,   # Memory usage limit percentage
            "enable_pause_resume": True,  # Enable pause/resume functionality
            "save_job_state": True        # Save job state for resuming later
        },
        "image_analysis": {
            "enabled": True,                  # Enable image analysis
            "extract_exif": True,             # Extract EXIF metadata
            "generate_thumbnails": True,      # Generate thumbnails
            # Thumbnail size [width, height]
            "thumbnail_size": [200, 200],
            "vision_api_enabled": False,      # Enable vision API integration
            "vision_api_provider": "google",  # 'google' or 'azure'
            # Vision API key (stored encrypted)
            "vision_api_key": "",
            "detect_objects": True,           # Detect objects in images
            # Detect faces in images (privacy concern)
            "detect_faces": False,
            # Extract text from images (OCR)
            "extract_text": True,
            "content_moderation": False       # Enable content moderation
        },
        "document_summarization": {
            "summary_length": "medium",       # 'short', 'medium', 'long'
            "extract_key_points": True,       # Extract key points
            "extract_action_items": True,     # Extract action items
            "generate_executive_summary": False,  # Generate executive summary
            "summary_file_format": "md"       # 'txt', 'md', 'html'
        },
        "advanced": {
            "debug_mode": False,
            "log_level": "INFO",
            "max_file_size_mb": 50,           # Maximum file size to process in MB
            "excluded_directories": ["node_modules", ".git", "__pycache__"],
            "excluded_file_patterns": ["~$*", "Thumbs.db", ".DS_Store"]
        },
        # OCR Settings
        'ocr_config': {
            'enabled': True,
            'default_engine': 'auto',  # 'auto', 'tesseract', or 'easyocr'
            'tesseract_path': 'tesseract',  # Path to Tesseract executable
            # Minimum confidence score (0-100) for OCR results
            'confidence_threshold': 60.0,
            'default_language': 'eng',  # Default OCR language
            'additional_languages': [],  # Additional languages to support
            'image_preprocessing': {
                'enabled': True,
                'deskew': True,
                'denoise': True,
                'contrast_enhancement': True
            },
            'pdf_handling': {
                'force_ocr': False,  # Force OCR even if text is extractable
                'max_pages': 100,  # Maximum pages to process in a single PDF
                'dpi': 300,  # DPI for PDF to image conversion
                'batch_size': 10  # Number of pages to process in parallel
            },
            'cache': {
                'enabled': True,
                'max_size_mb': 1000,  # Maximum cache size in MB
                'expiration_days': 30  # Cache expiration in days
            }
        }
    }

    def __init__(self, config_path: Optional[str] = None):
        """Initialize settings manager with optional config path."""
        self.logger = logging.getLogger(__name__)
        self.config_path = config_path or os.path.join(
            os.path.expanduser('~'),
            '.smartfileorganizer',
            'config.json'
        )
        self.settings = self.load_settings()

        # Determine settings directory based on platform
        if os.name == 'nt':  # Windows
            self.settings_dir = os.path.join(os.path.expanduser(
                "~"), "AppData", "Local", "AIDocumentOrganizer")
        else:  # macOS/Linux
            self.settings_dir = os.path.join(
                os.path.expanduser("~"), ".config", "AIDocumentOrganizer")

        # Create settings directory if it doesn't exist
        os.makedirs(self.settings_dir, exist_ok=True)

        # Path to settings file
        self.settings_file = os.path.join(self.settings_dir, "settings.json")

    def get_api_key(self, service_type):
        """
        Get API key for the specified service

        Args:
            service_type: Service type ('google' or 'openai')

        Returns:
            API key string or empty string if not set
        """
        if service_type == "google":
            return self.settings["ai_service"]["google_api_key"]
        elif service_type == "openai":
            return self.settings["ai_service"]["openai_api_key"]
        elif service_type == "vision":
            return self.settings["image_analysis"]["vision_api_key"]
        else:
            return ""

    def set_api_key(self, service_type, api_key):
        """
        Set API key for the specified service

        Args:
            service_type: Service type ('google', 'openai', or 'vision')
            api_key: API key to set

        Returns:
            True if successful, False otherwise
        """
        try:
            if service_type == "google":
                self.settings["ai_service"]["google_api_key"] = api_key
            elif service_type == "openai":
                self.settings["ai_service"]["openai_api_key"] = api_key
            elif service_type == "vision":
                self.settings["image_analysis"]["vision_api_key"] = api_key
            else:
                return False

            self.save_settings()
            return True
        except Exception as e:
            logger.error(f"Error setting API key: {str(e)}")
            return False

    def get_selected_model(self, service_type):
        """
        Get selected model for the specified service

        Args:
            service_type: Service type ('google' or 'openai')

        Returns:
            Model name string
        """
        if service_type == "google":
            return self.settings["ai_service"]["google_model"]
        elif service_type == "openai":
            return self.settings["ai_service"]["openai_model"]
        else:
            return ""

    def set_selected_model(self, service_type, model_name):
        """
        Set selected model for the specified service

        Args:
            service_type: Service type ('google' or 'openai')
            model_name: Model name to set

        Returns:
            True if successful, False otherwise
        """
        try:
            if service_type == "google":
                self.settings["ai_service"]["google_model"] = model_name
            elif service_type == "openai":
                self.settings["ai_service"]["openai_model"] = model_name
            else:
                return False

            self.save_settings()
            return True
        except Exception as e:
            logger.error(f"Error setting model: {str(e)}")
            return False

    def load_settings(self):
        """
        Load settings from file

        Returns:
            Dictionary with settings
        """
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    loaded_settings = json.load(f)

                # Merge with defaults to ensure all settings exist
                merged_settings = self.DEFAULT_SETTINGS.copy()
                self._deep_update(merged_settings, loaded_settings)
                return merged_settings
            else:
                return self.DEFAULT_SETTINGS.copy()
        except Exception as e:
            logger.error(f"Error loading settings: {str(e)}")
            return self.DEFAULT_SETTINGS.copy()

    def save_settings(self):
        """
        Save settings to file

        Returns:
            True if successful, False otherwise
        """
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(self.settings, f, indent=4)
            return True
        except Exception as e:
            logger.error(f"Error saving settings: {str(e)}")
            return False

    def get_setting(self, key, default=None):
        """
        Get a setting value by key

        Args:
            key: Setting key (can be nested using dot notation, e.g., 'ai_service.service_type')
            default: Default value to return if key not found

        Returns:
            Setting value or default if not found
        """
        try:
            # Handle nested keys
            if '.' in key:
                parts = key.split('.')
                value = self.settings
                for part in parts:
                    if part in value:
                        value = value[part]
                    else:
                        return default
                return value
            else:
                return self.settings.get(key, default)
        except Exception as e:
            logger.error(f"Error getting setting {key}: {str(e)}")
            return default

    def set_setting(self, key, value):
        """
        Set a setting value by key

        Args:
            key: Setting key (can be nested using dot notation, e.g., 'ai_service.service_type')
            value: Value to set

        Returns:
            True if successful, False otherwise
        """
        try:
            # Handle nested keys
            if '.' in key:
                parts = key.split('.')
                target = self.settings
                for part in parts[:-1]:
                    if part not in target:
                        target[part] = {}
                    target = target[part]
                target[parts[-1]] = value
            else:
                self.settings[key] = value

            self.save_settings()
            return True
        except Exception as e:
            logger.error(f"Error setting {key}: {str(e)}")
            return False

    def _deep_update(self, target, source):
        """
        Deep update a nested dictionary

        Args:
            target: Target dictionary to update
            source: Source dictionary with updates
        """
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_update(target[key], value)
            else:
                target[key] = value

    def get_batch_processing_settings(self):
        """
        Get batch processing settings

        Returns:
            Dictionary with batch processing settings
        """
        return self.settings.get("batch_processing", self.DEFAULT_SETTINGS["batch_processing"])

    def get_image_analysis_settings(self):
        """
        Get image analysis settings

        Returns:
            Dictionary with image analysis settings
        """
        return self.settings.get("image_analysis", self.DEFAULT_SETTINGS["image_analysis"])

    def get_organization_rules_settings(self):
        """
        Get organization rules settings

        Returns:
            Dictionary with organization rules settings
        """
        return self.settings.get("organization_rules", self.DEFAULT_SETTINGS["organization_rules"])

    def get_document_summarization_settings(self):
        """
        Get document summarization settings

        Returns:
            Dictionary with document summarization settings
        """
        return self.settings.get("document_summarization", self.DEFAULT_SETTINGS["document_summarization"])
