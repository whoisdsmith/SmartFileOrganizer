"""
Plugin Base Module for AI Document Organizer V2.

This module defines the base classes for the plugin system,
providing a flexible architecture for extending functionality.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple, Union, TYPE_CHECKING

if TYPE_CHECKING:
    from .settings import SettingsManager

logger = logging.getLogger(__name__)

class PluginBase(ABC):
    """
    Base class for all plugins in the AI Document Organizer.
    
    This abstract class defines the common interface and functionality
    that all plugins must implement, ensuring consistency across
    different plugin types.
    """
    
    # Class attributes that should be overridden by subclasses
    plugin_name = "base_plugin"
    plugin_description = "Base plugin class"
    plugin_version = "1.0.0"
    plugin_type = "base"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the plugin with optional configuration.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.settings_manager: Optional['SettingsManager'] = None
    
    def initialize(self) -> bool:
        """
        Initialize the plugin. Override this method for custom initialization.
        
        Returns:
            True if initialization was successful, False otherwise
        """
        return True
    
    def shutdown(self) -> bool:
        """
        Shutdown the plugin and release resources. Override this method
        for custom shutdown logic.
        
        Returns:
            True if shutdown was successful, False otherwise
        """
        return True
    
    def get_info(self) -> Dict[str, Any]:
        """
        Get information about the plugin.
        
        Returns:
            Dictionary with plugin information
        """
        return {
            "name": self.plugin_name,
            "description": self.plugin_description,
            "version": self.plugin_version,
            "type": self.plugin_type
        }
    
    def is_compatible(self, version: str) -> bool:
        """
        Check if the plugin is compatible with a specific version.
        
        Args:
            version: Version string to check compatibility with
            
        Returns:
            True if compatible, False otherwise
        """
        # Basic implementation - should be overridden for version-specific checks
        return True
    
    def configure(self, config: Dict[str, Any]) -> bool:
        """
        Configure the plugin with new settings.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            True if configuration was successful, False otherwise
        """
        self.config.update(config)
        return True
    
    def get_config(self) -> Dict[str, Any]:
        """
        Get the current plugin configuration.
        
        Returns:
            Dictionary with current configuration
        """
        return self.config
    
    def get_default_config(self) -> Dict[str, Any]:
        """
        Get the default plugin configuration.
        
        Returns:
            Dictionary with default configuration values
        """
        return {}
    
    def validate_config(self, config: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validate a configuration dictionary.
        
        Args:
            config: Configuration dictionary to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Basic implementation - should be overridden for specific validation
        return True, None