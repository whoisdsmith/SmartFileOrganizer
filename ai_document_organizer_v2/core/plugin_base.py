"""
Base plugin class for AI Document Organizer V2.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


logger = logging.getLogger(__name__)


class PluginBase(ABC):
    """
    Base class for all plugins in the AI Document Organizer V2.
    
    This abstract class defines the interface that all plugins must implement.
    """
    
    # Plugin metadata - should be defined by subclasses
    plugin_name = "base_plugin"
    plugin_version = "0.1.0"
    plugin_description = "Base plugin class"
    plugin_author = "AI Document Organizer Team"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the plugin.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.enabled = False
        self.initialized = False
    
    def get_info(self) -> Dict[str, Any]:
        """
        Get information about the plugin.
        
        Returns:
            Dictionary with plugin information
        """
        return {
            "name": self.plugin_name,
            "version": self.plugin_version,
            "description": self.plugin_description,
            "author": self.plugin_author,
            "enabled": self.enabled,
            "initialized": self.initialized
        }
    
    def initialize(self) -> bool:
        """
        Initialize the plugin.
        
        Returns:
            True if initialization was successful, False otherwise
        """
        logger.info(f"Initializing plugin: {self.plugin_name}")
        self.initialized = True
        return True
    
    def activate(self) -> bool:
        """
        Activate the plugin.
        
        Returns:
            True if activation was successful, False otherwise
        """
        if not self.initialized:
            logger.warning(f"Plugin {self.plugin_name} is not initialized")
            return False
        
        logger.info(f"Activating plugin: {self.plugin_name}")
        self.enabled = True
        return True
    
    def deactivate(self) -> bool:
        """
        Deactivate the plugin.
        
        Returns:
            True if deactivation was successful, False otherwise
        """
        logger.info(f"Deactivating plugin: {self.plugin_name}")
        self.enabled = False
        return True
    
    @abstractmethod
    def shutdown(self) -> bool:
        """
        Shutdown the plugin and clean up resources.
        
        Returns:
            True if shutdown was successful, False otherwise
        """
        pass
    
    def get_config(self) -> Dict[str, Any]:
        """
        Get the plugin configuration.
        
        Returns:
            Configuration dictionary
        """
        return self.config
    
    def set_config(self, config: Dict[str, Any]) -> bool:
        """
        Set the plugin configuration.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            True if configuration was set successfully, False otherwise
        """
        self.config = config
        return True
    
    def is_enabled(self) -> bool:
        """
        Check if the plugin is enabled.
        
        Returns:
            True if enabled, False otherwise
        """
        return self.enabled
    
    def is_initialized(self) -> bool:
        """
        Check if the plugin is initialized.
        
        Returns:
            True if initialized, False otherwise
        """
        return self.initialized
    
    def get_dependencies(self) -> List[str]:
        """
        Get the list of plugin dependencies.
        
        Returns:
            List of plugin names that this plugin depends on
        """
        return []
    
    def validate_config(self, config: Optional[Dict[str, Any]] = None) -> Dict[str, List[str]]:
        """
        Validate the plugin configuration.
        
        Args:
            config: Optional configuration dictionary to validate
            
        Returns:
            Dictionary with validation errors by configuration key
        """
        # Default implementation: no validation
        return {}
    
    def get_default_config(self) -> Dict[str, Any]:
        """
        Get the default plugin configuration.
        
        Returns:
            Default configuration dictionary
        """
        return {}
    
    def reset_config(self) -> bool:
        """
        Reset the plugin configuration to default values.
        
        Returns:
            True if reset was successful, False otherwise
        """
        self.config = self.get_default_config()
        return True