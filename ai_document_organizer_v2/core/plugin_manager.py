"""
Plugin Manager Module for AI Document Organizer V2.

This module provides the plugin management system for discovering, loading, and
managing plugins in the AI Document Organizer V2 application.
"""

import os
import sys
import importlib
import inspect
import logging
import pkgutil
from typing import Dict, List, Any, Optional, Set, Type, Tuple

from .plugin_base import BasePlugin

logger = logging.getLogger("AIDocumentOrganizerV2.PluginManager")

class PluginManager:
    """
    Manages plugin discovery, loading, initialization, and lifecycle.
    
    This class provides functionality to:
    - Discover and load plugins from the plugin directory
    - Initialize and manage plugin lifecycle
    - Provide access to plugins by type and ID
    - Handle plugin dependencies and conflicts
    """
    
    def __init__(self, plugin_dirs: Optional[List[str]] = None):
        """
        Initialize the plugin manager.
        
        Args:
            plugin_dirs: Optional list of plugin directories. If None, uses default.
        """
        # Default plugin directories
        if plugin_dirs is None:
            # First, add the built-in plugins directory
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.plugin_dirs = [os.path.join(base_dir, "plugins")]
            
            # Then, add user plugins directory in home folder
            user_plugins_dir = os.path.join(os.path.expanduser("~"), ".ai_document_organizer", "plugins")
            if os.path.exists(user_plugins_dir):
                self.plugin_dirs.append(user_plugins_dir)
        else:
            self.plugin_dirs = plugin_dirs
        
        # Plugin registry
        self.plugins = {}  # plugin_id -> plugin instance
        self.plugin_modules = {}  # plugin_id -> module
        self.plugin_types = {}  # plugin_type -> {plugin_id -> plugin instance}
        
        # Keep track of plugin states
        self.initialized_plugins = set()
        
        logger.debug(f"Plugin manager initialized with directories: {self.plugin_dirs}")
    
    def discover_plugins(self) -> Dict[str, Any]:
        """
        Discover and load plugins from the plugin directories.
        
        Returns:
            Dictionary with discovery results:
            - 'found': Number of plugins found
            - 'loaded': Number of plugins successfully loaded
            - 'failed': Number of plugins that failed to load
            - 'failures': List of dictionaries with failure information
        """
        discovered_count = 0
        loaded_count = 0
        failed_count = 0
        failures = []
        
        for plugin_dir in self.plugin_dirs:
            if not os.path.exists(plugin_dir):
                logger.debug(f"Plugin directory does not exist: {plugin_dir}")
                continue
            
            # Each subdirectory in the plugin directory is a potential plugin
            for item in os.listdir(plugin_dir):
                item_path = os.path.join(plugin_dir, item)
                
                # Skip non-directories and hidden directories
                if not os.path.isdir(item_path) or item.startswith('.') or item == '__pycache__':
                    continue
                
                # Check if this is a valid plugin package (has an __init__.py)
                init_py = os.path.join(item_path, "__init__.py")
                plugin_py = os.path.join(item_path, "plugin.py")
                
                if not (os.path.exists(init_py) or os.path.exists(plugin_py)):
                    logger.debug(f"Skipping {item_path}: Not a valid plugin package")
                    continue
                
                discovered_count += 1
                
                # Try to load the plugin
                try:
                    # Determine module path for importing
                    rel_path = os.path.relpath(plugin_dir, os.path.dirname(base_dir))
                    
                    if os.path.exists(plugin_py):
                        # Direct plugin.py file
                        module_path = f"ai_document_organizer_v2.plugins.{item}.plugin"
                    else:
                        # Package with __init__.py
                        module_path = f"ai_document_organizer_v2.plugins.{item}"
                    
                    # Import the module
                    plugin_module = importlib.import_module(module_path)
                    
                    # Find plugin classes (subclasses of BasePlugin)
                    plugin_classes = []
                    for name, obj in inspect.getmembers(plugin_module):
                        if (inspect.isclass(obj) and issubclass(obj, BasePlugin) and 
                            obj is not BasePlugin and obj.__module__ == plugin_module.__name__):
                            plugin_classes.append(obj)
                    
                    if not plugin_classes:
                        logger.warning(f"No plugin classes found in {module_path}")
                        failed_count += 1
                        failures.append({
                            'path': item_path,
                            'error': "No plugin classes found"
                        })
                        continue
                    
                    # Create instances of the plugin classes
                    for plugin_class in plugin_classes:
                        try:
                            plugin_type = plugin_class.plugin_type
                            if plugin_type is None:
                                logger.warning(f"Plugin class {plugin_class.__name__} has no plugin_type")
                                continue
                            
                            # Generate plugin ID if needed
                            plugin_id = f"{plugin_type}.{item}"
                            
                            # Create plugin instance
                            plugin = plugin_class(plugin_id=plugin_id, 
                                                 name=getattr(plugin_class, 'name', plugin_class.__name__),
                                                 version=getattr(plugin_class, 'version', '1.0.0'),
                                                 description=getattr(plugin_class, 'description', ''))
                            
                            # Register the plugin
                            self.register_plugin(plugin, plugin_module)
                            loaded_count += 1
                            logger.info(f"Registered plugin: {plugin.name} ({plugin.plugin_id})")
                        except Exception as e:
                            logger.error(f"Error creating plugin instance for {plugin_class.__name__}: {e}")
                            failed_count += 1
                            failures.append({
                                'path': item_path,
                                'error': f"Error creating plugin instance: {str(e)}"
                            })
                except Exception as e:
                    logger.error(f"Error loading plugin from {item_path}: {e}")
                    failed_count += 1
                    failures.append({
                        'path': item_path,
                        'error': str(e)
                    })
        
        return {
            'found': discovered_count,
            'loaded': loaded_count,
            'failed': failed_count,
            'failures': failures
        }
    
    def register_plugin(self, plugin: BasePlugin, module=None) -> bool:
        """
        Register a plugin with the plugin manager.
        
        Args:
            plugin: Plugin instance to register
            module: Optional module the plugin was loaded from
            
        Returns:
            True if registration was successful, False otherwise
        """
        if plugin.plugin_id in self.plugins:
            logger.warning(f"Plugin ID collision: {plugin.plugin_id}")
            return False
        
        # Store the plugin instance
        self.plugins[plugin.plugin_id] = plugin
        
        # Store the module if provided
        if module is not None:
            self.plugin_modules[plugin.plugin_id] = module
        
        # Register by plugin type
        plugin_type = plugin.plugin_type
        if plugin_type not in self.plugin_types:
            self.plugin_types[plugin_type] = {}
        
        self.plugin_types[plugin_type][plugin.plugin_id] = plugin
        
        return True
    
    def initialize_plugins(self) -> Dict[str, Any]:
        """
        Initialize all registered plugins.
        
        Returns:
            Dictionary with initialization results:
            - 'successful': Number of plugins successfully initialized
            - 'failed': Number of plugins that failed to initialize
            - 'failures': List of dictionaries with failure information
        """
        successful = 0
        failed = 0
        failures = []
        
        # Initialize all plugins
        for plugin_id, plugin in self.plugins.items():
            if plugin_id in self.initialized_plugins:
                continue  # Skip already initialized plugins
            
            try:
                # Initialize the plugin
                if plugin.initialize():
                    self.initialized_plugins.add(plugin_id)
                    successful += 1
                    logger.debug(f"Initialized plugin: {plugin.name} ({plugin_id})")
                else:
                    failed += 1
                    failures.append({
                        'plugin_id': plugin_id,
                        'plugin_name': plugin.name,
                        'error': "Plugin initialize() returned False"
                    })
                    logger.warning(f"Plugin failed to initialize: {plugin.name} ({plugin_id})")
            except Exception as e:
                failed += 1
                failures.append({
                    'plugin_id': plugin_id,
                    'plugin_name': plugin.name,
                    'error': str(e)
                })
                logger.error(f"Error initializing plugin {plugin.name} ({plugin_id}): {e}")
        
        return {
            'successful': successful,
            'failed': failed,
            'failures': failures
        }
    
    def shutdown_plugins(self) -> Dict[str, Any]:
        """
        Shutdown all initialized plugins.
        
        Returns:
            Dictionary with shutdown results:
            - 'successful': Number of plugins successfully shut down
            - 'failed': Number of plugins that failed to shut down
            - 'failures': List of dictionaries with failure information
        """
        successful = 0
        failed = 0
        failures = []
        
        # Shutdown initialized plugins in reverse order
        for plugin_id in sorted(self.initialized_plugins, reverse=True):
            plugin = self.plugins.get(plugin_id)
            if plugin is None:
                continue
            
            try:
                # Shutdown the plugin
                if plugin.shutdown():
                    successful += 1
                    logger.debug(f"Shutdown plugin: {plugin.name} ({plugin_id})")
                else:
                    failed += 1
                    failures.append({
                        'plugin_id': plugin_id,
                        'plugin_name': plugin.name,
                        'error': "Plugin shutdown() returned False"
                    })
                    logger.warning(f"Plugin failed to shutdown: {plugin.name} ({plugin_id})")
            except Exception as e:
                failed += 1
                failures.append({
                    'plugin_id': plugin_id,
                    'plugin_name': plugin.name,
                    'error': str(e)
                })
                logger.error(f"Error shutting down plugin {plugin.name} ({plugin_id}): {e}")
        
        # Clear initialized plugins set
        self.initialized_plugins.clear()
        
        return {
            'successful': successful,
            'failed': failed,
            'failures': failures
        }
    
    def get_plugin(self, plugin_id: str) -> Optional[BasePlugin]:
        """
        Get a plugin by its ID.
        
        Args:
            plugin_id: Plugin ID to look up
            
        Returns:
            Plugin instance or None if not found
        """
        return self.plugins.get(plugin_id)
    
    def get_plugins_of_type(self, plugin_type: str) -> Dict[str, BasePlugin]:
        """
        Get all plugins of a specific type.
        
        Args:
            plugin_type: Plugin type to look up
            
        Returns:
            Dictionary mapping plugin IDs to plugin instances
        """
        return self.plugin_types.get(plugin_type, {})
    
    def get_plugin_types(self) -> List[str]:
        """
        Get list of all registered plugin types.
        
        Returns:
            List of plugin type strings
        """
        return list(self.plugin_types.keys())
    
    def is_plugin_initialized(self, plugin_id: str) -> bool:
        """
        Check if a plugin is initialized.
        
        Args:
            plugin_id: Plugin ID to check
            
        Returns:
            True if the plugin is initialized, False otherwise
        """
        return plugin_id in self.initialized_plugins
    
    def get_plugin_info(self, plugin_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a plugin.
        
        Args:
            plugin_id: Plugin ID to get information for
            
        Returns:
            Dictionary with plugin information
        """
        plugin = self.get_plugin(plugin_id)
        if plugin is None:
            return {}
        
        return {
            'id': plugin.plugin_id,
            'name': plugin.name,
            'version': plugin.version,
            'description': plugin.description,
            'type': plugin.plugin_type,
            'initialized': self.is_plugin_initialized(plugin_id),
            'enabled': plugin.enabled,
            'config': plugin.get_config()
        }


# Determine the base directory for the ai_document_organizer_v2 package
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))