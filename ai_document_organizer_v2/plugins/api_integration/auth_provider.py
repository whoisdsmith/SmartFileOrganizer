"""
Authentication Provider for External API Integration Framework.

This module provides authentication management for external API integrations,
supporting multiple authentication methods and secure credential storage.
"""

import logging
import os
import json
import base64
import time
import hashlib
import secrets
from typing import Any, Dict, List, Optional, Union, Set

# For secure storage
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    logging.warning("Cryptography package not available, using basic encryption")


logger = logging.getLogger(__name__)


class AuthenticationProvider:
    """
    Manages authentication for external API integrations.
    
    This class provides centralized authentication management, supporting
    multiple authentication methods (API keys, OAuth tokens, JWT) and
    secure credential storage.
    """
    
    # Authentication method types
    AUTH_METHOD_API_KEY = 'api_key'
    AUTH_METHOD_OAUTH = 'oauth'
    AUTH_METHOD_JWT = 'jwt'
    AUTH_METHOD_BASIC = 'basic'
    AUTH_METHOD_CUSTOM = 'custom'
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the Authentication Provider.
        
        Args:
            config: Optional configuration dictionary for the provider
        """
        self.config = config or {}
        
        # Credentials storage
        self.credentials = {}  # type: Dict[str, Dict[str, Any]]
        self.tokens = {}  # type: Dict[str, Dict[str, Any]]
        
        # Encryption settings
        self.encryption_key = None
        self.use_encryption = self.config.get('use_encryption', True) and CRYPTO_AVAILABLE
        
        # Storage settings
        self.credentials_file = self.config.get('credentials_file', 'api_credentials.json')
        self.tokens_file = self.config.get('tokens_file', 'api_tokens.json')
        self.storage_dir = self.config.get('storage_dir', os.path.join(os.path.expanduser('~'), '.ai_document_organizer'))
        
        # Ensure storage directory exists
        if not os.path.exists(self.storage_dir):
            try:
                os.makedirs(self.storage_dir, exist_ok=True)
            except Exception as e:
                logger.error(f"Failed to create storage directory: {e}")
        
        # Initialize encryption
        if self.use_encryption:
            self._init_encryption()
        
        # Load stored credentials and tokens
        self._load_credentials()
        self._load_tokens()
        
        logger.info("Authentication Provider initialized")
    
    def _init_encryption(self):
        """Initialize encryption for secure credential storage."""
        try:
            # Use a fixed key if provided in config, otherwise generate one
            config_key = self.config.get('encryption_key')
            
            if config_key:
                # Use the provided key (should be base64-encoded)
                self.encryption_key = config_key
            else:
                # Check for existing key file
                key_file = os.path.join(self.storage_dir, '.key')
                
                if os.path.exists(key_file):
                    # Load existing key
                    with open(key_file, 'rb') as f:
                        self.encryption_key = f.read().decode('utf-8')
                else:
                    # Generate a new key
                    key = Fernet.generate_key()
                    self.encryption_key = key.decode('utf-8')
                    
                    # Save the key
                    with open(key_file, 'wb') as f:
                        f.write(key)
                    
                    # Secure the key file permissions
                    try:
                        os.chmod(key_file, 0o600)  # Read/write for owner only
                    except Exception as e:
                        logger.warning(f"Could not set secure permissions on key file: {e}")
            
            logger.info("Encryption initialized for secure credential storage")
            
        except Exception as e:
            logger.error(f"Failed to initialize encryption: {e}")
            self.use_encryption = False
    
    def _encrypt_data(self, data: str) -> str:
        """
        Encrypt sensitive data.
        
        Args:
            data: Data to encrypt
            
        Returns:
            Encrypted data as a string
        """
        if not self.use_encryption or not data:
            return data
            
        try:
            # Create a Fernet cipher with the key
            key_bytes = self.encryption_key.encode('utf-8')
            cipher = Fernet(key_bytes)
            
            # Encrypt the data
            encrypted_data = cipher.encrypt(data.encode('utf-8'))
            
            # Return base64-encoded encrypted data
            return base64.b64encode(encrypted_data).decode('utf-8')
            
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            return data
    
    def _decrypt_data(self, encrypted_data: str) -> str:
        """
        Decrypt sensitive data.
        
        Args:
            encrypted_data: Encrypted data to decrypt
            
        Returns:
            Decrypted data as a string
        """
        if not self.use_encryption or not encrypted_data:
            return encrypted_data
            
        try:
            # Create a Fernet cipher with the key
            key_bytes = self.encryption_key.encode('utf-8')
            cipher = Fernet(key_bytes)
            
            # Decode from base64
            encrypted_bytes = base64.b64decode(encrypted_data.encode('utf-8'))
            
            # Decrypt the data
            decrypted_data = cipher.decrypt(encrypted_bytes).decode('utf-8')
            
            return decrypted_data
            
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            return encrypted_data
    
    def _load_credentials(self):
        """Load stored API credentials from file."""
        credentials_path = os.path.join(self.storage_dir, self.credentials_file)
        
        if os.path.exists(credentials_path):
            try:
                with open(credentials_path, 'r') as f:
                    encrypted_data = json.load(f)
                
                # Decrypt the credentials
                for api_name, creds in encrypted_data.items():
                    if 'api_key' in creds and creds.get('encrypted', False):
                        creds['api_key'] = self._decrypt_data(creds['api_key'])
                    if 'username' in creds and creds.get('encrypted', False):
                        creds['username'] = self._decrypt_data(creds['username'])
                    if 'password' in creds and creds.get('encrypted', False):
                        creds['password'] = self._decrypt_data(creds['password'])
                    
                    self.credentials[api_name] = creds
                
                logger.info(f"Loaded credentials for {len(self.credentials)} API services")
                
            except Exception as e:
                logger.error(f"Failed to load credentials: {e}")
    
    def _save_credentials(self):
        """Save API credentials to file."""
        credentials_path = os.path.join(self.storage_dir, self.credentials_file)
        
        try:
            # Create a copy for encryption
            encrypted_data = {}
            
            # Encrypt the credentials
            for api_name, creds in self.credentials.items():
                encrypted_creds = creds.copy()
                
                if 'api_key' in creds:
                    encrypted_creds['api_key'] = self._encrypt_data(creds['api_key'])
                    encrypted_creds['encrypted'] = True
                if 'username' in creds:
                    encrypted_creds['username'] = self._encrypt_data(creds['username'])
                    encrypted_creds['encrypted'] = True
                if 'password' in creds:
                    encrypted_creds['password'] = self._encrypt_data(creds['password'])
                    encrypted_creds['encrypted'] = True
                
                encrypted_data[api_name] = encrypted_creds
            
            # Save to file
            with open(credentials_path, 'w') as f:
                json.dump(encrypted_data, f, indent=2)
            
            # Secure the file permissions
            try:
                os.chmod(credentials_path, 0o600)  # Read/write for owner only
            except Exception as e:
                logger.warning(f"Could not set secure permissions on credentials file: {e}")
            
            logger.info(f"Saved credentials for {len(self.credentials)} API services")
            
        except Exception as e:
            logger.error(f"Failed to save credentials: {e}")
    
    def _load_tokens(self):
        """Load stored API tokens from file."""
        tokens_path = os.path.join(self.storage_dir, self.tokens_file)
        
        if os.path.exists(tokens_path):
            try:
                with open(tokens_path, 'r') as f:
                    encrypted_data = json.load(f)
                
                # Decrypt the tokens
                for api_name, token_data in encrypted_data.items():
                    if 'access_token' in token_data and token_data.get('encrypted', False):
                        token_data['access_token'] = self._decrypt_data(token_data['access_token'])
                    if 'refresh_token' in token_data and token_data.get('encrypted', False):
                        token_data['refresh_token'] = self._decrypt_data(token_data['refresh_token'])
                    
                    self.tokens[api_name] = token_data
                
                logger.info(f"Loaded tokens for {len(self.tokens)} API services")
                
            except Exception as e:
                logger.error(f"Failed to load tokens: {e}")
    
    def _save_tokens(self):
        """Save API tokens to file."""
        tokens_path = os.path.join(self.storage_dir, self.tokens_file)
        
        try:
            # Create a copy for encryption
            encrypted_data = {}
            
            # Encrypt the tokens
            for api_name, token_data in self.tokens.items():
                encrypted_token_data = token_data.copy()
                
                if 'access_token' in token_data:
                    encrypted_token_data['access_token'] = self._encrypt_data(token_data['access_token'])
                    encrypted_token_data['encrypted'] = True
                if 'refresh_token' in token_data:
                    encrypted_token_data['refresh_token'] = self._encrypt_data(token_data['refresh_token'])
                    encrypted_token_data['encrypted'] = True
                
                encrypted_data[api_name] = encrypted_token_data
            
            # Save to file
            with open(tokens_path, 'w') as f:
                json.dump(encrypted_data, f, indent=2)
            
            # Secure the file permissions
            try:
                os.chmod(tokens_path, 0o600)  # Read/write for owner only
            except Exception as e:
                logger.warning(f"Could not set secure permissions on tokens file: {e}")
            
            logger.info(f"Saved tokens for {len(self.tokens)} API services")
            
        except Exception as e:
            logger.error(f"Failed to save tokens: {e}")
    
    def store_api_key(self, api_name: str, api_key: str, meta: Optional[Dict[str, Any]] = None) -> bool:
        """
        Store an API key for a service.
        
        Args:
            api_name: Name of the API service
            api_key: API key to store
            meta: Optional metadata for the API key
            
        Returns:
            True if the key was stored successfully, False otherwise
        """
        try:
            # Create or update credentials entry
            if api_name not in self.credentials:
                self.credentials[api_name] = {}
            
            # Store the API key
            self.credentials[api_name]['auth_method'] = self.AUTH_METHOD_API_KEY
            self.credentials[api_name]['api_key'] = api_key
            
            # Add metadata if provided
            if meta:
                self.credentials[api_name].update(meta)
            
            # Add timestamp
            self.credentials[api_name]['timestamp'] = time.time()
            
            # Save credentials to file
            self._save_credentials()
            
            logger.info(f"Stored API key for {api_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store API key for {api_name}: {e}")
            return False
    
    def get_api_key(self, api_name: str) -> Optional[str]:
        """
        Get an API key for a service.
        
        Args:
            api_name: Name of the API service
            
        Returns:
            API key or None if not found
        """
        if api_name not in self.credentials or 'api_key' not in self.credentials[api_name]:
            return None
            
        return self.credentials[api_name]['api_key']
    
    def store_basic_auth(self, api_name: str, username: str, password: str, 
                         meta: Optional[Dict[str, Any]] = None) -> bool:
        """
        Store basic authentication credentials for a service.
        
        Args:
            api_name: Name of the API service
            username: Username for basic auth
            password: Password for basic auth
            meta: Optional metadata for the credentials
            
        Returns:
            True if the credentials were stored successfully, False otherwise
        """
        try:
            # Create or update credentials entry
            if api_name not in self.credentials:
                self.credentials[api_name] = {}
            
            # Store the credentials
            self.credentials[api_name]['auth_method'] = self.AUTH_METHOD_BASIC
            self.credentials[api_name]['username'] = username
            self.credentials[api_name]['password'] = password
            
            # Add metadata if provided
            if meta:
                self.credentials[api_name].update(meta)
            
            # Add timestamp
            self.credentials[api_name]['timestamp'] = time.time()
            
            # Save credentials to file
            self._save_credentials()
            
            logger.info(f"Stored basic auth credentials for {api_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store basic auth credentials for {api_name}: {e}")
            return False
    
    def get_basic_auth(self, api_name: str) -> Optional[Dict[str, str]]:
        """
        Get basic authentication credentials for a service.
        
        Args:
            api_name: Name of the API service
            
        Returns:
            Dictionary with username and password or None if not found
        """
        if api_name not in self.credentials or self.credentials[api_name].get('auth_method') != self.AUTH_METHOD_BASIC:
            return None
            
        return {
            'username': self.credentials[api_name].get('username', ''),
            'password': self.credentials[api_name].get('password', '')
        }
    
    def store_oauth_credentials(self, api_name: str, client_id: str, client_secret: str,
                              meta: Optional[Dict[str, Any]] = None) -> bool:
        """
        Store OAuth client credentials for a service.
        
        Args:
            api_name: Name of the API service
            client_id: OAuth client ID
            client_secret: OAuth client secret
            meta: Optional metadata for the credentials
            
        Returns:
            True if the credentials were stored successfully, False otherwise
        """
        try:
            # Create or update credentials entry
            if api_name not in self.credentials:
                self.credentials[api_name] = {}
            
            # Store the credentials
            self.credentials[api_name]['auth_method'] = self.AUTH_METHOD_OAUTH
            self.credentials[api_name]['client_id'] = client_id
            self.credentials[api_name]['client_secret'] = client_secret
            
            # Add metadata if provided
            if meta:
                self.credentials[api_name].update(meta)
            
            # Add timestamp
            self.credentials[api_name]['timestamp'] = time.time()
            
            # Save credentials to file
            self._save_credentials()
            
            logger.info(f"Stored OAuth client credentials for {api_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store OAuth client credentials for {api_name}: {e}")
            return False
    
    def get_oauth_credentials(self, api_name: str) -> Optional[Dict[str, str]]:
        """
        Get OAuth client credentials for a service.
        
        Args:
            api_name: Name of the API service
            
        Returns:
            Dictionary with client_id and client_secret or None if not found
        """
        if api_name not in self.credentials or self.credentials[api_name].get('auth_method') != self.AUTH_METHOD_OAUTH:
            return None
            
        return {
            'client_id': self.credentials[api_name].get('client_id', ''),
            'client_secret': self.credentials[api_name].get('client_secret', '')
        }
    
    def store_oauth_tokens(self, api_name: str, access_token: str, 
                          refresh_token: Optional[str] = None,
                          expires_in: Optional[int] = None,
                          token_type: Optional[str] = None,
                          scope: Optional[str] = None) -> bool:
        """
        Store OAuth tokens for a service.
        
        Args:
            api_name: Name of the API service
            access_token: OAuth access token
            refresh_token: Optional OAuth refresh token
            expires_in: Optional token expiration time in seconds
            token_type: Optional token type (e.g., 'Bearer')
            scope: Optional token scope
            
        Returns:
            True if the tokens were stored successfully, False otherwise
        """
        try:
            # Create or update tokens entry
            if api_name not in self.tokens:
                self.tokens[api_name] = {}
            
            # Store the tokens
            self.tokens[api_name]['access_token'] = access_token
            
            if refresh_token:
                self.tokens[api_name]['refresh_token'] = refresh_token
                
            if expires_in:
                self.tokens[api_name]['expires_in'] = expires_in
                self.tokens[api_name]['expires_at'] = time.time() + expires_in
                
            if token_type:
                self.tokens[api_name]['token_type'] = token_type
                
            if scope:
                self.tokens[api_name]['scope'] = scope
            
            # Add timestamp
            self.tokens[api_name]['timestamp'] = time.time()
            
            # Save tokens to file
            self._save_tokens()
            
            logger.info(f"Stored OAuth tokens for {api_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store OAuth tokens for {api_name}: {e}")
            return False
    
    def get_oauth_tokens(self, api_name: str) -> Optional[Dict[str, Any]]:
        """
        Get OAuth tokens for a service.
        
        Args:
            api_name: Name of the API service
            
        Returns:
            Dictionary with token information or None if not found
        """
        if api_name not in self.tokens:
            return None
            
        return self.tokens[api_name]
    
    def is_token_expired(self, api_name: str) -> bool:
        """
        Check if an OAuth token is expired.
        
        Args:
            api_name: Name of the API service
            
        Returns:
            True if the token is expired or not found, False otherwise
        """
        if api_name not in self.tokens:
            return True
            
        # Check for expiration time
        if 'expires_at' in self.tokens[api_name]:
            # Add a buffer of 60 seconds to avoid using tokens right before expiration
            return time.time() + 60 > self.tokens[api_name]['expires_at']
            
        # If no expiration time is set, assume not expired
        return False
    
    def store_jwt(self, api_name: str, jwt_token: str, expires_in: Optional[int] = None,
                 meta: Optional[Dict[str, Any]] = None) -> bool:
        """
        Store a JWT token for a service.
        
        Args:
            api_name: Name of the API service
            jwt_token: JWT token to store
            expires_in: Optional token expiration time in seconds
            meta: Optional metadata for the token
            
        Returns:
            True if the token was stored successfully, False otherwise
        """
        try:
            # Create or update tokens entry
            if api_name not in self.tokens:
                self.tokens[api_name] = {}
            
            # Store the token
            self.tokens[api_name]['token_type'] = 'JWT'
            self.tokens[api_name]['access_token'] = jwt_token
            
            if expires_in:
                self.tokens[api_name]['expires_in'] = expires_in
                self.tokens[api_name]['expires_at'] = time.time() + expires_in
            
            # Add metadata if provided
            if meta:
                self.tokens[api_name].update(meta)
            
            # Add timestamp
            self.tokens[api_name]['timestamp'] = time.time()
            
            # Save tokens to file
            self._save_tokens()
            
            logger.info(f"Stored JWT token for {api_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store JWT token for {api_name}: {e}")
            return False
    
    def get_jwt(self, api_name: str) -> Optional[str]:
        """
        Get a JWT token for a service.
        
        Args:
            api_name: Name of the API service
            
        Returns:
            JWT token or None if not found
        """
        if api_name not in self.tokens or self.tokens[api_name].get('token_type') != 'JWT':
            return None
            
        return self.tokens[api_name].get('access_token')
    
    def delete_credentials(self, api_name: str) -> bool:
        """
        Delete credentials for a service.
        
        Args:
            api_name: Name of the API service
            
        Returns:
            True if the credentials were deleted, False otherwise
        """
        if api_name in self.credentials:
            del self.credentials[api_name]
            self._save_credentials()
            logger.info(f"Deleted credentials for {api_name}")
            return True
            
        return False
    
    def delete_tokens(self, api_name: str) -> bool:
        """
        Delete tokens for a service.
        
        Args:
            api_name: Name of the API service
            
        Returns:
            True if the tokens were deleted, False otherwise
        """
        if api_name in self.tokens:
            del self.tokens[api_name]
            self._save_tokens()
            logger.info(f"Deleted tokens for {api_name}")
            return True
            
        return False
    
    def get_auth_header(self, api_name: str, auth_method: Optional[str] = None) -> Dict[str, str]:
        """
        Get authorization header for an API request.
        
        Args:
            api_name: Name of the API service
            auth_method: Optional override for authentication method
            
        Returns:
            Dictionary with authorization header or empty dict if not available
        """
        # Determine the authentication method
        if auth_method is None:
            if api_name in self.credentials:
                auth_method = self.credentials[api_name].get('auth_method')
            else:
                return {}
        
        # Generate header based on auth method
        if auth_method == self.AUTH_METHOD_API_KEY:
            api_key = self.get_api_key(api_name)
            if api_key:
                # Check header format from credentials metadata
                header_name = self.credentials[api_name].get('header_name', 'Authorization')
                header_format = self.credentials[api_name].get('header_format', 'Bearer {token}')
                
                if '{token}' in header_format:
                    header_value = header_format.replace('{token}', api_key)
                else:
                    header_value = api_key
                    
                return {header_name: header_value}
                
        elif auth_method == self.AUTH_METHOD_OAUTH:
            tokens = self.get_oauth_tokens(api_name)
            if tokens and 'access_token' in tokens:
                token_type = tokens.get('token_type', 'Bearer')
                return {'Authorization': f"{token_type} {tokens['access_token']}"}
                
        elif auth_method == self.AUTH_METHOD_JWT:
            jwt = self.get_jwt(api_name)
            if jwt:
                return {'Authorization': f"Bearer {jwt}"}
                
        elif auth_method == self.AUTH_METHOD_BASIC:
            basic_auth = self.get_basic_auth(api_name)
            if basic_auth:
                auth_str = f"{basic_auth['username']}:{basic_auth['password']}"
                auth_bytes = auth_str.encode('utf-8')
                encoded = base64.b64encode(auth_bytes).decode('utf-8')
                return {'Authorization': f"Basic {encoded}"}
        
        # No valid auth header available
        return {}
    
    def get_auth_params(self, api_name: str, auth_method: Optional[str] = None) -> Dict[str, str]:
        """
        Get authorization parameters for an API request.
        
        Args:
            api_name: Name of the API service
            auth_method: Optional override for authentication method
            
        Returns:
            Dictionary with authorization parameters or empty dict if not available
        """
        # Determine the authentication method
        if auth_method is None:
            if api_name in self.credentials:
                auth_method = self.credentials[api_name].get('auth_method')
            else:
                return {}
        
        # Generate parameters based on auth method
        if auth_method == self.AUTH_METHOD_API_KEY:
            api_key = self.get_api_key(api_name)
            if api_key:
                # Check parameter format from credentials metadata
                param_name = self.credentials[api_name].get('param_name', 'key')
                return {param_name: api_key}
                
        elif auth_method == self.AUTH_METHOD_OAUTH:
            tokens = self.get_oauth_tokens(api_name)
            if tokens and 'access_token' in tokens:
                return {'access_token': tokens['access_token']}
                
        # No valid auth parameters available
        return {}