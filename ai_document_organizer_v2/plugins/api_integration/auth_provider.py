"""
Authentication Provider for the External API Integration Framework.

This module provides unified authentication handling for external APIs,
including credential management, token storage, and authentication flows.
"""

import logging
import os
import json
import base64
import threading
from typing import Any, Dict, List, Optional, Callable, Union, Tuple
from datetime import datetime, timedelta
import time
import hashlib
import secrets


logger = logging.getLogger(__name__)


class AuthProvider:
    """
    Unified authentication provider for external APIs.
    
    This class manages API credentials, token storage, and authentication flows,
    providing a consistent interface for authentication across different APIs.
    """
    
    AUTH_TYPE_API_KEY = "api_key"
    AUTH_TYPE_OAUTH2 = "oauth2"
    AUTH_TYPE_BASIC = "basic"
    AUTH_TYPE_BEARER = "bearer"
    AUTH_TYPE_JWT = "jwt"
    AUTH_TYPE_CUSTOM = "custom"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the authentication provider.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.credentials_store = {}  # type: Dict[str, Dict[str, Any]]
        self.token_store = {}  # type: Dict[str, Dict[str, Any]]
        self.lock = threading.RLock()
        
        # Path for storing credentials and tokens
        self.storage_dir = self.config.get('storage_dir', os.path.expanduser("~/.ai_document_organizer/credentials"))
        self.credentials_file = os.path.join(self.storage_dir, "api_credentials.json")
        self.tokens_file = os.path.join(self.storage_dir, "api_tokens.json")
        
        # Encryption key for sensitive data
        self._encryption_key = self.config.get('encryption_key', self._generate_encryption_key())
        
        # Load stored credentials and tokens
        self._load_credentials()
        self._load_tokens()
        
        logger.info("Authentication provider initialized")
    
    def store_credentials(self, api_name: str, auth_type: str, credentials: Dict[str, Any]) -> bool:
        """
        Store credentials for an API.
        
        Args:
            api_name: Name of the API
            auth_type: Type of authentication (api_key, oauth2, basic, etc.)
            credentials: Dictionary with authentication credentials
            
        Returns:
            True if credentials were stored successfully, False otherwise
        """
        with self.lock:
            try:
                # Validate auth type
                if auth_type not in [self.AUTH_TYPE_API_KEY, self.AUTH_TYPE_OAUTH2, 
                                    self.AUTH_TYPE_BASIC, self.AUTH_TYPE_BEARER, 
                                    self.AUTH_TYPE_JWT, self.AUTH_TYPE_CUSTOM]:
                    logger.error(f"Invalid auth type: {auth_type}")
                    return False
                
                # Store credentials
                self.credentials_store[api_name] = {
                    'auth_type': auth_type,
                    'credentials': credentials,
                    'timestamp': datetime.now().isoformat()
                }
                
                # Save to file
                self._save_credentials()
                
                logger.info(f"Stored credentials for API: {api_name}")
                return True
                
            except Exception as e:
                logger.error(f"Error storing credentials for API {api_name}: {e}")
                return False
    
    def get_credentials(self, api_name: str) -> Optional[Dict[str, Any]]:
        """
        Get stored credentials for an API.
        
        Args:
            api_name: Name of the API
            
        Returns:
            Dictionary with credentials or None if not found
        """
        with self.lock:
            api_credentials = self.credentials_store.get(api_name)
            
            if api_credentials:
                return {
                    'auth_type': api_credentials['auth_type'],
                    'credentials': api_credentials['credentials']
                }
            else:
                logger.warning(f"No credentials found for API: {api_name}")
                return None
    
    def delete_credentials(self, api_name: str) -> bool:
        """
        Delete stored credentials for an API.
        
        Args:
            api_name: Name of the API
            
        Returns:
            True if credentials were deleted, False otherwise
        """
        with self.lock:
            if api_name in self.credentials_store:
                del self.credentials_store[api_name]
                self._save_credentials()
                logger.info(f"Deleted credentials for API: {api_name}")
                return True
            else:
                logger.warning(f"No credentials found to delete for API: {api_name}")
                return False
    
    def store_token(self, api_name: str, token_data: Dict[str, Any], expires_in: Optional[int] = None) -> bool:
        """
        Store an authentication token for an API.
        
        Args:
            api_name: Name of the API
            token_data: Dictionary with token data
            expires_in: Optional expiration time in seconds
            
        Returns:
            True if token was stored successfully, False otherwise
        """
        with self.lock:
            try:
                # Calculate expiration time if provided
                expiration = None
                if expires_in is not None:
                    expiration = (datetime.now() + timedelta(seconds=expires_in)).isoformat()
                
                # Store token
                self.token_store[api_name] = {
                    'token_data': token_data,
                    'created_at': datetime.now().isoformat(),
                    'expires_at': expiration
                }
                
                # Save to file
                self._save_tokens()
                
                logger.info(f"Stored token for API: {api_name}")
                return True
                
            except Exception as e:
                logger.error(f"Error storing token for API {api_name}: {e}")
                return False
    
    def get_token(self, api_name: str, check_expiration: bool = True) -> Optional[Dict[str, Any]]:
        """
        Get an authentication token for an API.
        
        Args:
            api_name: Name of the API
            check_expiration: Whether to check if the token has expired
            
        Returns:
            Dictionary with token data or None if not found or expired
        """
        with self.lock:
            token_info = self.token_store.get(api_name)
            
            if not token_info:
                logger.warning(f"No token found for API: {api_name}")
                return None
            
            # Check if token has expired
            if check_expiration and token_info.get('expires_at'):
                expires_at = datetime.fromisoformat(token_info['expires_at'])
                
                if datetime.now() >= expires_at:
                    logger.warning(f"Token for API {api_name} has expired")
                    return None
            
            return token_info['token_data']
    
    def delete_token(self, api_name: str) -> bool:
        """
        Delete a stored token for an API.
        
        Args:
            api_name: Name of the API
            
        Returns:
            True if token was deleted, False otherwise
        """
        with self.lock:
            if api_name in self.token_store:
                del self.token_store[api_name]
                self._save_tokens()
                logger.info(f"Deleted token for API: {api_name}")
                return True
            else:
                logger.warning(f"No token found to delete for API: {api_name}")
                return False
    
    def is_token_valid(self, api_name: str) -> bool:
        """
        Check if a stored token is valid and not expired.
        
        Args:
            api_name: Name of the API
            
        Returns:
            True if token is valid, False otherwise
        """
        with self.lock:
            token_info = self.token_store.get(api_name)
            
            if not token_info:
                return False
            
            # Check if token has an expiration time
            if token_info.get('expires_at'):
                expires_at = datetime.fromisoformat(token_info['expires_at'])
                
                if datetime.now() >= expires_at:
                    return False
            
            return True
    
    def get_auth_header(self, api_name: str) -> Optional[Dict[str, str]]:
        """
        Get authentication headers for an API based on stored credentials or tokens.
        
        Args:
            api_name: Name of the API
            
        Returns:
            Dictionary with authentication headers or None if not available
        """
        with self.lock:
            # First check if we have a valid token
            if self.is_token_valid(api_name):
                token_data = self.get_token(api_name)
                
                if token_data:
                    token_type = token_data.get('token_type', 'Bearer')
                    access_token = token_data.get('access_token')
                    
                    if access_token:
                        return {'Authorization': f"{token_type} {access_token}"}
            
            # If no valid token, try to use credentials
            credentials = self.get_credentials(api_name)
            
            if not credentials:
                logger.warning(f"No credentials or valid token for API: {api_name}")
                return None
            
            auth_type = credentials['auth_type']
            auth_creds = credentials['credentials']
            
            if auth_type == self.AUTH_TYPE_API_KEY:
                # API key can be in header, query param, or other locations
                # Here we assume it's in a header
                key_name = auth_creds.get('key_name', 'X-API-Key')
                key_value = auth_creds.get('key_value')
                
                if key_value:
                    return {key_name: key_value}
                    
            elif auth_type == self.AUTH_TYPE_BASIC:
                username = auth_creds.get('username')
                password = auth_creds.get('password')
                
                if username and password:
                    auth_string = f"{username}:{password}"
                    encoded = base64.b64encode(auth_string.encode()).decode()
                    return {'Authorization': f"Basic {encoded}"}
                    
            elif auth_type == self.AUTH_TYPE_BEARER:
                token = auth_creds.get('token')
                
                if token:
                    return {'Authorization': f"Bearer {token}"}
                    
            elif auth_type == self.AUTH_TYPE_JWT:
                token = auth_creds.get('token')
                
                if token:
                    return {'Authorization': f"Bearer {token}"}
            
            logger.warning(f"Could not generate auth header for API: {api_name}")
            return None
    
    def _load_credentials(self) -> None:
        """
        Load credentials from storage.
        """
        try:
            if os.path.exists(self.credentials_file):
                with open(self.credentials_file, 'r') as f:
                    encrypted_data = f.read()
                    
                    if encrypted_data:
                        decrypted_data = self._decrypt_data(encrypted_data)
                        self.credentials_store = json.loads(decrypted_data)
                        logger.info(f"Loaded credentials for {len(self.credentials_store)} APIs")
        except Exception as e:
            logger.error(f"Error loading credentials: {e}")
            self.credentials_store = {}
    
    def _save_credentials(self) -> None:
        """
        Save credentials to storage.
        """
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.credentials_file), exist_ok=True)
            
            # Encrypt and save credentials
            data_json = json.dumps(self.credentials_store)
            encrypted_data = self._encrypt_data(data_json)
            
            with open(self.credentials_file, 'w') as f:
                f.write(encrypted_data)
                
            logger.info(f"Saved credentials for {len(self.credentials_store)} APIs")
        except Exception as e:
            logger.error(f"Error saving credentials: {e}")
    
    def _load_tokens(self) -> None:
        """
        Load tokens from storage.
        """
        try:
            if os.path.exists(self.tokens_file):
                with open(self.tokens_file, 'r') as f:
                    encrypted_data = f.read()
                    
                    if encrypted_data:
                        decrypted_data = self._decrypt_data(encrypted_data)
                        self.token_store = json.loads(decrypted_data)
                        logger.info(f"Loaded tokens for {len(self.token_store)} APIs")
        except Exception as e:
            logger.error(f"Error loading tokens: {e}")
            self.token_store = {}
    
    def _save_tokens(self) -> None:
        """
        Save tokens to storage.
        """
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.tokens_file), exist_ok=True)
            
            # Encrypt and save tokens
            data_json = json.dumps(self.token_store)
            encrypted_data = self._encrypt_data(data_json)
            
            with open(self.tokens_file, 'w') as f:
                f.write(encrypted_data)
                
            logger.info(f"Saved tokens for {len(self.token_store)} APIs")
        except Exception as e:
            logger.error(f"Error saving tokens: {e}")
    
    def _generate_encryption_key(self) -> str:
        """
        Generate a new encryption key.
        
        Returns:
            Base64-encoded encryption key
        """
        # Generate a random key
        key = secrets.token_bytes(32)  # 256 bits
        return base64.b64encode(key).decode()
    
    def _encrypt_data(self, data: str) -> str:
        """
        Encrypt data using the encryption key.
        
        Args:
            data: String data to encrypt
            
        Returns:
            Encrypted data as a string
        """
        # For now, use a simple encryption method
        # In a production environment, use a proper encryption library like cryptography
        
        # Convert key to bytes
        key_bytes = base64.b64decode(self._encryption_key)
        
        # XOR each byte with a byte from the key
        data_bytes = data.encode()
        encrypted_bytes = bytearray()
        
        for i, b in enumerate(data_bytes):
            key_byte = key_bytes[i % len(key_bytes)]
            encrypted_bytes.append(b ^ key_byte)
        
        # Convert to base64 for storage
        return base64.b64encode(encrypted_bytes).decode()
    
    def _decrypt_data(self, encrypted_data: str) -> str:
        """
        Decrypt data using the encryption key.
        
        Args:
            encrypted_data: Encrypted data as a string
            
        Returns:
            Decrypted data as a string
        """
        # Convert key to bytes
        key_bytes = base64.b64decode(self._encryption_key)
        
        # Decode from base64
        encrypted_bytes = base64.b64decode(encrypted_data)
        decrypted_bytes = bytearray()
        
        # XOR each byte with a byte from the key
        for i, b in enumerate(encrypted_bytes):
            key_byte = key_bytes[i % len(key_bytes)]
            decrypted_bytes.append(b ^ key_byte)
        
        return decrypted_bytes.decode()