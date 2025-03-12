"""
Base class for plugins in the AI Document Organizer V2.

All plugins should inherit from this class.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class PluginBase(ABC):
    """
    Abstract base class for all plugins in the system.
    
    This class defines the interface that all plugins must implement.
    """
    
    plugin_name = "plugin_base"
    plugin_version = "1.0.0"
    plugin_description = "Base class for plugins"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the plugin.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.enabled = False
    
    @abstractmethod
    def initialize(self) -> bool:
        """
        Initialize the plugin. This is called after the plugin is loaded.
        
        Returns:
            True if initialization was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def shutdown(self) -> bool:
        """
        Shutdown the plugin. This is called before the plugin is unloaded.
        
        Returns:
            True if shutdown was successful, False otherwise
        """
        pass
    
    def activate(self) -> bool:
        """
        Activate the plugin. This is called when the plugin is enabled.
        
        Returns:
            True if activation was successful, False otherwise
        """
        self.enabled = True
        return True
    
    def deactivate(self) -> bool:
        """
        Deactivate the plugin. This is called when the plugin is disabled.
        
        Returns:
            True if deactivation was successful, False otherwise
        """
        self.enabled = False
        return True
    
    def get_name(self) -> str:
        """
        Get the plugin name.
        
        Returns:
            Plugin name
        """
        return self.plugin_name
    
    def get_version(self) -> str:
        """
        Get the plugin version.
        
        Returns:
            Plugin version
        """
        return self.plugin_version
    
    def get_description(self) -> str:
        """
        Get the plugin description.
        
        Returns:
            Plugin description
        """
        return self.plugin_description
    
    def get_type(self) -> str:
        """
        Get the plugin type.
        
        Returns:
            Plugin type
        """
        return "base"
    
    def get_capabilities(self) -> List[str]:
        """
        Get the plugin capabilities.
        
        Returns:
            List of capability strings
        """
        return []
    
    def get_config(self) -> Dict[str, Any]:
        """
        Get the plugin configuration.
        
        Returns:
            Plugin configuration dictionary
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
    
    def update_config(self, config_updates: Dict[str, Any]) -> bool:
        """
        Update the plugin configuration with the provided updates.
        
        Args:
            config_updates: Dictionary with configuration updates
            
        Returns:
            True if configuration was updated successfully, False otherwise
        """
        self.config.update(config_updates)
        return True
    
    def is_enabled(self) -> bool:
        """
        Check if the plugin is enabled.
        
        Returns:
            True if the plugin is enabled, False otherwise
        """
        return self.enabled
    
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
            "type": self.get_type(),
            "capabilities": self.get_capabilities(),
            "enabled": self.is_enabled()
        }
    
    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a configuration dictionary for this plugin.
        
        Args:
            config: Configuration dictionary to validate
            
        Returns:
            Dictionary with validation results, including any errors
        """
        # Base implementation just returns success
        return {
            "valid": True,
            "errors": []
        }
    
    def __str__(self) -> str:
        """
        String representation of the plugin.
        
        Returns:
            String representation
        """
        return f"{self.plugin_name} (v{self.plugin_version}): {self.plugin_description}"