"""
Translation API Plugin for the API Integration Framework.

This module implements an API plugin for document translation services
using the Google Cloud Translation API.
"""

import logging
import requests
import json
import time
from typing import Any, Dict, List, Optional, Union

from ..api_plugin_base import APIPluginBase


logger = logging.getLogger(__name__)


class TranslationAPIPlugin(APIPluginBase):
    """
    Translation API Plugin for document translation services.
    
    This plugin allows translation of text and documents through
    Google Cloud Translation API, supporting multiple languages
    and formats.
    """
    
    def __init__(self):
        """Initialize the Translation API plugin."""
        self._api_key = None
        self._base_url = "https://translation.googleapis.com/v3"
        self._project_id = None
        self._is_authenticated = False
        self._last_response = None
        self._supported_languages = None
        
    @property
    def api_name(self) -> str:
        """
        Return the name of the API this plugin interfaces with.
        
        Returns:
            String name of the API
        """
        return "google_translation"
    
    @property
    def api_version(self) -> str:
        """
        Return the version of the API this plugin supports.
        
        Returns:
            String version of the API
        """
        return "v3"
    
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
            'requests_per_minute': 200,  # Standard quota for Translation API
            'requests_per_day': 5000,    # Reasonable daily limit
            'concurrent_requests': 10
        }
    
    @property
    def supports_batch_operations(self) -> bool:
        """
        Indicate whether this API supports batch operations.
        
        Returns:
            Boolean indicating if the API supports batch operations
        """
        return True
        
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
        return [
            'translate_text',
            'detect_language',
            'get_supported_languages'
        ]
        
    @property
    def cache_ttls(self) -> Dict[str, int]:
        """
        Return a dictionary mapping operation names to TTL values in seconds.
        
        Returns:
            Dictionary mapping operation names to TTL values
        """
        return {
            'translate_text': 86400,        # 24 hours
            'detect_language': 86400,       # 24 hours
            'get_supported_languages': 604800  # 7 days
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
            # Required configuration: API key and project ID
            self._api_key = config.get('api_key')
            self._project_id = config.get('project_id')
            
            if not self._api_key:
                logger.error("API key is required for Translation API plugin")
                return False
                
            if not self._project_id:
                logger.error("Project ID is required for Translation API plugin")
                return False
            
            # Optional configuration
            self._base_url = config.get('base_url', self._base_url)
            
            logger.info(f"Initialized Translation API plugin with base URL: {self._base_url}")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing Translation API plugin: {e}")
            return False
    
    def authenticate(self) -> bool:
        """
        Authenticate with the API using configured credentials.
        
        For Translation API, we validate the API key by making a test request.
        
        Returns:
            True if authentication was successful, False otherwise
        """
        if not self._api_key or not self._project_id:
            logger.error("Cannot authenticate: API key or project ID not set")
            return False
        
        try:
            # Make a simple request to validate the API key by getting supported languages
            response = requests.get(
                f"{self._base_url}/projects/{self._project_id}/locations/global/supportedLanguages",
                params={
                    'key': self._api_key,
                }
            )
            
            if response.status_code == 200:
                self._is_authenticated = True
                
                # Store supported languages for future use
                try:
                    data = response.json()
                    self._supported_languages = data.get('languages', [])
                except Exception as e:
                    logger.warning(f"Error parsing supported languages: {e}")
                
                logger.info("Translation API authentication successful")
                return True
            elif response.status_code == 401:
                logger.error("Translation API authentication failed: Invalid API key")
                return False
            else:
                logger.error(f"Translation API authentication failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error authenticating with Translation API: {e}")
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
            if data and not request_headers.get('Content-Type'):
                request_headers['Content-Type'] = 'application/json'
            
            # Handle project ID in endpoint if not specified
            if '{project_id}' in url:
                url = url.replace('{project_id}', self._project_id)
            
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
            elif method.upper() == 'PUT':
                response = requests.put(
                    url,
                    params=request_params,
                    json=data,
                    headers=request_headers,
                    files=files,
                    timeout=timeout
                )
            elif method.upper() == 'DELETE':
                response = requests.delete(
                    url,
                    params=request_params,
                    headers=request_headers,
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
                logger.warning(f"Translation API request failed: {response.status_code} - {response.text}")
            
            return result
            
        except requests.RequestException as e:
            logger.error(f"Request error: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': None
            }
            
        except Exception as e:
            logger.error(f"Error executing Translation API request: {e}")
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
        - translate_text: Translate text from one language to another
        - batch_translate_text: Translate multiple texts or documents
        - detect_language: Detect the language of a text
        - get_supported_languages: Get list of supported languages
        
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
            if operation == 'translate_text':
                return self._operation_translate_text(**kwargs)
            elif operation == 'batch_translate_text':
                return self._operation_batch_translate_text(**kwargs)
            elif operation == 'detect_language':
                return self._operation_detect_language(**kwargs)
            elif operation == 'get_supported_languages':
                return self._operation_get_supported_languages(**kwargs)
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
    
    def _operation_translate_text(self, 
                                 text: str, 
                                 target_language: str, 
                                 source_language: Optional[str] = None,
                                 mime_type: str = 'text/plain',
                                 format: str = 'text',
                                 **kwargs) -> Dict[str, Any]:
        """
        Translate text from one language to another.
        
        Args:
            text: Text to translate
            target_language: Target language code (ISO-639-1)
            source_language: Optional source language code (ISO-639-1)
            mime_type: MIME type of the text ('text/plain' or 'text/html')
            format: Format of the text ('text' or 'html')
            **kwargs: Additional parameters
            
        Returns:
            Dictionary with translation results
        """
        request_data = {
            'contents': [text],
            'target_language_code': target_language,
            'mime_type': mime_type
        }
        
        if source_language:
            request_data['source_language_code'] = source_language
            
        endpoint = f"projects/{self._project_id}/locations/global:translateText"
        
        return self.execute_request(
            endpoint=endpoint,
            method='POST',
            data=request_data
        )
    
    def _operation_batch_translate_text(self, 
                                       texts: List[str], 
                                       target_language: str, 
                                       source_language: Optional[str] = None,
                                       mime_type: str = 'text/plain',
                                       **kwargs) -> Dict[str, Any]:
        """
        Translate multiple texts at once.
        
        Args:
            texts: List of texts to translate
            target_language: Target language code (ISO-639-1)
            source_language: Optional source language code (ISO-639-1)
            mime_type: MIME type of the texts ('text/plain' or 'text/html')
            **kwargs: Additional parameters
            
        Returns:
            Dictionary with batch translation results
        """
        request_data = {
            'contents': texts,
            'target_language_code': target_language,
            'mime_type': mime_type
        }
        
        if source_language:
            request_data['source_language_code'] = source_language
            
        endpoint = f"projects/{self._project_id}/locations/global:translateText"
        
        return self.execute_request(
            endpoint=endpoint,
            method='POST',
            data=request_data
        )
    
    def _operation_detect_language(self, text: str, **kwargs) -> Dict[str, Any]:
        """
        Detect the language of a text.
        
        Args:
            text: Text to detect language for
            **kwargs: Additional parameters
            
        Returns:
            Dictionary with language detection results
        """
        request_data = {
            'content': text
        }
        
        endpoint = f"projects/{self._project_id}/locations/global:detectLanguage"
        
        return self.execute_request(
            endpoint=endpoint,
            method='POST',
            data=request_data
        )
    
    def _operation_get_supported_languages(self, 
                                          display_language: Optional[str] = None,
                                          **kwargs) -> Dict[str, Any]:
        """
        Get list of supported languages.
        
        Args:
            display_language: Optional language code to display language names in
            **kwargs: Additional parameters
            
        Returns:
            Dictionary with supported languages
        """
        params = {}
        if display_language:
            params['display_language_code'] = display_language
            
        endpoint = f"projects/{self._project_id}/locations/global/supportedLanguages"
        
        # If we already have the supported languages cached, return them
        if self._supported_languages is not None and not display_language:
            return {
                'success': True,
                'data': {
                    'languages': self._supported_languages
                }
            }
            
        return self.execute_request(
            endpoint=endpoint,
            method='GET',
            params=params
        )
    
    @property
    def available_operations(self) -> List[str]:
        """
        Return a list of available operations supported by this API plugin.
        
        Returns:
            List of operation names
        """
        return ['translate_text', 'batch_translate_text', 'detect_language', 'get_supported_languages']
    
    def close(self) -> None:
        """
        Close any connections and clean up resources.
        
        For Translation API, there's no persistent connection to close.
        """
        self._is_authenticated = False
        logger.info("Translation API plugin closed")