"""
Base class and interfaces for cloud storage providers in AI Document Organizer V2.

This module defines the abstract base classes and interfaces that all cloud storage
provider plugins must implement to ensure consistent behavior and integration.
"""

import os
import abc
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, BinaryIO, Union, Iterator

from ai_document_organizer_v2.core.plugin_base import BasePlugin

logger = logging.getLogger("AIDocumentOrganizerV2.CloudStorage")


class CloudStorageError(Exception):
    """Base exception class for cloud storage errors."""
    
    def __init__(self, message: str, provider: str = None, code: str = None, details: Dict[str, Any] = None):
        """
        Initialize a cloud storage error.
        
        Args:
            message: Error message
            provider: Name of the cloud storage provider (optional)
            code: Error code (optional)
            details: Additional error details (optional)
        """
        self.provider = provider
        self.code = code
        self.details = details or {}
        
        # Enhance message with provider and code if available
        full_message = message
        if provider:
            full_message = f"[{provider}] {full_message}"
        if code:
            full_message = f"{full_message} (Code: {code})"
            
        super().__init__(full_message)


class CloudProviderPlugin(BasePlugin, abc.ABC):
    """
    Abstract base class for cloud storage provider plugins.
    
    This class defines the interface that all cloud storage provider plugins must implement.
    It inherits from BasePlugin for lifecycle management and plugin registration.
    """
    
    # Plugin type and metadata
    PLUGIN_TYPE = "cloud_storage"
    
    def __init__(self, plugin_id: str, name: str, version: str, description: str = ""):
        """
        Initialize the cloud storage provider plugin.
        
        Args:
            plugin_id: Unique identifier for the plugin
            name: Display name for the plugin
            version: Version of the plugin
            description: Description of the plugin
        """
        super().__init__(plugin_id, name, version, description)
        
        # Provider-specific attributes
        self.provider_name = self._get_provider_name()
        self.authenticated = False
        self.credentials = {}
        
        # Default configuration
        self.config = {
            "credentials_file": None,  # Path to credentials file
            "token_file": None,        # Path to token file for cached authentication
            "cache_dir": None,         # Directory for caching files
            "chunk_size": 10 * 1024 * 1024,  # 10 MB default chunk size for uploads/downloads
            "timeout": 300,            # Default timeout in seconds
            "max_retries": 3,          # Default number of retries for operations
            "verify_ssl": True,        # Whether to verify SSL certificates
        }
        
        # Initialize provider-specific endpoints and settings
        self._init_provider_settings()
    
    def _get_provider_name(self) -> str:
        """
        Get the name of the cloud storage provider.
        Override this in provider-specific implementations.
        
        Returns:
            Provider name string
        """
        return "generic"
    
    def _init_provider_settings(self) -> None:
        """
        Initialize provider-specific settings.
        Override this in provider-specific implementations.
        """
        pass
    
    def initialize(self) -> bool:
        """
        Initialize the plugin and prepare it for use.
        Called by the plugin manager during plugin loading.
        
        Returns:
            True if initialization was successful, False otherwise
        """
        logger.info(f"Initializing {self.provider_name} cloud storage provider plugin")
        
        # Apply settings from settings manager if available
        if self.settings_manager:
            self._apply_settings()
        
        # Create cache directory if specified
        if self.config["cache_dir"]:
            os.makedirs(self.config["cache_dir"], exist_ok=True)
        
        # Try to authenticate if credentials are available
        try:
            if self._has_valid_credentials():
                return self.authenticate()
            return True  # Successfully initialized, but not authenticated
        except Exception as e:
            logger.error(f"Error initializing {self.provider_name} plugin: {e}")
            return False
    
    def _apply_settings(self) -> None:
        """Apply settings from the settings manager."""
        prefix = f"cloud_storage.{self.provider_name.lower()}."
        
        # Apply general settings
        for key in self.config.keys():
            setting_key = f"{prefix}{key}"
            value = self.settings_manager.get_setting(setting_key)
            if value is not None:
                self.config[key] = value
                
        # Apply provider-specific settings
        self._apply_provider_specific_settings()
    
    def _apply_provider_specific_settings(self) -> None:
        """
        Apply provider-specific settings from the settings manager.
        Override this in provider-specific implementations.
        """
        pass
    
    def _has_valid_credentials(self) -> bool:
        """
        Check if valid credentials are available.
        
        Returns:
            True if valid credentials are available, False otherwise
        """
        # Check if credentials file exists
        if self.config["credentials_file"] and os.path.exists(self.config["credentials_file"]):
            return True
        
        # Check if token file exists
        if self.config["token_file"] and os.path.exists(self.config["token_file"]):
            return True
            
        # Check if credentials are already loaded
        if self.credentials:
            return True
            
        return False
    
    def shutdown(self) -> bool:
        """
        Shutdown the plugin and release resources.
        Called by the plugin manager during plugin unloading.
        
        Returns:
            True if shutdown was successful, False otherwise
        """
        logger.info(f"Shutting down {self.provider_name} cloud storage provider plugin")
        
        # Save any cached tokens if needed
        try:
            if self.authenticated and self.config["token_file"]:
                self._save_tokens()
            return True
        except Exception as e:
            logger.error(f"Error shutting down {self.provider_name} plugin: {e}")
            return False
    
    def _save_tokens(self) -> None:
        """
        Save authentication tokens to the token file.
        Override this in provider-specific implementations if needed.
        """
        pass
    
    @abc.abstractmethod
    def authenticate(self) -> bool:
        """
        Authenticate with the cloud storage provider.
        
        Returns:
            True if authentication was successful, False otherwise
        """
        pass
    
    @abc.abstractmethod
    def list_files(self, path: str = "", page_size: int = 100, page_token: str = None) -> Dict[str, Any]:
        """
        List files and folders at the specified path.
        
        Args:
            path: Path to list files from (default: root)
            page_size: Number of items to return per page
            page_token: Token for pagination
            
        Returns:
            Dictionary containing file information and pagination details:
            {
                "items": [
                    {
                        "id": "file_id",
                        "name": "file_name",
                        "path": "file_path",
                        "type": "file" or "folder",
                        "size": size_in_bytes,
                        "modified": datetime_object,
                        "created": datetime_object,
                        "mime_type": "mime/type",
                        "web_url": "url_to_view_file",
                        "owner": "owner_email_or_name",
                        "shared": True/False,
                        "thumbnail_url": "thumbnail_url" (optional),
                        "md5": "file_md5_checksum" (optional),
                        "provider_info": {
                            # Provider-specific information
                        }
                    },
                    ...
                ],
                "next_page_token": "token_for_next_page" or None,
                "has_more": True/False
            }
        """
        pass
    
    @abc.abstractmethod
    def get_file_info(self, file_id: str) -> Dict[str, Any]:
        """
        Get information about a file.
        
        Args:
            file_id: ID of the file to get information for
            
        Returns:
            Dictionary containing file information (same structure as list_files items)
        """
        pass
    
    @abc.abstractmethod
    def download_file(self, file_id: str, local_path: str, 
                    callback: Optional[callable] = None) -> bool:
        """
        Download a file from cloud storage to local storage.
        
        Args:
            file_id: ID of the file in cloud storage
            local_path: Path to save the file locally
            callback: Optional callback function for progress updates (receives bytes_downloaded, total_bytes)
            
        Returns:
            True if download was successful, False otherwise
        """
        pass
    
    @abc.abstractmethod
    def upload_file(self, local_path: str, parent_id: str, file_name: Optional[str] = None,
                   mime_type: Optional[str] = None, callback: Optional[callable] = None) -> Dict[str, Any]:
        """
        Upload a file from local storage to cloud storage.
        
        Args:
            local_path: Path to the local file
            parent_id: ID of the parent folder in cloud storage
            file_name: Name to use for the uploaded file (default: local file name)
            mime_type: MIME type of the file (default: auto-detect)
            callback: Optional callback function for progress updates (receives bytes_uploaded, total_bytes)
            
        Returns:
            Dictionary containing uploaded file information (same structure as get_file_info)
        """
        pass
    
    @abc.abstractmethod
    def delete_file(self, file_id: str, permanent: bool = False) -> bool:
        """
        Delete a file from cloud storage.
        
        Args:
            file_id: ID of the file in cloud storage
            permanent: Whether to permanently delete the file (bypass trash)
            
        Returns:
            True if deletion was successful, False otherwise
        """
        pass
    
    @abc.abstractmethod
    def create_folder(self, name: str, parent_id: str) -> Dict[str, Any]:
        """
        Create a folder in cloud storage.
        
        Args:
            name: Name of the folder to create
            parent_id: ID of the parent folder
            
        Returns:
            Dictionary containing folder information (same structure as get_file_info)
        """
        pass
    
    @abc.abstractmethod
    def rename_file(self, file_id: str, new_name: str) -> Dict[str, Any]:
        """
        Rename a file in cloud storage.
        
        Args:
            file_id: ID of the file to rename
            new_name: New name for the file
            
        Returns:
            Dictionary containing updated file information (same structure as get_file_info)
        """
        pass
    
    @abc.abstractmethod
    def move_file(self, file_id: str, new_parent_id: str) -> Dict[str, Any]:
        """
        Move a file to a different folder in cloud storage.
        
        Args:
            file_id: ID of the file to move
            new_parent_id: ID of the new parent folder
            
        Returns:
            Dictionary containing updated file information (same structure as get_file_info)
        """
        pass
    
    @abc.abstractmethod
    def search_files(self, query: str, file_type: Optional[str] = None, 
                   max_results: int = 100) -> List[Dict[str, Any]]:
        """
        Search for files in cloud storage.
        
        Args:
            query: Search query
            file_type: Optional filter by file type ("document", "spreadsheet", "presentation", "image", "video", "audio", etc.)
            max_results: Maximum number of results to return
            
        Returns:
            List of dictionaries containing file information (same structure as list_files items)
        """
        pass
    
    @abc.abstractmethod
    def get_file_content(self, file_id: str, as_text: bool = True) -> Union[str, bytes]:
        """
        Get the content of a file without downloading it to disk.
        Useful for small text files or configuration files.
        
        Args:
            file_id: ID of the file
            as_text: Whether to return the content as text (True) or bytes (False)
            
        Returns:
            File content as string or bytes
        """
        pass
    
    @abc.abstractmethod
    def get_account_info(self) -> Dict[str, Any]:
        """
        Get information about the authenticated account.
        
        Returns:
            Dictionary containing account information:
            {
                "user": {
                    "id": "user_id",
                    "name": "user_name",
                    "email": "user_email",
                    "picture_url": "profile_picture_url"
                },
                "storage": {
                    "total": total_storage_in_bytes,
                    "used": used_storage_in_bytes,
                    "available": available_storage_in_bytes
                },
                "plan": {
                    "name": "plan_name",
                    "type": "free", "basic", "premium", etc.,
                    "features": {
                        # Plan-specific features
                    }
                },
                "provider_info": {
                    # Provider-specific information
                }
            }
        """
        pass
    
    def get_file_id_from_path(self, path: str) -> str:
        """
        Get the file ID from a cloud path.
        
        Args:
            path: Path to the file in cloud storage
            
        Returns:
            File ID
        """
        # Default implementation for providers that use paths directly as IDs
        return path
    
    def get_path_from_file_id(self, file_id: str) -> str:
        """
        Get the cloud path from a file ID.
        
        Args:
            file_id: ID of the file in cloud storage
            
        Returns:
            Path to the file in cloud storage
        """
        # Default implementation for providers that use paths directly as IDs
        return file_id
    
    def get_file_sharing_info(self, file_id: str) -> Dict[str, Any]:
        """
        Get sharing information for a file.
        
        Args:
            file_id: ID of the file in cloud storage
            
        Returns:
            Dictionary containing sharing information:
            {
                "shared": True/False,
                "sharing_url": "public_url" or None,
                "permissions": [
                    {
                        "type": "user" or "group" or "domain" or "anyone",
                        "id": "id" (if type is user or group),
                        "role": "reader", "writer", "owner", etc.,
                        "email": "email" (if type is user),
                        "name": "name" (if available),
                        "domain": "domain" (if type is domain)
                    },
                    ...
                ],
                "provider_info": {
                    # Provider-specific information
                }
            }
        """
        # Default implementation that returns minimal information
        # Should be overridden by provider-specific implementations
        return {
            "shared": False,
            "sharing_url": None,
            "permissions": [],
            "provider_info": {}
        }
    
    def share_file(self, file_id: str, email: Optional[str] = None, role: str = "reader",
                 type: str = "user", domain: Optional[str] = None) -> Dict[str, Any]:
        """
        Share a file with a user, group, domain, or make it public.
        
        Args:
            file_id: ID of the file to share
            email: Email address of the user to share with (if type is "user")
            role: Role to grant ("reader", "writer", "owner", etc.)
            type: Type of sharing ("user", "group", "domain", "anyone")
            domain: Domain to share with (if type is "domain")
            
        Returns:
            Dictionary containing updated sharing information (same structure as get_file_sharing_info)
        """
        # Default implementation that raises an error
        # Should be overridden by provider-specific implementations
        raise CloudStorageError(
            "Sharing is not supported by this provider",
            provider=self.provider_name
        )
    
    def revoke_access(self, file_id: str, permission_id: str) -> bool:
        """
        Revoke access to a file.
        
        Args:
            file_id: ID of the file
            permission_id: ID of the permission to revoke
            
        Returns:
            True if access was revoked successfully, False otherwise
        """
        # Default implementation that raises an error
        # Should be overridden by provider-specific implementations
        raise CloudStorageError(
            "Revoking access is not supported by this provider",
            provider=self.provider_name
        )
    
    def get_changes(self, page_token: Optional[str] = None, include_removed: bool = True,
                  space: str = "drive", page_size: int = 100) -> Dict[str, Any]:
        """
        Get changes to files since the last check.
        
        Args:
            page_token: Token for pagination and tracking changes since last check
            include_removed: Whether to include removed files in changes
            space: Space to check for changes ("drive", "appDataFolder", etc.)
            page_size: Number of changes to return per page
            
        Returns:
            Dictionary containing changes and pagination details:
            {
                "changes": [
                    {
                        "file_id": "file_id",
                        "removed": True/False,
                        "file": {
                            # File information if removed is False
                            # Same structure as get_file_info
                        },
                        "time": datetime_object
                    },
                    ...
                ],
                "next_page_token": "token_for_next_page" or None,
                "new_start_page_token": "token_for_next_changes_query",
                "has_more": True/False
            }
        """
        # Default implementation that raises an error
        # Should be overridden by provider-specific implementations that support change tracking
        raise CloudStorageError(
            "Change tracking is not supported by this provider",
            provider=self.provider_name
        )
    
    def get_start_page_token(self) -> str:
        """
        Get a token for starting to track changes.
        
        Returns:
            Start page token for tracking changes
        """
        # Default implementation that raises an error
        # Should be overridden by provider-specific implementations that support change tracking
        raise CloudStorageError(
            "Change tracking is not supported by this provider",
            provider=self.provider_name
        )
    
    def upload_file_content(self, content: Union[str, bytes], parent_id: str, file_name: str,
                         mime_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Upload file content directly from a string or bytes object.
        
        Args:
            content: File content as string or bytes
            parent_id: ID of the parent folder in cloud storage
            file_name: Name for the uploaded file
            mime_type: MIME type of the file (default: auto-detect)
            
        Returns:
            Dictionary containing uploaded file information (same structure as get_file_info)
        """
        # Create a temporary file and upload it
        temp_file = os.path.join(
            self.config.get("cache_dir", "."),
            f"temp_{datetime.now().strftime('%Y%m%d%H%M%S')}_{file_name}"
        )
        
        try:
            # Write content to temporary file
            mode = "wb" if isinstance(content, bytes) else "w"
            encoding = None if isinstance(content, bytes) else "utf-8"
            
            with open(temp_file, mode, encoding=encoding) as f:
                f.write(content)
            
            # Upload the temporary file
            result = self.upload_file(temp_file, parent_id, file_name, mime_type)
            
            return result
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file):
                os.remove(temp_file)
    
    def is_authenticated(self) -> bool:
        """
        Check if the plugin is authenticated with the cloud storage provider.
        
        Returns:
            True if authenticated, False otherwise
        """
        return self.authenticated
    
    def can_paginate(self) -> bool:
        """
        Check if the provider supports pagination for listing files.
        
        Returns:
            True if pagination is supported, False otherwise
        """
        # Default implementation assumes pagination is supported
        # Should be overridden by provider-specific implementations if needed
        return True
    
    def supports_change_tracking(self) -> bool:
        """
        Check if the provider supports change tracking.
        
        Returns:
            True if change tracking is supported, False otherwise
        """
        # Default implementation assumes change tracking is not supported
        # Should be overridden by provider-specific implementations if supported
        return False
    
    def supports_sharing(self) -> bool:
        """
        Check if the provider supports file sharing.
        
        Returns:
            True if sharing is supported, False otherwise
        """
        # Default implementation assumes sharing is not supported
        # Should be overridden by provider-specific implementations if supported
        return False
    
    def get_shared_with_me(self, page_size: int = 100, page_token: str = None) -> Dict[str, Any]:
        """
        Get files shared with the authenticated user.
        
        Args:
            page_size: Number of items to return per page
            page_token: Token for pagination
            
        Returns:
            Dictionary containing file information and pagination details
            (same structure as list_files return value)
        """
        # Default implementation that raises an error
        # Should be overridden by provider-specific implementations that support sharing
        raise CloudStorageError(
            "Shared files listing is not supported by this provider",
            provider=self.provider_name
        )