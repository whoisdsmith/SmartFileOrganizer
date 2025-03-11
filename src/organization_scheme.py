import os
import json
import yaml
import logging
import datetime
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
import hashlib

logger = logging.getLogger("AIDocumentOrganizer")


class OrganizationScheme:
    """
    Class for managing file organization schemes, including import/export functionality
    and template management.
    """

    def __init__(self, name: str, description: str = "", author: str = "", version: str = "1.0.0"):
        """
        Initialize a new organization scheme.

        Args:
            name: Name of the organization scheme
            description: Description of the scheme
            author: Author of the scheme
            version: Version of the scheme
        """
        self.name = name
        self.description = description
        self.author = author
        self.version = version
        self.created_at = datetime.datetime.now().isoformat()
        self.modified_at = self.created_at

        # Organization rules
        self.rules = []

        # File type mappings
        self.file_type_mappings = {}

        # Category definitions
        self.categories = {}

        # Naming patterns
        self.naming_patterns = {}

        # Metadata extraction rules
        self.metadata_rules = {}

        # AI analysis configuration
        self.ai_config = {}

        # Media handling configuration
        self.media_config = {}

        # Cloud storage configuration
        self.cloud_config = {}

    def add_rule(self, rule: Dict[str, Any]) -> bool:
        """
        Add an organization rule to the scheme.

        Args:
            rule: Dictionary containing rule configuration

        Returns:
            True if rule was added successfully, False otherwise
        """
        try:
            # Validate rule structure
            required_fields = ['name', 'type', 'conditions', 'actions']
            if not all(field in rule for field in required_fields):
                logger.error("Missing required fields in rule")
                return False

            # Add rule to scheme
            self.rules.append(rule)
            self._update_modified_time()
            return True

        except Exception as e:
            logger.error(f"Error adding rule: {str(e)}")
            return False

    def remove_rule(self, rule_name: str) -> bool:
        """
        Remove an organization rule from the scheme.

        Args:
            rule_name: Name of the rule to remove

        Returns:
            True if rule was removed successfully, False otherwise
        """
        try:
            # Find and remove rule
            for i, rule in enumerate(self.rules):
                if rule['name'] == rule_name:
                    self.rules.pop(i)
                    self._update_modified_time()
                    return True

            logger.error(f"Rule not found: {rule_name}")
            return False

        except Exception as e:
            logger.error(f"Error removing rule: {str(e)}")
            return False

    def add_file_type_mapping(self, extension: str, file_type: str) -> bool:
        """
        Add a file type mapping to the scheme.

        Args:
            extension: File extension (including dot)
            file_type: Type category for the extension

        Returns:
            True if mapping was added successfully, False otherwise
        """
        try:
            self.file_type_mappings[extension.lower()] = file_type
            self._update_modified_time()
            return True

        except Exception as e:
            logger.error(f"Error adding file type mapping: {str(e)}")
            return False

    def add_category(self, category: str, patterns: List[str]) -> bool:
        """
        Add a category definition to the scheme.

        Args:
            category: Category name
            patterns: List of patterns that define the category

        Returns:
            True if category was added successfully, False otherwise
        """
        try:
            self.categories[category] = patterns
            self._update_modified_time()
            return True

        except Exception as e:
            logger.error(f"Error adding category: {str(e)}")
            return False

    def add_naming_pattern(self, pattern_name: str, pattern: str) -> bool:
        """
        Add a naming pattern to the scheme.

        Args:
            pattern_name: Name of the pattern
            pattern: The naming pattern

        Returns:
            True if pattern was added successfully, False otherwise
        """
        try:
            self.naming_patterns[pattern_name] = pattern
            self._update_modified_time()
            return True

        except Exception as e:
            logger.error(f"Error adding naming pattern: {str(e)}")
            return False

    def export_scheme(self, file_path: str, format: str = "json") -> bool:
        """
        Export the organization scheme to a file.

        Args:
            file_path: Path to save the scheme
            format: Export format ("json" or "yaml")

        Returns:
            True if export was successful, False otherwise
        """
        try:
            # Create scheme data dictionary
            scheme_data = {
                'name': self.name,
                'description': self.description,
                'author': self.author,
                'version': self.version,
                'created_at': self.created_at,
                'modified_at': self.modified_at,
                'rules': self.rules,
                'file_type_mappings': self.file_type_mappings,
                'categories': self.categories,
                'naming_patterns': self.naming_patterns,
                'metadata_rules': self.metadata_rules,
                'ai_config': self.ai_config,
                'media_config': self.media_config,
                'cloud_config': self.cloud_config
            }

            # Export in specified format
            if format.lower() == "json":
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(scheme_data, f, indent=2, ensure_ascii=False)
            elif format.lower() == "yaml":
                with open(file_path, 'w', encoding='utf-8') as f:
                    yaml.dump(scheme_data, f, allow_unicode=True)
            else:
                logger.error(f"Unsupported export format: {format}")
                return False

            return True

        except Exception as e:
            logger.error(f"Error exporting scheme: {str(e)}")
            return False

    def import_scheme(self, file_path: str) -> bool:
        """
        Import an organization scheme from a file.

        Args:
            file_path: Path to the scheme file

        Returns:
            True if import was successful, False otherwise
        """
        try:
            # Determine file format from extension
            file_ext = os.path.splitext(file_path)[1].lower()

            # Load scheme data
            with open(file_path, 'r', encoding='utf-8') as f:
                if file_ext == '.json':
                    scheme_data = json.load(f)
                elif file_ext in ['.yml', '.yaml']:
                    scheme_data = yaml.safe_load(f)
                else:
                    logger.error(f"Unsupported file format: {file_ext}")
                    return False

            # Update scheme attributes
            self.name = scheme_data.get('name', self.name)
            self.description = scheme_data.get('description', self.description)
            self.author = scheme_data.get('author', self.author)
            self.version = scheme_data.get('version', self.version)
            self.created_at = scheme_data.get('created_at', self.created_at)
            self.modified_at = scheme_data.get('modified_at', self.modified_at)
            self.rules = scheme_data.get('rules', self.rules)
            self.file_type_mappings = scheme_data.get(
                'file_type_mappings', self.file_type_mappings)
            self.categories = scheme_data.get('categories', self.categories)
            self.naming_patterns = scheme_data.get(
                'naming_patterns', self.naming_patterns)
            self.metadata_rules = scheme_data.get(
                'metadata_rules', self.metadata_rules)
            self.ai_config = scheme_data.get('ai_config', self.ai_config)
            self.media_config = scheme_data.get(
                'media_config', self.media_config)
            self.cloud_config = scheme_data.get(
                'cloud_config', self.cloud_config)

            return True

        except Exception as e:
            logger.error(f"Error importing scheme: {str(e)}")
            return False

    def merge_scheme(self, other_scheme: 'OrganizationScheme') -> bool:
        """
        Merge another organization scheme into this one.

        Args:
            other_scheme: OrganizationScheme to merge

        Returns:
            True if merge was successful, False otherwise
        """
        try:
            # Merge rules (avoiding duplicates by name)
            existing_rule_names = {rule['name'] for rule in self.rules}
            for rule in other_scheme.rules:
                if rule['name'] not in existing_rule_names:
                    self.rules.append(rule)

            # Merge file type mappings
            self.file_type_mappings.update(other_scheme.file_type_mappings)

            # Merge categories
            self.categories.update(other_scheme.categories)

            # Merge naming patterns
            self.naming_patterns.update(other_scheme.naming_patterns)

            # Merge metadata rules
            self.metadata_rules.update(other_scheme.metadata_rules)

            # Merge configurations
            self._merge_dict(self.ai_config, other_scheme.ai_config)
            self._merge_dict(self.media_config, other_scheme.media_config)
            self._merge_dict(self.cloud_config, other_scheme.cloud_config)

            self._update_modified_time()
            return True

        except Exception as e:
            logger.error(f"Error merging schemes: {str(e)}")
            return False

    def validate_scheme(self) -> Dict[str, Any]:
        """
        Validate the organization scheme.

        Returns:
            Dictionary containing validation results
        """
        validation_results = {
            'valid': True,
            'errors': [],
            'warnings': []
        }

        try:
            # Check required fields
            if not self.name:
                validation_results['errors'].append("Scheme name is required")

            # Validate rules
            for rule in self.rules:
                if not self._validate_rule(rule):
                    validation_results['errors'].append(
                        f"Invalid rule: {rule.get('name', 'unnamed')}")

            # Check for rule conflicts
            conflicts = self._check_rule_conflicts()
            if conflicts:
                validation_results['warnings'].extend(conflicts)

            # Update validation status
            validation_results['valid'] = len(
                validation_results['errors']) == 0

            return validation_results

        except Exception as e:
            logger.error(f"Error validating scheme: {str(e)}")
            validation_results['valid'] = False
            validation_results['errors'].append(str(e))
            return validation_results

    def _validate_rule(self, rule: Dict[str, Any]) -> bool:
        """
        Validate a single organization rule.

        Args:
            rule: Rule dictionary to validate

        Returns:
            True if rule is valid, False otherwise
        """
        try:
            # Check required fields
            required_fields = ['name', 'type', 'conditions', 'actions']
            if not all(field in rule for field in required_fields):
                return False

            # Validate conditions
            if not isinstance(rule['conditions'], list) or not rule['conditions']:
                return False

            # Validate actions
            if not isinstance(rule['actions'], list) or not rule['actions']:
                return False

            return True

        except Exception:
            return False

    def _check_rule_conflicts(self) -> List[str]:
        """
        Check for conflicts between rules.

        Returns:
            List of conflict descriptions
        """
        conflicts = []

        try:
            # Check for rules with the same name
            rule_names = {}
            for rule in self.rules:
                name = rule.get('name')
                if name in rule_names:
                    conflicts.append(f"Duplicate rule name: {name}")
                rule_names[name] = True

            # Check for conflicting actions
            # This is a simplified check - in a real implementation,
            # you would need more sophisticated conflict detection
            for i, rule1 in enumerate(self.rules):
                for rule2 in self.rules[i+1:]:
                    if self._rules_conflict(rule1, rule2):
                        conflicts.append(
                            f"Potential conflict between rules: {rule1['name']} and {rule2['name']}")

            return conflicts

        except Exception as e:
            logger.error(f"Error checking rule conflicts: {str(e)}")
            return [f"Error checking conflicts: {str(e)}"]

    def _rules_conflict(self, rule1: Dict[str, Any], rule2: Dict[str, Any]) -> bool:
        """
        Check if two rules have conflicting actions.

        Args:
            rule1: First rule to check
            rule2: Second rule to check

        Returns:
            True if rules conflict, False otherwise
        """
        try:
            # This is a simplified conflict check
            # In a real implementation, you would need more sophisticated logic

            # Check if rules have overlapping conditions
            conditions_overlap = any(
                cond in rule2['conditions'] for cond in rule1['conditions'])

            if not conditions_overlap:
                return False

            # Check if rules have conflicting actions
            for action1 in rule1['actions']:
                for action2 in rule2['actions']:
                    if self._actions_conflict(action1, action2):
                        return True

            return False

        except Exception:
            return False

    def _actions_conflict(self, action1: Dict[str, Any], action2: Dict[str, Any]) -> bool:
        """
        Check if two actions conflict.

        Args:
            action1: First action to check
            action2: Second action to check

        Returns:
            True if actions conflict, False otherwise
        """
        try:
            # This is a simplified conflict check
            # In a real implementation, you would need more sophisticated logic

            # Check if actions are of the same type
            if action1['type'] != action2['type']:
                return False

            # Check for specific conflicts based on action type
            if action1['type'] == 'move':
                return action1['destination'] != action2['destination']
            elif action1['type'] == 'rename':
                return action1['pattern'] != action2['pattern']

            return False

        except Exception:
            return False

    def _merge_dict(self, target: Dict, source: Dict) -> None:
        """
        Recursively merge two dictionaries.

        Args:
            target: Target dictionary to merge into
            source: Source dictionary to merge from
        """
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._merge_dict(target[key], value)
            else:
                target[key] = value

    def _update_modified_time(self) -> None:
        """Update the modified timestamp."""
        self.modified_at = datetime.datetime.now().isoformat()

    def __str__(self) -> str:
        """String representation of the organization scheme."""
        return f"{self.name} (v{self.version}) by {self.author}"
