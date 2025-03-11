import os
import re
import shutil
import time
from pathlib import Path
import logging
import json

from .utils import sanitize_filename
from .ai_analyzer import AIAnalyzer
from .duplicate_detector import DuplicateDetector
from .tag_manager import TagManager
from .organization_rules import OrganizationRuleManager, OrganizationRule
from .image_analyzer import ImageAnalyzer


class FileOrganizer:
    """
    Class responsible for organizing files based on AI analysis
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.ai_analyzer = AIAnalyzer()
        self.duplicate_detector = DuplicateDetector()
        self.tag_manager = TagManager()
        self.image_analyzer = ImageAnalyzer()
        self.rule_manager = OrganizationRuleManager()

        # Default rules directory
        self.rules_dir = os.path.join(os.path.expanduser(
            "~"), ".ai_document_organizer", "rules")
        os.makedirs(self.rules_dir, exist_ok=True)

        # Default rules file
        self.rules_file = os.path.join(
            self.rules_dir, "organization_rules.json")
        if os.path.exists(self.rules_file):
            self.rule_manager.load_rules(self.rules_file)
        else:
            # Create default rules
            self._create_default_rules()
            self.rule_manager.save_rules(self.rules_file)

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
                - use_custom_rules: Whether to use custom organization rules (default: False)
                - rules_file: Path to custom rules file (default: None)

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
            "suggest_tags": False,
            "use_custom_rules": False,
            "rules_file": None
        }

        # Merge provided options with defaults
        if options:
            for key, value in options.items():
                default_options[key] = value
            options = default_options

        # Load custom rules if specified
        if options["use_custom_rules"] and options["rules_file"] and os.path.exists(options["rules_file"]):
            self.rule_manager.load_rules(options["rules_file"])

        # Create target directory if it doesn't exist
        os.makedirs(target_dir, exist_ok=True)

        # Initialize results
        results = {
            "organized_files": 0,
            "skipped_files": 0,
            "duplicate_files": 0,
            "error_files": 0,
            "organized_file_paths": [],
            "skipped_file_paths": [],
            "duplicate_file_paths": [],
            "error_file_paths": [],
            "rules_applied": {}
        }

        # Process each file
        total_files = len(analyzed_files)
        for index, file_info in enumerate(analyzed_files):
            try:
                # Update progress
                if callback:
                    status = f"Organizing file {index + 1}/{total_files}: {file_info['file_name']}"
                    callback(index, total_files, status)

                # Check if file exists
                file_path = file_info.get("file_path")
                if not file_path or not os.path.exists(file_path):
                    self.logger.warning(f"File not found: {file_path}")
                    results["skipped_files"] += 1
                    results["skipped_file_paths"].append(file_path)
                    continue

                # Determine target path
                target_path = None
                applied_rule = None

                # Use custom rules if enabled
                if options["use_custom_rules"]:
                    target_path, applied_rule = self.rule_manager.apply_rules(
                        file_info, target_dir)

                    # Track rule usage
                    if applied_rule:
                        rule_id = applied_rule.rule_id
                        if rule_id not in results["rules_applied"]:
                            results["rules_applied"][rule_id] = {
                                "name": applied_rule.name,
                                "count": 0,
                                "files": []
                            }
                        results["rules_applied"][rule_id]["count"] += 1
                        results["rules_applied"][rule_id]["files"].append(
                            file_info["file_name"])

                # If no rule matched or custom rules are disabled, use default organization
                if not target_path:
                    target_path = self._get_default_target_path(
                        file_info, target_dir, options)

                # Ensure target directory exists
                target_dir_path = os.path.dirname(target_path)
                os.makedirs(target_dir_path, exist_ok=True)

                # Check for duplicates if enabled
                is_duplicate = False
                if options["detect_duplicates"]:
                    duplicate_info = self.duplicate_detector.check_duplicate(
                        file_path, target_dir)
                    if duplicate_info["is_duplicate"]:
                        is_duplicate = True
                        duplicate_path = duplicate_info["duplicate_path"]

                        # Handle duplicate based on options
                        if options["duplicate_action"] == "report":
                            self.logger.info(
                                f"Duplicate found: {file_path} matches {duplicate_path}")
                            results["duplicate_files"] += 1
                            results["duplicate_file_paths"].append(file_path)
                            continue

                        elif options["duplicate_action"] == "move":
                            # Move to duplicates folder
                            duplicates_dir = os.path.join(
                                target_dir, "_Duplicates")
                            os.makedirs(duplicates_dir, exist_ok=True)
                            duplicate_target = os.path.join(
                                duplicates_dir, os.path.basename(file_path))

                            # Ensure unique filename
                            if os.path.exists(duplicate_target):
                                base_name, ext = os.path.splitext(
                                    os.path.basename(file_path))
                                duplicate_target = os.path.join(
                                    duplicates_dir, f"{base_name}_dup_{int(time.time())}{ext}")

                            # Copy or move the file
                            if options["copy_instead_of_move"]:
                                shutil.copy2(file_path, duplicate_target)
                            else:
                                shutil.move(file_path, duplicate_target)

                            results["duplicate_files"] += 1
                            results["duplicate_file_paths"].append(file_path)
                            continue

                        elif options["duplicate_action"] == "delete":
                            # Skip the file (don't copy/move)
                            results["duplicate_files"] += 1
                            results["duplicate_file_paths"].append(file_path)
                            continue

                        elif options["duplicate_action"] == "keep_newest":
                            # Compare modification times
                            current_mtime = os.path.getmtime(file_path)
                            existing_mtime = os.path.getmtime(duplicate_path)

                            if current_mtime <= existing_mtime:
                                # Skip if current file is older
                                results["duplicate_files"] += 1
                                results["duplicate_file_paths"].append(
                                    file_path)
                                continue
                            else:
                                # Replace existing file
                                if options["copy_instead_of_move"]:
                                    shutil.copy2(file_path, duplicate_path)
                                else:
                                    shutil.move(file_path, duplicate_path)

                                results["organized_files"] += 1
                                results["organized_file_paths"].append(
                                    target_path)
                                continue

                # Copy or move the file
                try:
                if options["copy_instead_of_move"]:
                    shutil.copy2(file_path, target_path)
                else:
                    shutil.move(file_path, target_path)

                    # Generate summary file if enabled
                if options["generate_summaries"]:
                        self._generate_summary_file(
                            file_info, target_path, options)

                    # Generate metadata file if enabled
                    if options["include_metadata"]:
                        self._generate_metadata_file(file_info, target_path)

                    # Apply tags if enabled
                    if options["apply_tags"]:
                        self._apply_tags(file_info, target_path,
                                         options["suggest_tags"])

                    results["organized_files"] += 1
                    results["organized_file_paths"].append(target_path)

                except Exception as e:
                    self.logger.error(
                        f"Error organizing file {file_path}: {str(e)}")
                    results["error_files"] += 1
                    results["error_file_paths"].append(file_path)

            except Exception as e:
                self.logger.error(
                    f"Error processing file {file_info.get('file_path', 'Unknown')}: {str(e)}")
                results["error_files"] += 1
                results["error_file_paths"].append(
                    file_info.get("file_path", "Unknown"))

        # Save updated rule statistics if custom rules were used
        if options["use_custom_rules"]:
            self.rule_manager.save_rules(
                options["rules_file"] or self.rules_file)

        # Final progress update
        if callback:
            callback(total_files, total_files,
                     f"Organized {results['organized_files']} files")

        return results

    def _get_default_target_path(self, file_info, target_dir, options):
        """
        Get the default target path for a file based on its analysis

        Args:
            file_info: Dictionary with file information and analysis
            target_dir: Base target directory
            options: Organization options

        Returns:
            Target path for the file
        """
        file_path = file_info.get("file_path", "")
        file_name = file_info.get("file_name", os.path.basename(file_path))

        # Handle image files differently
        if file_info.get("is_image", False):
            return self._get_image_target_path(file_info, target_dir, options)

        # For document files, use AI analysis
        if "ai_analysis" in file_info and "category" in file_info.get("ai_analysis", {}):
            category = file_info["ai_analysis"]["category"]

            if options["create_category_folders"]:
                # Create category folder
                category_dir = os.path.join(
                    target_dir, sanitize_filename(category))
                return os.path.join(category_dir, file_name)
            else:
                return os.path.join(target_dir, file_name)
        else:
            # No category available, use file type
            file_type = file_info.get("file_type", "Other")
            type_dir = os.path.join(target_dir, sanitize_filename(file_type))
            return os.path.join(type_dir, file_name)

    def _get_image_target_path(self, file_info, target_dir, options):
        """
        Get the target path for an image file based on its analysis

        Args:
            file_info: Dictionary with file information and analysis
            target_dir: Base target directory
            options: Organization options

        Returns:
            Target path for the image file
        """
        file_path = file_info.get("file_path", "")
        file_name = file_info.get("file_name", os.path.basename(file_path))

        # Base image directory
        images_dir = os.path.join(target_dir, "Images")

        # Check if we have image analysis
        if "image_analysis" in file_info:
            image_analysis = file_info["image_analysis"]

            # Check if we have vision API results
            if "labels" in image_analysis and image_analysis["labels"]:
                # Organize by primary label/content
                primary_label = image_analysis["labels"][0]
                return os.path.join(images_dir, "Content", sanitize_filename(primary_label), file_name)

            # Check if we have camera information
            elif "metadata" in file_info and "camera_make" in file_info["metadata"]:
                camera_make = file_info["metadata"]["camera_make"]

                # Get date information
                if "date_time_original" in file_info["metadata"]:
                    # Parse date from EXIF
                    try:
                        date_str = file_info["metadata"]["date_time_original"]
                        date_parts = date_str.split(":")
                        year = date_parts[0]
                        month = date_parts[1]
                        return os.path.join(images_dir, "Cameras", sanitize_filename(camera_make), year, month, file_name)
                    except:
                        return os.path.join(images_dir, "Cameras", sanitize_filename(camera_make), file_name)
                else:
                    return os.path.join(images_dir, "Cameras", sanitize_filename(camera_make), file_name)

            # Check if we have date information
            elif "metadata" in file_info and "date_time_original" in file_info["metadata"]:
                # Parse date from EXIF
                try:
                    date_str = file_info["metadata"]["date_time_original"]
                    date_parts = date_str.split(":")
                    year = date_parts[0]
                    month = date_parts[1]
                    return os.path.join(images_dir, "Dates", year, month, file_name)
                except:
                    pass

        # Default to file type organization
        return os.path.join(images_dir, "Other", file_name)

    def _generate_summary_file(self, file_info, target_path, options):
        """
        Generate a summary file for the organized file

        Args:
            file_info: Dictionary with file information and analysis
            target_path: Path where the file was organized to
            options: Organization options
        """
        # Skip for image files unless they have text content
        if file_info.get("is_image", False) and not file_info.get("image_analysis", {}).get("text", ""):
            return

        # Get AI analysis
        ai_analysis = file_info.get("ai_analysis", {})

        # Skip if no analysis available
        if not ai_analysis:
            return

        # Create summary content
        summary_content = f"# Summary for {os.path.basename(target_path)}\n\n"

        # Add category
        if "category" in ai_analysis:
            summary_content += f"**Category:** {ai_analysis['category']}\n\n"

        # Add summary
        if "summary" in ai_analysis:
            summary_content += f"## Summary\n\n{ai_analysis['summary']}\n\n"

        # Add key points
        if "key_points" in ai_analysis and ai_analysis["key_points"]:
            summary_content += "## Key Points\n\n"
            for point in ai_analysis["key_points"]:
                summary_content += f"- {point}\n"
            summary_content += "\n"

        # Add entities
        if "entities" in ai_analysis and ai_analysis["entities"]:
            summary_content += "## Entities\n\n"
            for entity_type, entities in ai_analysis["entities"].items():
                if entities:
                    summary_content += f"### {entity_type}\n"
                    for entity in entities:
                        summary_content += f"- {entity}\n"
                    summary_content += "\n"

        # Add sentiment
        if "sentiment" in ai_analysis:
            summary_content += f"## Sentiment\n\n{ai_analysis['sentiment']}\n\n"

        # Write summary file
        summary_path = os.path.splitext(target_path)[0] + "_summary.md"
        try:
            with open(summary_path, "w", encoding="utf-8") as f:
                f.write(summary_content)
        except Exception as e:
            self.logger.error(f"Error creating summary file: {str(e)}")

    def _generate_metadata_file(self, file_info, target_path):
        """
        Generate a metadata file for the organized file

        Args:
            file_info: Dictionary with file information and analysis
            target_path: Path where the file was organized to
        """
        # Create metadata content
        metadata = {
            "file_name": file_info.get("file_name", ""),
            "file_type": file_info.get("file_type", ""),
            "file_size": file_info.get("file_size", 0),
            "created_time": file_info.get("created_time", 0),
            "modified_time": file_info.get("modified_time", 0),
            "original_path": file_info.get("file_path", ""),
            "organized_path": target_path,
            "organized_time": time.time()
        }

        # Add file-specific metadata
        if "metadata" in file_info:
            metadata["file_metadata"] = file_info["metadata"]

        # Add AI analysis summary
        if "ai_analysis" in file_info:
            metadata["ai_analysis"] = {
                "category": file_info["ai_analysis"].get("category", ""),
                "summary": file_info["ai_analysis"].get("summary", ""),
                "sentiment": file_info["ai_analysis"].get("sentiment", "")
            }

        # Add image analysis if available
        if "image_analysis" in file_info:
            # Extract relevant image analysis data
            image_analysis = file_info["image_analysis"]
            metadata["image_analysis"] = {
                "dimensions": image_analysis.get("dimensions", ""),
                "format": image_analysis.get("format", ""),
                "has_transparency": image_analysis.get("has_transparency", False),
                "is_animated": image_analysis.get("is_animated", False),
                "dominant_colors": image_analysis.get("dominant_colors", []),
                "labels": image_analysis.get("labels", []),
                "objects": image_analysis.get("objects", []),
                "faces": image_analysis.get("faces", []),
                "text": image_analysis.get("text", "")
            }

        # Write metadata file
        metadata_path = os.path.splitext(target_path)[0] + "_metadata.json"
        try:
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error creating metadata file: {str(e)}")

    def _apply_tags(self, file_info, target_path, suggest_tags=False):
        """
        Apply tags to the organized file

        Args:
            file_info: Dictionary with file information and analysis
            target_path: Path where the file was organized to
            suggest_tags: Whether to suggest tags based on content
        """
        tags = []

        # Add file type tag
        file_type = file_info.get("file_type", "")
        if file_type:
            tags.append(file_type)

        # Add category tag if available
        if "ai_analysis" in file_info and "category" in file_info["ai_analysis"]:
            category = file_info["ai_analysis"]["category"]
            if category:
                tags.append(category)

        # Add image-specific tags
        if file_info.get("is_image", False) and "image_analysis" in file_info:
            # Add camera make if available
            if "metadata" in file_info and "camera_make" in file_info["metadata"]:
                camera_make = file_info["metadata"]["camera_make"]
                if camera_make:
                    tags.append(f"Camera:{camera_make}")

            # Add content labels if available
            if "labels" in file_info["image_analysis"]:
                # Add top 5 labels
                for label in file_info["image_analysis"]["labels"][:5]:
                    tags.append(label)

        # Suggest additional tags if enabled
        if suggest_tags:
            if "ai_analysis" in file_info:
                # Extract keywords from summary
                if "summary" in file_info["ai_analysis"]:
                    summary = file_info["ai_analysis"]["summary"]
                    suggested_tags = self.tag_manager.extract_tags_from_text(
                        summary)
                    tags.extend(suggested_tags)

                # Add entities as tags
                if "entities" in file_info["ai_analysis"]:
                    for entity_type, entities in file_info["ai_analysis"]["entities"].items():
                        # Add top 3 entities of each type
                        for entity in entities[:3]:
                            tags.append(f"{entity_type}:{entity}")

        # Apply tags to the file
        if tags:
            self.tag_manager.tag_file(target_path, tags)

    def _create_default_rules(self):
        """
        Create default organization rules
        """
        # Document type rule
        doc_rule = self.rule_manager.create_rule_template("document_type")
        doc_rule.priority = 100
        self.rule_manager.add_rule(doc_rule)

        # Date-based rule
        date_rule = self.rule_manager.create_rule_template("date")
        date_rule.priority = 200
        self.rule_manager.add_rule(date_rule)

        # Category-based rule
        category_rule = self.rule_manager.create_rule_template("category")
        category_rule.priority = 50  # Higher priority than document type
        self.rule_manager.add_rule(category_rule)

        # Image camera rule
        camera_rule = self.rule_manager.create_rule_template("image_camera")
        camera_rule.priority = 30  # High priority for images
        self.rule_manager.add_rule(camera_rule)

        # Image content rule
        content_rule = self.rule_manager.create_rule_template("image_content")
        content_rule.priority = 20  # Highest priority
        self.rule_manager.add_rule(content_rule)

    def create_custom_rule(self, rule_type, name=None, description=None):
        """
        Create a custom organization rule

        Args:
            rule_type: Type of rule to create (pattern, content, metadata, date, tag, ai, image)
            name: Optional name for the rule
            description: Optional description for the rule

        Returns:
            Created rule
        """
        rule = OrganizationRule(name=name, description=description)

        # Set default condition based on rule type
        if rule_type == "pattern":
            rule.set_name_pattern_condition(".*", OrganizationRule.OP_REGEX)
        elif rule_type == "content":
            rule.set_content_condition("", OrganizationRule.OP_CONTAINS)
        elif rule_type == "metadata":
            rule.set_metadata_condition(
                "file_type", "", OrganizationRule.OP_EXISTS)
        elif rule_type == "date":
            rule.set_date_condition(
                "modified_time", None, OrganizationRule.OP_EXISTS)
        elif rule_type == "tag":
            rule.set_tag_condition("", OrganizationRule.OP_EXISTS)
        elif rule_type == "ai":
            rule.set_ai_analysis_condition(
                "category", "", OrganizationRule.OP_EXISTS)
        elif rule_type == "image":
            rule.set_image_condition(
                "dimensions", "", OrganizationRule.OP_EXISTS)

        # Add to rule manager
        self.rule_manager.add_rule(rule)

        # Save rules
        self.rule_manager.save_rules(self.rules_file)

        return rule

    def get_all_rules(self):
        """
        Get all organization rules

        Returns:
            List of rules
        """
        return self.rule_manager.get_all_rules()

    def get_rule(self, rule_id):
        """
        Get a rule by ID

        Args:
            rule_id: ID of the rule to get

        Returns:
            Rule or None if not found
        """
        return self.rule_manager.get_rule(rule_id)

    def update_rule(self, rule):
        """
        Update an existing rule

        Args:
            rule: Rule to update

        Returns:
            True if successful, False otherwise
        """
        result = self.rule_manager.update_rule(rule)
        if result:
            self.rule_manager.save_rules(self.rules_file)
        return result

    def delete_rule(self, rule_id):
        """
        Delete a rule

        Args:
            rule_id: ID of the rule to delete

        Returns:
            True if successful, False otherwise
        """
        result = self.rule_manager.delete_rule(rule_id)
        if result:
            self.rule_manager.save_rules(self.rules_file)
        return result

    def import_rules(self, rules_file):
        """
        Import rules from a file

        Args:
            rules_file: Path to the rules file

        Returns:
            True if successful, False otherwise
        """
        return self.rule_manager.load_rules(rules_file)

    def export_rules(self, rules_file):
        """
        Export rules to a file

        Args:
            rules_file: Path to save the rules to

        Returns:
            True if successful, False otherwise
        """
        return self.rule_manager.save_rules(rules_file)
