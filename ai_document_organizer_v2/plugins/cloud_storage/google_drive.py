"""
Google Drive cloud storage provider plugin for AI Document Organizer V2.

This module provides integration with Google Drive, allowing the application to
access, store, and manage files and folders in Google Drive.
"""

import os
import json
import logging
import mimetypes
import time
from typing import Dict, List, Any, Optional, Tuple, BinaryIO, Union, Iterator
from datetime import datetime, timezone

from ai_document_organizer_v2.plugins.cloud_storage.provider_base import CloudProviderPlugin, CloudStorageError
from ai_document_organizer_v2.plugins.cloud_storage.auth_manager import AuthManager, CredentialError

# Import Google API client libraries (optional dependency)
GOOGLE_DRIVE_AVAILABLE = False
try:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    GOOGLE_DRIVE_AVAILABLE = True
except ImportError:
    pass

logger = logging.getLogger("AIDocumentOrganizerV2.CloudStorage.GoogleDrive")


class GoogleDrivePlugin(CloudProviderPlugin):
    """
    Google Drive integration plugin for AI Document Organizer V2.
    
    This plugin provides integration with Google Drive, allowing the application to
    access, store, and manage files and folders in Google Drive.
    """
    
    # Class constants
    MIME_FOLDER = "application/vnd.google-apps.folder"
    MIME_TYPE_MAP = {
        "document": "application/vnd.google-apps.document",
        "spreadsheet": "application/vnd.google-apps.spreadsheet",
        "presentation": "application/vnd.google-apps.presentation",
        "drawing": "application/vnd.google-apps.drawing",
        "form": "application/vnd.google-apps.form"
    }
    
    # Required OAuth 2.0 scopes for various operations
    SCOPES = [
        'https://www.googleapis.com/auth/drive.file',  # Per-file access
        'https://www.googleapis.com/auth/drive.metadata.readonly',  # Read metadata
        'https://www.googleapis.com/auth/drive.readonly'  # Read all files
    ]
    
    def __init__(self, plugin_id: str = "google_drive", 
                name: str = "Google Drive", 
                version: str = "1.0.0", 
                description: str = "Google Drive cloud storage provider"):
        """
        Initialize the Google Drive plugin.
        
        Args:
            plugin_id: Unique identifier for the plugin
            name: Display name for the plugin
            version: Version of the plugin
            description: Description of the plugin
        """
        super().__init__(plugin_id, name, version, description)
        
        # Check if Google Drive API is available
        if not GOOGLE_DRIVE_AVAILABLE:
            logger.warning("Google Drive API client libraries not available. "
                          "Install them with: pip install google-api-python-client "
                          "google-auth-httplib2 google-auth-oauthlib")
        
        # Initialize auth manager
        self.auth_manager = AuthManager("GoogleDrive", "AI Document Organizer")
        
        # Initialize service
        self.service = None
        
        # File cache (id -> file info)
        self._file_cache = {}
        
        # Folder ID cache (path -> folder id)
        self._folder_id_cache = {}
    
    def _get_provider_name(self) -> str:
        """Get the name of the cloud storage provider."""
        return "GoogleDrive"
    
    def _init_provider_settings(self) -> None:
        """Initialize provider-specific settings."""
        self.config.update({
            "scopes": self.SCOPES,
            "authorize_url": "https://accounts.google.com/o/oauth2/auth",
            "token_url": "https://oauth2.googleapis.com/token",
            "api_version": "v3",
            "page_size": 100,
            "fields": "files(id,name,mimeType,parents,modifiedTime,createdTime,size,webViewLink,md5Checksum,thumbnailLink,shared),nextPageToken",
            "order_by": "folder,name",
            "use_service_account": False,
            "service_account_file": None
        })
    
    def _apply_provider_specific_settings(self) -> None:
        """Apply provider-specific settings from the settings manager."""
        prefix = f"cloud_storage.google_drive."
        
        # OAuth scopes
        scopes = self.settings_manager.get_setting(f"{prefix}scopes")
        if scopes:
            self.config["scopes"] = scopes
        
        # API version
        api_version = self.settings_manager.get_setting(f"{prefix}api_version")
        if api_version:
            self.config["api_version"] = api_version
        
        # Page size
        page_size = self.settings_manager.get_setting(f"{prefix}page_size")
        if page_size:
            self.config["page_size"] = page_size
        
        # Fields
        fields = self.settings_manager.get_setting(f"{prefix}fields")
        if fields:
            self.config["fields"] = fields
        
        # Order by
        order_by = self.settings_manager.get_setting(f"{prefix}order_by")
        if order_by:
            self.config["order_by"] = order_by
        
        # Use service account
        use_service_account = self.settings_manager.get_setting(f"{prefix}use_service_account")
        if use_service_account is not None:
            self.config["use_service_account"] = use_service_account
        
        # Service account file
        service_account_file = self.settings_manager.get_setting(f"{prefix}service_account_file")
        if service_account_file:
            self.config["service_account_file"] = service_account_file
    
    def initialize(self) -> bool:
        """
        Initialize the plugin and prepare it for use.
        
        Returns:
            True if initialization was successful, False otherwise
        """
        if not GOOGLE_DRIVE_AVAILABLE:
            logger.error("Google Drive API client libraries not available")
            return False
            
        try:
            # Call parent initialization
            if not super().initialize():
                return False
                
            # Set the token refresh callback
            self.auth_manager.set_token_refresh_callback(self._refresh_token)
            
            # Enable encryption for token storage if supported
            self.auth_manager.enable_encryption()
            
            return True
        except Exception as e:
            logger.error(f"Error initializing Google Drive plugin: {e}")
            return False
    
    def authenticate(self) -> bool:
        """
        Authenticate with Google Drive.
        
        Returns:
            True if authentication was successful, False otherwise
        """
        if not GOOGLE_DRIVE_AVAILABLE:
            logger.error("Google Drive API client libraries not available")
            return False
            
        try:
            # Check if service account authentication is enabled
            if self.config["use_service_account"] and self.config["service_account_file"]:
                return self._authenticate_service_account()
                
            # Try to load credentials file
            credentials_loaded = False
            if self.config["credentials_file"]:
                credentials_loaded = self.auth_manager.load_credentials_from_file(self.config["credentials_file"])
                
            if not credentials_loaded:
                logger.error("No valid credentials found for Google Drive")
                return False
                
            # Try to load tokens from file
            token_loaded = False
            if self.config["token_file"]:
                token_loaded = self.auth_manager.load_tokens_from_file(self.config["token_file"])
                
            # Check if we need to get new tokens
            if not token_loaded or self.auth_manager.is_token_expired():
                if not self._get_new_tokens():
                    return False
            
            # Build the Drive service
            creds = self._build_credentials()
            self.service = build('drive', self.config["api_version"], credentials=creds)
            
            self.authenticated = True
            return True
            
        except Exception as e:
            logger.error(f"Error authenticating with Google Drive: {e}")
            return False
    
    def _authenticate_service_account(self) -> bool:
        """
        Authenticate using a service account.
        
        Returns:
            True if authentication was successful, False otherwise
        """
        try:
            from google.oauth2 import service_account
            
            # Check if service account file exists
            if not os.path.exists(self.config["service_account_file"]):
                logger.error(f"Service account file not found: {self.config['service_account_file']}")
                return False
                
            # Load service account credentials
            creds = service_account.Credentials.from_service_account_file(
                self.config["service_account_file"],
                scopes=self.config["scopes"]
            )
            
            # Build the Drive service
            self.service = build('drive', self.config["api_version"], credentials=creds)
            
            self.authenticated = True
            return True
            
        except Exception as e:
            logger.error(f"Error authenticating with service account: {e}")
            return False
    
    def _get_new_tokens(self) -> bool:
        """
        Get new OAuth tokens using the authentication flow.
        
        Returns:
            True if tokens were obtained successfully, False otherwise
        """
        try:
            # Create the flow using the client secrets file
            credentials = self.auth_manager.get_credentials()
            
            flow = InstalledAppFlow.from_client_config(
                {
                    "installed": {
                        "client_id": credentials.get("client_id"),
                        "client_secret": credentials.get("client_secret"),
                        "auth_uri": self.config["authorize_url"],
                        "token_uri": self.config["token_url"],
                        "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"]
                    }
                },
                self.config["scopes"]
            )
            
            # Run the authorization flow
            creds = flow.run_local_server(port=0)
            
            # Store tokens
            tokens = {
                "access_token": creds.token,
                "refresh_token": creds.refresh_token,
                "token_type": "Bearer",
                "expires_at": int(time.time() + creds.expires_in)
            }
            
            self.auth_manager.set_tokens(tokens)
            
            # Save tokens to file if configured
            if self.config["token_file"]:
                self.auth_manager.save_tokens_to_file(self.config["token_file"])
                
            return True
            
        except Exception as e:
            logger.error(f"Error getting new tokens: {e}")
            return False
    
    def _refresh_token(self, refresh_token: str) -> bool:
        """
        Refresh the access token using the refresh token.
        
        Args:
            refresh_token: Refresh token
            
        Returns:
            True if token was refreshed successfully, False otherwise
        """
        try:
            # Build credentials with the refresh token
            creds = Credentials(
                token=None,
                refresh_token=refresh_token,
                token_uri=self.config["token_url"],
                client_id=self.auth_manager.get_credentials().get("client_id"),
                client_secret=self.auth_manager.get_credentials().get("client_secret"),
                scopes=self.config["scopes"]
            )
            
            # Refresh the credentials
            creds.refresh(Request())
            
            # Update tokens
            tokens = {
                "access_token": creds.token,
                "refresh_token": creds.refresh_token or refresh_token,
                "token_type": "Bearer",
                "expires_at": int(time.time() + creds.expires_in)
            }
            
            self.auth_manager.set_tokens(tokens)
            
            # Save tokens to file if configured
            if self.config["token_file"]:
                self.auth_manager.save_tokens_to_file(self.config["token_file"])
                
            return True
            
        except Exception as e:
            logger.error(f"Error refreshing token: {e}")
            return False
    
    def _build_credentials(self) -> Credentials:
        """
        Build Google OAuth credentials from stored tokens.
        
        Returns:
            Google OAuth credentials
        """
        tokens = self.auth_manager.tokens
        credentials = self.auth_manager.get_credentials()
        
        return Credentials(
            token=tokens.get("access_token"),
            refresh_token=tokens.get("refresh_token"),
            token_uri=self.config["token_url"],
            client_id=credentials.get("client_id"),
            client_secret=credentials.get("client_secret"),
            scopes=self.config["scopes"]
        )
    
    def _save_tokens(self) -> None:
        """Save authentication tokens to the token file."""
        if self.config["token_file"] and self.auth_manager.tokens:
            self.auth_manager.save_tokens_to_file(self.config["token_file"])
    
    def list_files(self, path: str = "", page_size: int = 100, page_token: str = None) -> Dict[str, Any]:
        """
        List files and folders at the specified path.
        
        Args:
            path: Path to list files from (default: root)
            page_size: Number of items to return per page
            page_token: Token for pagination
            
        Returns:
            Dictionary containing file information and pagination details
        """
        if not self.service:
            if not self.authenticate():
                raise CloudStorageError(
                    "Not authenticated with Google Drive",
                    provider=self.provider_name
                )
                
        try:
            # Use provided page size or default from config
            page_size = page_size or self.config["page_size"]
            
            # Get folder ID from path
            folder_id = 'root'  # Default to root folder
            if path and path != '/':
                folder_id = self.get_file_id_from_path(path)
                
            # Prepare query
            query = f"'{folder_id}' in parents and trashed = false"
            
            # Execute the query
            results = self.service.files().list(
                q=query,
                pageSize=page_size,
                pageToken=page_token,
                fields=f"nextPageToken, {self.config['fields']}",
                orderBy=self.config["order_by"]
            ).execute()
            
            items = results.get('files', [])
            next_page_token = results.get('nextPageToken')
            
            # Process the results
            processed_items = []
            for item in items:
                processed_item = self._process_file_item(item)
                processed_items.append(processed_item)
                
                # Cache the file info
                self._file_cache[item['id']] = processed_item
            
            return {
                'items': processed_items,
                'next_page_token': next_page_token,
                'has_more': next_page_token is not None
            }
            
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            raise CloudStorageError(
                f"Error listing files: {str(e)}",
                provider=self.provider_name
            )
    
    def _process_file_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a file item from Google Drive API response.
        
        Args:
            item: File item from Google Drive API
            
        Returns:
            Processed file information
        """
        is_folder = item.get('mimeType') == self.MIME_FOLDER
        
        # Parse timestamps
        created_time = item.get('createdTime')
        modified_time = item.get('modifiedTime')
        
        created = None
        if created_time:
            created = datetime.fromisoformat(created_time.replace('Z', '+00:00'))
            
        modified = None
        if modified_time:
            modified = datetime.fromisoformat(modified_time.replace('Z', '+00:00'))
            
        # Determine MIME type and file type
        mime_type = item.get('mimeType', '')
        file_type = 'folder' if is_folder else self._get_file_type_from_mime(mime_type)
        
        # Build result
        result = {
            'id': item.get('id', ''),
            'name': item.get('name', ''),
            'path': self._get_path_for_file(item),
            'type': file_type,
            'size': int(item.get('size', 0)) if 'size' in item else 0,
            'modified': modified,
            'created': created,
            'mime_type': mime_type,
            'web_url': item.get('webViewLink', ''),
            'owner': item.get('owners', [{}])[0].get('emailAddress', '') if 'owners' in item else '',
            'shared': item.get('shared', False),
            'provider_info': {
                'drive_id': item.get('id', ''),
                'parents': item.get('parents', []),
                'thumbnail_url': item.get('thumbnailLink', '') if not is_folder else '',
                'md5_checksum': item.get('md5Checksum', '') if not is_folder else ''
            }
        }
        
        # Add thumbnail URL if available
        if 'thumbnailLink' in item:
            result['thumbnail_url'] = item['thumbnailLink']
            
        # Add MD5 if available (for non-Google formats)
        if 'md5Checksum' in item:
            result['md5'] = item['md5Checksum']
            
        return result
    
    def _get_file_type_from_mime(self, mime_type: str) -> str:
        """
        Get a file type from a MIME type.
        
        Args:
            mime_type: MIME type
            
        Returns:
            File type
        """
        # Check Google specific types
        for file_type, google_mime in self.MIME_TYPE_MAP.items():
            if mime_type == google_mime:
                return file_type
                
        # Check general categories
        if mime_type.startswith('image/'):
            return 'image'
        elif mime_type.startswith('video/'):
            return 'video'
        elif mime_type.startswith('audio/'):
            return 'audio'
        elif mime_type in ['application/pdf']:
            return 'pdf'
        elif mime_type in ['application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                        'application/msword']:
            return 'document'
        elif mime_type in ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                        'application/vnd.ms-excel']:
            return 'spreadsheet'
        elif mime_type in ['application/vnd.openxmlformats-officedocument.presentationml.presentation',
                        'application/vnd.ms-powerpoint']:
            return 'presentation'
        elif mime_type.startswith('text/'):
            return 'text'
        else:
            return 'file'
    
    def _get_path_for_file(self, item: Dict[str, Any]) -> str:
        """
        Get the path for a file based on its ID and parent IDs.
        
        Args:
            item: File item from Google Drive API
            
        Returns:
            File path
        """
        # This is a simplified implementation that returns a virtual path
        # In a real implementation, you would need to traverse the parent hierarchy
        file_id = item.get('id', '')
        file_name = item.get('name', '')
        
        return f"/{file_name} ({file_id})"
    
    def get_file_info(self, file_id: str) -> Dict[str, Any]:
        """
        Get information about a file.
        
        Args:
            file_id: ID of the file to get information for
            
        Returns:
            Dictionary containing file information
        """
        if not self.service:
            if not self.authenticate():
                raise CloudStorageError(
                    "Not authenticated with Google Drive",
                    provider=self.provider_name
                )
                
        try:
            # Check if file info is cached
            if file_id in self._file_cache:
                return self._file_cache[file_id]
                
            # Get file metadata
            file = self.service.files().get(
                fileId=file_id,
                fields='id,name,mimeType,parents,modifiedTime,createdTime,size,webViewLink,md5Checksum,thumbnailLink,shared,owners'
            ).execute()
            
            # Process the file
            result = self._process_file_item(file)
            
            # Cache the result
            self._file_cache[file_id] = result
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting file info: {e}")
            raise CloudStorageError(
                f"Error getting file info: {str(e)}",
                provider=self.provider_name
            )
    
    def download_file(self, file_id: str, local_path: str, 
                    callback: Optional[callable] = None) -> bool:
        """
        Download a file from Google Drive to local storage.
        
        Args:
            file_id: ID of the file in Google Drive
            local_path: Path to save the file locally
            callback: Optional callback function for progress updates
            
        Returns:
            True if download was successful, False otherwise
        """
        if not self.service:
            if not self.authenticate():
                raise CloudStorageError(
                    "Not authenticated with Google Drive",
                    provider=self.provider_name
                )
                
        try:
            # Get file info to check if it's a Google Workspace file
            file_info = self.get_file_info(file_id)
            mime_type = file_info["mime_type"]
            
            # Handle Google Workspace files (need to export them)
            if mime_type in self.MIME_TYPE_MAP.values():
                return self._export_google_file(file_id, mime_type, local_path)
                
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(os.path.abspath(local_path)), exist_ok=True)
            
            # Create a request to download the file
            request = self.service.files().get_media(fileId=file_id)
            
            # Download the file
            with open(local_path, 'wb') as f:
                downloader = MediaIoBaseDownload(f, request, chunksize=self.config["chunk_size"])
                
                done = False
                while not done:
                    status, done = downloader.next_chunk()
                    if callback:
                        callback(int(status.progress() * 100), 100, f"Downloading {file_info['name']}")
                        
            return True
            
        except Exception as e:
            logger.error(f"Error downloading file: {e}")
            # Clean up partial file
            if os.path.exists(local_path):
                try:
                    os.remove(local_path)
                except:
                    pass
                    
            raise CloudStorageError(
                f"Error downloading file: {str(e)}",
                provider=self.provider_name
            )
    
    def _export_google_file(self, file_id: str, mime_type: str, local_path: str) -> bool:
        """
        Export a Google Workspace file to a local file.
        
        Args:
            file_id: ID of the file
            mime_type: MIME type of the file
            local_path: Path to save the exported file
            
        Returns:
            True if export was successful, False otherwise
        """
        try:
            # Determine export format based on the Google file type
            export_format = self._get_export_format(mime_type, local_path)
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(os.path.abspath(local_path)), exist_ok=True)
            
            # Export the file
            response = self.service.files().export(
                fileId=file_id,
                mimeType=export_format
            ).execute()
            
            # Write the exported content to file
            with open(local_path, 'wb') as f:
                f.write(response)
                
            return True
            
        except Exception as e:
            logger.error(f"Error exporting Google file: {e}")
            return False
    
    def _get_export_format(self, mime_type: str, local_path: str) -> str:
        """
        Determine the export format based on the Google file type and local path extension.
        
        Args:
            mime_type: MIME type of the Google file
            local_path: Local path to save the file
            
        Returns:
            Export MIME type
        """
        # Default export formats
        default_exports = {
            "application/vnd.google-apps.document": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.google-apps.spreadsheet": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.google-apps.presentation": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "application/vnd.google-apps.drawing": "application/pdf",
            "application/vnd.google-apps.form": "application/pdf"
        }
        
        # Check file extension
        _, ext = os.path.splitext(local_path)
        ext = ext.lower()
        
        # Map extensions to MIME types
        extension_exports = {
            ".pdf": "application/pdf",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            ".txt": "text/plain",
            ".csv": "text/csv",
            ".tsv": "text/tab-separated-values",
            ".html": "text/html",
            ".rtf": "application/rtf",
            ".zip": "application/zip",
            ".epub": "application/epub+zip"
        }
        
        # Get export format based on extension
        if ext in extension_exports:
            return extension_exports[ext]
            
        # Return default export format
        return default_exports.get(mime_type, "application/pdf")
    
    def upload_file(self, local_path: str, parent_id: str, file_name: Optional[str] = None,
                   mime_type: Optional[str] = None, callback: Optional[callable] = None) -> Dict[str, Any]:
        """
        Upload a file from local storage to Google Drive.
        
        Args:
            local_path: Path to the local file
            parent_id: ID of the parent folder in Google Drive
            file_name: Name to use for the uploaded file (default: local file name)
            mime_type: MIME type of the file (default: auto-detect)
            callback: Optional callback function for progress updates
            
        Returns:
            Dictionary containing uploaded file information
        """
        if not self.service:
            if not self.authenticate():
                raise CloudStorageError(
                    "Not authenticated with Google Drive",
                    provider=self.provider_name
                )
                
        try:
            # Determine file name if not provided
            if not file_name:
                file_name = os.path.basename(local_path)
                
            # Determine MIME type if not provided
            if not mime_type:
                mime_type, _ = mimetypes.guess_type(local_path)
                if not mime_type:
                    mime_type = 'application/octet-stream'
                    
            # Prepare file metadata
            file_metadata = {
                'name': file_name,
                'parents': [parent_id]
            }
            
            # Create media upload
            media = MediaFileUpload(
                local_path,
                mimetype=mime_type,
                chunksize=self.config["chunk_size"],
                resumable=True
            )
            
            # Create the upload request
            request = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id,name,mimeType,parents,modifiedTime,createdTime,size,webViewLink,md5Checksum,thumbnailLink,shared'
            )
            
            # Execute the upload with progress tracking
            response = None
            last_progress = 0
            
            while response is None:
                status, response = request.next_chunk()
                if status and callback:
                    progress = int(status.progress() * 100)
                    if progress != last_progress:
                        callback(progress, 100, f"Uploading {file_name}")
                        last_progress = progress
                        
            # Process the uploaded file info
            result = self._process_file_item(response)
            
            # Cache the result
            self._file_cache[response['id']] = result
            
            return result
            
        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            raise CloudStorageError(
                f"Error uploading file: {str(e)}",
                provider=self.provider_name
            )
    
    def delete_file(self, file_id: str, permanent: bool = False) -> bool:
        """
        Delete a file from Google Drive.
        
        Args:
            file_id: ID of the file in Google Drive
            permanent: Whether to permanently delete the file (bypass trash)
            
        Returns:
            True if deletion was successful, False otherwise
        """
        if not self.service:
            if not self.authenticate():
                raise CloudStorageError(
                    "Not authenticated with Google Drive",
                    provider=self.provider_name
                )
                
        try:
            if permanent:
                # Permanently delete the file
                self.service.files().delete(fileId=file_id).execute()
            else:
                # Move the file to trash
                self.service.files().update(
                    fileId=file_id,
                    body={'trashed': True}
                ).execute()
                
            # Remove from cache
            if file_id in self._file_cache:
                del self._file_cache[file_id]
                
            return True
            
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            raise CloudStorageError(
                f"Error deleting file: {str(e)}",
                provider=self.provider_name
            )
    
    def create_folder(self, name: str, parent_id: str) -> Dict[str, Any]:
        """
        Create a folder in Google Drive.
        
        Args:
            name: Name of the folder to create
            parent_id: ID of the parent folder
            
        Returns:
            Dictionary containing folder information
        """
        if not self.service:
            if not self.authenticate():
                raise CloudStorageError(
                    "Not authenticated with Google Drive",
                    provider=self.provider_name
                )
                
        try:
            # Prepare folder metadata
            folder_metadata = {
                'name': name,
                'parents': [parent_id],
                'mimeType': self.MIME_FOLDER
            }
            
            # Create the folder
            folder = self.service.files().create(
                body=folder_metadata,
                fields='id,name,mimeType,parents,modifiedTime,createdTime,webViewLink,shared'
            ).execute()
            
            # Process the folder info
            result = self._process_file_item(folder)
            
            # Cache the result
            self._file_cache[folder['id']] = result
            
            return result
            
        except Exception as e:
            logger.error(f"Error creating folder: {e}")
            raise CloudStorageError(
                f"Error creating folder: {str(e)}",
                provider=self.provider_name
            )
    
    def rename_file(self, file_id: str, new_name: str) -> Dict[str, Any]:
        """
        Rename a file in Google Drive.
        
        Args:
            file_id: ID of the file to rename
            new_name: New name for the file
            
        Returns:
            Dictionary containing updated file information
        """
        if not self.service:
            if not self.authenticate():
                raise CloudStorageError(
                    "Not authenticated with Google Drive",
                    provider=self.provider_name
                )
                
        try:
            # Prepare the update
            file_metadata = {
                'name': new_name
            }
            
            # Update the file
            updated_file = self.service.files().update(
                fileId=file_id,
                body=file_metadata,
                fields='id,name,mimeType,parents,modifiedTime,createdTime,size,webViewLink,md5Checksum,thumbnailLink,shared'
            ).execute()
            
            # Process the updated file info
            result = self._process_file_item(updated_file)
            
            # Update cache
            self._file_cache[file_id] = result
            
            return result
            
        except Exception as e:
            logger.error(f"Error renaming file: {e}")
            raise CloudStorageError(
                f"Error renaming file: {str(e)}",
                provider=self.provider_name
            )
    
    def move_file(self, file_id: str, new_parent_id: str) -> Dict[str, Any]:
        """
        Move a file to a different folder in Google Drive.
        
        Args:
            file_id: ID of the file to move
            new_parent_id: ID of the new parent folder
            
        Returns:
            Dictionary containing updated file information
        """
        if not self.service:
            if not self.authenticate():
                raise CloudStorageError(
                    "Not authenticated with Google Drive",
                    provider=self.provider_name
                )
                
        try:
            # Get the file to know its current parents
            file = self.service.files().get(
                fileId=file_id,
                fields='parents'
            ).execute()
            
            # Remove the current parent and add the new one
            previous_parents = ",".join(file.get('parents', []))
            
            # Move the file to the new folder
            updated_file = self.service.files().update(
                fileId=file_id,
                addParents=new_parent_id,
                removeParents=previous_parents,
                fields='id,name,mimeType,parents,modifiedTime,createdTime,size,webViewLink,md5Checksum,thumbnailLink,shared'
            ).execute()
            
            # Process the updated file info
            result = self._process_file_item(updated_file)
            
            # Update cache
            self._file_cache[file_id] = result
            
            return result
            
        except Exception as e:
            logger.error(f"Error moving file: {e}")
            raise CloudStorageError(
                f"Error moving file: {str(e)}",
                provider=self.provider_name
            )
    
    def search_files(self, query: str, file_type: Optional[str] = None, 
                   max_results: int = 100) -> List[Dict[str, Any]]:
        """
        Search for files in Google Drive.
        
        Args:
            query: Search query
            file_type: Optional filter by file type
            max_results: Maximum number of results to return
            
        Returns:
            List of dictionaries containing file information
        """
        if not self.service:
            if not self.authenticate():
                raise CloudStorageError(
                    "Not authenticated with Google Drive",
                    provider=self.provider_name
                )
                
        try:
            # Prepare the search query
            search_query = f"name contains '{query}' and trashed = false"
            
            # Add file type filter if specified
            if file_type:
                if file_type == 'folder':
                    search_query += f" and mimeType = '{self.MIME_FOLDER}'"
                elif file_type in self.MIME_TYPE_MAP:
                    search_query += f" and mimeType = '{self.MIME_TYPE_MAP[file_type]}'"
                elif file_type in ['image', 'video', 'audio']:
                    search_query += f" and mimeType contains '{file_type}/'"
                elif file_type == 'document':
                    # Include both Google Docs and Microsoft Word
                    search_query += f" and (mimeType = '{self.MIME_TYPE_MAP['document']}' or mimeType contains 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' or mimeType = 'application/msword')"
                elif file_type == 'spreadsheet':
                    # Include both Google Sheets and Microsoft Excel
                    search_query += f" and (mimeType = '{self.MIME_TYPE_MAP['spreadsheet']}' or mimeType contains 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' or mimeType = 'application/vnd.ms-excel')"
                elif file_type == 'presentation':
                    # Include both Google Slides and Microsoft PowerPoint
                    search_query += f" and (mimeType = '{self.MIME_TYPE_MAP['presentation']}' or mimeType contains 'application/vnd.openxmlformats-officedocument.presentationml.presentation' or mimeType = 'application/vnd.ms-powerpoint')"
                    
            # Execute the search
            results = self.service.files().list(
                q=search_query,
                spaces='drive',
                fields=f"files({self.config['fields']})",
                pageSize=max_results
            ).execute()
            
            # Process the results
            items = results.get('files', [])
            processed_items = []
            
            for item in items:
                processed_item = self._process_file_item(item)
                processed_items.append(processed_item)
                
                # Cache the file info
                self._file_cache[item['id']] = processed_item
                
            return processed_items
            
        except Exception as e:
            logger.error(f"Error searching files: {e}")
            raise CloudStorageError(
                f"Error searching files: {str(e)}",
                provider=self.provider_name
            )
    
    def get_file_content(self, file_id: str, as_text: bool = True) -> Union[str, bytes]:
        """
        Get the content of a file without downloading it to disk.
        
        Args:
            file_id: ID of the file
            as_text: Whether to return the content as text or bytes
            
        Returns:
            File content as string or bytes
        """
        if not self.service:
            if not self.authenticate():
                raise CloudStorageError(
                    "Not authenticated with Google Drive",
                    provider=self.provider_name
                )
                
        try:
            # Get file info to check if it's a Google Workspace file
            file_info = self.get_file_info(file_id)
            mime_type = file_info["mime_type"]
            
            # Handle Google Workspace files
            if mime_type in self.MIME_TYPE_MAP.values():
                # Determine export format based on the Google file type
                export_format = "text/plain" if as_text else "application/pdf"
                
                # Export the file
                response = self.service.files().export(
                    fileId=file_id,
                    mimeType=export_format
                ).execute()
                
                if as_text and isinstance(response, bytes):
                    return response.decode('utf-8')
                return response
                
            # Download regular file content
            request = self.service.files().get_media(fileId=file_id)
            
            from io import BytesIO
            buffer = BytesIO()
            downloader = MediaIoBaseDownload(buffer, request)
            
            done = False
            while not done:
                _, done = downloader.next_chunk()
                
            # Get the content
            content = buffer.getvalue()
            
            if as_text:
                return content.decode('utf-8')
            return content
            
        except Exception as e:
            logger.error(f"Error getting file content: {e}")
            raise CloudStorageError(
                f"Error getting file content: {str(e)}",
                provider=self.provider_name
            )
    
    def get_account_info(self) -> Dict[str, Any]:
        """
        Get information about the authenticated account.
        
        Returns:
            Dictionary containing account information
        """
        if not self.service:
            if not self.authenticate():
                raise CloudStorageError(
                    "Not authenticated with Google Drive",
                    provider=self.provider_name
                )
                
        try:
            # Get about information from Drive
            about = self.service.about().get(fields="user,storageQuota").execute()
            
            # Extract user information
            user = about.get("user", {})
            storage = about.get("storageQuota", {})
            
            # Build the result
            result = {
                "user": {
                    "id": user.get("permissionId", ""),
                    "name": user.get("displayName", ""),
                    "email": user.get("emailAddress", ""),
                    "picture_url": user.get("photoLink", "")
                },
                "storage": {
                    "total": int(storage.get("limit", 0)),
                    "used": int(storage.get("usage", 0)),
                    "available": int(storage.get("limit", 0)) - int(storage.get("usage", 0))
                },
                "plan": {
                    "name": "Google Drive",
                    "type": "google",
                    "features": {}
                },
                "provider_info": {
                    "drive_usage": storage.get("usageInDrive", 0),
                    "trash_usage": storage.get("usageInTrash", 0)
                }
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            raise CloudStorageError(
                f"Error getting account info: {str(e)}",
                provider=self.provider_name
            )
    
    def get_file_id_from_path(self, path: str) -> str:
        """
        Get the file ID from a path.
        
        Args:
            path: Path to the file or folder
            
        Returns:
            File ID
        """
        # Check if the path is already a file ID (for compatibility)
        if path.startswith("file:") or path.startswith("folder:"):
            return path.split(":", 1)[1]
            
        # Check if this path is cached
        if path in self._folder_id_cache:
            return self._folder_id_cache[path]
            
        # Path may be a file ID directly
        if not path.startswith('/'):
            return path
            
        # Split the path into components
        components = [c for c in path.split('/') if c]
        
        if not components:
            return 'root'
            
        # Traverse the path to find the ID
        parent_id = 'root'
        
        for i, component in enumerate(components):
            # Check if it's a file ID pattern
            if ' (' in component and component.endswith(')'):
                # Extract ID from "name (id)" format
                name, file_id = component.rsplit(' (', 1)
                file_id = file_id.rstrip(')')
                return file_id
                
            # Find component in the current parent
            current_path = '/' + '/'.join(components[:i+1])
            
            try:
                query = f"name = '{component}' and '{parent_id}' in parents and trashed = false"
                results = self.service.files().list(
                    q=query,
                    spaces='drive',
                    fields="files(id)",
                    pageSize=1
                ).execute()
                
                items = results.get('files', [])
                
                if not items:
                    raise CloudStorageError(
                        f"Path component not found: {component}",
                        provider=self.provider_name
                    )
                    
                parent_id = items[0]['id']
                
                # Cache this path component
                self._folder_id_cache[current_path] = parent_id
                
            except Exception as e:
                logger.error(f"Error resolving path: {e}")
                raise CloudStorageError(
                    f"Error resolving path: {str(e)}",
                    provider=self.provider_name
                )
                
        return parent_id
    
    def get_path_from_file_id(self, file_id: str) -> str:
        """
        Get the path from a file ID.
        
        Args:
            file_id: ID of the file or folder
            
        Returns:
            Path to the file or folder
        """
        # Simple implementation that just adds a prefix
        # A real implementation would traverse the parent hierarchy
        if file_id == 'root':
            return '/'
            
        try:
            # Get file info
            file_info = self.get_file_info(file_id)
            return f"/{file_info['name']} ({file_id})"
            
        except Exception as e:
            logger.error(f"Error resolving file ID to path: {e}")
            return f"/Unknown ({file_id})"
    
    def get_file_sharing_info(self, file_id: str) -> Dict[str, Any]:
        """
        Get sharing information for a file.
        
        Args:
            file_id: ID of the file
            
        Returns:
            Dictionary containing sharing information
        """
        if not self.service:
            if not self.authenticate():
                raise CloudStorageError(
                    "Not authenticated with Google Drive",
                    provider=self.provider_name
                )
                
        try:
            # Get the permissions for the file
            permissions = self.service.permissions().list(
                fileId=file_id,
                fields="permissions(id,type,role,emailAddress,domain,displayName)"
            ).execute()
            
            # Check if the file has a sharing link
            sharing_url = None
            try:
                # Get the sharing link if available
                sharing_link = self.service.files().get(
                    fileId=file_id,
                    fields="webViewLink"
                ).execute()
                
                sharing_url = sharing_link.get("webViewLink")
            except:
                pass
                
            # Process the permissions
            processed_permissions = []
            for permission in permissions.get("permissions", []):
                processed_permission = {
                    "id": permission.get("id"),
                    "type": permission.get("type"),
                    "role": permission.get("role")
                }
                
                # Add optional fields if available
                if "emailAddress" in permission:
                    processed_permission["email"] = permission["emailAddress"]
                    
                if "domain" in permission:
                    processed_permission["domain"] = permission["domain"]
                    
                if "displayName" in permission:
                    processed_permission["name"] = permission["displayName"]
                    
                processed_permissions.append(processed_permission)
                
            # Build the result
            result = {
                "shared": len(processed_permissions) > 0,
                "sharing_url": sharing_url,
                "permissions": processed_permissions,
                "provider_info": {
                    "drive_id": file_id
                }
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting file sharing info: {e}")
            raise CloudStorageError(
                f"Error getting file sharing info: {str(e)}",
                provider=self.provider_name
            )
    
    def share_file(self, file_id: str, email: Optional[str] = None, role: str = "reader",
                 type: str = "user", domain: Optional[str] = None) -> Dict[str, Any]:
        """
        Share a file with a user, group, domain, or make it public.
        
        Args:
            file_id: ID of the file to share
            email: Email address of the user to share with
            role: Role to grant ("reader", "writer", "commenter", "owner", "organizer")
            type: Type of sharing ("user", "group", "domain", "anyone")
            domain: Domain to share with (if type is "domain")
            
        Returns:
            Dictionary containing updated sharing information
        """
        if not self.service:
            if not self.authenticate():
                raise CloudStorageError(
                    "Not authenticated with Google Drive",
                    provider=self.provider_name
                )
                
        try:
            # Validate the parameters
            if type in ["user", "group"] and not email:
                raise CloudStorageError(
                    f"Email address is required for {type} sharing",
                    provider=self.provider_name
                )
                
            if type == "domain" and not domain:
                raise CloudStorageError(
                    "Domain is required for domain sharing",
                    provider=self.provider_name
                )
                
            # Prepare the permission
            permission = {
                "role": role,
                "type": type
            }
            
            # Add type-specific fields
            if type in ["user", "group"]:
                permission["emailAddress"] = email
                
            if type == "domain":
                permission["domain"] = domain
                
            # Create the permission
            created_permission = self.service.permissions().create(
                fileId=file_id,
                body=permission,
                fields="id,type,role,emailAddress,domain,displayName",
                sendNotificationEmail=False
            ).execute()
            
            # Get updated sharing info
            return self.get_file_sharing_info(file_id)
            
        except Exception as e:
            logger.error(f"Error sharing file: {e}")
            raise CloudStorageError(
                f"Error sharing file: {str(e)}",
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
        if not self.service:
            if not self.authenticate():
                raise CloudStorageError(
                    "Not authenticated with Google Drive",
                    provider=self.provider_name
                )
                
        try:
            # Delete the permission
            self.service.permissions().delete(
                fileId=file_id,
                permissionId=permission_id
            ).execute()
            
            return True
            
        except Exception as e:
            logger.error(f"Error revoking access: {e}")
            raise CloudStorageError(
                f"Error revoking access: {str(e)}",
                provider=self.provider_name
            )
    
    def get_changes(self, page_token: Optional[str] = None, include_removed: bool = True,
                  space: str = "drive", page_size: int = 100) -> Dict[str, Any]:
        """
        Get changes to files since the last check.
        
        Args:
            page_token: Token for pagination and tracking changes
            include_removed: Whether to include removed files in changes
            space: Space to check for changes
            page_size: Number of changes to return per page
            
        Returns:
            Dictionary containing changes and pagination details
        """
        if not self.service:
            if not self.authenticate():
                raise CloudStorageError(
                    "Not authenticated with Google Drive",
                    provider=self.provider_name
                )
                
        try:
            # Get a start page token if none is provided
            if not page_token:
                page_token = self.get_start_page_token()
                
            # Get the changes
            response = self.service.changes().list(
                pageToken=page_token,
                spaces=space,
                pageSize=page_size,
                includeRemoved=include_removed,
                includeItemsFromAllDrives=False,
                supportsAllDrives=False,
                fields="newStartPageToken,nextPageToken,changes(fileId,removed,time,file(id,name,mimeType,parents,modifiedTime,createdTime,size,webViewLink,md5Checksum,thumbnailLink,shared))"
            ).execute()
            
            # Process the changes
            changes = []
            for change in response.get("changes", []):
                file_item = None
                if not change.get("removed", False) and "file" in change:
                    file_item = self._process_file_item(change["file"])
                    
                # Add to changes list
                changes.append({
                    "file_id": change.get("fileId"),
                    "removed": change.get("removed", False),
                    "file": file_item,
                    "time": datetime.fromisoformat(change.get("time", "").replace('Z', '+00:00'))
                            if change.get("time") else datetime.now(timezone.utc)
                })
                
            # Build the result
            result = {
                "changes": changes,
                "next_page_token": response.get("nextPageToken"),
                "new_start_page_token": response.get("newStartPageToken"),
                "has_more": response.get("nextPageToken") is not None
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting changes: {e}")
            raise CloudStorageError(
                f"Error getting changes: {str(e)}",
                provider=self.provider_name
            )
    
    def get_start_page_token(self) -> str:
        """
        Get a token for starting to track changes.
        
        Returns:
            Start page token for tracking changes
        """
        if not self.service:
            if not self.authenticate():
                raise CloudStorageError(
                    "Not authenticated with Google Drive",
                    provider=self.provider_name
                )
                
        try:
            # Get the start page token
            response = self.service.changes().getStartPageToken().execute()
            return response.get("startPageToken")
            
        except Exception as e:
            logger.error(f"Error getting start page token: {e}")
            raise CloudStorageError(
                f"Error getting start page token: {str(e)}",
                provider=self.provider_name
            )
    
    def get_shared_with_me(self, page_size: int = 100, page_token: str = None) -> Dict[str, Any]:
        """
        Get files shared with the authenticated user.
        
        Args:
            page_size: Number of items to return per page
            page_token: Token for pagination
            
        Returns:
            Dictionary containing file information and pagination details
        """
        if not self.service:
            if not self.authenticate():
                raise CloudStorageError(
                    "Not authenticated with Google Drive",
                    provider=self.provider_name
                )
                
        try:
            # Prepare query for shared files
            query = "sharedWithMe = true and trashed = false"
            
            # Execute the query
            results = self.service.files().list(
                q=query,
                pageSize=page_size,
                pageToken=page_token,
                fields=f"nextPageToken, {self.config['fields']}",
                orderBy=self.config["order_by"]
            ).execute()
            
            items = results.get('files', [])
            next_page_token = results.get('nextPageToken')
            
            # Process the results
            processed_items = []
            for item in items:
                processed_item = self._process_file_item(item)
                processed_items.append(processed_item)
                
                # Cache the file info
                self._file_cache[item['id']] = processed_item
            
            return {
                'items': processed_items,
                'next_page_token': next_page_token,
                'has_more': next_page_token is not None
            }
            
        except Exception as e:
            logger.error(f"Error listing shared files: {e}")
            raise CloudStorageError(
                f"Error listing shared files: {str(e)}",
                provider=self.provider_name
            )
    
    def supports_change_tracking(self) -> bool:
        """Check if the provider supports change tracking."""
        return True
    
    def supports_sharing(self) -> bool:
        """Check if the provider supports file sharing."""
        return True