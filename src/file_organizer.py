import os
import re
import shutil
import time
from pathlib import Path
import logging

from .utils import sanitize_filename
from .ai_analyzer import AIAnalyzer
from .duplicate_detector import DuplicateDetector
from .tag_manager import TagManager


class FileOrganizer:
    """
    Class responsible for organizing files based on AI analysis
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.ai_analyzer = AIAnalyzer()
        self.duplicate_detector = DuplicateDetector()
        self.tag_manager = TagManager()

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
                - detect_duplicates: Whether to detect and handle duplicates (default: False)
                - duplicate_action: Action to take for duplicates ('report', 'move', 'delete') (default: 'report')
                - duplicate_strategy: Strategy for keeping files ('newest', 'oldest', 'largest', 'smallest') (default: 'newest')
                - apply_tags: Whether to apply tags to files (default: False)
                - suggest_tags: Whether to suggest tags based on content (default: False)

        Returns:
            Dictionary with organization results
        """
        # Default options
        default_options = {
            "create_category_folders": True,
            "generate_summaries": True,
            "include_metadata": True,
            "copy_instead_of_move": True,
            "detect_duplicates": False,
            "duplicate_action": "report",
            "duplicate_strategy": "newest",
            "apply_tags": False,
            "suggest_tags": False
        }

        # Use provided options or defaults
        if options is None:
            options = default_options
        else:
            # Merge with defaults for any missing options
            for key, value in default_options.items():
                if key not in options:
                    options[key] = value

        # Create target directory if it doesn't exist
        os.makedirs(target_dir, exist_ok=True)

        # Track results
        results = {
            "organized_count": 0,
            "failed_count": 0,
            "failed_files": [],
            "categories": {},
            "processed": [],
            "metadata_files": [],
            "summary_files": [],
            "errors": [],
            "duplicates": {}
        }

        total_files = len(analyzed_files)

        # Process each file
        for index, file_info in enumerate(analyzed_files):
            try:
                # Check if operation was cancelled
                if callback:
                    should_continue = callback(
                        index, total_files, file_info.get("path", "Unknown file"))
                    if should_continue is False:
                        self.logger.info("Organization cancelled by user")
                        break

                # Get file information
                file_path = file_info.get("path")
                if not file_path or not os.path.exists(file_path):
                    self.logger.warning(f"File not found: {file_path}")
                    results["failed_count"] += 1
                    results["failed_files"].append(file_path)
                    continue

                # Get file category from AI analysis
                category = file_info.get("category", "Uncategorized")

                # Create category folder if needed
                category_dir = target_dir
                if options["create_category_folders"]:
                    category_dir = os.path.join(target_dir, category)
                    os.makedirs(category_dir, exist_ok=True)

                    # Track categories
                    if category not in results["categories"]:
                        results["categories"][category] = 0
                    results["categories"][category] += 1

                # Get file name and extension
                file_name = os.path.basename(file_path)

                # Create target path
                target_path = os.path.join(category_dir, file_name)

                # Handle file name conflicts
                if os.path.exists(target_path):
                    base_name, ext = os.path.splitext(file_name)
                    counter = 1
                    while os.path.exists(target_path):
                        new_name = f"{base_name}_{counter}{ext}"
                        target_path = os.path.join(category_dir, new_name)
                        counter += 1

                # Copy or move the file
                if options["copy_instead_of_move"]:
                    shutil.copy2(file_path, target_path)
                    self.logger.info(f"Copied {file_path} to {target_path}")
                else:
                    shutil.move(file_path, target_path)
                    self.logger.info(f"Moved {file_path} to {target_path}")

                # Create metadata file if requested
                if options["include_metadata"]:
                    self._create_metadata_file(file_info, target_path)

                # Create summary file if requested
                if options["generate_summaries"]:
                    self._create_summary_file(file_info, target_path)

                # Apply tags if requested
                if options['apply_tags']:
                    # Apply category as a tag
                    if category and category != 'Uncategorized':
                        self.tag_manager.add_tag_to_file(
                            target_path, category, confidence=1.0, is_ai_suggested=False)

                    # Apply AI-suggested tags if available
                    if 'tags' in file_info and file_info['tags']:
                        for tag in file_info['tags']:
                            self.tag_manager.add_tag_to_file(
                                target_path, tag, confidence=0.9, is_ai_suggested=True)

                    # Suggest additional tags based on content if requested
                    if options['suggest_tags']:
                        tag_suggestions = self.tag_manager.get_tag_suggestions(
                            file_info)
                        # Limit to top 5 suggestions
                        for suggestion in tag_suggestions[:5]:
                            self.tag_manager.add_tag_to_file(
                                target_path,
                                suggestion['name'],
                                confidence=suggestion['confidence'],
                                is_ai_suggested=True
                            )

                # Update success count
                results["organized_count"] += 1

                # Update progress
                if callback:
                    should_continue = callback(
                        index + 1, total_files, file_path)
                    if should_continue is False:
                        self.logger.info("Organization cancelled by user")
                        break

            except Exception as e:
                self.logger.error(
                    f"Error organizing file {file_info.get('path')}: {str(e)}")
                results["failed_count"] += 1
                results["failed_files"].append(file_info.get("path"))

        # Detect and handle duplicates if requested
        if options['detect_duplicates']:
            # Get all processed files
            processed_files = [result['target']
                               for result in results['processed']]

            # Detect duplicates
            duplicate_groups = self.duplicate_detector.find_duplicates(
                processed_files)

            if duplicate_groups:
                # Handle duplicates
                duplicate_results = self.duplicate_detector.handle_duplicates(
                    duplicate_groups,
                    action=options['duplicate_action'],
                    target_dir=os.path.join(target_dir, 'Duplicates'),
                    keep_strategy=options['duplicate_strategy']
                )

                results['duplicates'] = duplicate_results

        return results

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

                if 'theme' in file_info:
                    f.write(f"Theme: {file_info.get('theme', '')}\n")

                if 'keywords' in file_info:
                    f.write(f"Keywords: {', '.join(file_info['keywords'])}\n")

                if 'summary' in file_info:
                    f.write(f"\nSummary:\n{file_info['summary']}\n")

                # Include relationship information if available
                if 'related_documents' in file_info and file_info['related_documents']:
                    f.write("\nRelated Documents:\n")
                    for doc in file_info['related_documents'][:3]:  # Limit to top 3
                        rel_strength = doc.get(
                            'relationship_strength', 'medium')
                        rel_explanation = doc.get(
                            'relationship_explanation', '')
                        f.write(
                            f"- {doc.get('filename', '')}: {rel_strength.capitalize()} relationship")
                        if rel_explanation:
                            f.write(f" - {rel_explanation}")
                        f.write("\n")

                if 'metadata' in file_info:
                    f.write("\nMetadata:\n")
                    for key, value in file_info['metadata'].items():
                        f.write(f"- {key}: {value}\n")
        except Exception as e:
            self.logger.error(
                f"Error creating metadata file for {target_path}: {str(e)}")

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
                    f.write(
                        f"Keywords: {', '.join(file_info['keywords'])}\n\n")

                # Add the main summary content
                if 'summary' in file_info and file_info['summary']:
                    f.write(
                        f"## Content Summary\n\n{file_info['summary']}\n\n")
                else:
                    f.write("No summary available for this file.\n\n")

                # Add related documents section if available
                if 'related_documents' in file_info and file_info['related_documents']:
                    f.write("## Related Documents\n\n")
                    for doc in file_info['related_documents'][:3]:  # Limit to top 3
                        rel_strength = doc.get(
                            'relationship_strength', 'medium')
                        rel_explanation = doc.get(
                            'relationship_explanation', '')
                        f.write(
                            f"- **{doc.get('filename', '')}**: {rel_strength.capitalize()} relationship")
                        if rel_explanation:
                            f.write(f"\n  {rel_explanation}")
                        f.write("\n\n")

                # Add AI analysis note
                f.write("---\n")
                f.write(
                    "Generated by AI Document Organizer using Google Gemini Flash 2.0\n")
                f.write(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")

            self.logger.info(f"Created summary file: {summary_path}")
        except Exception as e:
            self.logger.error(
                f"Error creating summary file for {target_path}: {str(e)}")

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
                self.logger.error(
                    f"Invalid folder path for report: {folder_path}")
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
                files = [f for f in files if not f.endswith('.meta.txt') and not f.endswith(
                    '_summary.txt') and not f.endswith('_Report.md')]

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
                            category_match = re.search(
                                r'Category:\s*(.+?)$', meta_content, re.MULTILINE)
                            if category_match:
                                category = category_match.group(1).strip()
                                file_info["category"] = category

                                # Update category statistics
                                if category in category_stats:
                                    category_stats[category] += 1
                                else:
                                    category_stats[category] = 1

                            # Extract keywords
                            keywords_match = re.search(
                                r'Keywords:\s*(.+?)$', meta_content, re.MULTILINE)
                            if keywords_match:
                                keywords = keywords_match.group(1).strip()
                                file_info["keywords"] = keywords

                            # Extract summary if needed
                            if include_summaries:
                                summary_match = re.search(
                                    r'Summary:\s*\n(.*?)(?:\n\n|\nMetadata:|$)', meta_content, re.DOTALL)
                                if summary_match:
                                    summary = summary_match.group(1).strip()
                                    file_info["summary"] = summary

                    file_data.append(file_info)

            # Generate the report
            with open(report_path, 'w', encoding='utf-8') as f:
                # Report header
                f.write(f"# Folder Content Report: {folder_name}\n\n")
                f.write(
                    f"Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write(f"Total files: {total_files}\n\n")

                # Category statistics
                f.write("## Category Distribution\n\n")
                if category_stats:
                    for category, count in sorted(category_stats.items(), key=lambda x: x[1], reverse=True):
                        percentage = (count / total_files) * 100
                        f.write(
                            f"- **{category}**: {count} files ({percentage:.1f}%)\n")
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

                # Document relationships section (if we have enough documents)
                if len(file_data) > 1:
                    f.write("\n## Document Relationships\n\n")
                    f.write(
                        "This section shows the relationships between documents based on content analysis.\n\n")

                    # Process document relationships for important documents
                    max_relationships = min(5, len(file_data))
                    relationships_analyzed = 0

                    # Find primary documents to analyze (prioritize by category importance)
                    primary_docs = []
                    for category in category_stats:
                        # Get documents from this category
                        category_docs = [doc for doc in file_data if doc.get(
                            "category", "") == category]
                        if category_docs:
                            # Add the first document from each category to analyze
                            primary_docs.append(category_docs[0])
                            if len(primary_docs) >= max_relationships:
                                break

                    # If we still don't have enough, add any remaining docs
                    if len(primary_docs) < max_relationships:
                        for doc in file_data:
                            if doc not in primary_docs:
                                primary_docs.append(doc)
                                if len(primary_docs) >= max_relationships:
                                    break

                    # Process each primary document to find relationships
                    for primary_doc in primary_docs:
                        # Convert keywords string to list if needed
                        if "keywords" in primary_doc and isinstance(primary_doc["keywords"], str):
                            primary_doc["keywords"] = [
                                k.strip() for k in primary_doc["keywords"].split(",")]

                        # Find similar documents for this primary document
                        try:
                            similar_docs = self.ai_analyzer.find_similar_documents(
                                primary_doc, file_data, max_results=3)

                            if similar_docs:
                                f.write(
                                    f"### Related to: {primary_doc['filename']}\n\n")
                                if "category" in primary_doc:
                                    f.write(
                                        f"Category: {primary_doc.get('category', 'Unknown')}\n\n")

                                # List related documents
                                for i, doc in enumerate(similar_docs):
                                    score = doc.get("similarity_score", 0)
                                    similarity = "High" if score >= 5 else "Medium" if score >= 3 else "Low"
                                    f.write(
                                        f"{i+1}. **{doc.get('filename', '')}** - {similarity} similarity\n")
                                    if "relationship_explanation" in doc:
                                        f.write(
                                            f"   - {doc.get('relationship_explanation', '')}\n")
                                f.write("\n")

                                relationships_analyzed += 1
                        except Exception as e:
                            self.logger.error(
                                f"Error analyzing relationships for {primary_doc.get('filename', '')}: {str(e)}")

                    if relationships_analyzed == 0:
                        f.write(
                            "No significant relationships found between documents.\n\n")

                # Footer
                f.write("\n## About this Report\n\n")
                f.write(
                    "This report was automatically generated by AI Document Organizer using Google Gemini Flash 2.0 AI analysis.\n")
                f.write("The content categorization, relationships, and summaries are AI-generated and may require human verification for critical information.\n")

            self.logger.info(f"Generated folder report: {report_path}")
            return report_path

        except Exception as e:
            self.logger.error(f"Error generating folder report: {str(e)}")
            return None
