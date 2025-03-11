"""
Test script for the cloud storage plugin framework.

This script tests the functionality of the cloud storage plugins,
focusing on Google Drive integration, authentication, and file operations.

Usage:
    python test_cloud_storage.py [options]
    
Options:
    --provider PROVIDER     Cloud storage provider to test (default: google_drive)
    --list-path PATH        Path to list files from (default: root)
    --upload-file FILE      File to upload for testing
    --download-id ID        File ID to download for testing
    --create-folder NAME    Create a test folder with the given name
    --operation OPERATION   Specific operation to test (list, upload, download, etc.)
"""

import os
import sys
import argparse
import logging
from datetime import datetime
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_cloud_storage")

# Import our cloud storage modules
from ai_document_organizer_v2.core.settings import SettingsManager
from ai_document_organizer_v2.plugins.cloud_storage.provider_base import CloudProviderPlugin, CloudStorageError
from ai_document_organizer_v2.plugins.cloud_storage.google_drive import GoogleDrivePlugin

def print_separator(title: str):
    """Print a separator with a title."""
    width = 80
    print("\n" + "=" * width)
    print(f"{title.center(width)}")
    print("=" * width + "\n")

def print_file_info(info: Dict[str, Any], indent: int = 0):
    """Print file information in a formatted way."""
    indent_str = " " * indent
    
    # Basic properties
    print(f"{indent_str}Name: {info.get('name', 'Unknown')}")
    print(f"{indent_str}ID: {info.get('id', 'Unknown')}")
    print(f"{indent_str}Type: {info.get('type', 'Unknown')}")
    print(f"{indent_str}Path: {info.get('path', 'Unknown')}")
    
    # Size (if available)
    if 'size' in info:
        size = info['size']
        if size < 1024:
            size_str = f"{size} bytes"
        elif size < 1024 * 1024:
            size_str = f"{size / 1024:.2f} KB"
        elif size < 1024 * 1024 * 1024:
            size_str = f"{size / (1024 * 1024):.2f} MB"
        else:
            size_str = f"{size / (1024 * 1024 * 1024):.2f} GB"
        print(f"{indent_str}Size: {size_str}")
    
    # Dates (if available)
    if 'modified' in info and info['modified']:
        print(f"{indent_str}Modified: {info['modified'].strftime('%Y-%m-%d %H:%M:%S')}")
    if 'created' in info and info['created']:
        print(f"{indent_str}Created: {info['created'].strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Web URL (if available)
    if 'web_url' in info and info['web_url']:
        print(f"{indent_str}Web URL: {info['web_url']}")
    
    # Thumbnail (if available)
    if 'thumbnail_url' in info and info['thumbnail_url']:
        print(f"{indent_str}Thumbnail: {info['thumbnail_url']}")
    
    # MIME type (if available)
    if 'mime_type' in info and info['mime_type']:
        print(f"{indent_str}MIME Type: {info['mime_type']}")
    
    # Sharing status (if available)
    if 'shared' in info:
        print(f"{indent_str}Shared: {'Yes' if info['shared'] else 'No'}")
    
    # Provider-specific info (simplified)
    if 'provider_info' in info and info['provider_info']:
        print(f"{indent_str}Provider Info: {', '.join(info['provider_info'].keys())}")

def test_list_files(provider: CloudProviderPlugin, path: str = ""):
    """Test listing files from a path."""
    print_separator(f"Listing Files from {path or 'Root'}")
    
    try:
        # List files
        result = provider.list_files(path)
        
        # Print results
        print(f"Found {len(result['items'])} items")
        
        for i, item in enumerate(result['items']):
            print(f"\nItem {i+1}:")
            print_file_info(item, indent=2)
        
        # Check for pagination
        if result.get('has_more', False):
            print(f"\nMore items available, next page token: {result.get('next_page_token')}")
        
        return True
    except CloudStorageError as e:
        logger.error(f"Error listing files: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False

def test_upload_file(provider: CloudProviderPlugin, local_path: str, parent_path: str = ""):
    """Test uploading a file."""
    print_separator(f"Uploading File: {local_path}")
    
    if not os.path.exists(local_path):
        logger.error(f"File not found: {local_path}")
        return False
    
    try:
        # Get parent ID from path
        parent_id = "root"  # Default to root
        if parent_path:
            parent_id = provider.get_file_id_from_path(parent_path)
        
        def progress_callback(current, total, message):
            """Progress callback function."""
            percent = int(current / total * 100)
            bar_length = 30
            filled_length = int(bar_length * current // total)
            bar = '█' * filled_length + '-' * (bar_length - filled_length)
            print(f"\r[{bar}] {percent}% {message}", end='', flush=True)
        
        # Upload the file
        file_name = os.path.basename(local_path)
        print(f"Uploading {file_name} to parent ID: {parent_id}")
        
        result = provider.upload_file(
            local_path=local_path,
            parent_id=parent_id,
            callback=progress_callback
        )
        
        print("\n\nUpload completed successfully!")
        print("\nFile information:")
        print_file_info(result, indent=2)
        
        return True
    except CloudStorageError as e:
        logger.error(f"Error uploading file: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False

def test_download_file(provider: CloudProviderPlugin, file_id: str, output_dir: str = "."):
    """Test downloading a file."""
    print_separator(f"Downloading File: {file_id}")
    
    try:
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Get file info
        file_info = provider.get_file_info(file_id)
        file_name = file_info.get('name', 'downloaded_file')
        
        # Prepare output path
        output_path = os.path.join(output_dir, file_name)
        
        # Progress callback
        def progress_callback(current, total, message):
            """Progress callback function."""
            percent = int(current / total * 100)
            bar_length = 30
            filled_length = int(bar_length * current // total)
            bar = '█' * filled_length + '-' * (bar_length - filled_length)
            print(f"\r[{bar}] {percent}% {message}", end='', flush=True)
        
        # Download the file
        print(f"Downloading {file_name} to {output_path}")
        
        success = provider.download_file(
            file_id=file_id,
            local_path=output_path,
            callback=progress_callback
        )
        
        print("\n\nDownload completed successfully!")
        print(f"File saved to: {output_path}")
        
        # Verify file exists
        if os.path.exists(output_path):
            size = os.path.getsize(output_path)
            print(f"File size: {size} bytes")
        
        return True
    except CloudStorageError as e:
        logger.error(f"Error downloading file: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False

def test_create_folder(provider: CloudProviderPlugin, folder_name: str, parent_path: str = ""):
    """Test creating a folder."""
    print_separator(f"Creating Folder: {folder_name}")
    
    try:
        # Get parent ID from path
        parent_id = "root"  # Default to root
        if parent_path:
            parent_id = provider.get_file_id_from_path(parent_path)
        
        # Create the folder
        print(f"Creating folder {folder_name} in parent ID: {parent_id}")
        
        result = provider.create_folder(
            name=folder_name,
            parent_id=parent_id
        )
        
        print("Folder created successfully!")
        print("\nFolder information:")
        print_file_info(result, indent=2)
        
        return True
    except CloudStorageError as e:
        logger.error(f"Error creating folder: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False

def test_account_info(provider: CloudProviderPlugin):
    """Test getting account information."""
    print_separator("Account Information")
    
    try:
        # Get account info
        info = provider.get_account_info()
        
        # Print user info
        user = info.get('user', {})
        print("User Information:")
        print(f"  Name: {user.get('name', 'Unknown')}")
        print(f"  Email: {user.get('email', 'Unknown')}")
        print(f"  ID: {user.get('id', 'Unknown')}")
        
        # Print storage info
        storage = info.get('storage', {})
        total_gb = storage.get('total', 0) / (1024 * 1024 * 1024)
        used_gb = storage.get('used', 0) / (1024 * 1024 * 1024)
        available_gb = storage.get('available', 0) / (1024 * 1024 * 1024)
        
        print("\nStorage Information:")
        print(f"  Total: {total_gb:.2f} GB")
        print(f"  Used: {used_gb:.2f} GB")
        print(f"  Available: {available_gb:.2f} GB")
        print(f"  Usage: {(used_gb / total_gb * 100) if total_gb > 0 else 0:.2f}%")
        
        # Print plan info
        plan = info.get('plan', {})
        print("\nPlan Information:")
        print(f"  Name: {plan.get('name', 'Unknown')}")
        print(f"  Type: {plan.get('type', 'Unknown')}")
        
        return True
    except CloudStorageError as e:
        logger.error(f"Error getting account info: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False

def test_search_files(provider: CloudProviderPlugin, query: str, file_type: str = None):
    """Test searching for files."""
    print_separator(f"Searching Files: {query}")
    
    try:
        # Search for files
        results = provider.search_files(
            query=query,
            file_type=file_type,
            max_results=10
        )
        
        # Print results
        print(f"Found {len(results)} items matching '{query}'")
        
        for i, item in enumerate(results):
            print(f"\nItem {i+1}:")
            print_file_info(item, indent=2)
        
        return True
    except CloudStorageError as e:
        logger.error(f"Error searching files: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Test cloud storage plugins")
    
    # Provider selection
    parser.add_argument('--provider', default='google_drive',
                      choices=['google_drive'],
                      help='Cloud storage provider to test')
    
    # Operations
    parser.add_argument('--operation', 
                      choices=['list', 'upload', 'download', 'create-folder', 'account-info', 'search', 'all'],
                      default='list',
                      help='Operation to test')
    
    # Operation parameters
    parser.add_argument('--list-path', default='',
                      help='Path to list files from')
    
    parser.add_argument('--upload-file', 
                      help='Local file to upload')
    
    parser.add_argument('--download-id',
                      help='File ID to download')
    
    parser.add_argument('--parent-path', default='',
                      help='Parent path for operations that need it')
    
    parser.add_argument('--folder-name', default='Test Folder',
                      help='Folder name for create-folder operation')
    
    parser.add_argument('--search-query', default='document',
                      help='Query for search operation')
    
    parser.add_argument('--file-type',
                      help='File type filter for search operation')
    
    parser.add_argument('--credentials-file',
                      help='Path to credentials file')
    
    parser.add_argument('--token-file',
                      help='Path to token file')
    
    return parser.parse_args()

def create_provider(provider_name: str, args):
    """Create the appropriate provider instance."""
    if provider_name == 'google_drive':
        provider = GoogleDrivePlugin()
    else:
        raise ValueError(f"Unsupported provider: {provider_name}")
    
    # Create settings manager
    settings = SettingsManager()
    provider.settings_manager = settings
    
    # Configure provider from arguments
    if args.credentials_file:
        provider.config["credentials_file"] = args.credentials_file
    
    if args.token_file:
        provider.config["token_file"] = args.token_file
    
    # Initialize the provider
    if not provider.initialize():
        raise RuntimeError(f"Failed to initialize {provider_name} provider")
    
    # Authenticate with the provider
    if not provider.authenticate():
        raise RuntimeError(f"Failed to authenticate with {provider_name}")
    
    return provider

def main():
    """Main function."""
    args = parse_args()
    
    try:
        # Create the provider
        provider = create_provider(args.provider, args)
        
        print_separator(f"Testing {provider.provider_name} Cloud Storage Plugin")
        
        # Run the requested operation
        if args.operation == 'list' or args.operation == 'all':
            test_list_files(provider, args.list_path)
        
        if args.operation == 'upload' or args.operation == 'all':
            if args.upload_file:
                test_upload_file(provider, args.upload_file, args.parent_path)
            else:
                print("No upload file specified, skipping upload test")
        
        if args.operation == 'download' or args.operation == 'all':
            if args.download_id:
                test_download_file(provider, args.download_id)
            else:
                print("No download ID specified, skipping download test")
        
        if args.operation == 'create-folder' or args.operation == 'all':
            test_create_folder(provider, args.folder_name, args.parent_path)
        
        if args.operation == 'account-info' or args.operation == 'all':
            test_account_info(provider)
        
        if args.operation == 'search' or args.operation == 'all':
            test_search_files(provider, args.search_query, args.file_type)
        
        print_separator("Tests Completed Successfully")
        
    except Exception as e:
        logger.error(f"Error running tests: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()