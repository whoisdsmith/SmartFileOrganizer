"""
Taxonomy models for the Advanced Categorization Plugin.
"""

import enum
import time
import uuid
from typing import Any, Dict, List, Optional, Set


class TaxonomyType(enum.Enum):
    """Taxonomy type enumeration."""
    HIERARCHICAL = "hierarchical"  # Categories can have parent-child relationships
    FLAT = "flat"                  # No hierarchy, just a flat list of categories
    TAG_BASED = "tag_based"        # Categories are used as tags (can be applied multiple times)
    FACETED = "faceted"            # Multiple independent taxonomy dimensions


class Taxonomy:
    """
    Represents a taxonomy (classification scheme) with metadata.
    
    A taxonomy defines a structure and rules for organizing categories.
    It can be hierarchical, flat, tag-based, or faceted.
    """
    
    def __init__(self,
                name: str,
                taxonomy_id: Optional[str] = None,
                description: Optional[str] = None,
                taxonomy_type: TaxonomyType = TaxonomyType.HIERARCHICAL,
                metadata: Optional[Dict[str, Any]] = None,
                created_at: Optional[float] = None,
                updated_at: Optional[float] = None,
                icon: Optional[str] = None,
                color: Optional[str] = None,
                is_system: bool = False,
                is_default: bool = False,
                max_depth: Optional[int] = None,
                allow_multiple_parents: bool = False,
                allow_custom_categories: bool = True):
        """
        Initialize a taxonomy.
        
        Args:
            name: Taxonomy name
            taxonomy_id: Optional taxonomy ID (generated if not provided)
            description: Optional taxonomy description
            taxonomy_type: Taxonomy type
            metadata: Optional metadata dictionary
            created_at: Optional creation timestamp
            updated_at: Optional update timestamp
            icon: Optional icon name or path
            color: Optional color code (hex)
            is_system: Whether this is a system-defined taxonomy
            is_default: Whether this is the default taxonomy
            max_depth: Maximum depth for hierarchical taxonomies
            allow_multiple_parents: Whether categories can have multiple parents
            allow_custom_categories: Whether users can create custom categories
        """
        self.name = name
        self.taxonomy_id = taxonomy_id or f"tax_{str(uuid.uuid4())}"
        self.description = description
        
        # Set taxonomy type
        if isinstance(taxonomy_type, str):
            try:
                self.taxonomy_type = TaxonomyType(taxonomy_type)
            except ValueError:
                self.taxonomy_type = TaxonomyType.HIERARCHICAL
        else:
            self.taxonomy_type = taxonomy_type
        
        self.metadata = metadata or {}
        
        # Set timestamps
        current_time = time.time()
        self.created_at = created_at or current_time
        self.updated_at = updated_at or current_time
        
        # Appearance
        self.icon = icon
        self.color = color
        
        # Flags
        self.is_system = is_system
        self.is_default = is_default
        
        # Constraints
        self.max_depth = max_depth
        self.allow_multiple_parents = allow_multiple_parents
        self.allow_custom_categories = allow_custom_categories
        
        # Track category IDs (filled by categorization plugin)
        self.category_ids = []
    
    def add_category_id(self, category_id: str) -> None:
        """
        Add a category ID to the taxonomy.
        
        Args:
            category_id: Category ID to add
        """
        if category_id not in self.category_ids:
            self.category_ids.append(category_id)
            self.updated_at = time.time()
    
    def remove_category_id(self, category_id: str) -> bool:
        """
        Remove a category ID from the taxonomy.
        
        Args:
            category_id: Category ID to remove
            
        Returns:
            True if the category ID was removed, False if it wasn't found
        """
        if category_id in self.category_ids:
            self.category_ids.remove(category_id)
            self.updated_at = time.time()
            return True
        return False
    
    def update_metadata(self, key: str, value: Any) -> None:
        """
        Update a metadata value.
        
        Args:
            key: Metadata key
            value: Metadata value
        """
        self.metadata[key] = value
        self.updated_at = time.time()
    
    def remove_metadata(self, key: str) -> bool:
        """
        Remove a metadata key-value pair.
        
        Args:
            key: Metadata key to remove
            
        Returns:
            True if the key was removed, False if it wasn't found
        """
        if key in self.metadata:
            del self.metadata[key]
            self.updated_at = time.time()
            return True
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the taxonomy to a dictionary.
        
        Returns:
            Dictionary representation of the taxonomy
        """
        return {
            "taxonomy_id": self.taxonomy_id,
            "name": self.name,
            "description": self.description,
            "taxonomy_type": self.taxonomy_type.value,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "icon": self.icon,
            "color": self.color,
            "is_system": self.is_system,
            "is_default": self.is_default,
            "max_depth": self.max_depth,
            "allow_multiple_parents": self.allow_multiple_parents,
            "allow_custom_categories": self.allow_custom_categories,
            "category_ids": self.category_ids
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Taxonomy':
        """
        Create a taxonomy from a dictionary.
        
        Args:
            data: Dictionary containing taxonomy data
            
        Returns:
            Taxonomy instance
        """
        # Extract category_ids but don't pass to constructor
        category_ids = data.pop("category_ids", []) if "category_ids" in data else []
        
        # Create taxonomy
        taxonomy = cls(**data)
        
        # Set category_ids after creation
        taxonomy.category_ids = category_ids
        
        return taxonomy