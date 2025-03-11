"""
API Plugin Base for External API Integration Framework.

This module provides the base class for all API plugins, defining the
standard interface that all plugins must implement.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union, Set

from .api_capabilities import CapabilitySet


logger = logging.getLogger(__name__)


class APIPluginBase(ABC):
    """
    Abstract base class for all API plugins.
    
    This class defines the standard interface that all API plugins must implement,
    providing a consistent way to interact with external APIs.
    """
    
    @property
    @abstractmethod
    def api_name(self) -> str:
        """
        Return the name of the API this plugin interfaces with.
        
        Returns:
            String name of the API
        """
        pass
    
    @property
    @abstractmethod
    def api_version(self) -> str:
        """
        Return the version of the API this plugin supports.
        
        Returns:
            String version of the API
        """
        pass
    
    @property
    @abstractmethod
    def supported_auth_methods(self) -> List[str]:
        """
        Return a list of supported authentication methods.
        
        Returns:
            List of strings representing supported auth methods
        """
        pass
    
    @property
    def supports_webhooks(self) -> bool:
        """
        Indicate whether this API supports webhooks.
        
        Returns:
            Boolean indicating if the API supports webhooks
        """
        return False
    
    @property
    def supports_streaming(self) -> bool:
        """
        Indicate whether this API supports streaming responses.
        
        Returns:
            Boolean indicating if the API supports streaming responses
        """
        return False
    
    @property
    def supports_batch_operations(self) -> bool:
        """
        Indicate whether this API supports batch operations.
        
        Returns:
            Boolean indicating if the API supports batch operations
        """
        return False
        
    @property
    def supports_caching(self) -> bool:
        """
        Indicate whether this API supports response caching.
        
        Returns:
            Boolean indicating if the API supports response caching
        """
        return True
        
    @property
    def cacheable_operations(self) -> List[str]:
        """
        Return a list of operations that can be cached.
        
        Returns:
            List of operation names that support caching
        """
        return []
        
    @property
    def cache_ttls(self) -> Dict[str, int]:
        """
        Return a dictionary mapping operation names to TTL values in seconds.
        
        Returns:
            Dictionary mapping operation names to TTL values
        """
        return {}
    
    @property
    @abstractmethod
    def requires_rate_limiting(self) -> bool:
        """
        Indicate whether this API requires rate limiting.
        
        Returns:
            Boolean indicating if the API requires rate limiting
        """
        pass
    
    @property
    def rate_limit_rules(self) -> Dict[str, Any]:
        """
        Return the rate limit rules for this API.
        
        Returns:
            Dictionary with rate limit rules
        """
        return {
            'requests_per_minute': 60,
            'requests_per_hour': 1000,
            'concurrent_requests': 5
        }
    
    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> bool:
        """
        Initialize the API plugin with configuration.
        
        Args:
            config: Dictionary containing configuration for the API plugin
            
        Returns:
            True if initialization was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def authenticate(self) -> bool:
        """
        Authenticate with the API using configured credentials.
        
        Returns:
            True if authentication was successful, False otherwise
        """
        pass
    
    @property
    @abstractmethod
    def is_authenticated(self) -> bool:
        """
        Check if the plugin is currently authenticated.
        
        Returns:
            True if authenticated, False otherwise
        """
        pass
    
    @abstractmethod
    def execute_request(self, 
                       endpoint: str,
                       method: str = 'GET',
                       params: Optional[Dict[str, Any]] = None,
                       data: Optional[Dict[str, Any]] = None,
                       headers: Optional[Dict[str, str]] = None,
                       files: Optional[Dict[str, Any]] = None,
                       timeout: Optional[int] = None,
                       **kwargs) -> Dict[str, Any]:
        """
        Execute a request to the API.
        
        Args:
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
        pass
    
    def execute_operation(self, 
                         operation: str, 
                         **kwargs) -> Dict[str, Any]:
        """
        Execute a named operation on the API.
        
        This method provides a higher-level interface than execute_request,
        allowing for more semantic operations like 'get_user', 'create_post', etc.
        
        Args:
            operation: Name of the operation to execute
            **kwargs: Operation-specific parameters
            
        Returns:
            Dictionary with operation results
        """
        logger.error(f"Operation {operation} not implemented by {self.__class__.__name__}")
        return {
            'success': False,
            'error': f"Operation {operation} not implemented by {self.__class__.__name__}",
            'data': None
        }
    
    @property
    def available_operations(self) -> List[str]:
        """
        Return a list of available operations supported by this API plugin.
        
        Returns:
            List of operation names
        """
        return []
    
    def close(self) -> None:
        """
        Close any connections and clean up resources.
        
        This method should be called when the plugin is no longer needed.
        """
        pass
        
    def get_capabilities(self) -> CapabilitySet:
        """
        Get the capabilities supported by this API plugin.
        
        Returns:
            CapabilitySet containing the capabilities supported by this plugin
        """
        capabilities = CapabilitySet()
        
        # Add authentication capabilities
        for auth_method in self.supported_auth_methods:
            capabilities.add_capability(f"auth:{auth_method}")
        
        # Add integration capabilities
        if self.supports_webhooks:
            capabilities.add_capability("integration:webhooks")
            
        if self.supports_streaming:
            capabilities.add_capability("integration:streaming")
            
        if self.supports_batch_operations:
            capabilities.add_capability("integration:batch")
        
        # Add performance capabilities
        if self.supports_caching:
            capabilities.add_capability("performance:caching")
            
        if self.requires_rate_limiting:
            capabilities.add_capability("performance:rate_limited")
        
        # Add data format capabilities
        capabilities.add_capability("format:json")  # Assume all APIs support JSON
        
        # Add operation capabilities
        for operation in self.available_operations:
            capabilities.add_capability(f"operation:{operation}")
        
        return capabilities
    
    def discover_remote_capabilities(self) -> Optional[CapabilitySet]:
        """
        Discover capabilities by querying the remote API.
        
        This method should be overridden by plugins that support runtime
        capability discovery from the API server.
        
        Returns:
            CapabilitySet of remote capabilities or None if discovery failed
        """
        logger.info(f"Remote capability discovery not supported by {self.__class__.__name__}")
        return None
        
    def supports_capability(self, capability_name: str) -> bool:
        """
        Check if this plugin supports a specific capability.
        
        Args:
            capability_name: Name of the capability to check
            
        Returns:
            True if the capability is supported, False otherwise
        """
        capabilities = self.get_capabilities()
        return capabilities.has_capability(capability_name)
    
    def negotiate_capabilities(self, required_capabilities: CapabilitySet) -> Dict[str, Any]:
        """
        Negotiate capabilities with the client.
        
        Args:
            required_capabilities: CapabilitySet of capabilities required by the client
            
        Returns:
            Dictionary with negotiation results:
            {
                'success': bool,
                'supported': List[str],  # Supported capability names
                'missing': List[str],    # Missing capability names
                'alternatives': Dict[str, List[str]]  # Alternative capabilities
            }
        """
        supported_capabilities = self.get_capabilities()
        
        # Check if all required capabilities are supported
        is_compatible = supported_capabilities.is_compatible_with(required_capabilities)
        missing = required_capabilities.get_missing_capabilities(supported_capabilities)
        
        # Get alternative capabilities for missing ones
        alternatives = {}
        for cap in missing:
            alternatives[cap] = self._get_alternative_capabilities(cap)
        
        return {
            'success': is_compatible,
            'supported': supported_capabilities.get_capability_names(),
            'missing': missing,
            'alternatives': alternatives
        }
        
    def _get_alternative_capabilities(self, capability_name: str) -> List[str]:
        """
        Get alternative capabilities for a missing capability.
        
        Args:
            capability_name: Name of the missing capability
            
        Returns:
            List of alternative capability names
        """
        # Example alternatives - override in specific plugins for better suggestions
        alternatives = {
            "auth:oauth2": ["auth:api_key", "auth:jwt"],
            "format:xml": ["format:json"],
            "integration:webhooks": ["integration:polling"],
            "integration:streaming": ["integration:batch"]
        }
        
        return alternatives.get(capability_name, [])
    
    def __str__(self) -> str:
        """
        Return a string representation of the plugin.
        
        Returns:
            String representation of the plugin
        """
        return f"{self.__class__.__name__}(api={self.api_name}, version={self.api_version})"
    
    def __repr__(self) -> str:
        """
        Return a string representation of the plugin for debugging.
        
        Returns:
            String representation of the plugin for debugging
        """
        return self.__str__()