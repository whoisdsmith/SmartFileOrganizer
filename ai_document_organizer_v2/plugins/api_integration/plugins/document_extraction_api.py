"""
Document Extraction API Plugin for the API Integration Framework.

This module implements an API plugin for extracting structured data from documents
using various document processing APIs.
"""

import logging
import requests
import json
import time
import os
import base64
from typing import Any, Dict, List, Optional, Union, BinaryIO

from ..api_plugin_base import APIPluginBase


logger = logging.getLogger(__name__)


class DocumentExtractionAPIPlugin(APIPluginBase):
    """
    Document Extraction API Plugin for extracting structured data from documents.
    
    This plugin supports extracting structured data such as text, tables, forms,
    and entities from various document formats (PDF, DOCX, images) using
    Google Document AI API.
    """
    
    def __init__(self):
        """Initialize the Document Extraction API plugin."""
        self._api_key = None
        self._base_url = "https://documentai.googleapis.com/v1"
        self._project_id = None
        self._location = "us"  # Default Document AI location
        self._processor_id = None
        self._is_authenticated = False
        self._last_response = None
        
    @property
    def api_name(self) -> str:
        """
        Return the name of the API this plugin interfaces with.
        
        Returns:
            String name of the API
        """
        return "google_document_ai"
    
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
            'requests_per_minute': 60,     # Standard quota for Document AI
            'requests_per_day': 1000,      # Reasonable daily limit
            'concurrent_requests': 5
        }
    
    @property
    def supports_batch_operations(self) -> bool:
        """
        Indicate whether this API supports batch operations.
        
        Returns:
            Boolean indicating if the API supports batch operations
        """
        return True
    
    def initialize(self, config: Dict[str, Any]) -> bool:
        """
        Initialize the API plugin with configuration.
        
        Args:
            config: Dictionary containing configuration for the API plugin
            
        Returns:
            True if initialization was successful, False otherwise
        """
        try:
            # Required configuration: API key, project ID, and processor ID
            self._api_key = config.get('api_key')
            self._project_id = config.get('project_id')
            self._processor_id = config.get('processor_id')
            
            if not self._api_key:
                logger.error("API key is required for Document AI plugin")
                return False
                
            if not self._project_id:
                logger.error("Project ID is required for Document AI plugin")
                return False
                
            if not self._processor_id:
                logger.error("Processor ID is required for Document AI plugin")
                return False
            
            # Optional configuration
            self._base_url = config.get('base_url', self._base_url)
            self._location = config.get('location', self._location)
            
            logger.info(f"Initialized Document AI plugin with base URL: {self._base_url}")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing Document AI plugin: {e}")
            return False
    
    def authenticate(self) -> bool:
        """
        Authenticate with the API using configured credentials.
        
        For Document AI, we validate the API key by making a test request.
        
        Returns:
            True if authentication was successful, False otherwise
        """
        if not self._api_key or not self._project_id or not self._processor_id:
            logger.error("Cannot authenticate: API key, project ID, or processor ID not set")
            return False
        
        try:
            # Make a simple request to validate the API key by getting processor info
            response = requests.get(
                f"{self._base_url}/projects/{self._project_id}/locations/{self._location}/processors/{self._processor_id}",
                params={
                    'key': self._api_key,
                }
            )
            
            if response.status_code == 200:
                self._is_authenticated = True
                logger.info("Document AI authentication successful")
                return True
            elif response.status_code == 401:
                logger.error("Document AI authentication failed: Invalid API key")
                return False
            elif response.status_code == 404:
                logger.error("Document AI authentication failed: Invalid processor ID")
                return False
            else:
                logger.error(f"Document AI authentication failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error authenticating with Document AI: {e}")
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
            
            # Handle project/location/processor IDs in endpoint if not specified
            if '{project_id}' in url:
                url = url.replace('{project_id}', self._project_id)
            if '{location}' in url:
                url = url.replace('{location}', self._location)
            if '{processor_id}' in url:
                url = url.replace('{processor_id}', self._processor_id)
            
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
                logger.warning(f"Document AI request failed: {response.status_code} - {response.text}")
            
            return result
            
        except requests.RequestException as e:
            logger.error(f"Request error: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': None
            }
            
        except Exception as e:
            logger.error(f"Error executing Document AI request: {e}")
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
        - process_document: Process a document using the configured processor
        - batch_process_documents: Process multiple documents in batch
        - get_processor_info: Get information about the configured processor
        - get_processor_types: Get list of available processor types
        
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
            if operation == 'process_document':
                return self._operation_process_document(**kwargs)
            elif operation == 'batch_process_documents':
                return self._operation_batch_process_documents(**kwargs)
            elif operation == 'get_processor_info':
                return self._operation_get_processor_info(**kwargs)
            elif operation == 'get_processor_types':
                return self._operation_get_processor_types(**kwargs)
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
    
    def _operation_process_document(self, 
                                   file_path: Optional[str] = None,
                                   file_content: Optional[bytes] = None,
                                   mime_type: Optional[str] = None,
                                   **kwargs) -> Dict[str, Any]:
        """
        Process a document using the configured processor.
        
        Args:
            file_path: Path to the document file
            file_content: Binary content of the document file
            mime_type: MIME type of the document
            **kwargs: Additional parameters
            
        Returns:
            Dictionary with document processing results
        """
        if not file_path and not file_content:
            return {
                'success': False,
                'error': 'Either file_path or file_content must be provided',
                'data': None
            }
            
        try:
            # Read file content if file_path is provided
            if file_path and not file_content:
                with open(file_path, 'rb') as file:
                    file_content = file.read()
                    
                # Determine MIME type if not provided
                if not mime_type:
                    mime_type = self._get_mime_type(file_path)
            
            # Ensure MIME type is set
            if not mime_type:
                mime_type = 'application/pdf'  # Default to PDF
                
            # Encode file content as base64
            encoded_content = base64.b64encode(file_content).decode('utf-8')
            
            # Prepare request data
            request_data = {
                'rawDocument': {
                    'content': encoded_content,
                    'mimeType': mime_type
                }
            }
            
            # Add optional parameters
            if 'process_options' in kwargs:
                request_data['processOptions'] = kwargs['process_options']
                
            if 'skip_human_review' in kwargs:
                request_data['skipHumanReview'] = kwargs['skip_human_review']
                
            # Prepare endpoint
            endpoint = f"projects/{self._project_id}/locations/{self._location}/processors/{self._processor_id}:process"
            
            # Execute request
            return self.execute_request(
                endpoint=endpoint,
                method='POST',
                data=request_data
            )
            
        except Exception as e:
            logger.error(f"Error processing document: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': None
            }
    
    def _operation_batch_process_documents(self, 
                                          file_paths: List[str],
                                          output_config: Optional[Dict[str, Any]] = None,
                                          **kwargs) -> Dict[str, Any]:
        """
        Process multiple documents in batch.
        
        Args:
            file_paths: List of paths to the document files
            output_config: Output configuration for batch processing
            **kwargs: Additional parameters
            
        Returns:
            Dictionary with batch processing results
        """
        if not file_paths:
            return {
                'success': False,
                'error': 'No files provided for batch processing',
                'data': None
            }
            
        try:
            # Prepare input config for each file
            input_configs = []
            
            for file_path in file_paths:
                mime_type = self._get_mime_type(file_path)
                
                input_configs.append({
                    'gcsSource': {
                        'uri': file_path  # Assuming file_paths are GCS URIs
                    },
                    'mimeType': mime_type
                })
            
            # Prepare output config (required for batch processing)
            if not output_config:
                output_config = {
                    'gcsDestination': {
                        'uri': f"gs://{self._project_id}-docai/output/"
                    }
                }
            
            # Prepare request data
            request_data = {
                'inputConfigs': input_configs,
                'outputConfig': output_config
            }
            
            # Add optional parameters
            if 'document_type' in kwargs:
                request_data['documentType'] = kwargs['document_type']
                
            if 'process_options' in kwargs:
                request_data['processOptions'] = kwargs['process_options']
                
            if 'skip_human_review' in kwargs:
                request_data['skipHumanReview'] = kwargs['skip_human_review']
                
            # Prepare endpoint
            endpoint = f"projects/{self._project_id}/locations/{self._location}/processors/{self._processor_id}:batchProcess"
            
            # Execute request
            return self.execute_request(
                endpoint=endpoint,
                method='POST',
                data=request_data
            )
            
        except Exception as e:
            logger.error(f"Error batch processing documents: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': None
            }
    
    def _operation_get_processor_info(self, **kwargs) -> Dict[str, Any]:
        """
        Get information about the configured processor.
        
        Args:
            **kwargs: Additional parameters
            
        Returns:
            Dictionary with processor information
        """
        endpoint = f"projects/{self._project_id}/locations/{self._location}/processors/{self._processor_id}"
        
        return self.execute_request(
            endpoint=endpoint,
            method='GET'
        )
    
    def _operation_get_processor_types(self, **kwargs) -> Dict[str, Any]:
        """
        Get list of available processor types.
        
        Args:
            **kwargs: Additional parameters
            
        Returns:
            Dictionary with processor types
        """
        endpoint = f"projects/{self._project_id}/locations/{self._location}/processorTypes"
        
        return self.execute_request(
            endpoint=endpoint,
            method='GET'
        )
    
    def _get_mime_type(self, file_path: str) -> str:
        """
        Determine the MIME type of a file based on its extension.
        
        Args:
            file_path: Path to the file
            
        Returns:
            MIME type string
        """
        ext = os.path.splitext(file_path)[1].lower()
        
        mime_types = {
            '.pdf': 'application/pdf',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.tiff': 'image/tiff',
            '.tif': 'image/tiff',
            '.gif': 'image/gif',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.doc': 'application/msword',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.xls': 'application/vnd.ms-excel',
            '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            '.ppt': 'application/vnd.ms-powerpoint',
            '.txt': 'text/plain',
            '.csv': 'text/csv',
            '.html': 'text/html',
            '.htm': 'text/html',
            '.xml': 'application/xml',
            '.json': 'application/json'
        }
        
        return mime_types.get(ext, 'application/octet-stream')
    
    @property
    def available_operations(self) -> List[str]:
        """
        Return a list of available operations supported by this API plugin.
        
        Returns:
            List of operation names
        """
        return ['process_document', 'batch_process_documents', 'get_processor_info', 'get_processor_types']
    
    def close(self) -> None:
        """
        Close any connections and clean up resources.
        
        For Document AI, there's no persistent connection to close.
        """
        self._is_authenticated = False
        logger.info("Document AI plugin closed")