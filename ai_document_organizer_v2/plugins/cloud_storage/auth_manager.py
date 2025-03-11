"""
Authentication manager for cloud storage providers.

This module provides utilities for securely managing credentials and tokens,
supporting OAuth 2.0 flows, refresh token management, and secure storage.
"""

import os
import json
import time
import logging
import base64
import secrets
import threading
from typing import Dict, Any, Optional, Tuple, List, Callable
from datetime import datetime, timedelta

# Optional dependency for secure storage
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

logger = logging.getLogger("AIDocumentOrganizerV2.CloudStorage.Auth")


class CredentialError(Exception):
    """Exception raised for credential-related errors."""
    pass


class AuthManager:
    """
    Authentication manager for cloud storage providers.
    
    This class provides utilities for securely managing credentials and tokens,
    supporting OAuth 2.0 flows, refresh token management, and secure storage.
    """
    
    def __init__(self, provider_name: str, app_name: str = "AI Document Organizer"):
        """
        Initialize the authentication manager.
        
        Args:
            provider_name: Name of the cloud storage provider
            app_name: Name of the application (for OAuth client identification)
        """
        self.provider_name = provider_name
        self.app_name = app_name
        
        # Authentication state
        self.authenticated = False
        self.credentials = {}
        self.tokens = {}
        self._access_token_expiry = 0
        
        # Token refresh lock to prevent concurrent refresh attempts
        self._refresh_lock = threading.Lock()
        
        # Token refresh callback
        self._token_refresh_callback = None
        
        # Secure storage
        self._encryption_key = None
        
    def load_credentials_from_file(self, credentials_file: str) -> bool:
        """
        Load credentials from a file.
        
        Args:
            credentials_file: Path to the credentials file
            
        Returns:
            True if credentials were loaded successfully, False otherwise
        """
        if not os.path.exists(credentials_file):
            logger.error(f"Credentials file not found: {credentials_file}")
            return False
            
        try:
            with open(credentials_file, 'r') as f:
                credentials = json.load(f)
                
            self.credentials = credentials
            logger.info(f"Loaded credentials from {credentials_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading credentials: {e}")
            return False
    
    def load_tokens_from_file(self, token_file: str) -> bool:
        """
        Load authentication tokens from a file.
        
        Args:
            token_file: Path to the token file
            
        Returns:
            True if tokens were loaded successfully, False otherwise
        """
        if not os.path.exists(token_file):
            logger.debug(f"Token file not found: {token_file}")
            return False
            
        try:
            with open(token_file, 'r') as f:
                data = f.read()
                
            # Check if data is encrypted
            if data.startswith('gAAAAA'):
                if not self._encryption_key:
                    logger.warning("Token file is encrypted, but no encryption key is set")
                    return False
                    
                # Decrypt data
                data = self._decrypt_data(data)
                
            # Parse JSON
            token_data = json.loads(data)
            
            # Check token expiry
            if 'expiry' in token_data:
                expiry = token_data['expiry']
                if expiry < time.time():
                    logger.warning("Token has expired")
                    
            self.tokens = token_data
            self._update_token_expiry()
            
            logger.info(f"Loaded tokens from {token_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading tokens: {e}")
            return False
    
    def save_tokens_to_file(self, token_file: str) -> bool:
        """
        Save authentication tokens to a file.
        
        Args:
            token_file: Path to save tokens to
            
        Returns:
            True if tokens were saved successfully, False otherwise
        """
        try:
            os.makedirs(os.path.dirname(os.path.abspath(token_file)), exist_ok=True)
            
            # Convert tokens to JSON
            token_data = json.dumps(self.tokens)
            
            # Encrypt data if encryption is enabled
            if self._encryption_key:
                token_data = self._encrypt_data(token_data)
                
            # Write to file
            with open(token_file, 'w') as f:
                f.write(token_data)
                
            logger.info(f"Saved tokens to {token_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving tokens: {e}")
            return False
    
    def set_token_refresh_callback(self, callback: Callable) -> None:
        """
        Set a callback function to be called when tokens need to be refreshed.
        
        Args:
            callback: Function to call for token refresh
        """
        self._token_refresh_callback = callback
    
    def refresh_tokens(self) -> bool:
        """
        Refresh the authentication tokens using the refresh token.
        
        Returns:
            True if tokens were refreshed successfully, False otherwise
        """
        with self._refresh_lock:
            # Check if we have a refresh callback
            if not self._token_refresh_callback:
                logger.error("No token refresh callback set")
                return False
                
            # Check if we have a refresh token
            refresh_token = self.tokens.get('refresh_token')
            if not refresh_token:
                logger.error("No refresh token available")
                return False
                
            try:
                # Call the refresh callback
                result = self._token_refresh_callback()
                
                # Update token expiry
                self._update_token_expiry()
                
                logger.info("Tokens refreshed successfully")
                return result
                
            except Exception as e:
                logger.error(f"Error refreshing tokens: {e}")
                return False
    
    def get_access_token(self) -> Optional[str]:
        """
        Get the current access token, refreshing if necessary.
        
        Returns:
            Access token or None if not available
        """
        # Check if we have an access token
        access_token = self.tokens.get('access_token')
        if not access_token:
            logger.error("No access token available")
            return None
            
        # Check if token is expired
        if self._is_token_expired():
            logger.info("Access token has expired, refreshing...")
            if not self.refresh_tokens():
                logger.error("Failed to refresh tokens")
                return None
                
            # Get the new access token
            access_token = self.tokens.get('access_token')
            
        return access_token
    
    def _is_token_expired(self) -> bool:
        """
        Check if the current access token is expired.
        
        Returns:
            True if token is expired, False otherwise
        """
        # Add a 5-minute buffer to expiry time
        buffer_time = 300  # 5 minutes in seconds
        
        return time.time() >= (self._access_token_expiry - buffer_time)
    
    def _update_token_expiry(self) -> None:
        """Update the access token expiry time from token data."""
        # Check for explicit expiry timestamp
        if 'expiry' in self.tokens:
            self._access_token_expiry = self.tokens['expiry']
            return
            
        # Check for expires_in field (seconds from now)
        if 'expires_in' in self.tokens:
            expires_in = self.tokens['expires_in']
            self._access_token_expiry = time.time() + expires_in
            # Update tokens with absolute expiry time
            self.tokens['expiry'] = self._access_token_expiry
            return
            
        # If no expiry info available, use a default (1 hour)
        self._access_token_expiry = time.time() + 3600
        self.tokens['expiry'] = self._access_token_expiry
    
    def enable_encryption(self, password: Optional[str] = None) -> bool:
        """
        Enable encryption for token storage.
        
        Args:
            password: Optional password for encryption, if not provided, a random key will be used
            
        Returns:
            True if encryption was enabled successfully, False otherwise
        """
        if not CRYPTO_AVAILABLE:
            logger.warning("Encryption not available. Install cryptography package to enable.")
            return False
            
        try:
            if password:
                # Derive key from password
                salt = b'AIDOSaltValue'  # This should ideally be stored securely
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=salt,
                    iterations=100000,
                )
                key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
            else:
                # Generate a random key
                key = Fernet.generate_key()
                
            # Create Fernet cipher
            self._encryption_key = Fernet(key)
            
            logger.info("Encryption enabled for token storage")
            return True
            
        except Exception as e:
            logger.error(f"Error enabling encryption: {e}")
            return False
    
    def _encrypt_data(self, data: str) -> str:
        """
        Encrypt data using the encryption key.
        
        Args:
            data: Data to encrypt
            
        Returns:
            Encrypted data as a string
        """
        if not self._encryption_key:
            return data
            
        try:
            return self._encryption_key.encrypt(data.encode()).decode()
        except Exception as e:
            logger.error(f"Error encrypting data: {e}")
            return data
    
    def _decrypt_data(self, data: str) -> str:
        """
        Decrypt data using the encryption key.
        
        Args:
            data: Encrypted data as a string
            
        Returns:
            Decrypted data
        """
        if not self._encryption_key:
            return data
            
        try:
            return self._encryption_key.decrypt(data.encode()).decode()
        except Exception as e:
            logger.error(f"Error decrypting data: {e}")
            return data
    
    def generate_oauth_url(self, client_id: str, scopes: List[str], 
                          redirect_uri: str, auth_url: str,
                          state: Optional[str] = None) -> Tuple[str, str]:
        """
        Generate an OAuth 2.0 authorization URL.
        
        Args:
            client_id: OAuth client ID
            scopes: List of requested scopes
            redirect_uri: Redirect URI after authorization
            auth_url: Authorization endpoint URL
            state: Optional state parameter for security
            
        Returns:
            Tuple of (authorization URL, state)
        """
        if not state:
            state = secrets.token_urlsafe(16)
            
        # Build scope string
        scope = ' '.join(scopes)
        
        # Build auth URL
        params = {
            'client_id': client_id,
            'redirect_uri': redirect_uri,
            'scope': scope,
            'response_type': 'code',
            'state': state,
            'access_type': 'offline',
            'prompt': 'consent'
        }
        
        # Convert params to query string
        query = '&'.join([f"{k}={v}" for k, v in params.items()])
        auth_uri = f"{auth_url}?{query}"
        
        return auth_uri, state
    
    def exchange_code_for_tokens(self, client_id: str, client_secret: str, 
                               code: str, redirect_uri: str, token_url: str) -> bool:
        """
        Exchange an authorization code for access and refresh tokens.
        
        Args:
            client_id: OAuth client ID
            client_secret: OAuth client secret
            code: Authorization code
            redirect_uri: Redirect URI
            token_url: Token endpoint URL
            
        Returns:
            True if token exchange was successful, False otherwise
        """
        try:
            # This is a placeholder for the actual token exchange
            # In a real implementation, you would make an HTTP request to the token endpoint
            
            # TODO: Implement actual token exchange logic
            # For now, we'll just simulate a successful token exchange
            self.tokens = {
                'access_token': 'simulated_access_token',
                'refresh_token': 'simulated_refresh_token',
                'expires_in': 3600,
                'token_type': 'Bearer'
            }
            
            # Update token expiry
            self._update_token_expiry()
            
            # Set authenticated flag
            self.authenticated = True
            
            logger.info("Simulated token exchange successful")
            return True
            
        except Exception as e:
            logger.error(f"Error exchanging code for tokens: {e}")
            return False
"""