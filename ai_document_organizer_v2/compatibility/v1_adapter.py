"""
V1 Compatibility Module - Provides compatibility with Version 1 components

This module defines adapters that bridge V1 and V2 functionality, allowing
V1 components to work with V2 plugins and vice versa.
"""

import os
import sys
import logging
import importlib
from typing import Dict, Any, Optional, List, Callable, Type

logger = logging.getLogger("AIDocumentOrganizerV2.Compatibility")

class V1Adapter:
    """Base adapter for V1 components"""
    
    def __init__(self, plugin_manager, settings_manager):
        """
        Initialize the adapter.
        
        Args:
            plugin_manager: Plugin manager instance
            settings_manager: Settings manager instance
        """
        self.plugin_manager = plugin_manager
        self.settings_manager = settings_manager
    
    def create_instance(self):
        """Create a V1-compatible instance"""
        raise NotImplementedError("Subclasses must implement create_instance()")


class V1FileParserWrapper(V1Adapter):
    """Wrapper for V2 file parser plugins to provide V1 FileParser API"""
    
    def __init__(self, plugin_manager, settings_manager):
        """
        Initialize the wrapper.
        
        Args:
            plugin_manager: Plugin manager instance
            settings_manager: Settings manager instance
        """
        super().__init__(plugin_manager, settings_manager)
        self._parsers = {}
        self._load_parsers()
        
    def create_instance(self):
        """
        Create a V1-compatible FileParser instance
        
        Returns:
            FileParser instance or wrapper
        """
        # Return self as it implements the same interface
        return self
    
    def _load_parsers(self):
        """Load all file parser plugins"""
        file_parsers = self.plugin_manager.get_plugins_of_type("file_parser")
        for plugin_id, parser in file_parsers.items():
            if not self.plugin_manager.is_plugin_initialized(plugin_id):
                continue
                
            # Add parser for each supported extension
            for ext in parser.supported_extensions:
                self._parsers[ext.lower()] = parser
    
    def extract_text(self, file_path, file_ext):
        """
        Extract text content from various file types (V1 API)
        
        Args:
            file_path: Path to the file
            file_ext: File extension (including the dot)
            
        Returns:
            Extracted text content as a string
        """
        ext = file_ext.lower()
        if ext in self._parsers:
            try:
                result = self._parsers[ext].parse_file(file_path)
                return result.get('content', '')
            except Exception as e:
                logger.error(f"Error parsing file {file_path}: {e}")
        
        # Fall back to V1 implementation if no parser found
        # Import here to avoid circular imports
        from src.file_parser import FileParser
        v1_parser = FileParser()
        return v1_parser.extract_text(file_path, file_ext)
    
    def extract_metadata(self, file_path, file_ext):
        """
        Extract metadata from files (V1 API)
        
        Args:
            file_path: Path to the file
            file_ext: File extension (including the dot)
            
        Returns:
            Dictionary containing metadata
        """
        ext = file_ext.lower()
        if ext in self._parsers:
            try:
                result = self._parsers[ext].parse_file(file_path)
                return result.get('metadata', {})
            except Exception as e:
                logger.error(f"Error extracting metadata from {file_path}: {e}")
        
        # Fall back to V1 implementation if no parser found
        from src.file_parser import FileParser
        v1_parser = FileParser()
        return v1_parser.extract_metadata(file_path, file_ext)


class V1FileOrganizerWrapper(V1Adapter):
    """Wrapper for V2 organizer plugins to provide V1 FileOrganizer API"""
    
    def __init__(self, plugin_manager, settings_manager):
        """
        Initialize the wrapper.
        
        Args:
            plugin_manager: Plugin manager instance
            settings_manager: Settings manager instance
        """
        super().__init__(plugin_manager, settings_manager)
        self._organizers = []
        self._load_organizers()
        
    def create_instance(self):
        """
        Create a V1-compatible FileOrganizer instance
        
        Returns:
            FileOrganizer instance or wrapper
        """
        # Return self as it implements the same interface
        return self
        
        # Need access to the V1 rule manager
        from src.file_organizer import FileOrganizer
        v1_organizer = FileOrganizer()
        self.rule_manager = v1_organizer.rule_manager
    
    def _load_organizers(self):
        """Load all organizer plugins"""
        organizers = self.plugin_manager.get_plugins_of_type("organizer")
        for plugin_id, organizer in organizers.items():
            if self.plugin_manager.is_plugin_initialized(plugin_id):
                self._organizers.append(organizer)
    
    def organize_files(self, analyzed_files, target_dir, callback=None, options=None):
        """
        Organize files based on their AI analysis (V1 API)
        
        Args:
            analyzed_files: List of file information dictionaries with AI analysis
            target_dir: Target directory for organized files
            callback: Optional callback function for progress updates
            options: Dictionary with organization options
            
        Returns:
            Dictionary with organization results
        """
        if self._organizers:
            # Try using V2 organizers if available
            for organizer in self._organizers:
                try:
                    return organizer.organize_files(analyzed_files, target_dir, callback, options)
                except Exception as e:
                    logger.error(f"Error using organizer {organizer.name}: {e}")
        
        # Fall back to V1 implementation if no organizer found
        from src.file_organizer import FileOrganizer
        v1_organizer = FileOrganizer()
        return v1_organizer.organize_files(analyzed_files, target_dir, callback, options)


class V1AIAnalyzerWrapper(V1Adapter):
    """Wrapper for V2 AI analyzer plugins to provide V1 AIAnalyzer API"""
    
    def __init__(self, plugin_manager, settings_manager):
        """
        Initialize the wrapper.
        
        Args:
            plugin_manager: Plugin manager instance
            settings_manager: Settings manager instance
        """
        super().__init__(plugin_manager, settings_manager)
        self._analyzer = None
        self._load_analyzer()
        
    def create_instance(self):
        """
        Create a V1-compatible AIAnalyzer instance
        
        Returns:
            AIAnalyzer instance or wrapper
        """
        # Return self as it implements the same interface
        return self
    
    def _load_analyzer(self):
        """Load an AI analyzer plugin"""
        analyzers = self.plugin_manager.get_plugins_of_type("ai_analyzer")
        for plugin_id, analyzer in analyzers.items():
            if self.plugin_manager.is_plugin_initialized(plugin_id):
                self._analyzer = analyzer
                logger.info(f"Using AI analyzer plugin: {analyzer.name}")
                break
        
        if self._analyzer is None:
            logger.warning("No AI analyzer plugin found, falling back to V1 AIAnalyzer")
    
    def get_available_models(self):
        """
        Get list of available AI models (V1 API)
        
        Returns:
            List of model names
        """
        if self._analyzer:
            try:
                return self._analyzer.get_available_models()
            except Exception as e:
                logger.error(f"Error getting available models: {e}")
        
        # Fall back to V1 implementation
        from src.ai_analyzer import AIAnalyzer
        v1_analyzer = AIAnalyzer()
        return v1_analyzer.get_available_models()
    
    def set_model(self, model_name):
        """
        Set the model to use for analysis (V1 API)
        
        Args:
            model_name: Name of the model to use
            
        Returns:
            True if successful, False otherwise
        """
        if self._analyzer:
            try:
                return self._analyzer.set_model(model_name)
            except Exception as e:
                logger.error(f"Error setting model: {e}")
        
        # Fall back to V1 implementation
        from src.ai_analyzer import AIAnalyzer
        v1_analyzer = AIAnalyzer()
        return v1_analyzer.set_model(model_name)
    
    def analyze_content(self, text, file_type):
        """
        Analyze document content using AI (V1 API)
        
        Args:
            text: The document text content
            file_type: The type of document (CSV, Excel, HTML, etc.)
            
        Returns:
            Dictionary with analysis results
        """
        if self._analyzer:
            try:
                return self._analyzer.analyze_content(text, file_type)
            except Exception as e:
                logger.error(f"Error analyzing content: {e}")
        
        # Fall back to V1 implementation
        from src.ai_analyzer import AIAnalyzer
        v1_analyzer = AIAnalyzer()
        return v1_analyzer.analyze_content(text, file_type)
    
    def find_similar_documents(self, target_doc, document_list, max_results=5):
        """
        Find documents similar to the target document (V1 API)
        
        Args:
            target_doc: Target document info dictionary
            document_list: List of document info dictionaries to compare against
            max_results: Maximum number of similar documents to return
            
        Returns:
            List of similar document dictionaries with similarity scores
        """
        # Just use V1 implementation for now
        from src.ai_analyzer import AIAnalyzer
        v1_analyzer = AIAnalyzer()
        return v1_analyzer.find_similar_documents(target_doc, document_list, max_results)
    
    def find_related_content(self, target_doc, document_list, max_results=5):
        """
        Find documents related to the target document (V1 API)
        
        Args:
            target_doc: Target document info dictionary with content analysis
            document_list: List of document info dictionaries to compare against
            max_results: Maximum number of related documents to return
            
        Returns:
            Dictionary with relationship information and related documents
        """
        # Just use V1 implementation for now
        from src.ai_analyzer import AIAnalyzer
        v1_analyzer = AIAnalyzer()
        return v1_analyzer.find_related_content(target_doc, document_list, max_results)


class V1SettingsWrapper(V1Adapter):
    """Wrapper for V2 settings to provide V1 SettingsManager API"""
    
    def __init__(self, plugin_manager, settings_manager):
        """
        Initialize the wrapper.
        
        Args:
            plugin_manager: Plugin manager instance
            settings_manager: Settings manager instance
        """
        super().__init__(plugin_manager, settings_manager)
        
    def create_instance(self):
        """
        Create a V1-compatible SettingsManager instance
        
        Returns:
            SettingsManager instance or wrapper
        """
        # Return self as it implements the same interface
        return self
    
    def load_settings(self):
        """
        Load settings from file (V1 API)
        
        Returns:
            Dictionary with settings
        """
        # Convert V2 settings to V1 format
        v2_settings = self.settings_manager.settings
        
        # Create a V1-compatible settings dictionary
        v1_settings = {
            "version": v2_settings.get("version", "2.0.0"),
            "last_source_dir": v2_settings.get("last_source_dir", ""),
            "last_target_dir": v2_settings.get("last_target_dir", ""),
            "theme": v2_settings.get("theme", "default"),
            "batch_size": v2_settings.get("batch_processing", {}).get("batch_size", 10),
            "batch_delay": v2_settings.get("batch_processing", {}).get("batch_delay", 0.1),
            
            # Organization options
            "create_category_folders": v2_settings.get("file_organization", {}).get("create_category_folders", True),
            "generate_summaries": v2_settings.get("file_organization", {}).get("generate_summaries", True),
            "include_metadata": v2_settings.get("file_organization", {}).get("include_metadata", True),
            "copy_instead_of_move": v2_settings.get("file_organization", {}).get("copy_instead_of_move", True),
            "detect_duplicates": v2_settings.get("file_organization", {}).get("detect_duplicates", False),
            "duplicate_action": v2_settings.get("file_organization", {}).get("duplicate_action", "report"),
            "duplicate_strategy": v2_settings.get("file_organization", {}).get("duplicate_strategy", "newest"),
            "apply_tags": v2_settings.get("file_organization", {}).get("apply_tags", False),
            "suggest_tags": v2_settings.get("file_organization", {}).get("suggest_tags", False),
            
            # V1 settings structure for backward compatibility
            "organization_rules": {
                "create_category_folders": v2_settings.get("file_organization", {}).get("create_category_folders", True),
                "generate_summaries": v2_settings.get("file_organization", {}).get("generate_summaries", True),
                "include_metadata": v2_settings.get("file_organization", {}).get("include_metadata", True),
                "copy_instead_of_move": v2_settings.get("file_organization", {}).get("copy_instead_of_move", True),
                "use_custom_rules": v2_settings.get("file_organization", {}).get("use_custom_rules", False),
                "rules_file": v2_settings.get("file_organization", {}).get("rules_file", ""),
                "detect_duplicates": v2_settings.get("file_organization", {}).get("detect_duplicates", False),
                "duplicate_action": v2_settings.get("file_organization", {}).get("duplicate_action", "report"),
                "apply_tags": v2_settings.get("file_organization", {}).get("apply_tags", False),
                "suggest_tags": v2_settings.get("file_organization", {}).get("suggest_tags", False)
            }
        }
        
        return v1_settings
    
    def save_settings(self, settings):
        """
        Save settings to file (V1 API)
        
        Args:
            settings: Settings dictionary to save
            
        Returns:
            True if successful, False otherwise
        """
        # Update V2 settings with values from V1 settings
        if "last_source_dir" in settings:
            self.settings_manager.set_setting("last_source_dir", settings["last_source_dir"])
        
        if "last_target_dir" in settings:
            self.settings_manager.set_setting("last_target_dir", settings["last_target_dir"])
        
        if "theme" in settings:
            self.settings_manager.set_setting("theme", settings["theme"])
        
        if "batch_size" in settings:
            self.settings_manager.set_setting("batch_processing.batch_size", settings["batch_size"])
        
        if "batch_delay" in settings:
            self.settings_manager.set_setting("batch_processing.batch_delay", settings["batch_delay"])
        
        # Organization options
        if "organization_rules" in settings:
            org_rules = settings["organization_rules"]
            
            for key, value in org_rules.items():
                self.settings_manager.set_setting(f"file_organization.{key}", value)
        
        # Save updated settings
        return self.settings_manager.save_settings()
    
    def get_setting(self, key, default=None):
        """
        Get a setting value (V1 API)
        
        Args:
            key: Setting key
            default: Default value if setting not found
            
        Returns:
            Setting value or default if not found
        """
        # V1 uses flat structure, V2 uses hierarchical
        # Need to map between them
        if key in ["last_source_dir", "last_target_dir", "theme", "version"]:
            return self.settings_manager.get_setting(key, default)
        
        if key in ["batch_size", "batch_delay"]:
            return self.settings_manager.get_setting(f"batch_processing.{key}", default)
        
        # Organization rules are in file_organization in V2
        if key.startswith("organization_rules."):
            # Strip the organization_rules. prefix
            subkey = key[len("organization_rules."):]
            return self.settings_manager.get_setting(f"file_organization.{subkey}", default)
        
        # For other settings, try direct lookup first
        val = self.settings_manager.get_setting(key, None)
        if val is not None:
            return val
        
        # Try in file_organization
        val = self.settings_manager.get_setting(f"file_organization.{key}", None)
        if val is not None:
            return val
        
        # Try in batch_processing
        val = self.settings_manager.get_setting(f"batch_processing.{key}", None)
        if val is not None:
            return val
        
        # Fall back to default
        return default


class V1DuplicateDetectorWrapper(V1Adapter):
    """Wrapper for V2 duplicate detector plugins to provide V1 DuplicateDetector API"""
    
    def __init__(self, plugin_manager, settings_manager):
        """
        Initialize the wrapper.
        
        Args:
            plugin_manager: Plugin manager instance
            settings_manager: Settings manager instance
        """
        super().__init__(plugin_manager, settings_manager)
        self._detector = None
        self._load_detector()
        
    def create_instance(self):
        """
        Create a V1-compatible DuplicateDetector instance
        
        Returns:
            DuplicateDetector instance or wrapper
        """
        # Return self as it implements the same interface
        return self
    
    def _load_detector(self):
        """Load a duplicate detector plugin"""
        detectors = self.plugin_manager.get_plugins_of_type("duplicate_detector")
        for plugin_id, detector in detectors.items():
            if self.plugin_manager.is_plugin_initialized(plugin_id):
                self._detector = detector
                logger.info(f"Using duplicate detector plugin: {detector.name}")
                break
        
        if self._detector is None:
            logger.warning("No duplicate detector plugin found, falling back to V1 DuplicateDetector")
    
    def find_duplicates(self, files, callback=None):
        """
        Find duplicate files (V1 API)
        
        Args:
            files: List of file dictionaries with paths and metadata
            callback: Optional progress callback function
            
        Returns:
            Dictionary with duplicate groups and statistics
        """
        # Just use V1 implementation for now as we don't have a V2 duplicate detector yet
        from src.duplicate_detector import DuplicateDetector
        v1_detector = DuplicateDetector()
        return v1_detector.find_duplicates(files, callback)
    
    def check_duplicates(self, file_path, existing_files):
        """
        Check if a file is a duplicate (V1 API)
        
        Args:
            file_path: Path to the file to check
            existing_files: List of existing file dictionaries
            
        Returns:
            Dictionary with duplicate information
        """
        # Just use V1 implementation for now
        from src.duplicate_detector import DuplicateDetector
        v1_detector = DuplicateDetector()
        return v1_detector.check_duplicates(file_path, existing_files)
    
    def handle_duplicates(self, duplicate_groups, action="report", target_dir=None, keep_strategy="newest"):
        """
        Handle duplicate files (V1 API)
        
        Args:
            duplicate_groups: List of duplicate file groups
            action: Action to take ('report', 'move', 'delete')
            target_dir: Target directory for moving duplicates
            keep_strategy: Strategy for keeping files
            
        Returns:
            Dictionary with handling results
        """
        # Just use V1 implementation for now
        from src.duplicate_detector import DuplicateDetector
        v1_detector = DuplicateDetector()
        return v1_detector.handle_duplicates(duplicate_groups, action, target_dir, keep_strategy)


class CompatibilityManager:
    """
    Manages compatibility between V1 and V2 components.
    
    This class provides adapters for V1 components to work with V2 plugins,
    and bridges the gap between the two architectures.
    """
    
    def __init__(self, plugin_manager, settings_manager):
        """
        Initialize the compatibility manager.
        
        Args:
            plugin_manager: PluginManager instance
            settings_manager: SettingsManager instance
        """
        self.plugin_manager = plugin_manager
        self.settings_manager = settings_manager
        
        # Adapter registry
        self.adapters = {
            'FileParser': V1FileParserWrapper,
            'FileOrganizer': V1FileOrganizerWrapper,
            'AIAnalyzer': V1AIAnalyzerWrapper,
            'SettingsManager': V1SettingsWrapper,
            'DuplicateDetector': V1DuplicateDetectorWrapper
        }
        
        # Adapter instances cache
        self._adapter_instances = {}
        
        logger.info("Compatibility manager initialized")
    
    def get_adapter(self, adapter_name):
        """
        Get an adapter for a V1 component.
        
        Args:
            adapter_name: Name of the V1 component to adapt
            
        Returns:
            Adapter instance or None if not found
        """
        if adapter_name not in self.adapters:
            logger.warning(f"No adapter found for {adapter_name}")
            return None
        
        # Check if we already have an instance of this adapter
        if adapter_name in self._adapter_instances:
            return self._adapter_instances[adapter_name]
        
        # Create a new adapter instance
        try:
            adapter_class = self.adapters[adapter_name]
            adapter = adapter_class(self.plugin_manager, self.settings_manager)
            self._adapter_instances[adapter_name] = adapter
            return adapter
        except Exception as e:
            logger.error(f"Error creating adapter for {adapter_name}: {e}")
            return None