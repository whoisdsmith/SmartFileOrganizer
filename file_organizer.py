import os
import shutil
from pathlib import Path
import logging

from utils import sanitize_filename

class FileOrganizer:
    """
    Class responsible for organizing files based on AI analysis
    """
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def organize_files(self, analyzed_files, target_dir):
        """
        Organize files based on their AI analysis
        
        Args:
            analyzed_files: List of file information dictionaries with AI analysis
            target_dir: Target directory for organized files
            
        Returns:
            Dictionary with organization results
        """
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
        
        result = {
            "success": 0,
            "failed": 0,
            "failed_files": []
        }
        
        # Create category directories first
        categories = set()
        for file_info in analyzed_files:
            if "category" in file_info and file_info["category"]:
                categories.add(file_info["category"])
        
        # Create category directories
        for category in categories:
            category_dir = os.path.join(target_dir, sanitize_filename(category))
            if not os.path.exists(category_dir):
                os.makedirs(category_dir)
        
        # Now organize files
        for file_info in analyzed_files:
            try:
                source_path = file_info["path"]
                
                # Skip if source doesn't exist
                if not os.path.exists(source_path):
                    result["failed"] += 1
                    result["failed_files"].append(file_info["filename"])
                    continue
                
                # Determine target directory and filename
                if "category" in file_info and file_info["category"]:
                    category_dir = sanitize_filename(file_info["category"])
                    file_target_dir = os.path.join(target_dir, category_dir)
                else:
                    file_target_dir = os.path.join(target_dir, "Uncategorized")
                    
                # Create directory if it doesn't exist
                if not os.path.exists(file_target_dir):
                    os.makedirs(file_target_dir)
                
                # Create target filename
                target_filename = file_info["filename"]
                target_path = os.path.join(file_target_dir, target_filename)
                
                # Handle duplicate filenames
                counter = 1
                while os.path.exists(target_path):
                    file_name, file_ext = os.path.splitext(target_filename)
                    target_filename = f"{file_name}_{counter}{file_ext}"
                    target_path = os.path.join(file_target_dir, target_filename)
                    counter += 1
                
                # Copy the file
                shutil.copy2(source_path, target_path)
                result["success"] += 1
                
                # Create metadata file with AI analysis
                self._create_metadata_file(file_info, target_path)
                
            except Exception as e:
                self.logger.error(f"Error organizing file {file_info.get('filename', '')}: {str(e)}")
                result["failed"] += 1
                result["failed_files"].append(file_info.get("filename", "Unknown"))
        
        return result
    
    def _create_metadata_file(self, file_info, target_path):
        """
        Create a metadata file with AI analysis next to the original file
        
        Args:
            file_info: File information dictionary
            target_path: Path where the file was copied
        """
        try:
            metadata_path = f"{target_path}.meta.txt"
            
            with open(metadata_path, 'w', encoding='utf-8') as f:
                f.write(f"Filename: {file_info.get('filename', '')}\n")
                f.write(f"Original Path: {file_info.get('path', '')}\n")
                f.write(f"Type: {file_info.get('file_type', '')}\n")
                f.write(f"Size: {file_info.get('size', 0)} bytes\n")
                f.write(f"Category: {file_info.get('category', '')}\n")
                
                if 'keywords' in file_info:
                    f.write(f"Keywords: {', '.join(file_info['keywords'])}\n")
                
                if 'summary' in file_info:
                    f.write(f"\nSummary:\n{file_info['summary']}\n")
                
                if 'metadata' in file_info:
                    f.write("\nMetadata:\n")
                    for key, value in file_info['metadata'].items():
                        f.write(f"- {key}: {value}\n")
        except Exception as e:
            self.logger.error(f"Error creating metadata file for {target_path}: {str(e)}")
