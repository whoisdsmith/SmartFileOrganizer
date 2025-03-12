"""
Plugin manager for AI Document Organizer V2.

Provides plugin discovery, loading, and management capabilities.
"""

import importlib
import inspect
import logging
import os
import pkgutil
import sys
from typing import Any, Dict, List, Optional, Set, Type, Union

from .plugin_base import PluginBase


logger = logging.getLogger(__name__)


class PluginManager:
    """
    Plugin manager for discovering, loading, and managing plugins.
    
    This class is responsible for:
    - Discovering plugins in specified directories
    - Loading plugin modules
    - Registering plugin classes
    - Managing plugin lifecycle (initialization, activation, deactivation, shutdown)
    """
    
    def __init__(self, plugin_directories: Optional[List[str]] = None):
        """
        Initialize the plugin manager.
        
        Args:
            plugin_directories: Optional list of directories to search for plugins
        """
        # Plugin directories
        self.plugin_directories = plugin_directories or []
        self._default_plugin_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "plugins"
        )
        if self._default_plugin_dir not in self.plugin_directories:
            self.plugin_directories.append(self._default_plugin_dir)
        
        # Plugin storage
        self.plugin_classes: Dict[str, Type[PluginBase]] = {}
        self.plugin_modules: Dict[str, Any] = {}
        self.plugins: Dict[str, PluginBase] = {}
        self.active_plugins: Dict[str, PluginBase] = {}
        
        # Plugin loading flags
        self.plugins_loaded = False
        self.plugin_discovery_complete = False
    
    def discover_plugins(self) -> List[str]:
        """
        Discover available plugins in the plugin directories.
        
        Returns:
            List of discovered plugin module names
        """
        if self.plugin_discovery_complete:
            return list(self.plugin_modules.keys())
        
        discovered_modules = []
        
        # Add plugin directories to Python path
        for directory in self.plugin_directories:
            if directory not in sys.path and os.path.isdir(directory):
                sys.path.append(directory)
        
        # Discover plugins in each directory
        for directory in self.plugin_directories:
            if not os.path.isdir(directory):
                logger.warning(f"Plugin directory not found: {directory}")
                continue
            
            logger.debug(f"Searching for plugins in: {directory}")
            
            # Get the package name from the directory path
            package_name = os.path.basename(directory)
            
            # Check if the directory is a Python package (has __init__.py)
            if not os.path.isfile(os.path.join(directory, "__init__.py")):
                logger.warning(f"Directory is not a Python package: {directory}")
                continue
            
            try:
                # Import the package
                package = importlib.import_module(package_name)
                
                # Walk through the package to find plugin modules
                for _, module_name, is_pkg in pkgutil.iter_modules([directory]):
                    # If it's a package (directory with __init__.py), explore it
                    if is_pkg:
                        # Import the subpackage
                        subpkg_name = f"{package_name}.{module_name}"
                        try:
                            subpkg = importlib.import_module(subpkg_name)
                            # Add the subpackage to discovered modules
                            self.plugin_modules[subpkg_name] = subpkg
                            discovered_modules.append(subpkg_name)
                            logger.debug(f"Discovered plugin module: {subpkg_name}")
                        except ImportError as e:
                            logger.error(f"Failed to import plugin module {subpkg_name}: {e}")
                
            except ImportError as e:
                logger.error(f"Failed to import plugin package {package_name}: {e}")
        
        self.plugin_discovery_complete = True
        return discovered_modules
    
    def load_plugins(self) -> Dict[str, Type[PluginBase]]:
        """
        Load discovered plugins and register plugin classes.
        
        Returns:
            Dictionary of plugin classes by name
        """
        if self.plugins_loaded:
            return self.plugin_classes
        
        # Discover plugins if not already done
        if not self.plugin_discovery_complete:
            self.discover_plugins()
        
        # Find all plugin classes in the discovered modules
        for module_name, module in self.plugin_modules.items():
            # Find all classes in the module that inherit from PluginBase
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if (issubclass(obj, PluginBase) and 
                    obj is not PluginBase and 
                    module_name == obj.__module__):
                    plugin_name = obj.plugin_name
                    self.plugin_classes[plugin_name] = obj
                    logger.debug(f"Registered plugin class: {plugin_name} ({obj.__name__})")
        
        self.plugins_loaded = True
        return self.plugin_classes
    
    def get_plugin_class(self, plugin_name: str) -> Optional[Type[PluginBase]]:
        """
        Get a plugin class by name.
        
        Args:
            plugin_name: Name of the plugin class to get
            
        Returns:
            Plugin class or None if not found
        """
        # Load plugins if not already done
        if not self.plugins_loaded:
            self.load_plugins()
        
        return self.plugin_classes.get(plugin_name)
    
    def get_plugin_classes(self) -> Dict[str, Type[PluginBase]]:
        """
        Get all registered plugin classes.
        
        Returns:
            Dictionary of plugin classes by name
        """
        # Load plugins if not already done
        if not self.plugins_loaded:
            self.load_plugins()
        
        return self.plugin_classes
    
    def create_plugin_instance(self, plugin_name: str, config: Optional[Dict[str, Any]] = None) -> Optional[PluginBase]:
        """
        Create an instance of a plugin by name.
        
        Args:
            plugin_name: Name of the plugin to create
            config: Optional configuration dictionary for the plugin
            
        Returns:
            Plugin instance or None if the plugin class is not found
        """
        plugin_class = self.get_plugin_class(plugin_name)
        if not plugin_class:
            logger.error(f"Plugin class not found: {plugin_name}")
            return None
        
        try:
            plugin = plugin_class(config)
            return plugin
        except Exception as e:
            logger.error(f"Failed to create plugin instance {plugin_name}: {e}")
            return None
    
    def register_plugin(self, plugin: PluginBase) -> bool:
        """
        Register a plugin instance.
        
        Args:
            plugin: Plugin instance to register
            
        Returns:
            True if the plugin was registered successfully, False otherwise
        """
        try:
            plugin_name = plugin.get_name()
            if plugin_name in self.plugins:
                logger.warning(f"Plugin already registered: {plugin_name}")
                return False
            
            self.plugins[plugin_name] = plugin
            logger.debug(f"Registered plugin instance: {plugin_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to register plugin: {e}")
            return False
    
    def unregister_plugin(self, plugin_name: str) -> bool:
        """
        Unregister a plugin instance.
        
        Args:
            plugin_name: Name of the plugin to unregister
            
        Returns:
            True if the plugin was unregistered successfully, False otherwise
        """
        if plugin_name not in self.plugins:
            logger.warning(f"Plugin not registered: {plugin_name}")
            return False
        
        # Deactivate the plugin if it's active
        if plugin_name in self.active_plugins:
            self.deactivate_plugin(plugin_name)
        
        # Remove the plugin from the registry
        del self.plugins[plugin_name]
        logger.debug(f"Unregistered plugin: {plugin_name}")
        return True
    
    def initialize_plugin(self, plugin_name: str) -> bool:
        """
        Initialize a plugin.
        
        Args:
            plugin_name: Name of the plugin to initialize
            
        Returns:
            True if the plugin was initialized successfully, False otherwise
        """
        if plugin_name not in self.plugins:
            logger.error(f"Plugin not registered: {plugin_name}")
            return False
        
        plugin = self.plugins[plugin_name]
        try:
            success = plugin.initialize()
            if success:
                logger.debug(f"Initialized plugin: {plugin_name}")
            else:
                logger.error(f"Plugin initialization failed: {plugin_name}")
            return success
        except Exception as e:
            logger.error(f"Error initializing plugin {plugin_name}: {e}")
            return False
    
    def activate_plugin(self, plugin_name: str) -> bool:
        """
        Activate a plugin.
        
        Args:
            plugin_name: Name of the plugin to activate
            
        Returns:
            True if the plugin was activated successfully, False otherwise
        """
        if plugin_name not in self.plugins:
            logger.error(f"Plugin not registered: {plugin_name}")
            return False
        
        if plugin_name in self.active_plugins:
            logger.warning(f"Plugin already active: {plugin_name}")
            return True
        
        plugin = self.plugins[plugin_name]
        try:
            success = plugin.activate()
            if success:
                self.active_plugins[plugin_name] = plugin
                logger.debug(f"Activated plugin: {plugin_name}")
            else:
                logger.error(f"Plugin activation failed: {plugin_name}")
            return success
        except Exception as e:
            logger.error(f"Error activating plugin {plugin_name}: {e}")
            return False
    
    def deactivate_plugin(self, plugin_name: str) -> bool:
        """
        Deactivate a plugin.
        
        Args:
            plugin_name: Name of the plugin to deactivate
            
        Returns:
            True if the plugin was deactivated successfully, False otherwise
        """
        if plugin_name not in self.active_plugins:
            logger.warning(f"Plugin not active: {plugin_name}")
            return True
        
        plugin = self.active_plugins[plugin_name]
        try:
            success = plugin.deactivate()
            if success:
                del self.active_plugins[plugin_name]
                logger.debug(f"Deactivated plugin: {plugin_name}")
            else:
                logger.error(f"Plugin deactivation failed: {plugin_name}")
            return success
        except Exception as e:
            logger.error(f"Error deactivating plugin {plugin_name}: {e}")
            return False
    
    def shutdown_plugin(self, plugin_name: str) -> bool:
        """
        Shutdown a plugin.
        
        Args:
            plugin_name: Name of the plugin to shutdown
            
        Returns:
            True if the plugin was shutdown successfully, False otherwise
        """
        if plugin_name not in self.plugins:
            logger.error(f"Plugin not registered: {plugin_name}")
            return False
        
        # Deactivate the plugin first if it's active
        if plugin_name in self.active_plugins:
            self.deactivate_plugin(plugin_name)
        
        plugin = self.plugins[plugin_name]
        try:
            success = plugin.shutdown()
            if success:
                logger.debug(f"Shutdown plugin: {plugin_name}")
            else:
                logger.error(f"Plugin shutdown failed: {plugin_name}")
            return success
        except Exception as e:
            logger.error(f"Error shutting down plugin {plugin_name}: {e}")
            return False
    
    def get_plugin(self, plugin_name: str) -> Optional[PluginBase]:
        """
        Get a plugin instance by name.
        
        Args:
            plugin_name: Name of the plugin to get
            
        Returns:
            Plugin instance or None if not found
        """
        return self.plugins.get(plugin_name)
    
    def get_plugins(self) -> Dict[str, PluginBase]:
        """
        Get all registered plugin instances.
        
        Returns:
            Dictionary of plugin instances by name
        """
        return self.plugins
    
    def get_active_plugins(self) -> Dict[str, PluginBase]:
        """
        Get all active plugin instances.
        
        Returns:
            Dictionary of active plugin instances by name
        """
        return self.active_plugins
    
    def get_plugins_by_type(self, plugin_type: str) -> Dict[str, PluginBase]:
        """
        Get all plugins of a specific type.
        
        Args:
            plugin_type: Type of plugins to get
            
        Returns:
            Dictionary of plugin instances by name
        """
        return {name: plugin for name, plugin in self.plugins.items() 
                if plugin.get_type() == plugin_type}
    
    def get_plugins_by_capability(self, capability: str) -> Dict[str, PluginBase]:
        """
        Get all plugins with a specific capability.
        
        Args:
            capability: Capability to search for
            
        Returns:
            Dictionary of plugin instances by name
        """
        return {name: plugin for name, plugin in self.plugins.items() 
                if capability in plugin.get_capabilities()}
    
    def has_plugin(self, plugin_name: str) -> bool:
        """
        Check if a plugin is registered.
        
        Args:
            plugin_name: Name of the plugin to check
            
        Returns:
            True if the plugin is registered, False otherwise
        """
        return plugin_name in self.plugins
    
    def is_plugin_active(self, plugin_name: str) -> bool:
        """
        Check if a plugin is active.
        
        Args:
            plugin_name: Name of the plugin to check
            
        Returns:
            True if the plugin is active, False otherwise
        """
        return plugin_name in self.active_plugins
    
    def get_plugin_info(self, plugin_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a plugin.
        
        Args:
            plugin_name: Name of the plugin to get info for
            
        Returns:
            Dictionary with plugin information or None if not found
        """
        plugin = self.get_plugin(plugin_name)
        if not plugin:
            return None
        
        return plugin.get_info()
    
    def get_plugins_info(self) -> Dict[str, Dict[str, Any]]:
        """
        Get information about all registered plugins.
        
        Returns:
            Dictionary of plugin information by name
        """
        return {name: plugin.get_info() for name, plugin in self.plugins.items()}
    
    def load_all_plugins(self, config: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[str, PluginBase]:
        """
        Load all available plugins.
        
        Args:
            config: Optional configuration dictionary for plugins
            
        Returns:
            Dictionary of loaded plugin instances by name
        """
        # Load plugin classes if not already done
        if not self.plugins_loaded:
            self.load_plugins()
        
        # Create and register an instance of each plugin class
        for plugin_name, plugin_class in self.plugin_classes.items():
            if plugin_name in self.plugins:
                continue
            
            plugin_config = None
            if config and plugin_name in config:
                plugin_config = config[plugin_name]
            
            plugin = self.create_plugin_instance(plugin_name, plugin_config)
            if plugin:
                self.register_plugin(plugin)
        
        return self.plugins
    
    def initialize_all_plugins(self) -> Dict[str, bool]:
        """
        Initialize all registered plugins.
        
        Returns:
            Dictionary of initialization results by plugin name
        """
        results = {}
        for plugin_name in self.plugins:
            results[plugin_name] = self.initialize_plugin(plugin_name)
        
        return results
    
    def activate_all_plugins(self) -> Dict[str, bool]:
        """
        Activate all registered plugins.
        
        Returns:
            Dictionary of activation results by plugin name
        """
        results = {}
        for plugin_name in self.plugins:
            results[plugin_name] = self.activate_plugin(plugin_name)
        
        return results
    
    def deactivate_all_plugins(self) -> Dict[str, bool]:
        """
        Deactivate all active plugins.
        
        Returns:
            Dictionary of deactivation results by plugin name
        """
        results = {}
        for plugin_name in list(self.active_plugins.keys()):
            results[plugin_name] = self.deactivate_plugin(plugin_name)
        
        return results
    
    def shutdown_all_plugins(self) -> Dict[str, bool]:
        """
        Shutdown all registered plugins.
        
        Returns:
            Dictionary of shutdown results by plugin name
        """
        # Deactivate all plugins first
        self.deactivate_all_plugins()
        
        # Shutdown all plugins
        results = {}
        for plugin_name in list(self.plugins.keys()):
            results[plugin_name] = self.shutdown_plugin(plugin_name)
        
        return results
    
    def reload_plugin(self, plugin_name: str, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Reload a plugin.
        
        Args:
            plugin_name: Name of the plugin to reload
            config: Optional new configuration for the plugin
            
        Returns:
            True if the plugin was reloaded successfully, False otherwise
        """
        # Get the plugin class
        plugin_class = self.get_plugin_class(plugin_name)
        if not plugin_class:
            logger.error(f"Plugin class not found: {plugin_name}")
            return False
        
        # Check if the plugin is active
        was_active = plugin_name in self.active_plugins
        
        # Shutdown and unregister the existing plugin
        if plugin_name in self.plugins:
            self.shutdown_plugin(plugin_name)
            self.unregister_plugin(plugin_name)
        
        # Create a new plugin instance
        plugin = self.create_plugin_instance(plugin_name, config)
        if not plugin:
            logger.error(f"Failed to create new plugin instance: {plugin_name}")
            return False
        
        # Register the new plugin
        if not self.register_plugin(plugin):
            logger.error(f"Failed to register new plugin instance: {plugin_name}")
            return False
        
        # Initialize the plugin
        if not self.initialize_plugin(plugin_name):
            logger.error(f"Failed to initialize new plugin instance: {plugin_name}")
            return False
        
        # Activate the plugin if it was active before
        if was_active:
            if not self.activate_plugin(plugin_name):
                logger.error(f"Failed to activate new plugin instance: {plugin_name}")
                return False
        
        logger.debug(f"Reloaded plugin: {plugin_name}")
        return True
    
    def reload_all_plugins(self, config: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[str, bool]:
        """
        Reload all plugins.
        
        Args:
            config: Optional new configuration for plugins
            
        Returns:
            Dictionary of reload results by plugin name
        """
        results = {}
        for plugin_name in list(self.plugins.keys()):
            plugin_config = None
            if config and plugin_name in config:
                plugin_config = config[plugin_name]
            
            results[plugin_name] = self.reload_plugin(plugin_name, plugin_config)
        
        return results