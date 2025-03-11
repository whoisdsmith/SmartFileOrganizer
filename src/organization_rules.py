import os
import re
import json
import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Union, Callable, Pattern
import logging

logger = logging.getLogger("AIDocumentOrganizer")


class OrganizationRule:
    """
    Class representing a single organization rule for file organization
    """

    # Rule types
    TYPE_PATTERN = "pattern"       # File name pattern matching
    TYPE_CONTENT = "content"       # Content-based rules
    TYPE_METADATA = "metadata"     # Metadata-based rules
    TYPE_DATE = "date"             # Date-based rules
    TYPE_TAG = "tag"               # Tag-based rules
    TYPE_AI = "ai"                 # AI analysis result rules
    TYPE_IMAGE = "image"           # Image-specific rules

    # Rule operators
    OP_EQUALS = "equals"           # Exact match
    OP_CONTAINS = "contains"       # Contains substring
    OP_REGEX = "regex"             # Regular expression match
    OP_GREATER = "greater_than"    # Greater than (for numeric values)
    OP_LESS = "less_than"          # Less than (for numeric values)
    # Between two values (for numeric/date values)
    OP_BETWEEN = "between"
    OP_EXISTS = "exists"           # Field exists

    def __init__(self, rule_id=None, name=None, description=None, enabled=True):
        """
        Initialize a new organization rule

        Args:
            rule_id: Optional unique identifier for the rule
            name: Optional name for the rule
            description: Optional description of the rule
            enabled: Whether the rule is enabled
        """
        self.rule_id = rule_id or self._generate_id()
        self.name = name or f"Rule {self.rule_id}"
        self.description = description or ""
        self.enabled = enabled
        # Default priority (lower number = higher priority)
        self.priority = 100

        # Rule conditions
        self.rule_type = None
        self.condition = {}

        # Rule actions
        self.target_path_template = ""  # Template for the target path
        self.should_copy = True  # Copy instead of move by default
        self.create_summary = False  # Whether to create a summary file

        # Rule metadata
        self.created_time = datetime.datetime.now().isoformat()
        self.modified_time = self.created_time
        self.last_applied = None  # When the rule was last applied
        self.application_count = 0  # How many times the rule has been applied
        self.success_count = 0  # How many successful applications

    def _generate_id(self):
        """
        Generate a unique rule ID

        Returns:
            Unique rule ID string
        """
        import uuid
        return f"rule_{uuid.uuid4().hex[:8]}"

    def set_name_pattern_condition(self, pattern, operator=OP_REGEX, case_sensitive=False):
        """
        Set a file name pattern matching condition

        Args:
            pattern: Pattern to match against file name
            operator: Operator to use (equals, contains, regex)
            case_sensitive: Whether the match is case sensitive
        """
        self.rule_type = self.TYPE_PATTERN
        self.condition = {
            "field": "file_name",
            "operator": operator,
            "pattern": pattern,
            "case_sensitive": case_sensitive
        }
        self.modified_time = datetime.datetime.now().isoformat()
        return self

    def set_content_condition(self, search_text, operator=OP_CONTAINS, case_sensitive=False):
        """
        Set a content-based condition

        Args:
            search_text: Text to search for in the file content
            operator: Operator to use (contains, regex)
            case_sensitive: Whether the search is case sensitive
        """
        self.rule_type = self.TYPE_CONTENT
        self.condition = {
            "field": "text_content",
            "operator": operator,
            "pattern": search_text,
            "case_sensitive": case_sensitive
        }
        self.modified_time = datetime.datetime.now().isoformat()
        return self

    def set_metadata_condition(self, field_name, value, operator=OP_EQUALS):
        """
        Set a metadata-based condition

        Args:
            field_name: Name of the metadata field to check
            value: Value to compare against
            operator: Operator to use (equals, contains, greater_than, less_than, etc.)
        """
        self.rule_type = self.TYPE_METADATA
        self.condition = {
            "field": field_name,
            "operator": operator,
            "value": value
        }
        self.modified_time = datetime.datetime.now().isoformat()
        return self

    def set_date_condition(self, date_field, date_range=None, operator=OP_BETWEEN):
        """
        Set a date-based condition

        Args:
            date_field: Field containing the date (created_time, modified_time, etc.)
            date_range: Tuple of (start_date, end_date) or single date value
            operator: Operator to use (equals, greater_than, less_than, between)
        """
        self.rule_type = self.TYPE_DATE

        if operator == self.OP_BETWEEN and isinstance(date_range, tuple) and len(date_range) == 2:
            start_date, end_date = date_range
            self.condition = {
                "field": date_field,
                "operator": operator,
                "start_date": start_date,
                "end_date": end_date
            }
        else:
            self.condition = {
                "field": date_field,
                "operator": operator,
                "value": date_range
            }

        self.modified_time = datetime.datetime.now().isoformat()
        return self

    def set_tag_condition(self, tag_name, operator=OP_EQUALS):
        """
        Set a tag-based condition

        Args:
            tag_name: Tag to check for
            operator: Operator to use (equals, contains)
        """
        self.rule_type = self.TYPE_TAG
        self.condition = {
            "field": "tags",
            "operator": operator,
            "value": tag_name
        }
        self.modified_time = datetime.datetime.now().isoformat()
        return self

    def set_ai_analysis_condition(self, ai_field, value, operator=OP_CONTAINS):
        """
        Set an AI analysis result condition

        Args:
            ai_field: AI analysis field to check (category, summary, etc.)
            value: Value to compare against
            operator: Operator to use (equals, contains, etc.)
        """
        self.rule_type = self.TYPE_AI
        self.condition = {
            "field": f"ai_analysis.{ai_field}",
            "operator": operator,
            "value": value
        }
        self.modified_time = datetime.datetime.now().isoformat()
        return self

    def set_image_condition(self, image_field, value, operator=OP_EQUALS):
        """
        Set an image-specific condition

        Args:
            image_field: Image field to check (dimensions, format, etc.)
            value: Value to compare against
            operator: Operator to use (equals, contains, greater_than, etc.)
        """
        self.rule_type = self.TYPE_IMAGE
        self.condition = {
            "field": f"image_analysis.{image_field}",
            "operator": operator,
            "value": value
        }
        self.modified_time = datetime.datetime.now().isoformat()
        return self

    def set_target_path(self, path_template):
        """
        Set the target path template for the rule

        Args:
            path_template: Template string for the target path
                           Can include placeholders like {category}, {year}, etc.
        """
        self.target_path_template = path_template
        self.modified_time = datetime.datetime.now().isoformat()
        return self

    def set_priority(self, priority):
        """
        Set the rule priority (lower number = higher priority)

        Args:
            priority: Priority value (1-1000)
        """
        self.priority = max(1, min(1000, int(priority)))
        self.modified_time = datetime.datetime.now().isoformat()
        return self

    def set_options(self, should_copy=None, create_summary=None):
        """
        Set rule options

        Args:
            should_copy: Whether to copy instead of move
            create_summary: Whether to create a summary file
        """
        if should_copy is not None:
            self.should_copy = should_copy
        if create_summary is not None:
            self.create_summary = create_summary

        self.modified_time = datetime.datetime.now().isoformat()
        return self

    def matches(self, file_info):
        """
        Check if a file matches this rule

        Args:
            file_info: Dictionary with file information

        Returns:
            True if the file matches the rule, False otherwise
        """
        if not self.enabled or not self.condition:
            return False

        try:
            # Extract the field value based on the rule type
            field_path = self.condition.get("field", "")
            field_value = self._get_nested_field(file_info, field_path)

            # If the field doesn't exist, the rule doesn't match
            if field_value is None and self.condition.get("operator") != self.OP_EXISTS:
                return False

            # Check the condition based on the operator
            operator = self.condition.get("operator", "")

            if operator == self.OP_EXISTS:
                return field_value is not None

            if operator == self.OP_EQUALS:
                return field_value == self.condition.get("value")

            if operator == self.OP_CONTAINS:
                if isinstance(field_value, str) and isinstance(self.condition.get("value"), str):
                    if self.condition.get("case_sensitive", False):
                        return self.condition.get("value") in field_value
                    else:
                        return self.condition.get("value").lower() in field_value.lower()
                elif isinstance(field_value, list):
                    return self.condition.get("value") in field_value
                return False

            if operator == self.OP_REGEX:
                if isinstance(field_value, str):
                    pattern = self.condition.get("pattern", "")
                    flags = 0 if self.condition.get(
                        "case_sensitive", False) else re.IGNORECASE
                    return bool(re.search(pattern, field_value, flags))
                return False

            if operator == self.OP_GREATER:
                if isinstance(field_value, (int, float)) and isinstance(self.condition.get("value"), (int, float)):
                    return field_value > self.condition.get("value")
                return False

            if operator == self.OP_LESS:
                if isinstance(field_value, (int, float)) and isinstance(self.condition.get("value"), (int, float)):
                    return field_value < self.condition.get("value")
                return False

            if operator == self.OP_BETWEEN:
                if isinstance(field_value, (int, float)):
                    start = self.condition.get("start_date") or self.condition.get(
                        "start_value", float("-inf"))
                    end = self.condition.get("end_date") or self.condition.get(
                        "end_value", float("inf"))
                    return start <= field_value <= end
                return False

            # Unknown operator
            return False

        except Exception as e:
            logger.error(f"Error matching rule {self.rule_id}: {str(e)}")
            return False

    def _get_nested_field(self, data, field_path):
        """
        Get a nested field value from a dictionary

        Args:
            data: Dictionary to extract from
            field_path: Dot-separated path to the field

        Returns:
            Field value or None if not found
        """
        if not field_path or not data:
            return None

        parts = field_path.split(".")
        value = data

        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return None

        return value

    def generate_target_path(self, file_info, base_dir):
        """
        Generate the target path for a file based on the rule template

        Args:
            file_info: Dictionary with file information
            base_dir: Base directory for the target path

        Returns:
            Target path for the file
        """
        if not self.target_path_template:
            return None

        try:
            # Start with the template
            path = self.target_path_template

            # Replace placeholders with values from file_info
            placeholders = re.findall(r'\{([^}]+)\}', path)

            for placeholder in placeholders:
                # Handle special placeholders
                if placeholder == "year":
                    # Use modified_time to get year
                    modified_time = file_info.get("modified_time", 0)
                    year = datetime.datetime.fromtimestamp(modified_time).year
                    path = path.replace(f"{{{placeholder}}}", str(year))

                elif placeholder == "month":
                    # Use modified_time to get month
                    modified_time = file_info.get("modified_time", 0)
                    month = datetime.datetime.fromtimestamp(
                        modified_time).month
                    path = path.replace(f"{{{placeholder}}}", f"{month:02d}")

                elif placeholder == "day":
                    # Use modified_time to get day
                    modified_time = file_info.get("modified_time", 0)
                    day = datetime.datetime.fromtimestamp(modified_time).day
                    path = path.replace(f"{{{placeholder}}}", f"{day:02d}")

                elif placeholder == "file_type":
                    # Use file_type directly
                    file_type = file_info.get("file_type", "Unknown")
                    path = path.replace(f"{{{placeholder}}}", file_type)

                elif placeholder == "category":
                    # Try to get category from AI analysis
                    category = self._get_nested_field(
                        file_info, "ai_analysis.category")
                    if category:
                        path = path.replace(f"{{{placeholder}}}", category)
                    else:
                        path = path.replace(
                            f"{{{placeholder}}}", "Uncategorized")

                elif placeholder == "camera_make":
                    # Try to get camera make from image metadata
                    camera_make = self._get_nested_field(
                        file_info, "metadata.camera_make")
                    if camera_make:
                        path = path.replace(f"{{{placeholder}}}", camera_make)
                    else:
                        path = path.replace(f"{{{placeholder}}}", "Unknown")

                else:
                    # Try to get the value from file_info
                    value = self._get_nested_field(file_info, placeholder)
                    if value is not None:
                        if isinstance(value, (int, float, bool)):
                            value = str(value)
                        if isinstance(value, str):
                            # Sanitize the value for use in a path
                            value = re.sub(r'[<>:"/\\|?*]', '_', value)
                            path = path.replace(f"{{{placeholder}}}", value)
                        else:
                            # For non-string values, use a default
                            path = path.replace(
                                f"{{{placeholder}}}", "Unknown")
                    else:
                        # If the value is not found, use a default
                        path = path.replace(f"{{{placeholder}}}", "Unknown")

            # Combine with base directory
            full_path = os.path.join(base_dir, path)

            # Normalize the path
            full_path = os.path.normpath(full_path)

            return full_path

        except Exception as e:
            logger.error(
                f"Error generating target path for rule {self.rule_id}: {str(e)}")
            return None

    def to_dict(self):
        """
        Convert the rule to a dictionary for serialization

        Returns:
            Dictionary representation of the rule
        """
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "description": self.description,
            "enabled": self.enabled,
            "priority": self.priority,
            "rule_type": self.rule_type,
            "condition": self.condition,
            "target_path_template": self.target_path_template,
            "should_copy": self.should_copy,
            "create_summary": self.create_summary,
            "created_time": self.created_time,
            "modified_time": self.modified_time,
            "last_applied": self.last_applied,
            "application_count": self.application_count,
            "success_count": self.success_count
        }

    @classmethod
    def from_dict(cls, data):
        """
        Create a rule from a dictionary

        Args:
            data: Dictionary with rule data

        Returns:
            OrganizationRule instance
        """
        rule = cls(
            rule_id=data.get("rule_id"),
            name=data.get("name"),
            description=data.get("description"),
            enabled=data.get("enabled", True)
        )

        rule.priority = data.get("priority", 100)
        rule.rule_type = data.get("rule_type")
        rule.condition = data.get("condition", {})
        rule.target_path_template = data.get("target_path_template", "")
        rule.should_copy = data.get("should_copy", True)
        rule.create_summary = data.get("create_summary", False)
        rule.created_time = data.get("created_time", rule.created_time)
        rule.modified_time = data.get("modified_time", rule.modified_time)
        rule.last_applied = data.get("last_applied")
        rule.application_count = data.get("application_count", 0)
        rule.success_count = data.get("success_count", 0)

        return rule


class OrganizationRuleManager:
    """
    Class for managing organization rules
    """

    def __init__(self, rules_file=None):
        """
        Initialize the rule manager

        Args:
            rules_file: Optional path to a JSON file with rules
        """
        self.rules = []
        self.rules_file = rules_file

        # Load rules from file if provided
        if rules_file and os.path.exists(rules_file):
            self.load_rules(rules_file)

    def add_rule(self, rule):
        """
        Add a rule to the manager

        Args:
            rule: OrganizationRule instance

        Returns:
            Added rule
        """
        self.rules.append(rule)
        return rule

    def get_rule(self, rule_id):
        """
        Get a rule by ID

        Args:
            rule_id: Rule ID to find

        Returns:
            OrganizationRule instance or None if not found
        """
        for rule in self.rules:
            if rule.rule_id == rule_id:
                return rule
        return None

    def update_rule(self, rule):
        """
        Update an existing rule

        Args:
            rule: OrganizationRule instance to update

        Returns:
            True if the rule was updated, False otherwise
        """
        for i, existing_rule in enumerate(self.rules):
            if existing_rule.rule_id == rule.rule_id:
                self.rules[i] = rule
                return True
        return False

    def delete_rule(self, rule_id):
        """
        Delete a rule by ID

        Args:
            rule_id: Rule ID to delete

        Returns:
            True if the rule was deleted, False otherwise
        """
        for i, rule in enumerate(self.rules):
            if rule.rule_id == rule_id:
                del self.rules[i]
                return True
        return False

    def get_all_rules(self, enabled_only=False):
        """
        Get all rules

        Args:
            enabled_only: Whether to return only enabled rules

        Returns:
            List of OrganizationRule instances
        """
        if enabled_only:
            return [rule for rule in self.rules if rule.enabled]
        return self.rules

    def get_sorted_rules(self, enabled_only=True):
        """
        Get rules sorted by priority

        Args:
            enabled_only: Whether to return only enabled rules

        Returns:
            List of OrganizationRule instances sorted by priority
        """
        rules = self.get_all_rules(enabled_only)
        return sorted(rules, key=lambda r: r.priority)

    def save_rules(self, file_path=None):
        """
        Save rules to a JSON file

        Args:
            file_path: Path to save the rules to (defaults to self.rules_file)

        Returns:
            True if successful, False otherwise
        """
        file_path = file_path or self.rules_file
        if not file_path:
            return False

        try:
            rules_data = [rule.to_dict() for rule in self.rules]
            with open(file_path, 'w') as f:
                json.dump(rules_data, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving rules: {str(e)}")
            return False

    def load_rules(self, file_path=None):
        """
        Load rules from a JSON file

        Args:
            file_path: Path to load the rules from (defaults to self.rules_file)

        Returns:
            True if successful, False otherwise
        """
        file_path = file_path or self.rules_file
        if not file_path or not os.path.exists(file_path):
            return False

        try:
            with open(file_path, 'r') as f:
                rules_data = json.load(f)

            self.rules = [OrganizationRule.from_dict(
                data) for data in rules_data]
            return True
        except Exception as e:
            logger.error(f"Error loading rules: {str(e)}")
            return False

    def create_rule_template(self, template_type):
        """
        Create a rule from a template

        Args:
            template_type: Template type (document, image, date, etc.)

        Returns:
            OrganizationRule instance
        """
        rule = OrganizationRule()

        if template_type == "document_type":
            rule.name = "Document Type Organization"
            rule.description = "Organize files by document type"
            rule.set_metadata_condition(
                "file_type", "", OrganizationRule.OP_EXISTS)
            rule.set_target_path("{file_type}/{file_name}")

        elif template_type == "date":
            rule.name = "Date-based Organization"
            rule.description = "Organize files by year and month"
            rule.set_date_condition(
                "modified_time", None, OrganizationRule.OP_EXISTS)
            rule.set_target_path("{year}/{month}/{file_name}")

        elif template_type == "category":
            rule.name = "Category-based Organization"
            rule.description = "Organize files by AI-detected category"
            rule.set_ai_analysis_condition(
                "category", "", OrganizationRule.OP_EXISTS)
            rule.set_target_path("{category}/{file_name}")

        elif template_type == "image_camera":
            rule.name = "Camera-based Image Organization"
            rule.description = "Organize images by camera make and model"
            rule.set_image_condition(
                "dimensions", "", OrganizationRule.OP_EXISTS)
            rule.set_target_path(
                "Images/{camera_make}/{year}/{month}/{file_name}")

        elif template_type == "image_content":
            rule.name = "Image Content Organization"
            rule.description = "Organize images by detected content"
            rule.set_image_condition("labels", "", OrganizationRule.OP_EXISTS)
            rule.set_target_path("Images/Content/{labels[0]}/{file_name}")

        else:
            # Default template
            rule.name = "Basic Organization"
            rule.description = "Basic file organization template"
            rule.set_target_path("{file_type}/{file_name}")

        return rule

    def apply_rules(self, file_info, base_dir):
        """
        Apply rules to a file and determine the target path

        Args:
            file_info: Dictionary with file information
            base_dir: Base directory for the target path

        Returns:
            Tuple of (target_path, matching_rule) or (None, None) if no rule matches
        """
        # Get sorted rules (by priority)
        sorted_rules = self.get_sorted_rules(enabled_only=True)

        for rule in sorted_rules:
            if rule.matches(file_info):
                # Update rule statistics
                rule.application_count += 1
                rule.last_applied = datetime.datetime.now().isoformat()

                # Generate target path
                target_path = rule.generate_target_path(file_info, base_dir)

                if target_path:
                    rule.success_count += 1
                    return (target_path, rule)

        return (None, None)

    def create_rule_from_example(self, file_info, target_path, base_dir):
        """
        Create a rule from an example file and target path

        Args:
            file_info: Dictionary with file information for the example file
            target_path: Target path for the example file
            base_dir: Base directory for the target path

        Returns:
            OrganizationRule instance
        """
        # Create a new rule
        rule = OrganizationRule()
        rule.name = f"Rule for {file_info.get('file_name', 'Unknown')}"

        # Determine the relative path from base_dir
        if target_path.startswith(base_dir):
            rel_path = os.path.relpath(target_path, base_dir)
        else:
            rel_path = target_path

        # Replace the filename with a placeholder
        file_name = file_info.get('file_name', '')
        if file_name and rel_path.endswith(file_name):
            rel_path = rel_path[:-len(file_name)] + "{file_name}"

        # Set the target path template
        rule.set_target_path(rel_path)

        # Try to determine a good condition based on the file info
        if file_info.get('is_image', False):
            # For images, use image type
            rule.set_metadata_condition(
                "file_type", "Image", OrganizationRule.OP_EQUALS)
        elif "ai_analysis" in file_info and "category" in file_info.get("ai_analysis", {}):
            # For documents with AI analysis, use category
            category = file_info["ai_analysis"]["category"]
            rule.set_ai_analysis_condition(
                "category", category, OrganizationRule.OP_EQUALS)
        else:
            # Default to file extension
            file_ext = file_info.get('file_ext', '')
            rule.set_metadata_condition(
                "file_ext", file_ext, OrganizationRule.OP_EQUALS)

        return rule
