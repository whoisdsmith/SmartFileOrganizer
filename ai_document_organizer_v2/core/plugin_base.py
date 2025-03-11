"""
Plugin Base Module for AI Document Organizer V2.

This module defines the base plugin classes that all plugins must inherit from.
"""

import os
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Set, Type, Tuple, Union

logger = logging.getLogger("AIDocumentOrganizerV2.PluginBase")

class BasePlugin(ABC):
    """
    Base class for all plugins.
    
    All plugins must inherit from this class and implement required methods.
    """
    
    # Plugin type identifier (must be set by subclasses)
    plugin_type = None
    
    # Plugin metadata (can be overridden by subclasses)
    name = "Unknown Plugin"
    version = "1.0.0"
    description = ""
    author = "Unknown"
    dependencies = []
    
    def __init__(self, plugin_id: str, name: Optional[str] = None, version: Optional[str] = None, 
                 description: Optional[str] = None):
        """
        Initialize the plugin.
        
        Args:
            plugin_id: Unique identifier for the plugin
            name: Plugin name (if None, uses class attribute)
            version: Plugin version (if None, uses class attribute)
            description: Plugin description (if None, uses class attribute)
        """
        self.plugin_id = plugin_id
        self.name = name or self.__class__.name
        self.version = version or self.__class__.version
        self.description = description or self.__class__.description
        self.enabled = True
        self._config = {}
        # Will be set by PluginManager during registration
        self.settings_manager = None
        
        logger.debug(f"Initialized plugin {self.name} ({self.plugin_id})")
    
    def initialize(self) -> bool:
        """
        Initialize the plugin. Called after plugin is loaded.
        
        Subclasses can override this to perform initialization tasks.
        
        Returns:
            True if initialization was successful, False otherwise
        """
        return True
    
    def shutdown(self) -> bool:
        """
        Shutdown the plugin. Called before plugin is unloaded.
        
        Subclasses can override this to perform cleanup tasks.
        
        Returns:
            True if shutdown was successful, False otherwise
        """
        return True
    
    def get_config(self) -> Dict[str, Any]:
        """
        Get plugin configuration.
        
        Returns:
            Dictionary with plugin configuration
        """
        return self._config.copy()
    
    def set_config(self, config: Dict[str, Any]) -> bool:
        """
        Set plugin configuration.
        
        Args:
            config: Dictionary with plugin configuration
            
        Returns:
            True if configuration was set successfully, False otherwise
        """
        self._config = config.copy()
        return True
    
    def get_config_schema(self) -> Dict[str, Any]:
        """
        Get JSON schema for plugin configuration.
        
        Returns:
            Dictionary with JSON schema for plugin configuration
        """
        # Default implementation returns empty schema
        return {
            "type": "object",
            "properties": {},
            "required": []
        }
    
    def get_metadata(self) -> Dict[str, Any]:
        """
        Get plugin metadata.
        
        Returns:
            Dictionary with plugin metadata
        """
        return {
            "id": self.plugin_id,
            "type": self.plugin_type,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": getattr(self.__class__, "author", "Unknown"),
            "dependencies": getattr(self.__class__, "dependencies", []),
            "enabled": self.enabled
        }
    
    def __str__(self) -> str:
        return f"{self.name} ({self.plugin_id}) v{self.version}"
        
    def get_setting(self, key: str, default: Any = None) -> Any:
        """
        Get a setting value from the settings manager.
        
        Args:
            key: Setting key (can use dot notation for nested settings)
            default: Default value if setting doesn't exist
            
        Returns:
            Setting value or default if not found
        """
        if self.settings_manager is None:
            logger.warning(f"No settings manager available for plugin {self.name}")
            return default
        
        return self.settings_manager.get_setting(key, default)
        
    def set_setting(self, key: str, value: Any) -> bool:
        """
        Set a setting value in the settings manager.
        
        Args:
            key: Setting key (can use dot notation for nested settings)
            value: Value to set
            
        Returns:
            True if successful, False otherwise
        """
        if self.settings_manager is None:
            logger.warning(f"No settings manager available for plugin {self.name}")
            return False
        
        return self.settings_manager.set_setting(key, value)


class FileParserPlugin(BasePlugin):
    """
    Base class for file parser plugins.
    
    File parser plugins are responsible for parsing different file types and
    extracting text content and metadata.
    """
    
    plugin_type = "file_parser"
    
    # List of supported file extensions (must be set by subclasses)
    supported_extensions = []
    
    def __init__(self, plugin_id: str, name: Optional[str] = None, version: Optional[str] = None,
                 description: Optional[str] = None):
        """
        Initialize the file parser plugin.
        
        Args:
            plugin_id: Unique identifier for the plugin
            name: Plugin name (if None, uses class attribute)
            version: Plugin version (if None, uses class attribute)
            description: Plugin description (if None, uses class attribute)
        """
        super().__init__(plugin_id, name, version, description)
        
        # Make sure subclasses set supported_extensions
        if not hasattr(self.__class__, "supported_extensions") or not self.__class__.supported_extensions:
            self.supported_extensions = []
            logger.warning(f"Plugin {self.name} does not define supported_extensions")
        else:
            self.supported_extensions = self.__class__.supported_extensions
    
    @abstractmethod
    def parse_file(self, file_path: str) -> Dict[str, Any]:
        """
        Parse a file and extract content and metadata.
        
        Args:
            file_path: Path to the file to parse
            
        Returns:
            Dictionary containing:
            - 'content': Extracted text content
            - 'metadata': Dictionary with file metadata
            - 'success': Boolean indicating success/failure
            - 'error': Error message if parsing failed
        """
        pass
    
    def can_parse(self, file_path: str) -> bool:
        """
        Check if this plugin can parse the given file.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            True if this plugin can parse the file, False otherwise
        """
        _, ext = os.path.splitext(file_path)
        return ext.lower() in [x.lower() for x in self.supported_extensions]


class AIAnalyzerPlugin(BasePlugin):
    """
    Base class for AI analyzer plugins.
    
    AI analyzer plugins are responsible for analyzing document content
    using different AI models.
    """
    
    plugin_type = "ai_analyzer"
    
    def __init__(self, plugin_id: str, name: Optional[str] = None, version: Optional[str] = None,
                 description: Optional[str] = None):
        """
        Initialize the AI analyzer plugin.
        
        Args:
            plugin_id: Unique identifier for the plugin
            name: Plugin name (if None, uses class attribute)
            version: Plugin version (if None, uses class attribute)
            description: Plugin description (if None, uses class attribute)
        """
        super().__init__(plugin_id, name, version, description)
    
    @abstractmethod
    def analyze_content(self, text: str, file_type: str) -> Dict[str, Any]:
        """
        Analyze document content using AI.
        
        Args:
            text: Document text content
            file_type: Type of document (e.g., 'txt', 'pdf', 'docx')
            
        Returns:
            Dictionary with analysis results
        """
        pass
    
    def get_available_models(self) -> List[str]:
        """
        Get list of available AI models.
        
        Returns:
            List of model names
        """
        return []
    
    def set_model(self, model_name: str) -> bool:
        """
        Set the AI model to use.
        
        Args:
            model_name: Name of the model to use
            
        Returns:
            True if successful, False otherwise
        """
        return False


class OrganizerPlugin(BasePlugin):
    """
    Base class for organizer plugins.
    
    Organizer plugins are responsible for organizing files based on
    AI analysis and user preferences.
    """
    
    plugin_type = "organizer"
    
    def __init__(self, plugin_id: str, name: Optional[str] = None, version: Optional[str] = None,
                 description: Optional[str] = None):
        """
        Initialize the organizer plugin.
        
        Args:
            plugin_id: Unique identifier for the plugin
            name: Plugin name (if None, uses class attribute)
            version: Plugin version (if None, uses class attribute)
            description: Plugin description (if None, uses class attribute)
        """
        super().__init__(plugin_id, name, version, description)
    
    @abstractmethod
    def organize_files(self, analyzed_files: List[Dict[str, Any]], target_dir: str,
                      callback: Optional[callable] = None, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Organize files based on AI analysis.
        
        Args:
            analyzed_files: List of file dictionaries with analysis results
            target_dir: Target directory for organized files
            callback: Optional callback function for progress updates
            options: Optional dictionary with organization options
            
        Returns:
            Dictionary with organization results
        """
        pass


class UtilityPlugin(BasePlugin):
    """
    Base class for utility plugins.
    
    Utility plugins provide additional functionality that doesn't fit into
    other plugin categories.
    """
    
    plugin_type = "utility"
    
    def __init__(self, plugin_id: str, name: Optional[str] = None, version: Optional[str] = None,
                 description: Optional[str] = None):
        """
        Initialize the utility plugin.
        
        Args:
            plugin_id: Unique identifier for the plugin
            name: Plugin name (if None, uses class attribute)
            version: Plugin version (if None, uses class attribute)
            description: Plugin description (if None, uses class attribute)
        """
        super().__init__(plugin_id, name, version, description)