"""
API Plugin Manager for the External API Integration Framework.

This module provides plugin discovery and management capabilities,
allowing for dynamic loading and registration of API plugins.
"""

import logging
import os
import importlib
import inspect
from typing import Any, Dict, List, Optional, Type, Set

from .api_plugin_base import APIPluginBase
from .api_gateway import APIGateway


logger = logging.getLogger(__name__)


class APIPluginManager:
    """
    Manages API plugin discovery, loading, and registration.
    
    This class is responsible for finding and loading API plugins, registering
    them with the API gateway, and providing plugin management operations.
    """
    
    def __init__(self, api_gateway: APIGateway, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the API Plugin Manager.
        
        Args:
            api_gateway: API Gateway instance for plugin registration
            config: Optional configuration dictionary
        """
        self.api_gateway = api_gateway
        self.config = config or {}
        self.plugin_dirs = self.config.get('plugin_dirs', [])
        self.plugin_classes = {}  # type: Dict[str, Type[APIPluginBase]]
        self.plugin_configs = {}  # type: Dict[str, Dict[str, Any]]
        
        # Add default plugin directory
        default_plugin_dir = os.path.join(os.path.dirname(__file__), 'plugins')
        if default_plugin_dir not in self.plugin_dirs:
            self.plugin_dirs.append(default_plugin_dir)
            
        logger.info(f"API Plugin Manager initialized with {len(self.plugin_dirs)} plugin directories")
    
    def discover_plugins(self) -> List[str]:
        """
        Discover available API plugins in the configured plugin directories.
        
        Returns:
            List of discovered plugin class names
        """
        discovered_plugins = []
        
        for plugin_dir in self.plugin_dirs:
            if not os.path.isdir(plugin_dir):
                logger.warning(f"Plugin directory does not exist: {plugin_dir}")
                continue
                
            logger.info(f"Searching for plugins in: {plugin_dir}")
            
            # Get all Python files in the directory
            for filename in os.listdir(plugin_dir):
                if filename.endswith('.py') and not filename.startswith('__'):
                    module_name = filename[:-3]  # Remove .py extension
                    
                    try:
                        # Determine the module path
                        module_path = os.path.join(plugin_dir, filename)
                        module_path = os.path.relpath(module_path)
                        module_path = module_path.replace(os.path.sep, '.')
                        module_path = module_path[:-3]  # Remove .py extension
                        
                        # Import the module
                        module = importlib.import_module(module_path)
                        
                        # Find all classes that inherit from APIPluginBase
                        for name, obj in inspect.getmembers(module):
                            if (inspect.isclass(obj) and 
                                issubclass(obj, APIPluginBase) and 
                                obj != APIPluginBase):
                                
                                # Store the plugin class
                                self.plugin_classes[name] = obj
                                discovered_plugins.append(name)
                                logger.info(f"Discovered API plugin: {name}")
                                
                    except Exception as e:
                        logger.error(f"Error discovering plugins in {filename}: {e}")
        
        return discovered_plugins
    
    def load_plugin(self, plugin_name: str, config: Optional[Dict[str, Any]] = None) -> Optional[APIPluginBase]:
        """
        Load and initialize a plugin by name.
        
        Args:
            plugin_name: Name of the plugin class to load
            config: Optional configuration for the plugin
            
        Returns:
            Initialized plugin instance or None if loading failed
        """
        if plugin_name not in self.plugin_classes:
            logger.error(f"Plugin not found: {plugin_name}")
            return None
            
        try:
            # Create plugin instance
            plugin_class = self.plugin_classes[plugin_name]
            plugin = plugin_class()
            
            # Initialize the plugin with configuration
            plugin_config = config or {}
            
            # Store the configuration for future reference
            self.plugin_configs[plugin_name] = plugin_config
            
            # Initialize the plugin
            if not plugin.initialize(plugin_config):
                logger.error(f"Failed to initialize plugin: {plugin_name}")
                return None
                
            logger.info(f"Loaded plugin: {plugin_name}")
            return plugin
            
        except Exception as e:
            logger.error(f"Error loading plugin {plugin_name}: {e}")
            return None
    
    def register_plugin(self, plugin_name: str, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Load and register a plugin with the API gateway.
        
        Args:
            plugin_name: Name of the plugin class to register
            config: Optional configuration for the plugin
            
        Returns:
            True if registration was successful, False otherwise
        """
        # Load the plugin
        plugin = self.load_plugin(plugin_name, config)
        
        if not plugin:
            return False
            
        # Register with the API gateway
        if self.api_gateway.register_plugin(plugin):
            logger.info(f"Registered plugin with API gateway: {plugin_name}")
            return True
        else:
            logger.error(f"Failed to register plugin with API gateway: {plugin_name}")
            return False
    
    def register_all_plugins(self, configs: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[str, bool]:
        """
        Discover, load, and register all available plugins.
        
        Args:
            configs: Optional dictionary mapping plugin names to configurations
            
        Returns:
            Dictionary mapping plugin names to registration success status
        """
        # Discover available plugins
        self.discover_plugins()
        
        # Process configurations
        plugin_configs = configs or {}
        results = {}
        
        # Register each plugin
        for plugin_name in self.plugin_classes:
            config = plugin_configs.get(plugin_name, {})
            results[plugin_name] = self.register_plugin(plugin_name, config)
        
        return results
    
    def get_available_plugins(self) -> List[str]:
        """
        Get a list of available plugin class names.
        
        Returns:
            List of plugin class names
        """
        return list(self.plugin_classes.keys())
    
    def get_registered_plugins(self) -> List[str]:
        """
        Get a list of registered plugin names.
        
        Returns:
            List of registered plugin names
        """
        return self.api_gateway.get_registered_plugins()
    
    def get_plugin_info(self, plugin_name: str) -> Dict[str, Any]:
        """
        Get information about a plugin.
        
        Args:
            plugin_name: Name of the plugin
            
        Returns:
            Dictionary with plugin information
        """
        if plugin_name not in self.plugin_classes:
            return {
                'name': plugin_name,
                'available': False,
                'registered': False
            }
            
        plugin_class = self.plugin_classes[plugin_name]
        registered = plugin_name in self.get_registered_plugins()
        
        # Create a temporary instance to get plugin information
        try:
            plugin_instance = plugin_class()
            
            info = {
                'name': plugin_name,
                'available': True,
                'registered': registered,
                'api_name': plugin_instance.api_name,
                'api_version': plugin_instance.api_version,
                'auth_methods': plugin_instance.supported_auth_methods,
                'requires_rate_limiting': plugin_instance.requires_rate_limiting,
                'operations': plugin_instance.available_operations,
                'capabilities': {
                    'streaming': plugin_instance.supports_streaming,
                    'webhooks': plugin_instance.supports_webhooks,
                    'batch_operations': plugin_instance.supports_batch_operations
                }
            }
            
            # Add status information if registered
            if registered:
                plugin_status = self.api_gateway.get_plugin_status(plugin_name)
                info['status'] = plugin_status
                
            return info
            
        except Exception as e:
            logger.error(f"Error getting plugin info for {plugin_name}: {e}")
            return {
                'name': plugin_name,
                'available': True,
                'registered': registered,
                'error': str(e)
            }
    
    def get_all_plugin_info(self) -> Dict[str, Dict[str, Any]]:
        """
        Get information about all available plugins.
        
        Returns:
            Dictionary mapping plugin names to plugin information
        """
        return {
            plugin_name: self.get_plugin_info(plugin_name)
            for plugin_name in self.plugin_classes
        }