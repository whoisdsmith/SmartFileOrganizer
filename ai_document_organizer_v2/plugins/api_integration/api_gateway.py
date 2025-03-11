"""
API Gateway for External API Integration Framework.

This module provides a centralized entry point for all external API calls,
managing authentication, rate limiting, response caching, transformation,
and plugin registration.
"""

import logging
import time
import threading
from typing import Any, Dict, List, Optional, Union, Set

from .api_plugin_base import APIPluginBase
from .rate_limiter import RateLimiter
from .auth_provider import AuthenticationProvider
from .cache_manager import CacheManager
from .transformer import TransformationManager


logger = logging.getLogger(__name__)


class APIGateway:
    """
    Central gateway for all external API calls.
    
    This class serves as the main entry point for the API Integration Framework,
    providing plugin registration, authentication management, and rate limiting.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the API Gateway.
        
        Args:
            config: Optional configuration dictionary for the gateway
        """
        self.config = config or {}
        self.rate_limiter = RateLimiter()
        self.auth_provider = AuthenticationProvider()
        
        # Initialize cache manager
        cache_config = self.config.get('cache_config', {})
        self.cache_manager = CacheManager(cache_config)
        
        # Initialize transformation manager
        transform_config_dir = self.config.get('transform_config_dir')
        self.transform_manager = TransformationManager(transform_config_dir)
        
        # Create default transformation pipelines if configured
        if self.config.get('create_default_transformations', True):
            self.transform_manager.create_default_pipelines()
        
        # Plugin registry
        self.plugins = {}  # type: Dict[str, APIPluginBase]
        self.plugin_status = {}  # type: Dict[str, Dict[str, Any]]
        
        # Thread safety
        self._lock = threading.RLock()
        
        logger.info("API Gateway initialized with caching and transformation capabilities")
    
    def register_plugin(self, plugin: APIPluginBase) -> bool:
        """
        Register an API plugin with the gateway.
        
        Args:
            plugin: API plugin instance to register
            
        Returns:
            True if registration was successful, False otherwise
        """
        try:
            plugin_name = plugin.__class__.__name__
            api_name = plugin.api_name
            
            with self._lock:
                # Check if plugin is already registered
                if plugin_name in self.plugins:
                    logger.warning(f"Plugin {plugin_name} is already registered")
                    return False
                
                # Register the plugin
                self.plugins[plugin_name] = plugin
                
                # Initialize plugin status
                self.plugin_status[plugin_name] = {
                    'registered_at': time.time(),
                    'api_name': api_name,
                    'is_authenticated': plugin.is_authenticated,
                    'last_used': None,
                    'request_count': 0,
                    'error_count': 0,
                    'active': True
                }
                
                # Configure rate limiting if required
                if plugin.requires_rate_limiting:
                    self.rate_limiter.register_api(
                        api_name, 
                        plugin.rate_limit_rules
                    )
                
                logger.info(f"Registered plugin {plugin_name} for API {api_name}")
                return True
                
        except Exception as e:
            logger.error(f"Error registering plugin: {e}")
            return False
    
    def unregister_plugin(self, plugin_name: str) -> bool:
        """
        Unregister an API plugin from the gateway.
        
        Args:
            plugin_name: Name of the plugin to unregister
            
        Returns:
            True if unregistration was successful, False otherwise
        """
        with self._lock:
            if plugin_name not in self.plugins:
                logger.warning(f"Plugin {plugin_name} is not registered")
                return False
            
            # Get the plugin instance
            plugin = self.plugins[plugin_name]
            
            # Close the plugin
            try:
                plugin.close()
            except Exception as e:
                logger.error(f"Error closing plugin {plugin_name}: {e}")
            
            # Remove the plugin from the registry
            del self.plugins[plugin_name]
            
            # Remove the plugin status
            if plugin_name in self.plugin_status:
                del self.plugin_status[plugin_name]
            
            # Unregister from rate limiter if needed
            if plugin.requires_rate_limiting:
                self.rate_limiter.unregister_api(plugin.api_name)
            
            logger.info(f"Unregistered plugin {plugin_name}")
            return True
    
    def get_plugin(self, plugin_name: str) -> Optional[APIPluginBase]:
        """
        Get a registered plugin by name.
        
        Args:
            plugin_name: Name of the plugin to retrieve
            
        Returns:
            Plugin instance or None if not found
        """
        return self.plugins.get(plugin_name)
    
    def get_plugin_by_api(self, api_name: str) -> Optional[APIPluginBase]:
        """
        Get a plugin by API name.
        
        Args:
            api_name: Name of the API to find a plugin for
            
        Returns:
            Plugin instance or None if not found
        """
        for plugin in self.plugins.values():
            if plugin.api_name == api_name:
                return plugin
        return None
    
    def authenticate_plugin(self, plugin_name: str) -> bool:
        """
        Authenticate a plugin with its API service.
        
        Args:
            plugin_name: Name of the plugin to authenticate
            
        Returns:
            True if authentication was successful, False otherwise
        """
        plugin = self.get_plugin(plugin_name)
        
        if not plugin:
            logger.error(f"Plugin {plugin_name} is not registered")
            return False
            
        try:
            # Authenticate the plugin
            auth_result = plugin.authenticate()
            
            # Update plugin status
            with self._lock:
                if plugin_name in self.plugin_status:
                    self.plugin_status[plugin_name]['is_authenticated'] = auth_result
                    
            return auth_result
            
        except Exception as e:
            logger.error(f"Error authenticating plugin {plugin_name}: {e}")
            return False
    
    def execute_request(self, 
                       plugin_name: str,
                       endpoint: str,
                       method: str = 'GET',
                       params: Optional[Dict[str, Any]] = None,
                       data: Optional[Dict[str, Any]] = None,
                       headers: Optional[Dict[str, str]] = None,
                       files: Optional[Dict[str, Any]] = None,
                       timeout: Optional[int] = None,
                       **kwargs) -> Dict[str, Any]:
        """
        Execute a request through a plugin.
        
        Args:
            plugin_name: Name of the plugin to use
            endpoint: API endpoint to call
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            params: URL parameters
            data: Request body data
            headers: HTTP headers
            files: Files to upload
            timeout: Request timeout in seconds
            **kwargs: Additional arguments for the request
            
        Returns:
            Dictionary with response data and metadata
        """
        plugin = self.get_plugin(plugin_name)
        
        if not plugin:
            logger.error(f"Plugin {plugin_name} is not registered")
            return {
                'success': False,
                'error': f"Plugin {plugin_name} is not registered",
                'data': None
            }
            
        # Check if plugin is authenticated
        if not plugin.is_authenticated:
            logger.warning(f"Plugin {plugin_name} is not authenticated, attempting authentication")
            if not self.authenticate_plugin(plugin_name):
                return {
                    'success': False,
                    'error': f"Failed to authenticate plugin {plugin_name}",
                    'data': None
                }
        
        # Check rate limits
        if plugin.requires_rate_limiting:
            if not self.rate_limiter.can_make_request(plugin.api_name):
                wait_time = self.rate_limiter.get_wait_time(plugin.api_name)
                logger.warning(f"Rate limit exceeded for {plugin.api_name}, need to wait {wait_time:.2f} seconds")
                return {
                    'success': False,
                    'error': f"Rate limit exceeded, try again in {wait_time:.2f} seconds",
                    'data': None,
                    'rate_limited': True,
                    'wait_time': wait_time
                }
        
        try:
            # Update plugin status
            with self._lock:
                if plugin_name in self.plugin_status:
                    self.plugin_status[plugin_name]['last_used'] = time.time()
                    self.plugin_status[plugin_name]['request_count'] += 1
            
            # Execute the request
            result = plugin.execute_request(
                endpoint=endpoint,
                method=method,
                params=params,
                data=data,
                headers=headers,
                files=files,
                timeout=timeout,
                **kwargs
            )
            
            # Record the request in rate limiter
            if plugin.requires_rate_limiting:
                self.rate_limiter.record_request(plugin.api_name)
            
            # Update error count if request failed
            if not result.get('success', False):
                with self._lock:
                    if plugin_name in self.plugin_status:
                        self.plugin_status[plugin_name]['error_count'] += 1
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing request through plugin {plugin_name}: {e}")
            
            # Update error count
            with self._lock:
                if plugin_name in self.plugin_status:
                    self.plugin_status[plugin_name]['error_count'] += 1
            
            return {
                'success': False,
                'error': str(e),
                'data': None
            }
    
    def execute_operation(self,
                         plugin_name: str,
                         operation: str,
                         transform_pipeline: Optional[str] = None,
                         bypass_cache: bool = False,
                         **kwargs) -> Dict[str, Any]:
        """
        Execute a named operation through a plugin.
        
        Args:
            plugin_name: Name of the plugin to use
            operation: Name of the operation to execute
            transform_pipeline: Optional name of a transformation pipeline to apply to the result
            bypass_cache: Whether to bypass the cache
            **kwargs: Operation-specific parameters
            
        Returns:
            Dictionary with operation results
        """
        plugin = self.get_plugin(plugin_name)
        
        if not plugin:
            logger.error(f"Plugin {plugin_name} is not registered")
            return {
                'success': False,
                'error': f"Plugin {plugin_name} is not registered",
                'data': None
            }
            
        # Check if plugin is authenticated
        if not plugin.is_authenticated:
            logger.warning(f"Plugin {plugin_name} is not authenticated, attempting authentication")
            if not self.authenticate_plugin(plugin_name):
                return {
                    'success': False,
                    'error': f"Failed to authenticate plugin {plugin_name}",
                    'data': None
                }
        
        # Check rate limits
        if plugin.requires_rate_limiting:
            if not self.rate_limiter.can_make_request(plugin.api_name):
                wait_time = self.rate_limiter.get_wait_time(plugin.api_name)
                logger.warning(f"Rate limit exceeded for {plugin.api_name}, need to wait {wait_time:.2f} seconds")
                return {
                    'success': False,
                    'error': f"Rate limit exceeded, try again in {wait_time:.2f} seconds",
                    'data': None,
                    'rate_limited': True,
                    'wait_time': wait_time
                }
        
        # Check cache if caching is enabled and not bypassed
        if not bypass_cache and plugin.cacheable_operations and operation in plugin.cacheable_operations:
            cache_result = self.cache_manager.get(plugin_name, operation, kwargs)
            
            if cache_result.get('cache_hit', False):
                # We have a cache hit
                logger.info(f"Cache hit for {plugin_name}.{operation}")
                
                # Apply transformation if requested
                if transform_pipeline and cache_result.get('cache_data') is not None:
                    transformed_data = self._apply_transformation(
                        cache_result['cache_data'], 
                        transform_pipeline,
                        {
                            'plugin_name': plugin_name,
                            'operation': operation,
                            'parameters': kwargs,
                            'from_cache': True,
                            'cache_metadata': cache_result.get('metadata', {})
                        }
                    )
                    
                    return {
                        'success': True,
                        'data': transformed_data,
                        'from_cache': True,
                        'cache_metadata': cache_result.get('metadata', {})
                    }
                    
                # Return cached data without transformation
                return {
                    'success': True,
                    'data': cache_result['cache_data'],
                    'from_cache': True,
                    'cache_metadata': cache_result.get('metadata', {})
                }
        
        try:
            # Update plugin status
            with self._lock:
                if plugin_name in self.plugin_status:
                    self.plugin_status[plugin_name]['last_used'] = time.time()
                    self.plugin_status[plugin_name]['request_count'] += 1
            
            # Execute the operation
            result = plugin.execute_operation(operation, **kwargs)
            
            # Record the request in rate limiter
            if plugin.requires_rate_limiting:
                self.rate_limiter.record_request(plugin.api_name)
            
            # Update error count if operation failed
            if not result.get('success', False):
                with self._lock:
                    if plugin_name in self.plugin_status:
                        self.plugin_status[plugin_name]['error_count'] += 1
                        
                # Apply error transformation if configured
                if transform_pipeline:
                    context = {
                        'plugin_name': plugin_name,
                        'operation': operation,
                        'parameters': kwargs,
                        'from_cache': False,
                        'error': result.get('error'),
                        'error_code': result.get('error_code', 500)
                    }
                    
                    transformed_data = self._apply_transformation(result, transform_pipeline, context)
                    result['data'] = transformed_data
                    
                return result
            
            # Cache successful result if caching is enabled
            if plugin.cacheable_operations and operation in plugin.cacheable_operations:
                ttl = None
                if hasattr(plugin, 'cache_ttls') and isinstance(plugin.cache_ttls, dict):
                    ttl = plugin.cache_ttls.get(operation)
                    
                self.cache_manager.put(plugin_name, operation, kwargs, result.get('data'), ttl)
            
            # Apply transformation if requested
            if transform_pipeline:
                context = {
                    'plugin_name': plugin_name,
                    'operation': operation,
                    'parameters': kwargs,
                    'from_cache': False
                }
                
                transformed_data = self._apply_transformation(result.get('data'), transform_pipeline, context)
                result['data'] = transformed_data
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing operation {operation} through plugin {plugin_name}: {e}")
            
            # Update error count
            with self._lock:
                if plugin_name in self.plugin_status:
                    self.plugin_status[plugin_name]['error_count'] += 1
            
            error_result = {
                'success': False,
                'error': str(e),
                'data': None
            }
            
            # Apply error transformation if configured
            if transform_pipeline:
                context = {
                    'plugin_name': plugin_name,
                    'operation': operation,
                    'parameters': kwargs,
                    'from_cache': False,
                    'error': str(e),
                    'error_code': 500
                }
                
                transformed_error = self._apply_transformation(error_result, transform_pipeline, context)
                error_result['data'] = transformed_error
                
            return error_result
    
    def get_registered_plugins(self) -> List[str]:
        """
        Get a list of registered plugin names.
        
        Returns:
            List of registered plugin names
        """
        return list(self.plugins.keys())
    
    def get_plugin_status(self, plugin_name: str) -> Dict[str, Any]:
        """
        Get status information for a plugin.
        
        Args:
            plugin_name: Name of the plugin
            
        Returns:
            Dictionary with plugin status information
        """
        if plugin_name not in self.plugin_status:
            return {
                'error': f"Plugin {plugin_name} is not registered",
                'registered': False
            }
            
        return self.plugin_status[plugin_name]
    
    def get_all_plugin_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get status information for all registered plugins.
        
        Returns:
            Dictionary mapping plugin names to status information
        """
        return dict(self.plugin_status)
    
    def reset_plugin_status(self, plugin_name: str) -> bool:
        """
        Reset status counters for a plugin.
        
        Args:
            plugin_name: Name of the plugin
            
        Returns:
            True if reset was successful, False otherwise
        """
        if plugin_name not in self.plugin_status:
            return False
            
        with self._lock:
            self.plugin_status[plugin_name]['request_count'] = 0
            self.plugin_status[plugin_name]['error_count'] = 0
            
        return True
    
    def reset_all_plugin_status(self) -> bool:
        """
        Reset status counters for all plugins.
        
        Returns:
            True if reset was successful
        """
        with self._lock:
            for plugin_name in self.plugin_status:
                self.plugin_status[plugin_name]['request_count'] = 0
                self.plugin_status[plugin_name]['error_count'] = 0
                
        return True
        
    def _apply_transformation(self, data: Any, pipeline_name: str, context: Optional[Dict[str, Any]] = None) -> Any:
        """
        Apply a transformation pipeline to data.
        
        Args:
            data: Data to transform
            pipeline_name: Name of the transformation pipeline to apply
            context: Optional context dictionary for the transformation
            
        Returns:
            Transformed data
        """
        if not pipeline_name:
            return data
            
        # Get the pipeline
        pipeline = self.transform_manager.get_pipeline(pipeline_name)
        
        if not pipeline:
            logger.warning(f"Transformation pipeline {pipeline_name} not found")
            return data
            
        try:
            # Apply the transformation
            return pipeline.transform(data, context)
            
        except Exception as e:
            logger.error(f"Error applying transformation pipeline {pipeline_name}: {e}")
            return data
            
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        return self.cache_manager.get_stats()
        
    def clear_cache(self) -> Dict[str, Any]:
        """
        Clear the cache.
        
        Returns:
            Dictionary with clear operation result
        """
        return self.cache_manager.clear()
        
    def invalidate_cache(self, plugin_name: Optional[str] = None, 
                       operation: Optional[str] = None,
                       parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Invalidate cache entries that match the given criteria.
        
        Args:
            plugin_name: Optional plugin name filter
            operation: Optional operation name filter
            parameters: Optional parameters filter
            
        Returns:
            Dictionary with invalidation result
        """
        return self.cache_manager.invalidate(plugin_name, operation, parameters)
        
    def get_transformation_pipelines(self) -> List[Dict[str, Any]]:
        """
        Get a list of available transformation pipelines.
        
        Returns:
            List of pipeline information dictionaries
        """
        return self.transform_manager.list_pipelines()
        
    def register_transformation_pipeline(self, name: str, config: Dict[str, Any]) -> bool:
        """
        Register a new transformation pipeline.
        
        Args:
            name: Name for the pipeline
            config: Configuration dictionary for the pipeline
            
        Returns:
            True if registration was successful, False otherwise
        """
        return self.transform_manager.register_pipeline(name, config)
        
    def save_transformation_pipeline(self, name: str) -> bool:
        """
        Save a transformation pipeline configuration to a file.
        
        Args:
            name: Name of the pipeline to save
            
        Returns:
            True if save was successful, False otherwise
        """
        return self.transform_manager.save_pipeline_config(name)