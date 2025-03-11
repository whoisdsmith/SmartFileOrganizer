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
                content = json.load(f)
                
            # Extract provider-specific credentials
            self.credentials = self._extract_provider_credentials(content)
            
            if not self.credentials:
                logger.error(f"No valid credentials found for {self.provider_name}")
                return False
                
            logger.info(f"Credentials loaded successfully for {self.provider_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading credentials: {e}")
            return False
            
    def _extract_provider_credentials(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract provider-specific credentials from the loaded content.
        Override this in provider-specific implementations.
        
        Args:
            content: Loaded credentials content
            
        Returns:
            Dictionary with provider-specific credentials
        """
        # Default implementation looks for provider_name key or generic credentials
        if self.provider_name.lower() in content:
            return content[self.provider_name.lower()]
            
        # Look for common credential formats
        for key in ["client_id", "api_key", "app_key"]:
            if key in content:
                return content
                
        return content
    
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
                content = f.read()
                
            # Decrypt if encryption is enabled
            if self._encryption_key:
                if not CRYPTO_AVAILABLE:
                    logger.warning("Encryption requested but cryptography module not available")
                else:
                    content = self._decrypt_data(content)
                    
            # Parse tokens
            tokens = json.loads(content)
            
            # Extract provider-specific tokens
            self.tokens = tokens
            
            # Check for expiry
            if "expires_at" in self.tokens:
                self._access_token_expiry = self.tokens["expires_at"]
                
            logger.info(f"Tokens loaded successfully for {self.provider_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading tokens: {e}")
            return False
    
    def save_tokens_to_file(self, token_file: str) -> bool:
        """
        Save authentication tokens to a file.
        
        Args:
            token_file: Path to save the tokens to
            
        Returns:
            True if tokens were saved successfully, False otherwise
        """
        if not self.tokens:
            logger.warning(f"No tokens to save for {self.provider_name}")
            return False
            
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(os.path.abspath(token_file)), exist_ok=True)
            
            # Serialize tokens
            content = json.dumps(self.tokens, indent=2)
            
            # Encrypt if encryption is enabled
            if self._encryption_key:
                if not CRYPTO_AVAILABLE:
                    logger.warning("Encryption requested but cryptography module not available")
                else:
                    content = self._encrypt_data(content)
            
            # Write to file
            with open(token_file, 'w') as f:
                f.write(content)
                
            logger.info(f"Tokens saved successfully for {self.provider_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving tokens: {e}")
            return False
    
    def set_tokens(self, tokens: Dict[str, Any], expires_in: Optional[int] = None) -> None:
        """
        Set authentication tokens.
        
        Args:
            tokens: Dictionary containing token information
            expires_in: Optional token expiration time in seconds
        """
        self.tokens = tokens
        
        # Calculate expiry time if provided
        if expires_in:
            self._access_token_expiry = int(time.time() + expires_in - 60)  # Subtract 60 seconds for safety
            self.tokens["expires_at"] = self._access_token_expiry
            
        self.authenticated = "access_token" in self.tokens
    
    def is_token_expired(self) -> bool:
        """
        Check if the access token is expired.
        
        Returns:
            True if the token is expired or missing, False otherwise
        """
        if not self.tokens or "access_token" not in self.tokens:
            return True
            
        # Check expiry time if available
        if self._access_token_expiry > 0:
            return time.time() >= self._access_token_expiry
            
        return False
    
    def get_access_token(self) -> str:
        """
        Get the current access token, refreshing if necessary.
        
        Returns:
            Current access token
        
        Raises:
            CredentialError: If no valid access token is available and cannot be refreshed
        """
        if self.is_token_expired():
            if not self.refresh_token():
                raise CredentialError(f"Access token expired and could not be refreshed for {self.provider_name}")
                
        return self.tokens.get("access_token", "")
    
    def refresh_token(self) -> bool:
        """
        Refresh the access token using the refresh token.
        
        Returns:
            True if token was refreshed successfully, False otherwise
        """
        # Prevent concurrent refresh attempts
        with self._refresh_lock:
            # Check if token has already been refreshed by another thread
            if not self.is_token_expired():
                return True
                
            # Check if refresh token is available
            if not self.tokens or "refresh_token" not in self.tokens:
                logger.error(f"No refresh token available for {self.provider_name}")
                return False
                
            # Call the refresh callback if set
            if self._token_refresh_callback:
                try:
                    success = self._token_refresh_callback(self.tokens.get("refresh_token"))
                    return success
                except Exception as e:
                    logger.error(f"Error refreshing token: {e}")
                    return False
            else:
                logger.error(f"No token refresh callback set for {self.provider_name}")
                return False
    
    def set_token_refresh_callback(self, callback: Callable[[str], bool]) -> None:
        """
        Set a callback function for refreshing tokens.
        
        Args:
            callback: Function that takes a refresh token and returns True if successful
        """
        self._token_refresh_callback = callback
    
    def enable_encryption(self, password: str = None) -> bool:
        """
        Enable encryption for token storage.
        
        Args:
            password: Optional password for encryption (if not provided, a random one will be generated)
            
        Returns:
            True if encryption was enabled successfully, False otherwise
        """
        if not CRYPTO_AVAILABLE:
            logger.warning("Encryption requested but cryptography module not available")
            return False
            
        try:
            # Generate or use provided password
            if not password:
                password = secrets.token_hex(16)
                
            password_bytes = password.encode('utf-8')
            
            # Generate a key
            salt = b'AI_Document_Organizer_Salt'  # Should be stored securely in a real app
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(password_bytes))
            
            # Initialize Fernet with the key
            self._encryption_key = key
            
            return True
            
        except Exception as e:
            logger.error(f"Error enabling encryption: {e}")
            return False
    
    def _encrypt_data(self, data: str) -> str:
        """
        Encrypt data using Fernet symmetric encryption.
        
        Args:
            data: Data to encrypt
            
        Returns:
            Encrypted data as a string
        """
        if not self._encryption_key or not CRYPTO_AVAILABLE:
            return data
            
        fernet = Fernet(self._encryption_key)
        encrypted = fernet.encrypt(data.encode('utf-8'))
        return encrypted.decode('utf-8')
    
    def _decrypt_data(self, data: str) -> str:
        """
        Decrypt data using Fernet symmetric encryption.
        
        Args:
            data: Encrypted data
            
        Returns:
            Decrypted data as a string
        """
        if not self._encryption_key or not CRYPTO_AVAILABLE:
            return data
            
        fernet = Fernet(self._encryption_key)
        decrypted = fernet.decrypt(data.encode('utf-8'))
        return decrypted.decode('utf-8')
    
    def get_authorization_header(self) -> Dict[str, str]:
        """
        Get the authorization header for API requests.
        
        Returns:
            Dictionary with authorization header
        """
        token = self.get_access_token()
        return {"Authorization": f"Bearer {token}"}
    
    def clear_tokens(self) -> None:
        """Clear stored tokens and reset authentication state."""
        self.tokens = {}
        self._access_token_expiry = 0
        self.authenticated = False
    
    def get_credentials(self) -> Dict[str, Any]:
        """
        Get the current credentials.
        
        Returns:
            Dictionary with credentials
        """
        return self.credentials