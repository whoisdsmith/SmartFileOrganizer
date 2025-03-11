"""
Cloud Storage Manager for AI Document Organizer V2.

This module provides a unified interface for managing cloud storage providers,
coordinating synchronization, and handling user configuration.
"""

import os
import json
import logging
import threading
import queue
from typing import Dict, List, Any, Optional, Tuple, Union, Callable
from datetime import datetime

from ai_document_organizer_v2.core.plugin_manager import PluginManager
from ai_document_organizer_v2.plugins.cloud_storage.provider_base import CloudProviderPlugin, CloudStorageError

logger = logging.getLogger("AIDocumentOrganizerV2.CloudStorage.Manager")


class CloudStorageManager:
    """
    Manager class for cloud storage integration.
    
    This class provides a unified interface for different cloud storage providers,
    manages provider registration, configuration, and coordination of file operations
    across multiple providers.
    """
    
    def __init__(self, plugin_manager: Optional[PluginManager] = None, 
                settings_manager: Optional[Any] = None):
        """
        Initialize the cloud storage manager.
        
        Args:
            plugin_manager: Optional plugin manager for auto-discovery of providers
            settings_manager: Optional settings manager for configuration
        """
        self.providers = {}
        self.active_provider = None
        self.settings_manager = settings_manager
        self.plugin_manager = plugin_manager
        
        # Synchronization
        self.sync_thread = None
        self.sync_queue = queue.Queue()
        self.sync_running = False
        self.sync_cancel = threading.Event()
        
        # If plugin manager is provided, auto-discover providers
        if plugin_manager:
            self._discover_providers()
    
    def _discover_providers(self) -> None:
        """
        Discover and register available cloud storage providers from plugin manager.
        """
        if not self.plugin_manager:
            return
            
        logger.info("Discovering cloud storage providers...")
        
        try:
            # Get all cloud storage plugins
            plugins = self.plugin_manager.get_plugins_by_type("cloud_storage")
            
            for plugin in plugins:
                if isinstance(plugin, CloudProviderPlugin):
                    provider_name = plugin.provider_name
                    logger.info(f"Found cloud storage provider: {provider_name}")
                    
                    # Add provider to registry
                    self.add_provider(provider_name, plugin)
        
        except Exception as e:
            logger.error(f"Error discovering cloud storage providers: {e}")
    
    def add_provider(self, provider_name: str, provider: CloudProviderPlugin) -> bool:
        """
        Add a cloud storage provider.
        
        Args:
            provider_name: Name to identify the provider
            provider: CloudProviderPlugin instance
            
        Returns:
            True if provider was added successfully, False otherwise
        """
        try:
            # Check if provider is valid
            if not isinstance(provider, CloudProviderPlugin):
                logger.error(f"Invalid provider type: {type(provider)}")
                return False
                
            # Add to registry
            self.providers[provider_name] = provider
            
            # Set as active provider if it's the first one
            if not self.active_provider:
                self.active_provider = provider_name
                
            logger.info(f"Added cloud provider: {provider_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding cloud provider {provider_name}: {e}")
            return False
    
    def remove_provider(self, provider_name: str) -> bool:
        """
        Remove a cloud storage provider.
        
        Args:
            provider_name: Name of the provider to remove
            
        Returns:
            True if provider was removed successfully, False otherwise
        """
        try:
            if provider_name in self.providers:
                # If removing active provider, clear active provider
                if provider_name == self.active_provider:
                    self.active_provider = None
                    # Set a new active provider if available
                    if self.providers:
                        self.active_provider = next(iter(self.providers))
                        
                # Remove from registry
                del self.providers[provider_name]
                logger.info(f"Removed cloud provider: {provider_name}")
                return True
            else:
                logger.warning(f"Provider not found: {provider_name}")
                return False
                
        except Exception as e:
            logger.error(f"Error removing cloud provider {provider_name}: {e}")
            return False
    
    def set_active_provider(self, provider_name: str) -> bool:
        """
        Set the active cloud storage provider.
        
        Args:
            provider_name: Name of the provider to set as active
            
        Returns:
            True if active provider was set successfully, False otherwise
        """
        try:
            if provider_name in self.providers:
                self.active_provider = provider_name
                logger.info(f"Set active cloud provider: {provider_name}")
                return True
            else:
                logger.warning(f"Provider not found: {provider_name}")
                return False
                
        except Exception as e:
            logger.error(f"Error setting active provider {provider_name}: {e}")
            return False
    
    def get_provider(self, provider_name: Optional[str] = None) -> Optional[CloudProviderPlugin]:
        """
        Get a specific cloud storage provider or the active provider.
        
        Args:
            provider_name: Name of the provider to get (default: active provider)
            
        Returns:
            CloudProviderPlugin instance or None if not found
        """
        try:
            # If provider_name is not specified, use active provider
            if provider_name is None:
                if self.active_provider:
                    return self.providers.get(self.active_provider)
                else:
                    logger.warning("No active provider set")
                    return None
            else:
                return self.providers.get(provider_name)
                
        except Exception as e:
            logger.error(f"Error getting provider {provider_name}: {e}")
            return None
    
    def get_provider_names(self) -> List[str]:
        """
        Get a list of all registered provider names.
        
        Returns:
            List of provider names
        """
        return list(self.providers.keys())
    
    def get_available_providers(self) -> Dict[str, Dict[str, Any]]:
        """
        Get information about all available providers.
        
        Returns:
            Dictionary mapping provider names to provider information dictionaries
        """
        result = {}
        
        for name, provider in self.providers.items():
            try:
                # Get basic information
                result[name] = {
                    "id": provider.plugin_id,
                    "name": provider.name,
                    "version": provider.version,
                    "description": provider.description,
                    "authenticated": provider.authenticated,
                    "active": (name == self.active_provider)
                }
                
                # Try to get account info if authenticated
                if provider.authenticated:
                    try:
                        account_info = provider.get_account_info()
                        result[name]["account_info"] = account_info
                    except Exception as e:
                        logger.warning(f"Error getting account info for {name}: {e}")
                        result[name]["account_info"] = {}
                        
            except Exception as e:
                logger.error(f"Error getting provider info for {name}: {e}")
                result[name] = {
                    "name": name,
                    "error": str(e)
                }
                
        return result
    
    def authenticate_provider(self, provider_name: Optional[str] = None) -> bool:
        """
        Authenticate with a specific provider or the active provider.
        
        Args:
            provider_name: Name of the provider to authenticate (default: active provider)
            
        Returns:
            True if authentication was successful, False otherwise
        """
        provider = self.get_provider(provider_name)
        
        if not provider:
            logger.error(f"Provider not found: {provider_name or self.active_provider}")
            return False
            
        try:
            return provider.authenticate()
        except Exception as e:
            logger.error(f"Error authenticating with provider {provider_name or self.active_provider}: {e}")
            return False
    
    def list_files(self, path: str = "", provider_name: Optional[str] = None, 
                  page_size: int = 100, page_token: str = None) -> Dict[str, Any]:
        """
        List files and folders at the specified path.
        
        Args:
            path: Path to list files from (default: root)
            provider_name: Name of the provider to use (default: active provider)
            page_size: Number of items to return per page
            page_token: Token for pagination
            
        Returns:
            Dictionary containing file information and pagination details
        """
        provider = self.get_provider(provider_name)
        
        if not provider:
            logger.error(f"Provider not found: {provider_name or self.active_provider}")
            return {"items": [], "has_more": False, "next_page_token": None}
            
        try:
            if not provider.authenticated and not provider.authenticate():
                logger.error(f"Provider not authenticated: {provider_name or self.active_provider}")
                return {"items": [], "has_more": False, "next_page_token": None}
                
            return provider.list_files(path, page_size, page_token)
        except Exception as e:
            logger.error(f"Error listing files from provider {provider_name or self.active_provider}: {e}")
            return {"items": [], "has_more": False, "next_page_token": None}
    
    def download_file(self, file_id: str, local_path: str, provider_name: Optional[str] = None,
                     callback: Optional[Callable] = None) -> bool:
        """
        Download a file from cloud storage to local storage.
        
        Args:
            file_id: ID of the file in cloud storage
            local_path: Path to save the file locally
            provider_name: Name of the provider to use (default: active provider)
            callback: Optional callback function for progress updates
            
        Returns:
            True if download was successful, False otherwise
        """
        provider = self.get_provider(provider_name)
        
        if not provider:
            logger.error(f"Provider not found: {provider_name or self.active_provider}")
            return False
            
        try:
            if not provider.authenticated and not provider.authenticate():
                logger.error(f"Provider not authenticated: {provider_name or self.active_provider}")
                return False
                
            return provider.download_file(file_id, local_path, callback)
        except Exception as e:
            logger.error(f"Error downloading file from provider {provider_name or self.active_provider}: {e}")
            return False
    
    def upload_file(self, local_path: str, parent_id: str, file_name: Optional[str] = None,
                   mime_type: Optional[str] = None, provider_name: Optional[str] = None,
                   callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        Upload a file from local storage to cloud storage.
        
        Args:
            local_path: Path to the local file
            parent_id: ID of the parent folder in cloud storage
            file_name: Name to use for the uploaded file (default: local file name)
            mime_type: MIME type of the file (default: auto-detect)
            provider_name: Name of the provider to use (default: active provider)
            callback: Optional callback function for progress updates
            
        Returns:
            Dictionary containing uploaded file information
        """
        provider = self.get_provider(provider_name)
        
        if not provider:
            logger.error(f"Provider not found: {provider_name or self.active_provider}")
            return {}
            
        try:
            if not provider.authenticated and not provider.authenticate():
                logger.error(f"Provider not authenticated: {provider_name or self.active_provider}")
                return {}
                
            return provider.upload_file(local_path, parent_id, file_name, mime_type, callback)
        except Exception as e:
            logger.error(f"Error uploading file to provider {provider_name or self.active_provider}: {e}")
            return {}
    
    def create_folder(self, name: str, parent_id: str, provider_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a folder in cloud storage.
        
        Args:
            name: Name of the folder to create
            parent_id: ID of the parent folder
            provider_name: Name of the provider to use (default: active provider)
            
        Returns:
            Dictionary containing folder information
        """
        provider = self.get_provider(provider_name)
        
        if not provider:
            logger.error(f"Provider not found: {provider_name or self.active_provider}")
            return {}
            
        try:
            if not provider.authenticated and not provider.authenticate():
                logger.error(f"Provider not authenticated: {provider_name or self.active_provider}")
                return {}
                
            return provider.create_folder(name, parent_id)
        except Exception as e:
            logger.error(f"Error creating folder with provider {provider_name or self.active_provider}: {e}")
            return {}
    
    def search_files(self, query: str, file_type: Optional[str] = None, 
                    max_results: int = 100, provider_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search for files in cloud storage.
        
        Args:
            query: Search query
            file_type: Optional filter by file type
            max_results: Maximum number of results to return
            provider_name: Name of the provider to use (default: active provider)
            
        Returns:
            List of dictionaries containing file information
        """
        provider = self.get_provider(provider_name)
        
        if not provider:
            logger.error(f"Provider not found: {provider_name or self.active_provider}")
            return []
            
        try:
            if not provider.authenticated and not provider.authenticate():
                logger.error(f"Provider not authenticated: {provider_name or self.active_provider}")
                return []
                
            return provider.search_files(query, file_type, max_results)
        except Exception as e:
            logger.error(f"Error searching files with provider {provider_name or self.active_provider}: {e}")
            return []
    
    def start_sync(self, local_dir: str, cloud_path: str = "", provider_name: Optional[str] = None,
                  bidirectional: bool = True, interval: int = 300,
                  callback: Optional[Callable] = None) -> bool:
        """
        Start background synchronization between local and cloud storage.
        
        Args:
            local_dir: Local directory to synchronize
            cloud_path: Cloud path to synchronize with (default: root)
            provider_name: Name of the provider to use (default: active provider)
            bidirectional: Whether to synchronize in both directions (default: True)
            interval: Synchronization interval in seconds (default: 300)
            callback: Optional callback function for progress updates
            
        Returns:
            True if synchronization was started successfully, False otherwise
        """
        # Stop existing sync if running
        if self.sync_running:
            self.stop_sync()
            
        # Get provider
        provider = self.get_provider(provider_name)
        
        if not provider:
            logger.error(f"Provider not found: {provider_name or self.active_provider}")
            return False
            
        # Check authentication
        if not provider.authenticated and not provider.authenticate():
            logger.error(f"Provider not authenticated: {provider_name or self.active_provider}")
            return False
            
        # Start sync thread
        try:
            self.sync_running = True
            self.sync_cancel.clear()
            
            # Store sync configuration
            self.sync_config = {
                "local_dir": local_dir,
                "cloud_path": cloud_path,
                "provider_name": provider_name or self.active_provider,
                "bidirectional": bidirectional,
                "interval": interval,
                "callback": callback
            }
            
            # Start sync thread
            self.sync_thread = threading.Thread(
                target=self._sync_worker,
                args=(local_dir, cloud_path, provider, bidirectional, interval, callback),
                daemon=True
            )
            self.sync_thread.start()
            
            logger.info(f"Started synchronization with provider {provider_name or self.active_provider}")
            return True
            
        except Exception as e:
            logger.error(f"Error starting synchronization: {e}")
            self.sync_running = False
            return False
    
    def sync_now(self, provider_name: Optional[str] = None) -> bool:
        """
        Trigger an immediate synchronization operation.
        
        Args:
            provider_name: Optional name of the provider to use (default: active provider)
            
        Returns:
            True if synchronization was triggered successfully, False otherwise
        """
        if not self.sync_running or not self.sync_config:
            logger.error("No active synchronization to trigger")
            return False
            
        try:
            # Get configuration
            config = self.sync_config
            
            # Get provider
            provider_to_use = provider_name or config["provider_name"]
            provider = self.get_provider(provider_to_use)
            
            if not provider:
                logger.error(f"Provider not found: {provider_to_use}")
                return False
                
            # Check authentication
            if not provider.authenticated and not provider.authenticate():
                logger.error(f"Provider not authenticated: {provider_to_use}")
                return False
                
            # Queue sync operation
            logger.info(f"Queuing manual synchronization for {provider_to_use}")
            self.sync_queue.put({
                "provider": provider,
                "local_dir": config["local_dir"],
                "cloud_path": config["cloud_path"],
                "bidirectional": config["bidirectional"],
                "callback": config["callback"]
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Error triggering manual synchronization: {e}")
            return False
    
    def stop_sync(self) -> bool:
        """
        Stop background synchronization.
        
        Returns:
            True if synchronization was stopped successfully, False otherwise
        """
        if not self.sync_running:
            logger.info("Synchronization not running")
            return True
            
        try:
            # Signal sync thread to stop
            self.sync_cancel.set()
            
            # Wait for thread to finish (with timeout)
            if self.sync_thread and self.sync_thread.is_alive():
                self.sync_thread.join(timeout=5.0)
                
            # Reset state
            self.sync_running = False
            self.sync_thread = None
            
            logger.info("Stopped synchronization")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping synchronization: {e}")
            return False
    
    def set_active_provider(self, provider_name: str) -> bool:
        """
        Set the active provider for cloud operations.
        
        Args:
            provider_name: Name of the provider to set as active
            
        Returns:
            True if provider was set as active, False if provider doesn't exist
        """
        if provider_name in self.providers:
            self.active_provider = provider_name
            logger.info(f"Set active provider to {provider_name}")
            return True
        else:
            logger.error(f"Provider {provider_name} not found")
            return False
    
    def _sync_worker(self, local_dir: str, cloud_path: str, provider: CloudProviderPlugin,
                   bidirectional: bool, interval: int, callback: Optional[Callable]) -> None:
        """
        Worker thread for background synchronization.
        
        Args:
            local_dir: Local directory to synchronize
            cloud_path: Cloud path to synchronize with
            provider: Provider to use for synchronization
            bidirectional: Whether to synchronize in both directions
            interval: Synchronization interval in seconds
            callback: Optional callback function for progress updates
        """
        logger.info(f"Sync worker started for {provider.provider_name}")
        
        while not self.sync_cancel.is_set():
            try:
                # Perform synchronization
                self._perform_sync(local_dir, cloud_path, provider, bidirectional, callback)
                
                # Wait for next sync or until cancelled
                self.sync_cancel.wait(interval)
                
            except Exception as e:
                logger.error(f"Error in sync worker: {e}")
                # Wait a bit before retrying
                self.sync_cancel.wait(10)
                
        logger.info(f"Sync worker stopped for {provider.provider_name}")
    
    def _get_local_files(self, local_dir: str) -> List[Dict[str, Any]]:
        """
        Get a list of local files with metadata for synchronization.
        
        Args:
            local_dir: Local directory to scan
            
        Returns:
            List of dictionaries with file information
        """
        local_files = []
        
        # Skip the sync state file
        skip_files = ['.cloudsync_state.json']
        
        for root, dirs, files in os.walk(local_dir):
            # Skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            for file in files:
                # Skip hidden files and sync state file
                if file.startswith('.') or file in skip_files:
                    continue
                    
                local_path = os.path.join(root, file)
                rel_path = os.path.relpath(local_path, local_dir)
                
                # Replace Windows backslashes with forward slashes for consistency
                rel_path = rel_path.replace('\\', '/')
                
                try:
                    file_stat = os.stat(local_path)
                    
                    local_files.append({
                        "path": rel_path,
                        "name": os.path.basename(rel_path),
                        "size": file_stat.st_size,
                        "modified": datetime.fromtimestamp(file_stat.st_mtime),
                        "created": datetime.fromtimestamp(file_stat.st_ctime),
                        "type": "file"
                    })
                except Exception as e:
                    logger.warning(f"Error getting info for local file {rel_path}: {e}")
        
        return local_files
    
    def _load_sync_state(self, state_file: str) -> Dict[str, Any]:
        """
        Load synchronization state from a file.
        
        Args:
            state_file: Path to the state file
            
        Returns:
            Dictionary with synchronization state
        """
        if os.path.exists(state_file):
            try:
                with open(state_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading sync state file: {e}")
                # If the file is corrupted, start with a fresh state
                return {}
        else:
            return {}
    
    def _save_sync_state(self, state: Dict[str, Any], state_file: str) -> None:
        """
        Save synchronization state to a file.
        
        Args:
            state: Dictionary with synchronization state
            state_file: Path to the state file
        """
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(os.path.abspath(state_file)), exist_ok=True)
            
            with open(state_file, 'w') as f:
                json.dump(state, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving sync state file: {e}")
    
    def _handle_conflict(self, local_file: Dict[str, Any], cloud_file: Dict[str, Any], 
                        provider: CloudProviderPlugin, local_dir: str, bidirectional: bool) -> None:
        """
        Handle a file conflict based on the configured conflict resolution strategy.
        
        Args:
            local_file: Local file information
            cloud_file: Cloud file information
            provider: Cloud provider plugin
            local_dir: Local directory path
            bidirectional: Whether synchronization is bidirectional
        """
        file_path = local_file["path"]
        conflict_strategy = getattr(self, "conflict_strategy", "rename")
        
        if conflict_strategy == "local_wins":
            # Local version wins, upload to cloud if bidirectional
            if bidirectional:
                logger.info(f"Conflict resolution: Local wins for {file_path}")
                abs_path = os.path.join(local_dir, file_path)
                try:
                    provider.upload_file(
                        local_path=abs_path,
                        parent_id=provider.get_file_id_from_path(os.path.dirname(cloud_file["path"])),
                        file_name=os.path.basename(file_path)
                    )
                except Exception as e:
                    logger.error(f"Error resolving conflict (local wins) for {file_path}: {e}")
        
        elif conflict_strategy == "cloud_wins":
            # Cloud version wins, download to local
            logger.info(f"Conflict resolution: Cloud wins for {file_path}")
            abs_path = os.path.join(local_dir, file_path)
            try:
                provider.download_file(cloud_file["id"], abs_path)
            except Exception as e:
                logger.error(f"Error resolving conflict (cloud wins) for {file_path}: {e}")
        
        elif conflict_strategy == "newer_wins":
            # Newer version wins based on modification time
            local_ts = local_file["modified"].timestamp() if isinstance(local_file["modified"], datetime) else local_file["modified"]
            cloud_ts = cloud_file["modified"].timestamp() if isinstance(cloud_file["modified"], datetime) else cloud_file["modified"]
            
            if local_ts > cloud_ts:
                # Local is newer
                if bidirectional:
                    logger.info(f"Conflict resolution: Local is newer for {file_path}")
                    abs_path = os.path.join(local_dir, file_path)
                    try:
                        provider.upload_file(
                            local_path=abs_path,
                            parent_id=provider.get_file_id_from_path(os.path.dirname(cloud_file["path"])),
                            file_name=os.path.basename(file_path)
                        )
                    except Exception as e:
                        logger.error(f"Error resolving conflict (newer wins) for {file_path}: {e}")
            else:
                # Cloud is newer
                logger.info(f"Conflict resolution: Cloud is newer for {file_path}")
                abs_path = os.path.join(local_dir, file_path)
                try:
                    provider.download_file(cloud_file["id"], abs_path)
                except Exception as e:
                    logger.error(f"Error resolving conflict (newer wins) for {file_path}: {e}")
        
        else:  # Default is "rename"
            # Rename conflict handling - keep both versions
            logger.info(f"Conflict resolution: Rename for {file_path}")
            
            # Download cloud version with a conflict suffix
            conflict_name = f"{os.path.splitext(file_path)[0]} (Cloud Conflict){os.path.splitext(file_path)[1]}"
            conflict_path = os.path.join(local_dir, conflict_name)
            
            try:
                provider.download_file(cloud_file["id"], conflict_path)
                logger.info(f"Created conflict copy: {conflict_name}")
            except Exception as e:
                logger.error(f"Error creating conflict copy for {file_path}: {e}")
    
    def _perform_sync(self, local_dir: str, cloud_path: str, provider: CloudProviderPlugin,
                    bidirectional: bool, callback: Optional[Callable]) -> None:
        """
        Perform a single synchronization operation.
        
        Args:
            local_dir: Local directory to synchronize
            cloud_path: Cloud path to synchronize with
            provider: Provider to use for synchronization
            bidirectional: Whether to synchronize in both directions
            callback: Optional callback function for progress updates
        """
        logger.info(f"Performing sync for {provider.provider_name}")
        
        try:
            # Create sync state database or file if it doesn't exist
            sync_state_file = os.path.join(local_dir, '.cloudsync_state.json')
            sync_state = self._load_sync_state(sync_state_file)
            
            # List local files with metadata
            local_files = self._get_local_files(local_dir)
            
            # List cloud files
            cloud_folder_id = provider.get_file_id_from_path(cloud_path)
            cloud_result = provider.list_files(cloud_path)
            cloud_files = cloud_result.get("items", [])
            
            # Build lookup dictionaries
            local_files_by_path = {f["path"]: f for f in local_files}
            cloud_files_by_path = {f["path"]: f for f in cloud_files}
            
            # Track progress
            total_operations = len(local_files) + len(cloud_files)
            completed_operations = 0
            
            # Files to upload (in local but not in cloud)
            files_to_upload = []
            
            # Files to download (in cloud but not in local)
            files_to_download = []
            
            # Files to compare (in both local and cloud)
            files_to_compare = []
            
            # First pass: Build operation lists
            for local_file in local_files:
                local_path = local_file["path"]
                if local_path in cloud_files_by_path:
                    # File exists in both places, add to comparison list
                    files_to_compare.append({
                        "local": local_file,
                        "cloud": cloud_files_by_path[local_path]
                    })
                elif bidirectional:
                    # File only exists locally, add to upload list for bidirectional sync
                    files_to_upload.append(local_file)
            
            for cloud_file in cloud_files:
                if cloud_file["type"] == "file":  # Skip folders
                    cloud_path = cloud_file["path"]
                    if cloud_path not in local_files_by_path:
                        # File only exists in cloud, add to download list
                        files_to_download.append(cloud_file)
            
            # Second pass: Compare files that exist in both places
            for file_pair in files_to_compare:
                local_file = file_pair["local"]
                cloud_file = file_pair["cloud"]
                
                # Get last known sync state
                file_path = local_file["path"]
                last_state = sync_state.get(file_path, {})
                
                # Compare modification times
                local_modified = local_file["modified"]
                cloud_modified = cloud_file["modified"]
                
                # Convert datetime objects to timestamps for comparison
                local_ts = local_modified.timestamp() if isinstance(local_modified, datetime) else local_modified
                cloud_ts = cloud_modified.timestamp() if isinstance(cloud_modified, datetime) else cloud_modified
                
                # Check if either side has been modified since last sync
                last_sync_time = last_state.get("last_sync", 0)
                
                if local_ts > last_sync_time and cloud_ts > last_sync_time:
                    # Both versions modified, handle conflict
                    logger.warning(f"Conflict detected for file: {file_path}")
                    self._handle_conflict(local_file, cloud_file, provider, local_dir, bidirectional)
                elif local_ts > last_sync_time:
                    # Local version is newer, upload if bidirectional
                    if bidirectional:
                        files_to_upload.append(local_file)
                elif cloud_ts > last_sync_time:
                    # Cloud version is newer, download
                    files_to_download.append(cloud_file)
                    
                completed_operations += 1
                if callback:
                    callback(completed_operations, total_operations, f"Comparing files: {file_path}")
            
            # Third pass: Execute operations
            # Upload files to cloud
            for local_file in files_to_upload:
                file_path = local_file["path"]
                abs_path = os.path.join(local_dir, file_path)
                
                # Log the upload operation
                logger.info(f"Uploading file to cloud: {file_path}")
                
                # Report progress
                if callback:
                    callback(completed_operations, total_operations, f"Uploading: {file_path}")
                    
                try:
                    # Upload the file
                    upload_result = provider.upload_file(
                        local_path=abs_path,
                        parent_id=cloud_folder_id,
                        file_name=os.path.basename(file_path)
                    )
                    
                    # Update sync state
                    sync_state[file_path] = {
                        "local_size": local_file["size"],
                        "cloud_id": upload_result["id"],
                        "last_sync": datetime.now().timestamp(),
                        "cloud_path": upload_result["path"]
                    }
                    
                except Exception as e:
                    logger.error(f"Error uploading file {file_path}: {e}")
                    
                completed_operations += 1
            
            # Download files from cloud
            for cloud_file in files_to_download:
                file_path = cloud_file["path"]
                file_id = cloud_file["id"]
                abs_path = os.path.join(local_dir, file_path)
                
                # Ensure directory exists
                os.makedirs(os.path.dirname(abs_path), exist_ok=True)
                
                # Log the download operation
                logger.info(f"Downloading file from cloud: {file_path}")
                
                # Report progress
                if callback:
                    callback(completed_operations, total_operations, f"Downloading: {file_path}")
                    
                try:
                    # Download the file
                    provider.download_file(file_id, abs_path)
                    
                    # Update sync state
                    sync_state[file_path] = {
                        "local_size": os.path.getsize(abs_path),
                        "cloud_id": file_id,
                        "last_sync": datetime.now().timestamp(),
                        "cloud_path": cloud_file["path"]
                    }
                    
                except Exception as e:
                    logger.error(f"Error downloading file {file_path}: {e}")
                    
                completed_operations += 1
            
            # Save updated sync state
            self._save_sync_state(sync_state, sync_state_file)
            
            # Log final counts
            logger.info(f"Sync completed - Local files: {len(local_files)}, Cloud files: {len(cloud_files)}")
            logger.info(f"Uploaded: {len(files_to_upload)}, Downloaded: {len(files_to_download)}, Compared: {len(files_to_compare)}")
            
            # Final callback update
            if callback:
                callback(total_operations, total_operations, "Synchronization completed")
                
        except Exception as e:
            logger.error(f"Error during synchronization: {e}")
            if callback:
                callback(0, 0, f"Error: {str(e)}")