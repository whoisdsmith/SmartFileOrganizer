"""
Plugin Manager Module for AI Document Organizer V2.

This module provides a centralized system for discovering, loading,
and managing plugins for the application.
"""

import os
import sys
import importlib
import logging
import inspect
from typing import Dict, List, Any, Optional, Type, Set, Union

from .plugin_base import PluginBase
from .settings import SettingsManager

logger = logging.getLogger(__name__)

class PluginManager:
    """
    Manages the discovery, loading, and lifecycle of plugins.
    
    This class provides methods for finding, initializing, and accessing plugins
    from various sources, with automatic dependency management.
    """
    
    def __init__(self, settings_manager: Optional[SettingsManager] = None):
        """
        Initialize the plugin manager.
        
        Args:
            settings_manager: Optional settings manager instance
        """
        self.settings_manager = settings_manager or SettingsManager()
        self.plugins: Dict[str, PluginBase] = {}
        self.plugin_classes: Dict[str, Type[PluginBase]] = {}
        self.plugin_modules: Dict[str, Any] = {}
        self.plugin_paths: List[str] = []
        
        # Set default plugin paths
        plugin_dir = self.settings_manager.get_setting("plugins.plugin_directory", "plugins")
        self.add_plugin_path(plugin_dir)
        
        # Built-in plugin paths
        builtin_path = os.path.join(os.path.dirname(__file__), "..", "plugins")
        self.add_plugin_path(builtin_path)
    
    def add_plugin_path(self, path: str) -> bool:
        """
        Add a directory to the plugin search paths.
        
        Args:
            path: Directory path to add
            
        Returns:
            True if the path was added, False otherwise
        """
        if not os.path.exists(path):
            # Try creating the directory
            try:
                os.makedirs(path, exist_ok=True)
            except Exception as e:
                logger.error(f"Failed to create plugin directory {path}: {e}")
                return False
        
        abs_path = os.path.abspath(path)
        if abs_path not in self.plugin_paths:
            self.plugin_paths.append(abs_path)
            return True
        
        return False
    
    def discover_plugins(self) -> Dict[str, Type[PluginBase]]:
        """
        Discover available plugins in the plugin search paths.
        
        Returns:
            Dictionary mapping plugin IDs to plugin classes
        """
        discovered_plugins = {}
        
        for path in self.plugin_paths:
            self._discover_in_path(path, discovered_plugins)
        
        return discovered_plugins
    
    def _discover_in_path(self, path: str, discovered_plugins: Dict[str, Type[PluginBase]]) -> None:
        """
        Discover plugins in the specified path.
        
        Args:
            path: Directory path to search in
            discovered_plugins: Dictionary to store discovered plugins
        """
        if not os.path.isdir(path):
            return
        
        # Add path to Python path if not already there
        if path not in sys.path:
            sys.path.insert(0, path)
        
        # Find potential plugin directories (must contain __init__.py)
        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            
            # Skip non-directories and hidden directories
            if not os.path.isdir(item_path) or item.startswith('.'):
                continue
            
            # Skip directories without __init__.py
            if not os.path.exists(os.path.join(item_path, "__init__.py")):
                continue
            
            # Try to import the package
            try:
                package_name = f"ai_document_organizer_v2.plugins.{item}"
                package = importlib.import_module(package_name)
                
                # Look for plugin modules in the package
                for module_name in dir(package):
                    if module_name.startswith('_'):
                        continue
                    
                    try:
                        module = getattr(package, module_name)
                        
                        # Look for plugin classes in the module
                        for class_name in dir(module):
                            if class_name.startswith('_'):
                                continue
                            
                            try:
                                cls = getattr(module, class_name)
                                
                                # Check if it's a plugin class (subclass of PluginBase)
                                if (inspect.isclass(cls) and 
                                    issubclass(cls, PluginBase) and 
                                    cls is not PluginBase):
                                    
                                    plugin_id = cls.plugin_name
                                    discovered_plugins[plugin_id] = cls
                                    self.plugin_classes[plugin_id] = cls
                                    self.plugin_modules[plugin_id] = module
                                    
                                    logger.debug(f"Discovered plugin: {plugin_id} ({cls.__module__}.{cls.__name__})")
                                    
                            except Exception as class_err:
                                logger.debug(f"Error inspecting class {class_name}: {class_err}")
                        
                    except Exception as module_err:
                        logger.debug(f"Error importing module {module_name}: {module_err}")
                
            except Exception as package_err:
                logger.debug(f"Error importing package {item}: {package_err}")
    
    def load_plugin(self, plugin_id: str, config: Optional[Dict[str, Any]] = None) -> Optional[PluginBase]:
        """
        Load and initialize a plugin.
        
        Args:
            plugin_id: ID of the plugin to load
            config: Optional configuration dictionary
            
        Returns:
            Initialized plugin instance or None if loading failed
        """
        # Check if the plugin is already loaded
        if plugin_id in self.plugins:
            return self.plugins[plugin_id]
        
        # Check if the plugin class is known
        if plugin_id not in self.plugin_classes:
            # Try to discover plugins
            self.discover_plugins()
            
            if plugin_id not in self.plugin_classes:
                logger.error(f"Plugin not found: {plugin_id}")
                return None
        
        # Get plugin-specific configuration from settings
        plugin_config = config or {}
        if self.settings_manager:
            settings_config = self.settings_manager.get_plugin_settings(plugin_id)
            # Merge settings with provided config (provided config takes precedence)
            merged_config = {**settings_config, **plugin_config}
            plugin_config = merged_config
        
        try:
            # Create plugin instance
            plugin_class = self.plugin_classes[plugin_id]
            plugin = plugin_class(plugin_config)
            
            # Set settings manager
            plugin.settings_manager = self.settings_manager
            
            # Initialize plugin
            if not plugin.initialize():
                logger.error(f"Failed to initialize plugin: {plugin_id}")
                return None
            
            # Store plugin instance
            self.plugins[plugin_id] = plugin
            
            logger.info(f"Loaded plugin: {plugin_id}")
            return plugin
        
        except Exception as e:
            logger.error(f"Error loading plugin {plugin_id}: {e}")
            return None
    
    def load_plugins(self, plugin_types: Optional[List[str]] = None, 
                     excluded_plugins: Optional[List[str]] = None) -> Dict[str, PluginBase]:
        """
        Load multiple plugins by type.
        
        Args:
            plugin_types: Optional list of plugin types to load
            excluded_plugins: Optional list of plugin IDs to exclude
            
        Returns:
            Dictionary mapping plugin IDs to plugin instances
        """
        # Discover available plugins
        available_plugins = self.discover_plugins()
        
        excluded_plugins = excluded_plugins or []
        loaded_plugins = {}
        
        # Filter plugins by type if specified
        plugin_classes = {}
        if plugin_types:
            for plugin_id, plugin_class in available_plugins.items():
                if plugin_class.plugin_type in plugin_types and plugin_id not in excluded_plugins:
                    plugin_classes[plugin_id] = plugin_class
        else:
            plugin_classes = {k: v for k, v in available_plugins.items() if k not in excluded_plugins}
        
        # Load each plugin
        for plugin_id in plugin_classes:
            plugin = self.load_plugin(plugin_id)
            if plugin:
                loaded_plugins[plugin_id] = plugin
        
        return loaded_plugins
    
    def unload_plugin(self, plugin_id: str) -> bool:
        """
        Unload a plugin.
        
        Args:
            plugin_id: ID of the plugin to unload
            
        Returns:
            True if the plugin was unloaded, False otherwise
        """
        if plugin_id not in self.plugins:
            logger.warning(f"Plugin not loaded: {plugin_id}")
            return False
        
        try:
            # Shutdown the plugin
            plugin = self.plugins[plugin_id]
            plugin.shutdown()
            
            # Remove plugin
            del self.plugins[plugin_id]
            
            logger.info(f"Unloaded plugin: {plugin_id}")
            return True
        
        except Exception as e:
            logger.error(f"Error unloading plugin {plugin_id}: {e}")
            return False
    
    def unload_all_plugins(self) -> bool:
        """
        Unload all loaded plugins.
        
        Returns:
            True if all plugins were unloaded, False if any unload failed
        """
        success = True
        plugin_ids = list(self.plugins.keys())
        
        for plugin_id in plugin_ids:
            if not self.unload_plugin(plugin_id):
                success = False
        
        return success
    
    def get_plugin(self, plugin_id: str) -> Optional[PluginBase]:
        """
        Get a loaded plugin by ID.
        
        Args:
            plugin_id: ID of the plugin to get
            
        Returns:
            Plugin instance or None if not loaded
        """
        return self.plugins.get(plugin_id)
    
    def get_plugins_by_type(self, plugin_type: str) -> Dict[str, PluginBase]:
        """
        Get all loaded plugins of a specific type.
        
        Args:
            plugin_type: Type of plugins to get
            
        Returns:
            Dictionary mapping plugin IDs to plugin instances
        """
        return {
            plugin_id: plugin for plugin_id, plugin in self.plugins.items()
            if plugin.plugin_type == plugin_type
        }
    
    def get_available_plugin_types(self) -> Set[str]:
        """
        Get a set of available plugin types.
        
        Returns:
            Set of plugin types
        """
        return {plugin_class.plugin_type for plugin_class in self.plugin_classes.values()}
    
    def reload_plugin(self, plugin_id: str) -> Optional[PluginBase]:
        """
        Reload a plugin.
        
        Args:
            plugin_id: ID of the plugin to reload
            
        Returns:
            Reloaded plugin instance or None if reloading failed
        """
        # Get the current configuration if the plugin is loaded
        config = None
        if plugin_id in self.plugins:
            config = self.plugins[plugin_id].get_config()
            
            # Unload the plugin
            if not self.unload_plugin(plugin_id):
                logger.error(f"Failed to unload plugin {plugin_id} for reloading")
                return None
        
        # Reimport the module
        if plugin_id in self.plugin_modules:
            module = self.plugin_modules[plugin_id]
            try:
                importlib.reload(module)
            except Exception as e:
                logger.error(f"Error reloading module for plugin {plugin_id}: {e}")
                return None
        
        # Rediscover plugin class
        self.discover_plugins()
        
        # Load the plugin with the same configuration
        return self.load_plugin(plugin_id, config)
    
    def configure_plugin(self, plugin_id: str, config: Dict[str, Any]) -> bool:
        """
        Configure a plugin.
        
        Args:
            plugin_id: ID of the plugin to configure
            config: Configuration dictionary
            
        Returns:
            True if the plugin was configured successfully, False otherwise
        """
        plugin = self.get_plugin(plugin_id)
        if not plugin:
            logger.error(f"Plugin not loaded: {plugin_id}")
            return False
        
        try:
            # Validate configuration
            valid, error = plugin.validate_config(config)
            if not valid:
                logger.error(f"Invalid configuration for plugin {plugin_id}: {error}")
                return False
            
            # Configure the plugin
            if not plugin.configure(config):
                logger.error(f"Failed to configure plugin {plugin_id}")
                return False
            
            # Update settings if available
            if self.settings_manager:
                for key, value in config.items():
                    self.settings_manager.set_plugin_setting(plugin_id, key, value)
                self.settings_manager.save_settings()
            
            return True
        
        except Exception as e:
            logger.error(f"Error configuring plugin {plugin_id}: {e}")
            return False
    
    def get_plugin_info(self, plugin_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a plugin.
        
        Args:
            plugin_id: ID of the plugin
            
        Returns:
            Dictionary with plugin information or None if not found
        """
        plugin = self.get_plugin(plugin_id)
        if plugin:
            return plugin.get_info()
        
        # Check if the plugin class is known
        if plugin_id in self.plugin_classes:
            plugin_class = self.plugin_classes[plugin_id]
            return {
                "name": plugin_class.plugin_name,
                "description": plugin_class.plugin_description,
                "version": plugin_class.plugin_version,
                "type": plugin_class.plugin_type,
                "loaded": False
            }
        
        return None
    
    def get_all_plugin_info(self) -> Dict[str, Dict[str, Any]]:
        """
        Get information about all known plugins.
        
        Returns:
            Dictionary mapping plugin IDs to plugin information
        """
        # Discover plugins
        self.discover_plugins()
        
        info = {}
        
        # Add information for known plugin classes
        for plugin_id, plugin_class in self.plugin_classes.items():
            info[plugin_id] = {
                "name": plugin_class.plugin_name,
                "description": plugin_class.plugin_description,
                "version": plugin_class.plugin_version,
                "type": plugin_class.plugin_type,
                "loaded": plugin_id in self.plugins
            }
        
        # Update with information for loaded plugins
        for plugin_id, plugin in self.plugins.items():
            info[plugin_id] = plugin.get_info()
            info[plugin_id]["loaded"] = True
        
        return info