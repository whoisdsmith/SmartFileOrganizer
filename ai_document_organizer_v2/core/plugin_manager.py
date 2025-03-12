"""
Plugin manager for AI Document Organizer V2.
"""

import importlib
import logging
import os
import sys
from typing import Any, Dict, List, Optional, Set, Type, Union

from ai_document_organizer_v2.core.plugin_base import PluginBase


logger = logging.getLogger(__name__)


class PluginManager:
    """
    Plugin manager for AI Document Organizer V2.
    
    This class is responsible for:
    - Loading plugins
    - Managing plugin lifecycle
    - Providing access to plugins
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the plugin manager.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.plugins = {}  # plugin_name -> plugin instance
        self.plugin_classes = {}  # plugin_name -> plugin class
        self.plugin_modules = {}  # plugin_name -> plugin module
        self.active_plugins = set()  # Set of active plugin names
    
    def discover_plugins(self, plugin_dirs: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Discover plugins in the specified directories.
        
        Args:
            plugin_dirs: Optional list of plugin directories
            
        Returns:
            List of discovered plugin information dictionaries
        """
        if plugin_dirs is None:
            # Default to standard plugin directory
            plugin_dirs = [
                os.path.join(os.path.dirname(os.path.dirname(__file__)), "plugins")
            ]
        
        discovered_plugins = []
        
        for plugin_dir in plugin_dirs:
            if not os.path.isdir(plugin_dir):
                logger.warning(f"Plugin directory not found: {plugin_dir}")
                continue
            
            # Get subdirectories in the plugin directory
            try:
                subdirs = [d for d in os.listdir(plugin_dir) 
                         if os.path.isdir(os.path.join(plugin_dir, d)) and 
                         not d.startswith('__') and not d.startswith('.')]
            except Exception as e:
                logger.error(f"Error listing plugin directory {plugin_dir}: {e}")
                continue
            
            # Check each subdirectory for plugins
            for subdir in subdirs:
                try:
                    plugin_info = self._check_plugin_directory(os.path.join(plugin_dir, subdir))
                    if plugin_info:
                        discovered_plugins.append(plugin_info)
                except Exception as e:
                    logger.error(f"Error checking plugin directory {subdir}: {e}")
        
        return discovered_plugins
    
    def _check_plugin_directory(self, plugin_dir: str) -> Optional[Dict[str, Any]]:
        """
        Check if a directory contains a valid plugin.
        
        Args:
            plugin_dir: Plugin directory to check
            
        Returns:
            Plugin information dictionary if a valid plugin was found, None otherwise
        """
        # Check if the directory is a Python package
        init_file = os.path.join(plugin_dir, "__init__.py")
        if not os.path.isfile(init_file):
            return None
        
        # Get the plugin name from the directory name
        plugin_name = os.path.basename(plugin_dir)
        
        # Import the plugin module
        try:
            # Convert directory path to module path
            module_path = plugin_dir.replace(os.path.sep, '.')
            if module_path.startswith('.'):
                module_path = module_path[1:]
            
            # Import the module
            module = importlib.import_module(f"ai_document_organizer_v2.plugins.{plugin_name}")
            
            # Look for plugin classes
            plugin_classes = []
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and 
                    issubclass(attr, PluginBase) and 
                    attr is not PluginBase):
                    plugin_classes.append(attr)
            
            if not plugin_classes:
                return None
            
            # Get information from the first plugin class
            plugin_class = plugin_classes[0]
            return {
                "name": plugin_class.plugin_name,
                "version": plugin_class.plugin_version,
                "description": plugin_class.plugin_description,
                "author": plugin_class.plugin_author,
                "module": f"ai_document_organizer_v2.plugins.{plugin_name}",
                "class": plugin_class.__name__,
                "directory": plugin_dir
            }
        except Exception as e:
            logger.error(f"Error importing plugin {plugin_name}: {e}")
            return None
    
    def register_plugin_class(self, plugin_class: Type[PluginBase]) -> bool:
        """
        Register a plugin class.
        
        Args:
            plugin_class: Plugin class to register
            
        Returns:
            True if registration was successful, False otherwise
        """
        if not issubclass(plugin_class, PluginBase):
            logger.error(f"Invalid plugin class: {plugin_class.__name__}")
            return False
        
        plugin_name = plugin_class.plugin_name
        
        if plugin_name in self.plugin_classes:
            logger.warning(f"Plugin {plugin_name} is already registered")
            return False
        
        self.plugin_classes[plugin_name] = plugin_class
        return True
    
    def register_plugin(self, plugin: PluginBase) -> bool:
        """
        Register a plugin instance.
        
        Args:
            plugin: Plugin instance to register
            
        Returns:
            True if registration was successful, False otherwise
        """
        plugin_name = plugin.plugin_name
        
        if plugin_name in self.plugins:
            logger.warning(f"Plugin {plugin_name} is already registered")
            return False
        
        self.plugins[plugin_name] = plugin
        return True
    
    def unregister_plugin(self, plugin_name: str) -> bool:
        """
        Unregister a plugin.
        
        Args:
            plugin_name: Name of the plugin to unregister
            
        Returns:
            True if unregistration was successful, False otherwise
        """
        if plugin_name not in self.plugins:
            logger.warning(f"Plugin {plugin_name} is not registered")
            return False
        
        # Deactivate plugin if active
        if plugin_name in self.active_plugins:
            self.deactivate_plugin(plugin_name)
        
        # Unregister plugin
        del self.plugins[plugin_name]
        if plugin_name in self.plugin_classes:
            del self.plugin_classes[plugin_name]
        
        return True
    
    def get_plugin(self, plugin_name: str) -> Optional[PluginBase]:
        """
        Get a plugin instance by name.
        
        Args:
            plugin_name: Name of the plugin to get
            
        Returns:
            Plugin instance or None if not found
        """
        return self.plugins.get(plugin_name)
    
    def get_plugin_class(self, plugin_name: str) -> Optional[Type[PluginBase]]:
        """
        Get a plugin class by name.
        
        Args:
            plugin_name: Name of the plugin class to get
            
        Returns:
            Plugin class or None if not found
        """
        return self.plugin_classes.get(plugin_name)
    
    def get_all_plugins(self) -> Dict[str, PluginBase]:
        """
        Get all registered plugins.
        
        Returns:
            Dictionary of plugin name to plugin instance
        """
        return self.plugins.copy()
    
    def get_active_plugins(self) -> Dict[str, PluginBase]:
        """
        Get all active plugins.
        
        Returns:
            Dictionary of plugin name to plugin instance
        """
        return {name: self.plugins[name] for name in self.active_plugins if name in self.plugins}
    
    def load_plugin(self, plugin_info: Union[str, Dict[str, Any]], config: Optional[Dict[str, Any]] = None) -> Optional[PluginBase]:
        """
        Load a plugin from the given information.
        
        Args:
            plugin_info: Plugin name or plugin information dictionary
            config: Optional configuration for the plugin
            
        Returns:
            Loaded plugin instance or None if loading failed
        """
        if isinstance(plugin_info, str):
            plugin_name = plugin_info
            plugin_module = None
            plugin_class_name = None
        else:
            plugin_name = plugin_info["name"]
            plugin_module = plugin_info.get("module")
            plugin_class_name = plugin_info.get("class")
        
        # If plugin is already loaded, return it
        if plugin_name in self.plugins:
            logger.info(f"Plugin {plugin_name} is already loaded")
            return self.plugins[plugin_name]
        
        # If we have plugin class, instantiate it
        if plugin_name in self.plugin_classes:
            plugin_class = self.plugin_classes[plugin_name]
            plugin = plugin_class(config)
            self.plugins[plugin_name] = plugin
            return plugin
        
        # If we have module information, import the module and get the class
        if plugin_module:
            try:
                module = importlib.import_module(plugin_module)
                
                if plugin_class_name:
                    # If we have class name, get the class
                    plugin_class = getattr(module, plugin_class_name)
                else:
                    # Otherwise, find the first plugin class in the module
                    plugin_class = None
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (isinstance(attr, type) and 
                            issubclass(attr, PluginBase) and 
                            attr is not PluginBase):
                            plugin_class = attr
                            break
                
                if not plugin_class:
                    logger.error(f"No plugin class found in module {plugin_module}")
                    return None
                
                # Register and instantiate the plugin class
                self.plugin_classes[plugin_name] = plugin_class
                plugin = plugin_class(config)
                self.plugins[plugin_name] = plugin
                return plugin
            except Exception as e:
                logger.error(f"Error loading plugin {plugin_name}: {e}")
                return None
        
        # If we only have plugin name, try to discover it
        discovered_plugins = self.discover_plugins()
        for discovered_plugin in discovered_plugins:
            if discovered_plugin["name"] == plugin_name:
                return self.load_plugin(discovered_plugin, config)
        
        logger.error(f"Plugin {plugin_name} not found")
        return None
    
    def initialize_plugin(self, plugin_name: str) -> bool:
        """
        Initialize a plugin.
        
        Args:
            plugin_name: Name of the plugin to initialize
            
        Returns:
            True if initialization was successful, False otherwise
        """
        if plugin_name not in self.plugins:
            logger.error(f"Plugin {plugin_name} is not registered")
            return False
        
        plugin = self.plugins[plugin_name]
        
        try:
            result = plugin.initialize()
            if result:
                logger.info(f"Plugin {plugin_name} initialized successfully")
            else:
                logger.error(f"Plugin {plugin_name} initialization failed")
            return result
        except Exception as e:
            logger.error(f"Error initializing plugin {plugin_name}: {e}")
            return False
    
    def activate_plugin(self, plugin_name: str) -> bool:
        """
        Activate a plugin.
        
        Args:
            plugin_name: Name of the plugin to activate
            
        Returns:
            True if activation was successful, False otherwise
        """
        if plugin_name not in self.plugins:
            logger.error(f"Plugin {plugin_name} is not registered")
            return False
        
        plugin = self.plugins[plugin_name]
        
        # Check if plugin is already active
        if plugin_name in self.active_plugins:
            logger.warning(f"Plugin {plugin_name} is already active")
            return True
        
        # Initialize plugin if not initialized
        if not plugin.is_initialized():
            if not self.initialize_plugin(plugin_name):
                logger.error(f"Failed to initialize plugin {plugin_name}")
                return False
        
        # Check plugin dependencies
        dependencies = plugin.get_dependencies()
        for dependency in dependencies:
            if dependency not in self.plugins:
                logger.error(f"Plugin {plugin_name} depends on {dependency}, which is not registered")
                return False
            
            if dependency not in self.active_plugins:
                # Try to activate dependency
                if not self.activate_plugin(dependency):
                    logger.error(f"Failed to activate dependency {dependency} for plugin {plugin_name}")
                    return False
        
        # Activate plugin
        try:
            result = plugin.activate()
            if result:
                logger.info(f"Plugin {plugin_name} activated successfully")
                self.active_plugins.add(plugin_name)
            else:
                logger.error(f"Plugin {plugin_name} activation failed")
            return result
        except Exception as e:
            logger.error(f"Error activating plugin {plugin_name}: {e}")
            return False
    
    def deactivate_plugin(self, plugin_name: str) -> bool:
        """
        Deactivate a plugin.
        
        Args:
            plugin_name: Name of the plugin to deactivate
            
        Returns:
            True if deactivation was successful, False otherwise
        """
        if plugin_name not in self.plugins:
            logger.error(f"Plugin {plugin_name} is not registered")
            return False
        
        # Check if plugin is active
        if plugin_name not in self.active_plugins:
            logger.warning(f"Plugin {plugin_name} is not active")
            return True
        
        plugin = self.plugins[plugin_name]
        
        # Check for dependent plugins
        dependents = self._get_dependent_plugins(plugin_name)
        if dependents:
            # If there are dependent plugins, deactivate them first
            for dependent in dependents:
                if not self.deactivate_plugin(dependent):
                    logger.error(f"Failed to deactivate dependent plugin {dependent}")
                    return False
        
        # Deactivate plugin
        try:
            result = plugin.deactivate()
            if result:
                logger.info(f"Plugin {plugin_name} deactivated successfully")
                self.active_plugins.remove(plugin_name)
            else:
                logger.error(f"Plugin {plugin_name} deactivation failed")
            return result
        except Exception as e:
            logger.error(f"Error deactivating plugin {plugin_name}: {e}")
            return False
    
    def _get_dependent_plugins(self, plugin_name: str) -> List[str]:
        """
        Get plugins that depend on the specified plugin.
        
        Args:
            plugin_name: Name of the plugin to check
            
        Returns:
            List of plugin names that depend on the specified plugin
        """
        dependent_plugins = []
        for name, plugin in self.plugins.items():
            if name == plugin_name:
                continue
            
            if plugin_name in plugin.get_dependencies():
                dependent_plugins.append(name)
        
        return dependent_plugins
    
    def shutdown_plugin(self, plugin_name: str) -> bool:
        """
        Shutdown a plugin.
        
        Args:
            plugin_name: Name of the plugin to shutdown
            
        Returns:
            True if shutdown was successful, False otherwise
        """
        if plugin_name not in self.plugins:
            logger.error(f"Plugin {plugin_name} is not registered")
            return False
        
        # Deactivate plugin if active
        if plugin_name in self.active_plugins:
            if not self.deactivate_plugin(plugin_name):
                logger.error(f"Failed to deactivate plugin {plugin_name}")
                return False
        
        plugin = self.plugins[plugin_name]
        
        # Shutdown plugin
        try:
            result = plugin.shutdown()
            if result:
                logger.info(f"Plugin {plugin_name} shutdown successfully")
            else:
                logger.error(f"Plugin {plugin_name} shutdown failed")
            return result
        except Exception as e:
            logger.error(f"Error shutting down plugin {plugin_name}: {e}")
            return False
    
    def shutdown_all_plugins(self) -> bool:
        """
        Shutdown all plugins.
        
        Returns:
            True if all plugins were shutdown successfully, False otherwise
        """
        # Deactivate all active plugins
        active_plugins = list(self.active_plugins)
        for plugin_name in active_plugins:
            if not self.deactivate_plugin(plugin_name):
                logger.error(f"Failed to deactivate plugin {plugin_name}")
                return False
        
        # Shutdown all plugins
        for plugin_name in list(self.plugins.keys()):
            if not self.shutdown_plugin(plugin_name):
                logger.error(f"Failed to shutdown plugin {plugin_name}")
                return False
        
        return True
    
    def reload_plugin(self, plugin_name: str, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Reload a plugin.
        
        Args:
            plugin_name: Name of the plugin to reload
            config: Optional new configuration for the plugin
            
        Returns:
            True if reload was successful, False otherwise
        """
        if plugin_name not in self.plugins:
            logger.error(f"Plugin {plugin_name} is not registered")
            return False
        
        # Get plugin information
        was_active = plugin_name in self.active_plugins
        
        # Shutdown plugin
        if not self.shutdown_plugin(plugin_name):
            logger.error(f"Failed to shutdown plugin {plugin_name}")
            return False
        
        # Unregister plugin
        if not self.unregister_plugin(plugin_name):
            logger.error(f"Failed to unregister plugin {plugin_name}")
            return False
        
        # Load plugin
        plugin = self.load_plugin(plugin_name, config)
        if plugin is None:
            logger.error(f"Failed to load plugin {plugin_name}")
            return False
        
        # If plugin was active, activate it again
        if was_active:
            if not self.activate_plugin(plugin_name):
                logger.error(f"Failed to activate plugin {plugin_name}")
                return False
        
        return True
    
    def get_plugin_config(self, plugin_name: str) -> Optional[Dict[str, Any]]:
        """
        Get the configuration of a plugin.
        
        Args:
            plugin_name: Name of the plugin
            
        Returns:
            Plugin configuration or None if plugin is not registered
        """
        if plugin_name not in self.plugins:
            logger.error(f"Plugin {plugin_name} is not registered")
            return None
        
        plugin = self.plugins[plugin_name]
        return plugin.get_config()
    
    def set_plugin_config(self, plugin_name: str, config: Dict[str, Any]) -> bool:
        """
        Set the configuration of a plugin.
        
        Args:
            plugin_name: Name of the plugin
            config: New configuration
            
        Returns:
            True if configuration was set successfully, False otherwise
        """
        if plugin_name not in self.plugins:
            logger.error(f"Plugin {plugin_name} is not registered")
            return False
        
        plugin = self.plugins[plugin_name]
        return plugin.set_config(config)
    
    def validate_plugin_config(self, plugin_name: str, config: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Validate the configuration of a plugin.
        
        Args:
            plugin_name: Name of the plugin
            config: Configuration to validate
            
        Returns:
            Dictionary with validation errors by configuration key
        """
        if plugin_name not in self.plugins:
            logger.error(f"Plugin {plugin_name} is not registered")
            return {"global": [f"Plugin {plugin_name} is not registered"]}
        
        plugin = self.plugins[plugin_name]
        return plugin.validate_config(config)
    
    def get_plugin_info(self, plugin_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a plugin.
        
        Args:
            plugin_name: Name of the plugin
            
        Returns:
            Dictionary with plugin information or None if plugin is not registered
        """
        if plugin_name not in self.plugins:
            logger.error(f"Plugin {plugin_name} is not registered")
            return None
        
        plugin = self.plugins[plugin_name]
        return plugin.get_info()
    
    def is_plugin_active(self, plugin_name: str) -> bool:
        """
        Check if a plugin is active.
        
        Args:
            plugin_name: Name of the plugin
            
        Returns:
            True if the plugin is active, False otherwise
        """
        return plugin_name in self.active_plugins
    
    def is_plugin_initialized(self, plugin_name: str) -> bool:
        """
        Check if a plugin is initialized.
        
        Args:
            plugin_name: Name of the plugin
            
        Returns:
            True if the plugin is initialized, False otherwise
        """
        if plugin_name not in self.plugins:
            return False
        
        plugin = self.plugins[plugin_name]
        return plugin.is_initialized()
    
    def get_plugin_dependencies(self, plugin_name: str) -> Optional[List[str]]:
        """
        Get the dependencies of a plugin.
        
        Args:
            plugin_name: Name of the plugin
            
        Returns:
            List of plugin dependencies or None if plugin is not registered
        """
        if plugin_name not in self.plugins:
            logger.error(f"Plugin {plugin_name} is not registered")
            return None
        
        plugin = self.plugins[plugin_name]
        return plugin.get_dependencies()
    
    def get_plugins_by_type(self, plugin_type: str) -> Dict[str, PluginBase]:
        """
        Get plugins of a specific type.
        
        Args:
            plugin_type: Type of plugins to get
            
        Returns:
            Dictionary of plugin name to plugin instance
        """
        plugins = {}
        for name, plugin in self.plugins.items():
            if hasattr(plugin, 'get_type') and plugin.get_type() == plugin_type:
                plugins[name] = plugin
        
        return plugins