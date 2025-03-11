"""
Test script for the cloud storage synchronization functionality.

This script tests the bidirectional synchronization capabilities of the 
cloud storage framework, verifying file uploads, downloads, and conflict resolution.

Usage:
    python test_cloud_sync.py [options]
    
Options:
    --provider PROVIDER    Cloud storage provider to test (default: google_drive)
    --local-dir DIR        Local directory for synchronization testing (default: ./sync_test)
    --cloud-path PATH      Cloud path for synchronization testing (default: /sync_test)
    --bidirectional        Enable bidirectional synchronization (default: False)
    --interval SECONDS     Synchronization interval in seconds (default: 60)
"""

import os
import sys
import time
import argparse
import logging
import tempfile
import shutil
from datetime import datetime
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_cloud_sync")

# Import our cloud storage modules
from ai_document_organizer_v2.core.settings import SettingsManager
from ai_document_organizer_v2.plugins.cloud_storage.provider_base import CloudProviderPlugin, CloudStorageError
from ai_document_organizer_v2.plugins.cloud_storage.google_drive import GoogleDrivePlugin
from ai_document_organizer_v2.plugins.cloud_storage.storage_manager import CloudStorageManager

def print_separator(title: str):
    """Print a separator with a title."""
    width = 80
    print("\n" + "=" * width)
    print(f"{title.center(width)}")
    print("=" * width + "\n")

def create_test_files(dir_path: str, count: int = 5) -> List[str]:
    """Create test files in a directory."""
    os.makedirs(dir_path, exist_ok=True)
    
    created_files = []
    for i in range(count):
        file_path = os.path.join(dir_path, f"test_file_{i}.txt")
        with open(file_path, "w") as f:
            f.write(f"Test file {i} content\nCreated at {datetime.now().isoformat()}\n")
        created_files.append(file_path)
        
    return created_files

def modify_test_file(file_path: str) -> None:
    """Modify a test file to simulate changes."""
    with open(file_path, "a") as f:
        f.write(f"Modified at {datetime.now().isoformat()}\n")

def setup_test_environment(local_dir: str) -> None:
    """Set up the test environment for synchronization testing."""
    # Create local directory if it doesn't exist
    os.makedirs(local_dir, exist_ok=True)
    
    # Create test files
    create_test_files(local_dir)
    
    # Create subdirectories with files
    subdir1 = os.path.join(local_dir, "subdir1")
    subdir2 = os.path.join(local_dir, "subdir2")
    
    create_test_files(subdir1, 3)
    create_test_files(subdir2, 3)

def progress_callback(current: int, total: int, message: str) -> None:
    """Progress callback function for synchronization operations."""
    if total > 0:
        progress = (current / total) * 100
        print(f"Progress: {progress:.1f}% ({current}/{total}) - {message}")
    else:
        print(f"Progress: {message}")

def test_cloud_sync(provider_name: str, local_dir: str, cloud_path: str, 
                   bidirectional: bool = False, interval: int = 60) -> None:
    """Test cloud storage synchronization functionality."""
    print_separator(f"Testing Cloud Sync with {provider_name}")
    
    # Set up test environment
    setup_test_environment(local_dir)
    print(f"Set up test environment in {local_dir}")
    
    # Create settings manager
    settings = SettingsManager()
    
    # Create cloud provider
    if provider_name == "google_drive":
        provider = GoogleDrivePlugin("google_drive_plugin", "Google Drive", "1.0.0")
        provider.settings_manager = settings
    else:
        raise ValueError(f"Unsupported provider: {provider_name}")
    
    # Create cloud storage manager
    manager = CloudStorageManager()
    manager.add_provider(provider_name, provider)
    manager.set_active_provider(provider_name)
    
    try:
        # Authenticate
        print("Authenticating with cloud provider...")
        if not provider.authenticate():
            print("Authentication failed. Please check your credentials and try again.")
            return
        
        # Create remote test folder if it doesn't exist
        print(f"Creating remote test folder: {cloud_path}")
        try:
            # Check if folder exists first
            folder_id = provider.get_file_id_from_path(cloud_path)
            print(f"Remote folder already exists with ID: {folder_id}")
        except Exception:
            # Create folder
            folder_parts = cloud_path.strip('/').split('/')
            current_path = ""
            parent_id = "root"
            
            for folder in folder_parts:
                if not folder:
                    continue
                    
                # Check if this folder exists
                try:
                    # Try to get folder ID
                    current_path += f"/{folder}" if current_path else f"{folder}"
                    folder_id = provider.get_file_id_from_path(current_path)
                    parent_id = folder_id
                except Exception:
                    # Create the folder
                    result = provider.create_folder(folder, parent_id)
                    parent_id = result["id"]
                    print(f"Created folder: {folder} with ID: {parent_id}")
            
            folder_id = parent_id
        
        # Start synchronization
        print(f"Starting synchronization (bidirectional={bidirectional})...")
        manager.start_sync(
            local_dir=local_dir,
            cloud_path=cloud_path,
            provider_name=provider_name,
            bidirectional=bidirectional,
            interval=interval,
            callback=progress_callback
        )
        
        # Wait for initial sync to complete
        print("Waiting for initial synchronization to complete...")
        time.sleep(10)
        
        # List files after initial sync
        print("\nLocal files after initial sync:")
        for root, dirs, files in os.walk(local_dir):
            for file in files:
                if not file.startswith('.'):  # Skip hidden files
                    print(f"  {os.path.relpath(os.path.join(root, file), local_dir)}")
        
        # Modify a file and create a new one to test sync
        test_file = os.path.join(local_dir, "test_file_0.txt")
        if os.path.exists(test_file):
            print(f"\nModifying local file: {test_file}")
            modify_test_file(test_file)
        
        new_file = os.path.join(local_dir, "new_after_sync.txt")
        print(f"Creating new local file: {new_file}")
        with open(new_file, "w") as f:
            f.write(f"New file created after sync at {datetime.now().isoformat()}\n")
        
        # Simulate changes from cloud by directly uploading a file
        remote_change_file = os.path.join(tempfile.gettempdir(), "remote_change.txt")
        with open(remote_change_file, "w") as f:
            f.write(f"File created directly in cloud at {datetime.now().isoformat()}\n")
        
        print(f"\nUploading file directly to cloud: {remote_change_file}")
        provider.upload_file(
            local_path=remote_change_file,
            parent_id=folder_id,
            file_name="remote_change.txt"
        )
        
        # Wait for sync
        print("\nWaiting for sync to detect changes (15 seconds)...")
        time.sleep(15)
        
        # Trigger manual sync
        print("Triggering manual sync...")
        manager.sync_now(provider_name)
        
        # Wait for sync to complete
        print("Waiting for manual sync to complete...")
        time.sleep(10)
        
        # List files after changes
        print("\nLocal files after changes:")
        for root, dirs, files in os.walk(local_dir):
            for file in files:
                if not file.startswith('.'):  # Skip hidden files
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, local_dir)
                    size = os.path.getsize(file_path)
                    print(f"  {rel_path} ({size} bytes)")
        
        # Test conflict resolution
        if bidirectional:
            print("\nTesting conflict resolution...")
            
            # Create a file with same name in both locations
            conflict_file_local = os.path.join(local_dir, "conflict_test.txt")
            with open(conflict_file_local, "w") as f:
                f.write(f"Local version of conflict file created at {datetime.now().isoformat()}\n")
            
            # Upload a different version directly
            conflict_file_remote = os.path.join(tempfile.gettempdir(), "conflict_test.txt")
            with open(conflict_file_remote, "w") as f:
                f.write(f"Remote version of conflict file created at {datetime.now().isoformat()}\n")
            
            print(f"Creating conflict file in cloud: {conflict_file_remote}")
            provider.upload_file(
                local_path=conflict_file_remote,
                parent_id=folder_id,
                file_name="conflict_test.txt"
            )
            
            # Wait for sync to detect conflict
            print("Waiting for sync to detect conflict (15 seconds)...")
            time.sleep(15)
            
            # Trigger manual sync
            print("Triggering manual sync...")
            manager.sync_now(provider_name)
            
            # Wait for sync to complete
            print("Waiting for manual sync to complete...")
            time.sleep(10)
            
            # Check for conflict resolution
            print("\nLocal files after conflict resolution:")
            for root, dirs, files in os.walk(local_dir):
                for file in files:
                    if not file.startswith('.') and "conflict" in file.lower():
                        file_path = os.path.join(root, file)
                        rel_path = os.path.relpath(file_path, local_dir)
                        with open(file_path, "r") as f:
                            content = f.read().strip()
                        print(f"  {rel_path}:")
                        print(f"    Content: {content[:50]}...")
        
        # Stop synchronization
        print("\nStopping synchronization...")
        manager.stop_sync()
        
        print("\nCloud synchronization test completed successfully!")
        
    except Exception as e:
        print(f"Error during cloud sync test: {e}")
        manager.stop_sync()
    finally:
        # Cleanup if needed
        pass

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Test cloud storage synchronization")
    
    parser.add_argument("--provider", default="google_drive",
                       help="Cloud storage provider to test (default: google_drive)")
    parser.add_argument("--local-dir", default="./sync_test",
                       help="Local directory for synchronization testing (default: ./sync_test)")
    parser.add_argument("--cloud-path", default="/sync_test",
                       help="Cloud path for synchronization testing (default: /sync_test)")
    parser.add_argument("--bidirectional", action="store_true",
                       help="Enable bidirectional synchronization")
    parser.add_argument("--interval", type=int, default=60,
                       help="Synchronization interval in seconds (default: 60)")
    
    return parser.parse_args()

def main():
    """Main function."""
    args = parse_args()
    
    # Create absolute path for local directory
    local_dir = os.path.abspath(args.local_dir)
    
    # Run the test
    test_cloud_sync(
        provider_name=args.provider,
        local_dir=local_dir,
        cloud_path=args.cloud_path,
        bidirectional=args.bidirectional,
        interval=args.interval
    )

if __name__ == "__main__":
    main()