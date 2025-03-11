"""
Base class for all API plugins in the AI Document Organizer V2.

This module defines the interface that all API plugins must implement,
providing a standardized way to interact with external APIs.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union, Callable


class APIPluginBase(ABC):
    """
    Abstract base class for all API plugins.
    
    This class defines the interface that all API plugins must implement to provide
    consistent functionality across different external API integrations.
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
            List of strings representing supported auth methods (e.g., ['api_key', 'oauth2'])
        """
        pass
    
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
            Dictionary with rate limit rules.
            Example: {
                'requests_per_minute': 60,
                'requests_per_day': 1000,
                'concurrent_requests': 5
            }
        """
        return {}
    
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
    
    @abstractmethod
    def execute_operation(self, 
                         operation: str, 
                         **kwargs) -> Dict[str, Any]:
        """
        Execute a named operation on the API.
        
        This method provides a higher-level interface to common API operations,
        abstracting away the specific endpoints, methods, and parameters.
        
        Args:
            operation: Name of the operation to execute
            **kwargs: Operation-specific parameters
            
        Returns:
            Dictionary with operation results
        """
        pass
    
    @property
    @abstractmethod
    def available_operations(self) -> List[str]:
        """
        Return a list of available operations supported by this API plugin.
        
        Returns:
            List of operation names
        """
        pass
    
    @property
    def supports_streaming(self) -> bool:
        """
        Check if this API plugin supports streaming responses.
        
        Returns:
            True if streaming is supported, False otherwise
        """
        return False
    
    @property
    def supports_webhooks(self) -> bool:
        """
        Check if this API plugin supports webhooks.
        
        Returns:
            True if webhooks are supported, False otherwise
        """
        return False
    
    @property
    def supports_batch_operations(self) -> bool:
        """
        Check if this API plugin supports batch operations.
        
        Returns:
            True if batch operations are supported, False otherwise
        """
        return False
    
    def get_api_status(self) -> Dict[str, Any]:
        """
        Get the current status of the API.
        
        Returns:
            Dictionary with API status information
        """
        return {
            'available': self.is_authenticated,
            'name': self.api_name,
            'version': self.api_version,
        }
    
    def get_operation_metadata(self, operation: str) -> Dict[str, Any]:
        """
        Get metadata about a specific operation.
        
        Args:
            operation: Operation name
            
        Returns:
            Dictionary with operation metadata
        """
        return {
            'operation': operation,
            'supported': operation in self.available_operations,
        }
    
    @abstractmethod
    def close(self) -> None:
        """
        Close any connections and clean up resources.
        
        This method should be called when the plugin is no longer needed.
        """
        pass