import os
import re
import shutil
import time
from pathlib import Path
import logging

from utils import sanitize_filename

class FileOrganizer:
    """
    Class responsible for organizing files based on AI analysis
    """
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def organize_files(self, analyzed_files, target_dir, callback=None, options=None):
        """
        Organize files based on their AI analysis
        
        Args:
            analyzed_files: List of file information dictionaries with AI analysis
            target_dir: Target directory for organized files
            callback: Optional callback function for progress updates, takes (current, total, filename)
            options: Dictionary with organization options
                - create_category_folders: Whether to create category folders (default: True)
                - generate_summaries: Whether to generate content summary files (default: True)
                - include_metadata: Whether to create metadata files (default: True)
                - copy_instead_of_move: Whether to copy files instead of moving them (default: True)
            
        Returns:
            Dictionary with organization results
        """
        # Default options
        default_options = {
            "create_category_folders": True,
            "generate_summaries": True,
            "include_metadata": True,
            "copy_instead_of_move": True
        }
        
        # Use provided options or defaults
        if options is None:
            options = default_options
        else:
            # Merge with defaults for any missing options
            for key, value in default_options.items():
                if key not in options:
                    options[key] = value
        
        self.logger.info(f"Organizing files with options: {options}")
                
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
        
        result = {
            "success": 0,
            "failed": 0,
            "failed_files": []
        }
        
        # Create category directories first (if enabled)
        if options["create_category_folders"]:
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
        total_files = len(analyzed_files)
        for index, file_info in enumerate(analyzed_files):
            try:
                source_path = file_info["path"]
                
                # Update progress if callback provided
                if callback:
                    callback(index, total_files, source_path)
                
                # Skip if source doesn't exist
                if not os.path.exists(source_path):
                    result["failed"] += 1
                    result["failed_files"].append(file_info["filename"])
                    continue
                
                # Determine target directory and filename
                if options["create_category_folders"] and "category" in file_info and file_info["category"]:
                    category_dir = sanitize_filename(file_info["category"])
                    file_target_dir = os.path.join(target_dir, category_dir)
                else:
                    # If category folders disabled, put directly in target dir
                    file_target_dir = target_dir
                    
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
                
                # Copy or move the file based on options
                if options["copy_instead_of_move"]:
                    shutil.copy2(source_path, target_path)
                else:
                    shutil.move(source_path, target_path)
                
                result["success"] += 1
                
                # Create metadata file with AI analysis if enabled
                if options["include_metadata"]:
                    self._create_metadata_file(file_info, target_path)
                
                # Create content summary file if enabled
                if options["generate_summaries"] and "summary" in file_info and file_info["summary"]:
                    self._create_summary_file(file_info, target_path)
                
            except Exception as e:
                self.logger.error(f"Error organizing file {file_info.get('filename', '')}: {str(e)}")
                result["failed"] += 1
                result["failed_files"].append(file_info.get("filename", "Unknown"))
        
        # Final callback with completed status
        if callback and total_files > 0:
            callback(total_files, total_files, "Completed")
            
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
            
    def _create_summary_file(self, file_info, target_path):
        """
        Create a separate summary file with content summary
        
        Args:
            file_info: File information dictionary
            target_path: Path where the file was copied
        """
        try:
            file_name, file_ext = os.path.splitext(target_path)
            summary_path = f"{file_name}_summary.txt"
            
            with open(summary_path, 'w', encoding='utf-8') as f:
                # Add file info header
                f.write(f"# Summary of {file_info.get('filename', '')}\n\n")
                
                # Add category and keywords if available
                if 'category' in file_info and file_info['category']:
                    f.write(f"Category: {file_info['category']}\n")
                
                if 'keywords' in file_info and file_info['keywords']:
                    f.write(f"Keywords: {', '.join(file_info['keywords'])}\n\n")
                
                # Add the main summary content
                if 'summary' in file_info and file_info['summary']:
                    f.write(f"## Content Summary\n\n{file_info['summary']}\n\n")
                else:
                    f.write("No summary available for this file.\n\n")
                
                # Add AI analysis note
                f.write("---\n")
                f.write("Generated by AI Document Organizer using Google Gemini Flash 2.0\n")
                f.write(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                
            self.logger.info(f"Created summary file: {summary_path}")
        except Exception as e:
            self.logger.error(f"Error creating summary file for {target_path}: {str(e)}")
            
    def generate_folder_report(self, folder_path, include_summaries=True):
        """
        Generate a report of the folder contents with AI analysis
        
        Args:
            folder_path: Path to the folder for which to generate the report
            include_summaries: Whether to include content summaries in the report
            
        Returns:
            Path to the generated report file
        """
        try:
            if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
                self.logger.error(f"Invalid folder path for report: {folder_path}")
                return None
                
            # Get the folder name for the report title
            folder_name = os.path.basename(folder_path)
            report_path = os.path.join(folder_path, f"{folder_name}_Report.md")
            
            # Collect information about files in the folder and subfolders
            file_data = []
            category_stats = {}
            total_files = 0
            
            # Walk through the directory structure
            for root, dirs, files in os.walk(folder_path):
                # Skip metadata and summary files
                files = [f for f in files if not f.endswith('.meta.txt') and not f.endswith('_summary.txt') and not f.endswith('_Report.md')]
                
                for file in files:
                    total_files += 1
                    file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(file_path, folder_path)
                    
                    # Check if metadata file exists
                    meta_path = f"{file_path}.meta.txt"
                    file_info = {"filename": file, "path": relative_path}
                    
                    if os.path.exists(meta_path):
                        # Extract category and other info from metadata
                        with open(meta_path, 'r', encoding='utf-8') as mf:
                            meta_content = mf.read()
                            
                            # Extract category
                            category_match = re.search(r'Category:\s*(.+?)$', meta_content, re.MULTILINE)
                            if category_match:
                                category = category_match.group(1).strip()
                                file_info["category"] = category
                                
                                # Update category statistics
                                if category in category_stats:
                                    category_stats[category] += 1
                                else:
                                    category_stats[category] = 1
                            
                            # Extract keywords
                            keywords_match = re.search(r'Keywords:\s*(.+?)$', meta_content, re.MULTILINE)
                            if keywords_match:
                                keywords = keywords_match.group(1).strip()
                                file_info["keywords"] = keywords
                            
                            # Extract summary if needed
                            if include_summaries:
                                summary_match = re.search(r'Summary:\s*\n(.*?)(?:\n\n|\nMetadata:|$)', meta_content, re.DOTALL)
                                if summary_match:
                                    summary = summary_match.group(1).strip()
                                    file_info["summary"] = summary
                    
                    file_data.append(file_info)
            
            # Generate the report
            with open(report_path, 'w', encoding='utf-8') as f:
                # Report header
                f.write(f"# Folder Content Report: {folder_name}\n\n")
                f.write(f"Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write(f"Total files: {total_files}\n\n")
                
                # Category statistics
                f.write("## Category Distribution\n\n")
                if category_stats:
                    for category, count in sorted(category_stats.items(), key=lambda x: x[1], reverse=True):
                        percentage = (count / total_files) * 100
                        f.write(f"- **{category}**: {count} files ({percentage:.1f}%)\n")
                else:
                    f.write("No category information available.\n")
                
                f.write("\n## File List\n\n")
                
                # Group files by category
                by_category = {}
                for file_info in file_data:
                    category = file_info.get("category", "Uncategorized")
                    if category not in by_category:
                        by_category[category] = []
                    by_category[category].append(file_info)
                
                # List files by category
                for category, files in sorted(by_category.items()):
                    f.write(f"### {category}\n\n")
                    
                    for file_info in sorted(files, key=lambda x: x["filename"]):
                        f.write(f"#### {file_info['filename']}\n\n")
                        f.write(f"Path: {file_info['path']}\n\n")
                        
                        if "keywords" in file_info:
                            f.write(f"Keywords: {file_info['keywords']}\n\n")
                            
                        if include_summaries and "summary" in file_info:
                            f.write(f"Summary:\n{file_info['summary']}\n\n")
                        
                        f.write("---\n\n")
                
                # Footer
                f.write("\n## About this Report\n\n")
                f.write("This report was automatically generated by AI Document Organizer using Google Gemini Flash 2.0 AI analysis.\n")
                f.write("The content categorization and summaries are AI-generated and may require human verification for critical information.\n")
            
            self.logger.info(f"Generated folder report: {report_path}")
            return report_path
            
        except Exception as e:
            self.logger.error(f"Error generating folder report: {str(e)}")
            return None
