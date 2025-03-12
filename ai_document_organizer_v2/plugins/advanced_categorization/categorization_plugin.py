"""
Advanced Categorization Plugin for AI Document Organizer V2.
"""

import json
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from ai_document_organizer_v2.core.plugin_base import PluginBase
from ai_document_organizer_v2.plugins.advanced_categorization.models.category import Category, CategoryHierarchy
from ai_document_organizer_v2.plugins.advanced_categorization.models.taxonomy import Taxonomy, TaxonomyType


logger = logging.getLogger(__name__)


class AdvancedCategorizationPlugin(PluginBase):
    """
    Advanced Categorization Plugin for AI Document Organizer V2.
    
    This plugin provides:
    - Hierarchical category management
    - Multiple taxonomy support
    - AI-assisted categorization
    - Rule-based categorization
    - Category suggestions
    - Bulk categorization
    """
    
    plugin_name = "advanced_categorization"
    plugin_version = "1.0.0"
    plugin_description = "Advanced categorization with hierarchical categories and multiple taxonomies"
    plugin_author = "AI Document Organizer Team"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the advanced categorization plugin.
        
        Args:
            config: Optional configuration dictionary
        """
        super().__init__(config)
        
        # Configuration
        self.config = config or {}
        self.data_dir = self.config.get("data_dir", "data/categories")
        
        # State
        self.taxonomies = {}  # taxonomy_id -> Taxonomy
        self.category_hierarchies = {}  # taxonomy_id -> CategoryHierarchy
        self.default_taxonomy_id = None
        
        # AI categorization settings
        self.use_ai_categorization = self.config.get("use_ai_categorization", True)
        self.ai_confidence_threshold = self.config.get("ai_confidence_threshold", 0.7)
        self.max_suggestions = self.config.get("max_suggestions", 5)
        
        # Custom categorization rules
        self.custom_rules = []
        
        # Cached category matches
        self.category_match_cache = {}  # file_path -> {taxonomy_id -> [category_ids]}
    
    def initialize(self) -> bool:
        """
        Initialize the plugin.
        
        Returns:
            True if initialization was successful, False otherwise
        """
        logger.info("Initializing AdvancedCategorizationPlugin")
        
        # Create data directory if it doesn't exist
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Load taxonomies and categories
        self._load_taxonomies()
        self._load_categories()
        
        # Create default taxonomy if none exists
        if not self.taxonomies:
            self._create_default_taxonomy()
        
        # Load custom rules
        self._load_custom_rules()
        
        return True
    
    def activate(self) -> bool:
        """
        Activate the plugin.
        
        Returns:
            True if activation was successful, False otherwise
        """
        logger.info("Activating AdvancedCategorizationPlugin")
        return True
    
    def deactivate(self) -> bool:
        """
        Deactivate the plugin.
        
        Returns:
            True if deactivation was successful, False otherwise
        """
        logger.info("Deactivating AdvancedCategorizationPlugin")
        return True
    
    def shutdown(self) -> bool:
        """
        Shutdown the plugin and clean up resources.
        
        Returns:
            True if shutdown was successful, False otherwise
        """
        logger.info("Shutting down AdvancedCategorizationPlugin")
        
        # Save taxonomies and categories
        self._save_taxonomies()
        self._save_categories()
        
        # Save custom rules
        self._save_custom_rules()
        
        return True
    
    def get_info(self) -> Dict[str, Any]:
        """
        Get information about the plugin.
        
        Returns:
            Dictionary with plugin information
        """
        info = super().get_info()
        info.update({
            "taxonomies_count": len(self.taxonomies),
            "categories_count": sum(len(hierarchy.categories) for hierarchy in self.category_hierarchies.values()),
            "default_taxonomy_id": self.default_taxonomy_id,
            "use_ai_categorization": self.use_ai_categorization,
            "ai_confidence_threshold": self.ai_confidence_threshold,
            "custom_rules_count": len(self.custom_rules)
        })
        return info
    
    def get_type(self) -> str:
        """
        Get the plugin type.
        
        Returns:
            Plugin type
        """
        return "categorization"
    
    def get_capabilities(self) -> List[str]:
        """
        Get the plugin capabilities.
        
        Returns:
            List of capabilities
        """
        return [
            "hierarchical_categories",
            "multiple_taxonomies",
            "ai_categorization",
            "rule_based_categorization",
            "category_suggestions",
            "bulk_categorization"
        ]
    
    def _create_default_taxonomy(self) -> str:
        """
        Create a default taxonomy with some common categories.
        
        Returns:
            ID of the created taxonomy
        """
        # Create default taxonomy
        default_taxonomy = Taxonomy(
            name="Default Taxonomy",
            description="Default hierarchical taxonomy",
            taxonomy_type=TaxonomyType.HIERARCHICAL,
            is_default=True,
            is_system=True
        )
        
        self.taxonomies[default_taxonomy.taxonomy_id] = default_taxonomy
        self.default_taxonomy_id = default_taxonomy.taxonomy_id
        
        # Create category hierarchy for the taxonomy
        hierarchy = CategoryHierarchy()
        self.category_hierarchies[default_taxonomy.taxonomy_id] = hierarchy
        
        # Create some common root categories
        document_category = Category(
            name="Documents",
            description="General documents",
            taxonomy_id=default_taxonomy.taxonomy_id,
            is_system=True,
            keywords=["document", "report", "paper"],
            icon="📄"
        )
        
        image_category = Category(
            name="Images",
            description="Image files",
            taxonomy_id=default_taxonomy.taxonomy_id,
            is_system=True,
            keywords=["image", "photo", "picture"],
            icon="🖼️"
        )
        
        media_category = Category(
            name="Media",
            description="Media files",
            taxonomy_id=default_taxonomy.taxonomy_id,
            is_system=True,
            keywords=["media", "video", "audio"],
            icon="🎬"
        )
        
        data_category = Category(
            name="Data",
            description="Data files",
            taxonomy_id=default_taxonomy.taxonomy_id,
            is_system=True,
            keywords=["data", "spreadsheet", "database"],
            icon="📊"
        )
        
        # Add root categories to hierarchy
        hierarchy.add_category(document_category)
        hierarchy.add_category(image_category)
        hierarchy.add_category(media_category)
        hierarchy.add_category(data_category)
        
        # Add category IDs to taxonomy
        default_taxonomy.add_category_id(document_category.category_id)
        default_taxonomy.add_category_id(image_category.category_id)
        default_taxonomy.add_category_id(media_category.category_id)
        default_taxonomy.add_category_id(data_category.category_id)
        
        # Create some subcategories
        
        # Document subcategories
        text_category = Category(
            name="Text Documents",
            description="Plain text documents",
            parent_id=document_category.category_id,
            taxonomy_id=default_taxonomy.taxonomy_id,
            is_system=True,
            keywords=["text", "txt", "plain text"],
            icon="📝"
        )
        
        pdf_category = Category(
            name="PDF Documents",
            description="PDF documents",
            parent_id=document_category.category_id,
            taxonomy_id=default_taxonomy.taxonomy_id,
            is_system=True,
            keywords=["pdf", "portable document format"],
            icon="📑"
        )
        
        word_category = Category(
            name="Word Documents",
            description="Microsoft Word documents",
            parent_id=document_category.category_id,
            taxonomy_id=default_taxonomy.taxonomy_id,
            is_system=True,
            keywords=["word", "doc", "docx", "microsoft word"],
            icon="📘"
        )
        
        # Image subcategories
        photo_category = Category(
            name="Photos",
            description="Photographic images",
            parent_id=image_category.category_id,
            taxonomy_id=default_taxonomy.taxonomy_id,
            is_system=True,
            keywords=["photo", "photograph", "jpg", "jpeg"],
            icon="📸"
        )
        
        diagram_category = Category(
            name="Diagrams",
            description="Diagrams and charts",
            parent_id=image_category.category_id,
            taxonomy_id=default_taxonomy.taxonomy_id,
            is_system=True,
            keywords=["diagram", "chart", "graph", "schematic"],
            icon="📈"
        )
        
        # Media subcategories
        video_category = Category(
            name="Videos",
            description="Video files",
            parent_id=media_category.category_id,
            taxonomy_id=default_taxonomy.taxonomy_id,
            is_system=True,
            keywords=["video", "movie", "mp4", "avi"],
            icon="🎥"
        )
        
        audio_category = Category(
            name="Audio",
            description="Audio files",
            parent_id=media_category.category_id,
            taxonomy_id=default_taxonomy.taxonomy_id,
            is_system=True,
            keywords=["audio", "sound", "mp3", "wav"],
            icon="🎧"
        )
        
        # Data subcategories
        spreadsheet_category = Category(
            name="Spreadsheets",
            description="Spreadsheet files",
            parent_id=data_category.category_id,
            taxonomy_id=default_taxonomy.taxonomy_id,
            is_system=True,
            keywords=["spreadsheet", "excel", "xlsx", "csv"],
            icon="📉"
        )
        
        database_category = Category(
            name="Databases",
            description="Database files",
            parent_id=data_category.category_id,
            taxonomy_id=default_taxonomy.taxonomy_id,
            is_system=True,
            keywords=["database", "db", "sql", "sqlite"],
            icon="🗃️"
        )
        
        # Add subcategories to hierarchy
        hierarchy.add_category(text_category)
        hierarchy.add_category(pdf_category)
        hierarchy.add_category(word_category)
        hierarchy.add_category(photo_category)
        hierarchy.add_category(diagram_category)
        hierarchy.add_category(video_category)
        hierarchy.add_category(audio_category)
        hierarchy.add_category(spreadsheet_category)
        hierarchy.add_category(database_category)
        
        # Add category IDs to taxonomy
        default_taxonomy.add_category_id(text_category.category_id)
        default_taxonomy.add_category_id(pdf_category.category_id)
        default_taxonomy.add_category_id(word_category.category_id)
        default_taxonomy.add_category_id(photo_category.category_id)
        default_taxonomy.add_category_id(diagram_category.category_id)
        default_taxonomy.add_category_id(video_category.category_id)
        default_taxonomy.add_category_id(audio_category.category_id)
        default_taxonomy.add_category_id(spreadsheet_category.category_id)
        default_taxonomy.add_category_id(database_category.category_id)
        
        # Save
        self._save_taxonomy(default_taxonomy)
        self._save_category_hierarchy(default_taxonomy.taxonomy_id, hierarchy)
        
        return default_taxonomy.taxonomy_id
    
    def _load_taxonomies(self) -> None:
        """Load taxonomies from files."""
        taxonomy_file = os.path.join(self.data_dir, 'taxonomies.json')
        if os.path.exists(taxonomy_file):
            try:
                with open(taxonomy_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                self.taxonomies = {}
                for taxonomy_data in data.get('taxonomies', []):
                    taxonomy = Taxonomy.from_dict(taxonomy_data)
                    self.taxonomies[taxonomy.taxonomy_id] = taxonomy
                
                self.default_taxonomy_id = data.get('default_taxonomy_id')
                
                logger.info(f"Loaded {len(self.taxonomies)} taxonomies")
            except Exception as e:
                logger.error(f"Error loading taxonomies: {e}")
                self.taxonomies = {}
        else:
            logger.info("No taxonomies file found, starting with empty taxonomies")
            self.taxonomies = {}
    
    def _save_taxonomies(self) -> None:
        """Save taxonomies to files."""
        os.makedirs(self.data_dir, exist_ok=True)
        
        taxonomy_file = os.path.join(self.data_dir, 'taxonomies.json')
        try:
            data = {
                'taxonomies': [taxonomy.to_dict() for taxonomy in self.taxonomies.values()],
                'default_taxonomy_id': self.default_taxonomy_id
            }
            
            with open(taxonomy_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved {len(self.taxonomies)} taxonomies")
        except Exception as e:
            logger.error(f"Error saving taxonomies: {e}")
    
    def _save_taxonomy(self, taxonomy: Taxonomy) -> None:
        """
        Save a single taxonomy.
        
        Args:
            taxonomy: Taxonomy to save
        """
        # Update taxonomies dictionary
        self.taxonomies[taxonomy.taxonomy_id] = taxonomy
        
        # Save all taxonomies
        self._save_taxonomies()
    
    def _load_categories(self) -> None:
        """Load categories for all taxonomies."""
        self.category_hierarchies = {}
        
        # Load categories for each taxonomy
        for taxonomy_id in self.taxonomies:
            category_file = os.path.join(self.data_dir, f'categories_{taxonomy_id}.json')
            if os.path.exists(category_file):
                try:
                    with open(category_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    hierarchy = CategoryHierarchy.from_dict(data)
                    self.category_hierarchies[taxonomy_id] = hierarchy
                    
                    logger.info(f"Loaded {len(hierarchy.categories)} categories for taxonomy {taxonomy_id}")
                except Exception as e:
                    logger.error(f"Error loading categories for taxonomy {taxonomy_id}: {e}")
                    self.category_hierarchies[taxonomy_id] = CategoryHierarchy()
            else:
                logger.info(f"No categories file found for taxonomy {taxonomy_id}, starting with empty categories")
                self.category_hierarchies[taxonomy_id] = CategoryHierarchy()
    
    def _save_categories(self) -> None:
        """Save categories for all taxonomies."""
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Save categories for each taxonomy
        for taxonomy_id, hierarchy in self.category_hierarchies.items():
            self._save_category_hierarchy(taxonomy_id, hierarchy)
    
    def _save_category_hierarchy(self, taxonomy_id: str, hierarchy: CategoryHierarchy) -> None:
        """
        Save a category hierarchy for a taxonomy.
        
        Args:
            taxonomy_id: Taxonomy ID
            hierarchy: Category hierarchy to save
        """
        category_file = os.path.join(self.data_dir, f'categories_{taxonomy_id}.json')
        try:
            data = hierarchy.to_dict()
            
            with open(category_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved {len(hierarchy.categories)} categories for taxonomy {taxonomy_id}")
        except Exception as e:
            logger.error(f"Error saving categories for taxonomy {taxonomy_id}: {e}")
    
    def _load_custom_rules(self) -> None:
        """Load custom categorization rules."""
        rules_file = os.path.join(self.data_dir, 'category_rules.json')
        if os.path.exists(rules_file):
            try:
                with open(rules_file, 'r', encoding='utf-8') as f:
                    self.custom_rules = json.load(f)
                
                logger.info(f"Loaded {len(self.custom_rules)} custom categorization rules")
            except Exception as e:
                logger.error(f"Error loading custom categorization rules: {e}")
                self.custom_rules = []
        else:
            logger.info("No custom categorization rules file found, starting with empty rules")
            self.custom_rules = []
    
    def _save_custom_rules(self) -> None:
        """Save custom categorization rules."""
        os.makedirs(self.data_dir, exist_ok=True)
        
        rules_file = os.path.join(self.data_dir, 'category_rules.json')
        try:
            with open(rules_file, 'w', encoding='utf-8') as f:
                json.dump(self.custom_rules, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved {len(self.custom_rules)} custom categorization rules")
        except Exception as e:
            logger.error(f"Error saving custom categorization rules: {e}")
    
    def create_taxonomy(self, 
                      name: str,
                      description: Optional[str] = None,
                      taxonomy_type: Union[str, TaxonomyType] = TaxonomyType.HIERARCHICAL,
                      **kwargs) -> str:
        """
        Create a new taxonomy.
        
        Args:
            name: Taxonomy name
            description: Optional taxonomy description
            taxonomy_type: Taxonomy type
            **kwargs: Additional taxonomy properties
            
        Returns:
            ID of the created taxonomy
        """
        # Create taxonomy
        taxonomy = Taxonomy(name=name, description=description, taxonomy_type=taxonomy_type, **kwargs)
        
        # Add to taxonomies
        self.taxonomies[taxonomy.taxonomy_id] = taxonomy
        
        # Create empty category hierarchy
        self.category_hierarchies[taxonomy.taxonomy_id] = CategoryHierarchy()
        
        # If this is the first taxonomy, make it default
        if len(self.taxonomies) == 1:
            self.default_taxonomy_id = taxonomy.taxonomy_id
            taxonomy.is_default = True
        
        # Save
        self._save_taxonomy(taxonomy)
        self._save_category_hierarchy(taxonomy.taxonomy_id, self.category_hierarchies[taxonomy.taxonomy_id])
        
        return taxonomy.taxonomy_id
    
    def update_taxonomy(self, 
                      taxonomy_id: str,
                      name: Optional[str] = None,
                      description: Optional[str] = None,
                      **kwargs) -> bool:
        """
        Update a taxonomy.
        
        Args:
            taxonomy_id: ID of the taxonomy to update
            name: Optional new name
            description: Optional new description
            **kwargs: Additional properties to update
            
        Returns:
            True if update was successful, False otherwise
        """
        if taxonomy_id not in self.taxonomies:
            logger.error(f"Taxonomy {taxonomy_id} not found")
            return False
        
        taxonomy = self.taxonomies[taxonomy_id]
        
        # Update properties
        if name is not None:
            taxonomy.name = name
        
        if description is not None:
            taxonomy.description = description
        
        # Update other properties
        for key, value in kwargs.items():
            if hasattr(taxonomy, key):
                setattr(taxonomy, key, value)
            elif key == 'metadata':
                taxonomy.metadata.update(value)
        
        # Update timestamp
        taxonomy.updated_at = time.time()
        
        # Save
        self._save_taxonomy(taxonomy)
        
        return True
    
    def delete_taxonomy(self, taxonomy_id: str, force: bool = False) -> bool:
        """
        Delete a taxonomy.
        
        Args:
            taxonomy_id: ID of the taxonomy to delete
            force: Whether to force deletion even if it's a system taxonomy
            
        Returns:
            True if deletion was successful, False otherwise
        """
        if taxonomy_id not in self.taxonomies:
            logger.error(f"Taxonomy {taxonomy_id} not found")
            return False
        
        taxonomy = self.taxonomies[taxonomy_id]
        
        # Don't delete system taxonomies unless forced
        if taxonomy.is_system and not force:
            logger.error(f"Cannot delete system taxonomy {taxonomy_id} without force flag")
            return False
        
        # Check if it's the default taxonomy
        if taxonomy_id == self.default_taxonomy_id:
            # Find another taxonomy to make default
            for tid in self.taxonomies:
                if tid != taxonomy_id:
                    self.default_taxonomy_id = tid
                    self.taxonomies[tid].is_default = True
                    break
            else:
                # No other taxonomies, so clear default
                self.default_taxonomy_id = None
        
        # Delete from taxonomies
        del self.taxonomies[taxonomy_id]
        
        # Delete category hierarchy
        if taxonomy_id in self.category_hierarchies:
            del self.category_hierarchies[taxonomy_id]
        
        # Delete category file
        category_file = os.path.join(self.data_dir, f'categories_{taxonomy_id}.json')
        if os.path.exists(category_file):
            try:
                os.remove(category_file)
            except Exception as e:
                logger.error(f"Error deleting category file for taxonomy {taxonomy_id}: {e}")
        
        # Save taxonomies
        self._save_taxonomies()
        
        return True
    
    def get_taxonomy(self, taxonomy_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a taxonomy by ID.
        
        Args:
            taxonomy_id: Taxonomy ID
            
        Returns:
            Dictionary with taxonomy information or None if not found
        """
        if taxonomy_id not in self.taxonomies:
            return None
        
        return self.taxonomies[taxonomy_id].to_dict()
    
    def get_all_taxonomies(self) -> List[Dict[str, Any]]:
        """
        Get all taxonomies.
        
        Returns:
            List of taxonomy dictionaries
        """
        return [taxonomy.to_dict() for taxonomy in self.taxonomies.values()]
    
    def set_default_taxonomy(self, taxonomy_id: str) -> bool:
        """
        Set the default taxonomy.
        
        Args:
            taxonomy_id: ID of the taxonomy to set as default
            
        Returns:
            True if successful, False otherwise
        """
        if taxonomy_id not in self.taxonomies:
            logger.error(f"Taxonomy {taxonomy_id} not found")
            return False
        
        # Clear default flag on current default
        if self.default_taxonomy_id in self.taxonomies:
            self.taxonomies[self.default_taxonomy_id].is_default = False
        
        # Set new default
        self.default_taxonomy_id = taxonomy_id
        self.taxonomies[taxonomy_id].is_default = True
        
        # Save
        self._save_taxonomies()
        
        return True
    
    def get_default_taxonomy_id(self) -> Optional[str]:
        """
        Get the ID of the default taxonomy.
        
        Returns:
            Default taxonomy ID or None if no default
        """
        return self.default_taxonomy_id
    
    def create_category(self,
                       name: str,
                       taxonomy_id: Optional[str] = None,
                       parent_id: Optional[str] = None,
                       description: Optional[str] = None,
                       **kwargs) -> str:
        """
        Create a new category.
        
        Args:
            name: Category name
            taxonomy_id: Optional taxonomy ID (default: default taxonomy)
            parent_id: Optional parent category ID
            description: Optional category description
            **kwargs: Additional category properties
            
        Returns:
            ID of the created category
        """
        # Use default taxonomy if not specified
        if taxonomy_id is None:
            if self.default_taxonomy_id is None:
                if not self.taxonomies:
                    # Create default taxonomy
                    self._create_default_taxonomy()
                else:
                    # Use first taxonomy
                    taxonomy_id = next(iter(self.taxonomies))
            else:
                taxonomy_id = self.default_taxonomy_id
        
        # Check if taxonomy exists
        if taxonomy_id not in self.taxonomies:
            logger.error(f"Taxonomy {taxonomy_id} not found")
            return None
        
        taxonomy = self.taxonomies[taxonomy_id]
        
        # Check parent if specified
        if parent_id:
            if taxonomy_id not in self.category_hierarchies:
                logger.error(f"Category hierarchy for taxonomy {taxonomy_id} not found")
                return None
            
            hierarchy = self.category_hierarchies[taxonomy_id]
            
            if parent_id not in hierarchy.categories:
                logger.error(f"Parent category {parent_id} not found in taxonomy {taxonomy_id}")
                return None
        
        # Create category
        category = Category(
            name=name,
            taxonomy_id=taxonomy_id,
            parent_id=parent_id,
            description=description,
            **kwargs
        )
        
        # Add to hierarchy
        if taxonomy_id not in self.category_hierarchies:
            self.category_hierarchies[taxonomy_id] = CategoryHierarchy()
        
        hierarchy = self.category_hierarchies[taxonomy_id]
        hierarchy.add_category(category)
        
        # Add to taxonomy
        taxonomy.add_category_id(category.category_id)
        
        # Save
        self._save_taxonomy(taxonomy)
        self._save_category_hierarchy(taxonomy_id, hierarchy)
        
        return category.category_id
    
    def update_category(self,
                       category_id: str,
                       taxonomy_id: str,
                       name: Optional[str] = None,
                       description: Optional[str] = None,
                       **kwargs) -> bool:
        """
        Update a category.
        
        Args:
            category_id: ID of the category to update
            taxonomy_id: Taxonomy ID
            name: Optional new name
            description: Optional new description
            **kwargs: Additional properties to update
            
        Returns:
            True if update was successful, False otherwise
        """
        if taxonomy_id not in self.category_hierarchies:
            logger.error(f"Category hierarchy for taxonomy {taxonomy_id} not found")
            return False
        
        hierarchy = self.category_hierarchies[taxonomy_id]
        
        if category_id not in hierarchy.categories:
            logger.error(f"Category {category_id} not found in taxonomy {taxonomy_id}")
            return False
        
        category = hierarchy.categories[category_id]
        
        # Don't modify system categories
        if category.is_system and kwargs.get('is_system') is not True:
            logger.warning(f"Modifying system category {category_id}")
        
        # Update properties
        if name is not None:
            category.name = name
        
        if description is not None:
            category.description = description
        
        # Update other properties
        for key, value in kwargs.items():
            if hasattr(category, key):
                setattr(category, key, value)
            elif key == 'keywords' and value is not None:
                category.keywords = value
            elif key == 'patterns' and value is not None:
                category.patterns = value
            elif key == 'metadata' and value is not None:
                category.metadata.update(value)
        
        # Update timestamp
        category.updated_at = time.time()
        
        # Save
        self._save_category_hierarchy(taxonomy_id, hierarchy)
        
        return True
    
    def delete_category(self, 
                      category_id: str, 
                      taxonomy_id: str, 
                      recursive: bool = False,
                      force: bool = False) -> bool:
        """
        Delete a category.
        
        Args:
            category_id: ID of the category to delete
            taxonomy_id: Taxonomy ID
            recursive: Whether to delete child categories
            force: Whether to force deletion even if it's a system category
            
        Returns:
            True if deletion was successful, False otherwise
        """
        if taxonomy_id not in self.category_hierarchies:
            logger.error(f"Category hierarchy for taxonomy {taxonomy_id} not found")
            return False
        
        hierarchy = self.category_hierarchies[taxonomy_id]
        
        if category_id not in hierarchy.categories:
            logger.error(f"Category {category_id} not found in taxonomy {taxonomy_id}")
            return False
        
        category = hierarchy.categories[category_id]
        
        # Don't delete system categories unless forced
        if category.is_system and not force:
            logger.error(f"Cannot delete system category {category_id} without force flag")
            return False
        
        # Remove from hierarchy
        result = hierarchy.remove_category(category_id, recursive=recursive)
        
        if not result:
            logger.error(f"Failed to remove category {category_id} from hierarchy")
            return False
        
        # Remove from taxonomy
        if taxonomy_id in self.taxonomies:
            taxonomy = self.taxonomies[taxonomy_id]
            taxonomy.remove_category_id(category_id)
            self._save_taxonomy(taxonomy)
        
        # Save
        self._save_category_hierarchy(taxonomy_id, hierarchy)
        
        return True
    
    def move_category(self, 
                    category_id: str, 
                    taxonomy_id: str, 
                    new_parent_id: Optional[str] = None) -> bool:
        """
        Move a category to a new parent.
        
        Args:
            category_id: ID of the category to move
            taxonomy_id: Taxonomy ID
            new_parent_id: ID of the new parent category, or None to make it a root
            
        Returns:
            True if move was successful, False otherwise
        """
        if taxonomy_id not in self.category_hierarchies:
            logger.error(f"Category hierarchy for taxonomy {taxonomy_id} not found")
            return False
        
        hierarchy = self.category_hierarchies[taxonomy_id]
        
        if category_id not in hierarchy.categories:
            logger.error(f"Category {category_id} not found in taxonomy {taxonomy_id}")
            return False
        
        # Check new parent if specified
        if new_parent_id and new_parent_id not in hierarchy.categories:
            logger.error(f"New parent category {new_parent_id} not found in taxonomy {taxonomy_id}")
            return False
        
        # Move in hierarchy
        result = hierarchy.move_category(category_id, new_parent_id)
        
        if not result:
            logger.error(f"Failed to move category {category_id} in hierarchy")
            return False
        
        # Save
        self._save_category_hierarchy(taxonomy_id, hierarchy)
        
        return True
    
    def get_category(self, 
                   category_id: str, 
                   taxonomy_id: str,
                   include_ancestry: bool = False,
                   include_descendants: bool = False) -> Optional[Dict[str, Any]]:
        """
        Get a category by ID.
        
        Args:
            category_id: Category ID
            taxonomy_id: Taxonomy ID
            include_ancestry: Whether to include ancestor categories
            include_descendants: Whether to include descendant categories
            
        Returns:
            Dictionary with category information or None if not found
        """
        if taxonomy_id not in self.category_hierarchies:
            logger.error(f"Category hierarchy for taxonomy {taxonomy_id} not found")
            return None
        
        hierarchy = self.category_hierarchies[taxonomy_id]
        
        if category_id not in hierarchy.categories:
            logger.error(f"Category {category_id} not found in taxonomy {taxonomy_id}")
            return None
        
        category = hierarchy.categories[category_id]
        result = category.to_dict()
        
        # Include ancestry if requested
        if include_ancestry:
            ancestors = hierarchy.get_ancestors(category_id)
            result['ancestry'] = [ancestor.to_dict() for ancestor in ancestors]
        
        # Include descendants if requested
        if include_descendants:
            descendants = hierarchy.get_descendants(category_id)
            result['descendants'] = [descendant.to_dict() for descendant in descendants]
        
        return result
    
    def get_categories(self, 
                     taxonomy_id: str,
                     parent_id: Optional[str] = None,
                     recursive: bool = False) -> List[Dict[str, Any]]:
        """
        Get categories for a taxonomy.
        
        Args:
            taxonomy_id: Taxonomy ID
            parent_id: Optional parent category ID to get children
            recursive: Whether to recursively get all descendants
            
        Returns:
            List of category dictionaries
        """
        if taxonomy_id not in self.category_hierarchies:
            logger.error(f"Category hierarchy for taxonomy {taxonomy_id} not found")
            return []
        
        hierarchy = self.category_hierarchies[taxonomy_id]
        
        if parent_id:
            # Get children of parent
            if parent_id not in hierarchy.categories:
                logger.error(f"Parent category {parent_id} not found in taxonomy {taxonomy_id}")
                return []
            
            if recursive:
                # Get all descendants
                descendants = hierarchy.get_descendants(parent_id)
                return [category.to_dict() for category in descendants]
            else:
                # Get direct children
                children = hierarchy.get_children(parent_id)
                return [category.to_dict() for category in children]
        else:
            # Get root categories or all categories
            if recursive:
                # Get all categories
                return [category.to_dict() for category in hierarchy.categories.values()]
            else:
                # Get root categories
                root_categories = hierarchy.get_root_categories()
                return [category.to_dict() for category in root_categories]
    
    def find_categories(self, 
                      query: str, 
                      taxonomy_id: Optional[str] = None,
                      search_type: str = 'name',
                      exact_match: bool = False) -> List[Dict[str, Any]]:
        """
        Find categories by name, keyword, or pattern.
        
        Args:
            query: Search query
            taxonomy_id: Optional taxonomy ID to search in
            search_type: Type of search ('name', 'keyword', 'pattern')
            exact_match: Whether to require exact match for name search
            
        Returns:
            List of matching category dictionaries
        """
        results = []
        
        # Determine taxonomies to search
        taxonomies_to_search = []
        if taxonomy_id:
            if taxonomy_id in self.category_hierarchies:
                taxonomies_to_search.append(taxonomy_id)
            else:
                logger.error(f"Taxonomy {taxonomy_id} not found")
                return []
        else:
            taxonomies_to_search = list(self.category_hierarchies.keys())
        
        # Search in each taxonomy
        for tax_id in taxonomies_to_search:
            hierarchy = self.category_hierarchies[tax_id]
            
            if search_type == 'name':
                # Search by name
                matches = hierarchy.find_categories_by_name(query, exact_match=exact_match)
                for category in matches:
                    results.append({
                        'category': category.to_dict(),
                        'taxonomy_id': tax_id
                    })
            elif search_type == 'keyword':
                # Search by keyword
                matches = hierarchy.find_categories_by_keyword(query)
                for category in matches:
                    results.append({
                        'category': category.to_dict(),
                        'taxonomy_id': tax_id
                    })
            elif search_type == 'pattern':
                # Search by pattern (in patterns)
                for category in hierarchy.categories.values():
                    for pattern in category.patterns:
                        if query.lower() in pattern.lower():
                            results.append({
                                'category': category.to_dict(),
                                'taxonomy_id': tax_id
                            })
        
        return results
    
    def get_category_path(self, 
                        category_id: str, 
                        taxonomy_id: str) -> List[Dict[str, Any]]:
        """
        Get the path from root to the specified category.
        
        Args:
            category_id: Category ID
            taxonomy_id: Taxonomy ID
            
        Returns:
            List of category dictionaries from root to the specified category
        """
        if taxonomy_id not in self.category_hierarchies:
            logger.error(f"Category hierarchy for taxonomy {taxonomy_id} not found")
            return []
        
        hierarchy = self.category_hierarchies[taxonomy_id]
        
        if category_id not in hierarchy.categories:
            logger.error(f"Category {category_id} not found in taxonomy {taxonomy_id}")
            return []
        
        path = hierarchy.get_path(category_id)
        return [category.to_dict() for category in path]
    
    def add_category_keyword(self, 
                           category_id: str, 
                           taxonomy_id: str, 
                           keyword: str) -> bool:
        """
        Add a keyword to a category.
        
        Args:
            category_id: Category ID
            taxonomy_id: Taxonomy ID
            keyword: Keyword to add
            
        Returns:
            True if successful, False otherwise
        """
        if taxonomy_id not in self.category_hierarchies:
            logger.error(f"Category hierarchy for taxonomy {taxonomy_id} not found")
            return False
        
        hierarchy = self.category_hierarchies[taxonomy_id]
        
        if category_id not in hierarchy.categories:
            logger.error(f"Category {category_id} not found in taxonomy {taxonomy_id}")
            return False
        
        category = hierarchy.categories[category_id]
        category.add_keyword(keyword)
        
        # Save
        self._save_category_hierarchy(taxonomy_id, hierarchy)
        
        return True
    
    def remove_category_keyword(self, 
                              category_id: str, 
                              taxonomy_id: str, 
                              keyword: str) -> bool:
        """
        Remove a keyword from a category.
        
        Args:
            category_id: Category ID
            taxonomy_id: Taxonomy ID
            keyword: Keyword to remove
            
        Returns:
            True if successful, False otherwise
        """
        if taxonomy_id not in self.category_hierarchies:
            logger.error(f"Category hierarchy for taxonomy {taxonomy_id} not found")
            return False
        
        hierarchy = self.category_hierarchies[taxonomy_id]
        
        if category_id not in hierarchy.categories:
            logger.error(f"Category {category_id} not found in taxonomy {taxonomy_id}")
            return False
        
        category = hierarchy.categories[category_id]
        result = category.remove_keyword(keyword)
        
        # Save if changed
        if result:
            self._save_category_hierarchy(taxonomy_id, hierarchy)
        
        return result
    
    def add_category_pattern(self, 
                           category_id: str, 
                           taxonomy_id: str, 
                           pattern: str) -> bool:
        """
        Add a regex pattern to a category.
        
        Args:
            category_id: Category ID
            taxonomy_id: Taxonomy ID
            pattern: Regex pattern to add
            
        Returns:
            True if successful, False otherwise
        """
        if taxonomy_id not in self.category_hierarchies:
            logger.error(f"Category hierarchy for taxonomy {taxonomy_id} not found")
            return False
        
        hierarchy = self.category_hierarchies[taxonomy_id]
        
        if category_id not in hierarchy.categories:
            logger.error(f"Category {category_id} not found in taxonomy {taxonomy_id}")
            return False
        
        # Validate pattern
        try:
            re.compile(pattern)
        except re.error:
            logger.error(f"Invalid regex pattern: {pattern}")
            return False
        
        category = hierarchy.categories[category_id]
        category.add_pattern(pattern)
        
        # Save
        self._save_category_hierarchy(taxonomy_id, hierarchy)
        
        return True
    
    def remove_category_pattern(self, 
                              category_id: str, 
                              taxonomy_id: str, 
                              pattern: str) -> bool:
        """
        Remove a regex pattern from a category.
        
        Args:
            category_id: Category ID
            taxonomy_id: Taxonomy ID
            pattern: Pattern to remove
            
        Returns:
            True if successful, False otherwise
        """
        if taxonomy_id not in self.category_hierarchies:
            logger.error(f"Category hierarchy for taxonomy {taxonomy_id} not found")
            return False
        
        hierarchy = self.category_hierarchies[taxonomy_id]
        
        if category_id not in hierarchy.categories:
            logger.error(f"Category {category_id} not found in taxonomy {taxonomy_id}")
            return False
        
        category = hierarchy.categories[category_id]
        result = category.remove_pattern(pattern)
        
        # Save if changed
        if result:
            self._save_category_hierarchy(taxonomy_id, hierarchy)
        
        return result
    
    def add_custom_rule(self, rule: Dict[str, Any]) -> str:
        """
        Add a custom categorization rule.
        
        Args:
            rule: Rule dictionary
            
        Returns:
            Rule ID
        """
        # Generate rule ID if not provided
        if 'rule_id' not in rule:
            rule['rule_id'] = f"rule_{str(uuid.uuid4())}"
        
        # Set timestamps
        current_time = time.time()
        rule['created_at'] = current_time
        rule['updated_at'] = current_time
        
        # Add to rules
        self.custom_rules.append(rule)
        
        # Save
        self._save_custom_rules()
        
        return rule['rule_id']
    
    def update_custom_rule(self, rule_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update a custom categorization rule.
        
        Args:
            rule_id: Rule ID
            updates: Updates to apply
            
        Returns:
            True if successful, False otherwise
        """
        # Find rule
        for i, rule in enumerate(self.custom_rules):
            if rule.get('rule_id') == rule_id:
                # Update rule
                self.custom_rules[i].update(updates)
                self.custom_rules[i]['updated_at'] = time.time()
                
                # Save
                self._save_custom_rules()
                
                return True
        
        logger.error(f"Custom rule {rule_id} not found")
        return False
    
    def delete_custom_rule(self, rule_id: str) -> bool:
        """
        Delete a custom categorization rule.
        
        Args:
            rule_id: Rule ID
            
        Returns:
            True if successful, False otherwise
        """
        # Find rule
        for i, rule in enumerate(self.custom_rules):
            if rule.get('rule_id') == rule_id:
                # Remove rule
                del self.custom_rules[i]
                
                # Save
                self._save_custom_rules()
                
                return True
        
        logger.error(f"Custom rule {rule_id} not found")
        return False
    
    def get_custom_rule(self, rule_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a custom categorization rule.
        
        Args:
            rule_id: Rule ID
            
        Returns:
            Rule dictionary or None if not found
        """
        for rule in self.custom_rules:
            if rule.get('rule_id') == rule_id:
                return rule.copy()
        
        return None
    
    def get_all_custom_rules(self) -> List[Dict[str, Any]]:
        """
        Get all custom categorization rules.
        
        Returns:
            List of rule dictionaries
        """
        return [rule.copy() for rule in self.custom_rules]
    
    def categorize_file(self,
                      file_info: Dict[str, Any],
                      taxonomy_id: Optional[str] = None,
                      use_ai: Optional[bool] = None) -> Dict[str, Any]:
        """
        Categorize a file.
        
        Args:
            file_info: File information dictionary
            taxonomy_id: Optional taxonomy ID (default: default taxonomy)
            use_ai: Whether to use AI for categorization (default: config setting)
            
        Returns:
            Dictionary with categorization results
        """
        # Use default taxonomy if not specified
        if taxonomy_id is None:
            if self.default_taxonomy_id is None:
                if not self.taxonomies:
                    # Create default taxonomy
                    taxonomy_id = self._create_default_taxonomy()
                else:
                    # Use first taxonomy
                    taxonomy_id = next(iter(self.taxonomies))
            else:
                taxonomy_id = self.default_taxonomy_id
        
        # Check if taxonomy exists
        if taxonomy_id not in self.taxonomies:
            logger.error(f"Taxonomy {taxonomy_id} not found")
            return {"error": f"Taxonomy {taxonomy_id} not found", "categories": []}
        
        taxonomy = self.taxonomies[taxonomy_id]
        
        # Default use_ai to config setting
        if use_ai is None:
            use_ai = self.use_ai_categorization
        
        # Check for cached results
        file_path = file_info.get('file_path')
        if file_path and file_path in self.category_match_cache:
            if taxonomy_id in self.category_match_cache[file_path]:
                return {
                    "taxonomy_id": taxonomy_id,
                    "taxonomy_name": taxonomy.name,
                    "categories": self.category_match_cache[file_path][taxonomy_id],
                    "from_cache": True
                }
        
        # Initialize result
        result = {
            "taxonomy_id": taxonomy_id,
            "taxonomy_name": taxonomy.name,
            "categories": [],
            "from_cache": False
        }
        
        # Get hierarchy
        if taxonomy_id not in self.category_hierarchies:
            logger.error(f"Category hierarchy for taxonomy {taxonomy_id} not found")
            return result
        
        hierarchy = self.category_hierarchies[taxonomy_id]
        
        # Apply custom rules
        rule_matches = self._apply_custom_rules(file_info, taxonomy_id)
        
        # Apply pattern matching
        pattern_matches = self._match_patterns(file_info, taxonomy_id)
        
        # Apply keyword matching
        keyword_matches = self._match_keywords(file_info, taxonomy_id)
        
        # Combine all rule-based matches
        rule_based_matches = {}
        for category_id, score in rule_matches.items():
            rule_based_matches[category_id] = max(rule_based_matches.get(category_id, 0), score)
        
        for category_id, score in pattern_matches.items():
            rule_based_matches[category_id] = max(rule_based_matches.get(category_id, 0), score)
        
        for category_id, score in keyword_matches.items():
            rule_based_matches[category_id] = max(rule_based_matches.get(category_id, 0), score)
        
        # Apply AI categorization if enabled
        ai_matches = {}
        if use_ai and len(rule_based_matches) < 3:  # Only use AI if rule-based had few matches
            ai_matches = self._categorize_with_ai(file_info, taxonomy_id)
        
        # Combine all matches
        all_matches = rule_based_matches.copy()
        for category_id, score in ai_matches.items():
            all_matches[category_id] = max(all_matches.get(category_id, 0), score)
        
        # Sort matches by score
        matches = [{"category_id": cid, "score": score} for cid, score in all_matches.items()]
        matches.sort(key=lambda x: x["score"], reverse=True)
        
        # Add category information
        for match in matches:
            category_id = match["category_id"]
            if category_id in hierarchy.categories:
                category = hierarchy.categories[category_id]
                match["category"] = category.to_dict()
            else:
                match["category"] = {"category_id": category_id, "name": "Unknown Category"}
        
        result["categories"] = matches
        
        # Cache results
        if file_path:
            if file_path not in self.category_match_cache:
                self.category_match_cache[file_path] = {}
            self.category_match_cache[file_path][taxonomy_id] = matches
        
        return result
    
    def categorize_files(self,
                       files: List[Dict[str, Any]],
                       taxonomy_id: Optional[str] = None,
                       use_ai: Optional[bool] = None,
                       callback: Optional[Callable[[int, int, str], None]] = None) -> List[Dict[str, Any]]:
        """
        Categorize multiple files.
        
        Args:
            files: List of file information dictionaries
            taxonomy_id: Optional taxonomy ID (default: default taxonomy)
            use_ai: Whether to use AI for categorization (default: config setting)
            callback: Optional progress callback function
            
        Returns:
            List of categorization results
        """
        results = []
        
        for i, file_info in enumerate(files):
            if callback:
                callback(i, len(files), file_info.get('file_name', f"File {i+1}"))
            
            result = self.categorize_file(file_info, taxonomy_id, use_ai)
            results.append(result)
        
        return results
    
    def suggest_categories(self,
                         file_info: Dict[str, Any],
                         taxonomy_id: Optional[str] = None,
                         max_suggestions: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Suggest categories for a file.
        
        Args:
            file_info: File information dictionary
            taxonomy_id: Optional taxonomy ID (default: default taxonomy)
            max_suggestions: Maximum number of suggestions
            
        Returns:
            List of category suggestions with scores
        """
        # Default max_suggestions to config setting
        if max_suggestions is None:
            max_suggestions = self.max_suggestions
        
        # Get categorization results
        results = self.categorize_file(file_info, taxonomy_id, True)
        
        # Extract suggestions
        suggestions = results.get("categories", [])
        
        # Limit to max_suggestions
        return suggestions[:max_suggestions]
    
    def _apply_custom_rules(self, 
                          file_info: Dict[str, Any], 
                          taxonomy_id: str) -> Dict[str, float]:
        """
        Apply custom categorization rules.
        
        Args:
            file_info: File information dictionary
            taxonomy_id: Taxonomy ID
            
        Returns:
            Dictionary mapping category IDs to scores
        """
        matches = {}
        
        # Apply each rule
        for rule in self.custom_rules:
            # Skip rules for other taxonomies
            if rule.get('taxonomy_id') and rule.get('taxonomy_id') != taxonomy_id:
                continue
            
            # Check rule conditions
            if self._check_rule_conditions(rule, file_info):
                # Apply rule actions
                for action in rule.get('actions', []):
                    if action.get('type') == 'assign_category':
                        category_id = action.get('category_id')
                        if category_id:
                            score = action.get('confidence', 1.0)
                            matches[category_id] = max(matches.get(category_id, 0), score)
            
        return matches
    
    def _check_rule_conditions(self, rule: Dict[str, Any], file_info: Dict[str, Any]) -> bool:
        """
        Check if a file matches rule conditions.
        
        Args:
            rule: Rule dictionary
            file_info: File information dictionary
            
        Returns:
            True if all conditions match, False otherwise
        """
        # Get conditions
        conditions = rule.get('conditions', [])
        
        # If no conditions, rule always matches
        if not conditions:
            return True
        
        # Check conditions
        for condition in conditions:
            condition_type = condition.get('type')
            
            if condition_type == 'file_name':
                # Check file name
                file_name = file_info.get('file_name', '')
                pattern = condition.get('pattern', '')
                operator = condition.get('operator', 'contains')
                
                if operator == 'contains':
                    if pattern.lower() not in file_name.lower():
                        return False
                elif operator == 'equals':
                    if pattern.lower() != file_name.lower():
                        return False
                elif operator == 'regex':
                    try:
                        if not re.search(pattern, file_name, re.IGNORECASE):
                            return False
                    except re.error:
                        logger.error(f"Invalid regex pattern in rule: {pattern}")
                        return False
            
            elif condition_type == 'file_type':
                # Check file type
                file_type = file_info.get('file_type', '').lower()
                types = [t.lower() for t in condition.get('types', [])]
                
                if file_type not in types:
                    return False
            
            elif condition_type == 'content':
                # Check content
                content = file_info.get('content', '')
                text = condition.get('text', '')
                operator = condition.get('operator', 'contains')
                
                if operator == 'contains':
                    if text.lower() not in content.lower():
                        return False
                elif operator == 'regex':
                    try:
                        if not re.search(text, content, re.IGNORECASE):
                            return False
                    except re.error:
                        logger.error(f"Invalid regex pattern in rule: {text}")
                        return False
            
            elif condition_type == 'metadata':
                # Check metadata
                metadata = file_info.get('metadata', {})
                field = condition.get('field', '')
                value = condition.get('value', '')
                operator = condition.get('operator', 'equals')
                
                if field not in metadata:
                    return False
                
                field_value = metadata[field]
                
                if operator == 'equals':
                    if str(field_value).lower() != str(value).lower():
                        return False
                elif operator == 'contains':
                    if str(value).lower() not in str(field_value).lower():
                        return False
                elif operator == 'greater_than':
                    try:
                        if float(field_value) <= float(value):
                            return False
                    except (ValueError, TypeError):
                        return False
                elif operator == 'less_than':
                    try:
                        if float(field_value) >= float(value):
                            return False
                    except (ValueError, TypeError):
                        return False
            
            elif condition_type == 'ai_analysis':
                # Check AI analysis
                analysis = file_info.get('ai_analysis', {})
                field = condition.get('field', '')
                value = condition.get('value', '')
                
                if field not in analysis:
                    return False
                
                field_value = analysis[field]
                
                if isinstance(field_value, list):
                    # For list fields (like keywords, topics)
                    if value.lower() not in [item.lower() for item in field_value]:
                        return False
                else:
                    # For string fields
                    if value.lower() not in str(field_value).lower():
                        return False
        
        # All conditions matched
        return True
    
    def _match_patterns(self, 
                      file_info: Dict[str, Any], 
                      taxonomy_id: str) -> Dict[str, float]:
        """
        Match file against category patterns.
        
        Args:
            file_info: File information dictionary
            taxonomy_id: Taxonomy ID
            
        Returns:
            Dictionary mapping category IDs to scores
        """
        matches = {}
        
        # Get hierarchy
        if taxonomy_id not in self.category_hierarchies:
            return matches
        
        hierarchy = self.category_hierarchies[taxonomy_id]
        
        # Get file name and content
        file_name = file_info.get('file_name', '')
        content = file_info.get('content', '')
        
        # Check each category
        for category_id, category in hierarchy.categories.items():
            for pattern in category.patterns:
                try:
                    # Check file name
                    if re.search(pattern, file_name, re.IGNORECASE):
                        matches[category_id] = 0.9  # High confidence for file name match
                        break
                    
                    # Check content (if available)
                    if content and re.search(pattern, content, re.IGNORECASE):
                        matches[category_id] = 0.8  # Good confidence for content match
                        break
                except re.error:
                    logger.error(f"Invalid regex pattern in category {category_id}: {pattern}")
        
        return matches
    
    def _match_keywords(self, 
                       file_info: Dict[str, Any], 
                       taxonomy_id: str) -> Dict[str, float]:
        """
        Match file against category keywords.
        
        Args:
            file_info: File information dictionary
            taxonomy_id: Taxonomy ID
            
        Returns:
            Dictionary mapping category IDs to scores
        """
        matches = {}
        
        # Get hierarchy
        if taxonomy_id not in self.category_hierarchies:
            return matches
        
        hierarchy = self.category_hierarchies[taxonomy_id]
        
        # Get file name, content, and AI analysis
        file_name = file_info.get('file_name', '').lower()
        content = file_info.get('content', '').lower()
        ai_analysis = file_info.get('ai_analysis', {})
        
        # Get AI-extracted keywords
        ai_keywords = []
        if 'keywords' in ai_analysis:
            ai_keywords = [kw.lower() for kw in ai_analysis.get('keywords', [])]
        
        # Get AI-extracted topics
        ai_topics = []
        if 'topics' in ai_analysis:
            ai_topics = [topic.lower() for topic in ai_analysis.get('topics', [])]
        
        # Check each category
        for category_id, category in hierarchy.categories.items():
            best_score = 0.0
            
            for keyword in category.keywords:
                keyword_lower = keyword.lower()
                
                # Check file name (highest priority)
                if keyword_lower in file_name:
                    score = 0.85
                    best_score = max(best_score, score)
                
                # Check AI keywords (high priority)
                if keyword_lower in ai_keywords:
                    score = 0.8
                    best_score = max(best_score, score)
                
                # Check AI topics (medium-high priority)
                if keyword_lower in ai_topics:
                    score = 0.75
                    best_score = max(best_score, score)
                
                # Check content (medium priority)
                if content and keyword_lower in content:
                    # Score based on keyword specificity (longer keywords more specific)
                    specificity = min(1.0, len(keyword) / 20.0)  # Cap at 20 chars
                    score = 0.5 + (specificity * 0.2)  # 0.5 - 0.7 range
                    best_score = max(best_score, score)
            
            if best_score > 0:
                matches[category_id] = best_score
        
        return matches
    
    def _categorize_with_ai(self, 
                          file_info: Dict[str, Any], 
                          taxonomy_id: str) -> Dict[str, float]:
        """
        Categorize a file using AI.
        
        Args:
            file_info: File information dictionary
            taxonomy_id: Taxonomy ID
            
        Returns:
            Dictionary mapping category IDs to scores
        """
        matches = {}
        
        # Currently, this is a placeholder
        # In a real implementation, this would:
        # 1. Extract taxonomy categories
        # 2. Send file info and categories to AI service
        # 3. Get AI predictions for category matches
        
        # TODO: Implement AI categorization with a real AI service
        
        # Return empty matches for now
        return matches