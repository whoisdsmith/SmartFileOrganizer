"""
API Gateway for the External API Integration Framework.

This module implements a centralized gateway for all external API interactions,
providing a single entry point for accessing different API services.
"""

import logging
import threading
from typing import Any, Dict, List, Optional, Callable, Union, Type
import time

from .api_plugin_base import APIPluginBase
from .rate_limiter import RateLimiter
from .auth_provider import AuthProvider


logger = logging.getLogger(__name__)


class APIGateway:
    """
    Centralized gateway for external API interactions.
    
    This class provides a unified interface for interacting with various external APIs,
    handling authentication, rate limiting, and plugin management.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the API Gateway.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.plugins = {}  # type: Dict[str, APIPluginBase]
        self.rate_limiters = {}  # type: Dict[str, RateLimiter]
        self.auth_provider = AuthProvider()
        self.lock = threading.RLock()
        
        logger.info("API Gateway initialized")
    
    def register_plugin(self, plugin: APIPluginBase) -> bool:
        """
        Register an API plugin with the gateway.
        
        Args:
            plugin: API plugin instance
            
        Returns:
            True if registration was successful, False otherwise
        """
        if not isinstance(plugin, APIPluginBase):
            logger.error(f"Cannot register plugin: not an APIPluginBase instance")
            return False
            
        plugin_name = plugin.api_name
        
        with self.lock:
            if plugin_name in self.plugins:
                logger.warning(f"Plugin '{plugin_name}' already registered")
                return False
                
            # If rate limiting is required, create a rate limiter
            if plugin.requires_rate_limiting:
                self.rate_limiters[plugin_name] = RateLimiter(plugin.rate_limit_rules)
                logger.info(f"Created rate limiter for '{plugin_name}'")
                
            # Store the plugin
            self.plugins[plugin_name] = plugin
            logger.info(f"Registered API plugin: {plugin_name} (v{plugin.api_version})")
            
            return True
    
    def unregister_plugin(self, plugin_name: str) -> bool:
        """
        Unregister an API plugin from the gateway.
        
        Args:
            plugin_name: Name of the plugin to unregister
            
        Returns:
            True if unregistration was successful, False otherwise
        """
        with self.lock:
            if plugin_name not in self.plugins:
                logger.warning(f"Plugin '{plugin_name}' not registered")
                return False
                
            # Clean up resources
            try:
                self.plugins[plugin_name].close()
            except Exception as e:
                logger.error(f"Error closing plugin '{plugin_name}': {e}")
                
            # Remove rate limiter if it exists
            if plugin_name in self.rate_limiters:
                del self.rate_limiters[plugin_name]
                
            # Remove the plugin
            del self.plugins[plugin_name]
            logger.info(f"Unregistered API plugin: {plugin_name}")
            
            return True
    
    def get_plugin(self, plugin_name: str) -> Optional[APIPluginBase]:
        """
        Get a registered API plugin by name.
        
        Args:
            plugin_name: Name of the plugin to retrieve
            
        Returns:
            API plugin instance or None if not found
        """
        return self.plugins.get(plugin_name)
    
    def get_registered_plugins(self) -> List[str]:
        """
        Get a list of all registered plugin names.
        
        Returns:
            List of plugin names
        """
        return list(self.plugins.keys())
    
    def execute_request(self, 
                       plugin_name: str,
                       endpoint: str,
                       method: str = 'GET',
                       params: Optional[Dict[str, Any]] = None,
                       data: Optional[Dict[str, Any]] = None,
                       headers: Optional[Dict[str, str]] = None,
                       files: Optional[Dict[str, Any]] = None,
                       timeout: Optional[int] = None,
                       retry_count: int = 3,
                       retry_delay: int = 1,
                       **kwargs) -> Dict[str, Any]:
        """
        Execute a request to an API through a registered plugin.
        
        Args:
            plugin_name: Name of the plugin to use
            endpoint: API endpoint to call
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            params: URL parameters
            data: Request body data
            headers: HTTP headers
            files: Files to upload
            timeout: Request timeout in seconds
            retry_count: Number of retries for failed requests
            retry_delay: Delay between retries in seconds
            **kwargs: Additional arguments for the request
            
        Returns:
            Dictionary with response data and metadata
        """
        plugin = self.get_plugin(plugin_name)
        
        if not plugin:
            logger.error(f"Plugin '{plugin_name}' not found")
            return {
                'success': False,
                'error': f"Plugin '{plugin_name}' not found",
                'data': None
            }
            
        # Check if plugin is authenticated
        if not plugin.is_authenticated and not plugin.authenticate():
            logger.error(f"Plugin '{plugin_name}' is not authenticated")
            return {
                'success': False,
                'error': f"Plugin '{plugin_name}' is not authenticated",
                'data': None
            }
            
        # Check rate limits
        if plugin.requires_rate_limiting:
            rate_limiter = self.rate_limiters.get(plugin_name)
            
            if rate_limiter and not rate_limiter.can_proceed():
                logger.warning(f"Rate limit exceeded for '{plugin_name}'")
                return {
                    'success': False,
                    'error': "Rate limit exceeded",
                    'data': None,
                    'retry_after': rate_limiter.get_retry_after()
                }
        
        # Execute the request with retry logic
        for attempt in range(retry_count):
            try:
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
                
                # Record successful request for rate limiting
                if plugin.requires_rate_limiting and plugin_name in self.rate_limiters:
                    self.rate_limiters[plugin_name].record_request()
                    
                return result
                
            except Exception as e:
                logger.warning(f"Request failed (attempt {attempt+1}/{retry_count}): {e}")
                
                if attempt < retry_count - 1:
                    # Wait before retrying
                    time.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
                else:
                    # Last attempt failed
                    logger.error(f"Request failed after {retry_count} attempts: {e}")
                    return {
                        'success': False,
                        'error': str(e),
                        'data': None
                    }
    
    def execute_operation(self,
                         plugin_name: str,
                         operation: str,
                         retry_count: int = 3,
                         **kwargs) -> Dict[str, Any]:
        """
        Execute a named operation through a registered plugin.
        
        Args:
            plugin_name: Name of the plugin to use
            operation: Name of the operation to execute
            retry_count: Number of retries for failed operations
            **kwargs: Operation-specific parameters
            
        Returns:
            Dictionary with operation results
        """
        plugin = self.get_plugin(plugin_name)
        
        if not plugin:
            logger.error(f"Plugin '{plugin_name}' not found")
            return {
                'success': False,
                'error': f"Plugin '{plugin_name}' not found",
                'data': None
            }
            
        # Check if operation is supported
        if operation not in plugin.available_operations:
            logger.error(f"Operation '{operation}' not supported by plugin '{plugin_name}'")
            return {
                'success': False,
                'error': f"Operation '{operation}' not supported",
                'data': None
            }
            
        # Check if plugin is authenticated
        if not plugin.is_authenticated and not plugin.authenticate():
            logger.error(f"Plugin '{plugin_name}' is not authenticated")
            return {
                'success': False,
                'error': f"Plugin '{plugin_name}' is not authenticated",
                'data': None
            }
            
        # Check rate limits
        if plugin.requires_rate_limiting:
            rate_limiter = self.rate_limiters.get(plugin_name)
            
            if rate_limiter and not rate_limiter.can_proceed():
                logger.warning(f"Rate limit exceeded for '{plugin_name}'")
                return {
                    'success': False,
                    'error': "Rate limit exceeded",
                    'data': None,
                    'retry_after': rate_limiter.get_retry_after()
                }
        
        # Execute the operation with retry logic
        for attempt in range(retry_count):
            try:
                result = plugin.execute_operation(
                    operation=operation,
                    **kwargs
                )
                
                # Record successful request for rate limiting
                if plugin.requires_rate_limiting and plugin_name in self.rate_limiters:
                    self.rate_limiters[plugin_name].record_request()
                    
                return result
                
            except Exception as e:
                logger.warning(f"Operation failed (attempt {attempt+1}/{retry_count}): {e}")
                
                if attempt < retry_count - 1:
                    # Wait before retrying
                    time.sleep(1 * (2 ** attempt))  # Exponential backoff
                else:
                    # Last attempt failed
                    logger.error(f"Operation failed after {retry_count} attempts: {e}")
                    return {
                        'success': False,
                        'error': str(e),
                        'data': None
                    }
    
    def get_plugin_status(self, plugin_name: str) -> Dict[str, Any]:
        """
        Get the status of a registered plugin.
        
        Args:
            plugin_name: Name of the plugin
            
        Returns:
            Dictionary with plugin status information
        """
        plugin = self.get_plugin(plugin_name)
        
        if not plugin:
            return {
                'name': plugin_name,
                'registered': False,
                'available': False
            }
            
        status = plugin.get_api_status()
        
        # Add rate limit information if applicable
        if plugin.requires_rate_limiting and plugin_name in self.rate_limiters:
            rate_limiter = self.rate_limiters[plugin_name]
            status['rate_limits'] = {
                'requests_remaining': rate_limiter.get_remaining_requests(),
                'reset_time': rate_limiter.get_reset_time()
            }
            
        return status
    
    def get_all_plugin_statuses(self) -> Dict[str, Dict[str, Any]]:
        """
        Get the status of all registered plugins.
        
        Returns:
            Dictionary mapping plugin names to status information
        """
        return {
            plugin_name: self.get_plugin_status(plugin_name)
            for plugin_name in self.plugins
        }
    
    def close(self) -> None:
        """
        Close all plugins and clean up resources.
        
        This method should be called when the gateway is no longer needed.
        """
        with self.lock:
            for plugin_name, plugin in list(self.plugins.items()):
                try:
                    plugin.close()
                    logger.info(f"Closed plugin: {plugin_name}")
                except Exception as e:
                    logger.error(f"Error closing plugin '{plugin_name}': {e}")
                    
            self.plugins.clear()
            self.rate_limiters.clear()
            
        logger.info("API Gateway closed")