"""
Weather API Plugin for the API Integration Framework.

This module implements an API plugin for accessing weather data through
the WeatherAPI.com service.
"""

import logging
import requests
import json
from typing import Any, Dict, List, Optional, Union
import time

from ..api_plugin_base import APIPluginBase


logger = logging.getLogger(__name__)


class WeatherAPIPlugin(APIPluginBase):
    """
    Weather API Plugin for accessing weather data from WeatherAPI.com.
    
    This plugin allows querying current weather conditions, forecasts,
    and historical weather data through the WeatherAPI.com service.
    """
    
    def __init__(self):
        """Initialize the Weather API plugin."""
        self._api_key = None
        self._base_url = "https://api.weatherapi.com/v1"
        self._is_authenticated = False
        self._last_response = None
    
    @property
    def api_name(self) -> str:
        """
        Return the name of the API this plugin interfaces with.
        
        Returns:
            String name of the API
        """
        return "weatherapi"
    
    @property
    def api_version(self) -> str:
        """
        Return the version of the API this plugin supports.
        
        Returns:
            String version of the API
        """
        return "v1"
    
    @property
    def supported_auth_methods(self) -> List[str]:
        """
        Return a list of supported authentication methods.
        
        Returns:
            List of strings representing supported auth methods
        """
        return ["api_key"]
    
    @property
    def requires_rate_limiting(self) -> bool:
        """
        Indicate whether this API requires rate limiting.
        
        Returns:
            Boolean indicating if the API requires rate limiting
        """
        return True
    
    @property
    def rate_limit_rules(self) -> Dict[str, Any]:
        """
        Return the rate limit rules for this API.
        
        Returns:
            Dictionary with rate limit rules
        """
        return {
            'requests_per_minute': 60,    # Free tier is typically limited to 1 million calls/month
            'requests_per_day': 1000,     # ~1 million / 30 days
            'concurrent_requests': 3
        }
    
    def initialize(self, config: Dict[str, Any]) -> bool:
        """
        Initialize the API plugin with configuration.
        
        Args:
            config: Dictionary containing configuration for the API plugin
            
        Returns:
            True if initialization was successful, False otherwise
        """
        try:
            # Required configuration: API key
            self._api_key = config.get('api_key')
            
            if not self._api_key:
                logger.error("API key is required for WeatherAPI plugin")
                return False
            
            # Optional configuration
            self._base_url = config.get('base_url', self._base_url)
            
            logger.info(f"Initialized WeatherAPI plugin with base URL: {self._base_url}")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing WeatherAPI plugin: {e}")
            return False
    
    def authenticate(self) -> bool:
        """
        Authenticate with the API using configured credentials.
        
        For WeatherAPI, we validate the API key by making a test request.
        
        Returns:
            True if authentication was successful, False otherwise
        """
        if not self._api_key:
            logger.error("Cannot authenticate: API key not set")
            return False
        
        try:
            # Make a simple request to validate the API key
            response = requests.get(
                f"{self._base_url}/current.json",
                params={
                    'key': self._api_key,
                    'q': 'London'  # Just a test location
                }
            )
            
            if response.status_code == 200:
                self._is_authenticated = True
                logger.info("WeatherAPI authentication successful")
                return True
            elif response.status_code == 401:
                logger.error("WeatherAPI authentication failed: Invalid API key")
                return False
            else:
                logger.error(f"WeatherAPI authentication failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error authenticating with WeatherAPI: {e}")
            return False
    
    @property
    def is_authenticated(self) -> bool:
        """
        Check if the plugin is currently authenticated.
        
        Returns:
            True if authenticated, False otherwise
        """
        return self._is_authenticated
    
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
        if not self.is_authenticated:
            logger.error("Cannot execute request: Not authenticated")
            return {
                'success': False,
                'error': 'Not authenticated',
                'data': None
            }
        
        try:
            # Prepare URL and parameters
            url = f"{self._base_url}/{endpoint.lstrip('/')}"
            request_params = params or {}
            request_params['key'] = self._api_key  # Add API key to params
            
            # Prepare headers
            request_headers = headers or {}
            
            # Execute request based on method
            start_time = time.time()
            
            if method.upper() == 'GET':
                response = requests.get(
                    url,
                    params=request_params,
                    headers=request_headers,
                    timeout=timeout
                )
            elif method.upper() == 'POST':
                response = requests.post(
                    url,
                    params=request_params,
                    json=data,
                    headers=request_headers,
                    files=files,
                    timeout=timeout
                )
            else:
                logger.error(f"Unsupported HTTP method: {method}")
                return {
                    'success': False,
                    'error': f"Unsupported HTTP method: {method}",
                    'data': None
                }
                
            # Calculate request duration
            duration = time.time() - start_time
            
            # Store the last response for debugging
            self._last_response = response
            
            # Parse response
            try:
                response_data = response.json() if response.content else None
            except json.JSONDecodeError:
                response_data = None
                
            # Prepare result
            result = {
                'success': 200 <= response.status_code < 300,
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'data': response_data,
                'duration': duration
            }
            
            if not result['success']:
                result['error'] = response.text
                logger.warning(f"WeatherAPI request failed: {response.status_code} - {response.text}")
            
            return result
            
        except requests.RequestException as e:
            logger.error(f"Request error: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': None
            }
            
        except Exception as e:
            logger.error(f"Error executing WeatherAPI request: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': None
            }
    
    def execute_operation(self, 
                         operation: str, 
                         **kwargs) -> Dict[str, Any]:
        """
        Execute a named operation on the API.
        
        Supported operations:
        - current_weather: Get current weather data for a location
        - forecast: Get weather forecast for a location
        - history: Get historical weather data for a location
        - search: Search for a location
        
        Args:
            operation: Name of the operation to execute
            **kwargs: Operation-specific parameters
            
        Returns:
            Dictionary with operation results
        """
        if not self.is_authenticated:
            logger.error("Cannot execute operation: Not authenticated")
            return {
                'success': False,
                'error': 'Not authenticated',
                'data': None
            }
            
        try:
            if operation == 'current_weather':
                return self._operation_current_weather(**kwargs)
            elif operation == 'forecast':
                return self._operation_forecast(**kwargs)
            elif operation == 'history':
                return self._operation_history(**kwargs)
            elif operation == 'search':
                return self._operation_search(**kwargs)
            else:
                logger.error(f"Unsupported operation: {operation}")
                return {
                    'success': False,
                    'error': f"Unsupported operation: {operation}",
                    'data': None
                }
                
        except Exception as e:
            logger.error(f"Error executing operation {operation}: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': None
            }
    
    def _operation_current_weather(self, location: str, **kwargs) -> Dict[str, Any]:
        """
        Get current weather data for a location.
        
        Args:
            location: Location to get weather for (city name, lat/lon, IP, etc.)
            **kwargs: Additional parameters
            
        Returns:
            Dictionary with current weather data
        """
        return self.execute_request(
            endpoint='/current.json',
            method='GET',
            params={
                'q': location,
                'aqi': kwargs.get('aqi', 'no')  # Air quality data
            }
        )
    
    def _operation_forecast(self, location: str, days: int = 3, **kwargs) -> Dict[str, Any]:
        """
        Get weather forecast for a location.
        
        Args:
            location: Location to get forecast for
            days: Number of days to forecast (1-10)
            **kwargs: Additional parameters
            
        Returns:
            Dictionary with forecast data
        """
        return self.execute_request(
            endpoint='/forecast.json',
            method='GET',
            params={
                'q': location,
                'days': min(max(days, 1), 10),  # Ensure days is between 1 and 10
                'aqi': kwargs.get('aqi', 'no'),
                'alerts': kwargs.get('alerts', 'no')
            }
        )
    
    def _operation_history(self, location: str, date: str, **kwargs) -> Dict[str, Any]:
        """
        Get historical weather data for a location.
        
        Args:
            location: Location to get historical data for
            date: Date in YYYY-MM-DD format
            **kwargs: Additional parameters
            
        Returns:
            Dictionary with historical weather data
        """
        return self.execute_request(
            endpoint='/history.json',
            method='GET',
            params={
                'q': location,
                'dt': date,
                'hour': kwargs.get('hour'),
                'end_dt': kwargs.get('end_date')
            }
        )
    
    def _operation_search(self, query: str, **kwargs) -> Dict[str, Any]:
        """
        Search for a location.
        
        Args:
            query: Location search query
            **kwargs: Additional parameters
            
        Returns:
            Dictionary with search results
        """
        return self.execute_request(
            endpoint='/search.json',
            method='GET',
            params={
                'q': query
            }
        )
    
    @property
    def available_operations(self) -> List[str]:
        """
        Return a list of available operations supported by this API plugin.
        
        Returns:
            List of operation names
        """
        return ['current_weather', 'forecast', 'history', 'search']
    
    def close(self) -> None:
        """
        Close any connections and clean up resources.
        
        For WeatherAPI, there's no persistent connection to close.
        """
        self._is_authenticated = False
        logger.info("WeatherAPI plugin closed")