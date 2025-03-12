"""
Category models for the Advanced Categorization Plugin.
"""

import time
import uuid
from typing import Any, Dict, List, Optional, Set, Tuple, Union


class Category:
    """
    Represents a category for document classification.
    
    Categories can be organized in a hierarchy and used to classify documents.
    They can contain keywords, patterns, and other metadata to aid in classification.
    """
    
    def __init__(self,
                name: str,
                taxonomy_id: str,
                category_id: Optional[str] = None,
                parent_id: Optional[str] = None,
                description: Optional[str] = None,
                keywords: Optional[List[str]] = None,
                patterns: Optional[List[str]] = None,
                icon: Optional[str] = None,
                color: Optional[str] = None,
                is_system: bool = False,
                metadata: Optional[Dict[str, Any]] = None,
                created_at: Optional[float] = None,
                updated_at: Optional[float] = None):
        """
        Initialize a category.
        
        Args:
            name: Category name
            taxonomy_id: ID of the taxonomy this category belongs to
            category_id: Optional category ID (generated if not provided)
            parent_id: Optional parent category ID
            description: Optional category description
            keywords: Optional list of keywords for matching documents
            patterns: Optional list of regex patterns for matching documents
            icon: Optional icon name or path
            color: Optional color code (hex)
            is_system: Whether this is a system-defined category
            metadata: Optional metadata dictionary
            created_at: Optional creation timestamp
            updated_at: Optional update timestamp
        """
        self.name = name
        self.taxonomy_id = taxonomy_id
        self.category_id = category_id or f"cat_{str(uuid.uuid4())}"
        self.parent_id = parent_id
        self.description = description
        self.keywords = keywords or []
        self.patterns = patterns or []
        self.icon = icon
        self.color = color
        self.is_system = is_system
        self.metadata = metadata or {}
        
        # Set timestamps
        current_time = time.time()
        self.created_at = created_at or current_time
        self.updated_at = updated_at or current_time
    
    def add_keyword(self, keyword: str) -> None:
        """
        Add a keyword to the category.
        
        Args:
            keyword: Keyword to add
        """
        if keyword not in self.keywords:
            self.keywords.append(keyword)
            self.updated_at = time.time()
    
    def remove_keyword(self, keyword: str) -> bool:
        """
        Remove a keyword from the category.
        
        Args:
            keyword: Keyword to remove
            
        Returns:
            True if the keyword was removed, False if it wasn't found
        """
        if keyword in self.keywords:
            self.keywords.remove(keyword)
            self.updated_at = time.time()
            return True
        return False
    
    def add_pattern(self, pattern: str) -> None:
        """
        Add a pattern to the category.
        
        Args:
            pattern: Pattern to add
        """
        if pattern not in self.patterns:
            self.patterns.append(pattern)
            self.updated_at = time.time()
    
    def remove_pattern(self, pattern: str) -> bool:
        """
        Remove a pattern from the category.
        
        Args:
            pattern: Pattern to remove
            
        Returns:
            True if the pattern was removed, False if it wasn't found
        """
        if pattern in self.patterns:
            self.patterns.remove(pattern)
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
        Convert the category to a dictionary.
        
        Returns:
            Dictionary representation of the category
        """
        return {
            "category_id": self.category_id,
            "name": self.name,
            "taxonomy_id": self.taxonomy_id,
            "parent_id": self.parent_id,
            "description": self.description,
            "keywords": self.keywords,
            "patterns": self.patterns,
            "icon": self.icon,
            "color": self.color,
            "is_system": self.is_system,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Category':
        """
        Create a category from a dictionary.
        
        Args:
            data: Dictionary containing category data
            
        Returns:
            Category instance
        """
        return cls(
            name=data.get("name", ""),
            taxonomy_id=data.get("taxonomy_id", ""),
            category_id=data.get("category_id"),
            parent_id=data.get("parent_id"),
            description=data.get("description"),
            keywords=data.get("keywords", []),
            patterns=data.get("patterns", []),
            icon=data.get("icon"),
            color=data.get("color"),
            is_system=data.get("is_system", False),
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at")
        )


class CategoryHierarchy:
    """
    Manages a hierarchy of categories.
    
    This class provides methods for adding, removing, and retrieving categories
    in a hierarchical structure.
    """
    
    def __init__(self):
        """Initialize a category hierarchy."""
        # Maps category ID to Category instance
        self.categories = {}
        
        # Maps parent ID to list of child category IDs
        self.children = {}
    
    def add_category(self, category: Category) -> bool:
        """
        Add a category to the hierarchy.
        
        Args:
            category: Category to add
            
        Returns:
            True if successful, False otherwise
        """
        # Check if category already exists
        if category.category_id in self.categories:
            return False
        
        # Check if parent exists if parent_id is specified
        if category.parent_id and category.parent_id not in self.categories:
            return False
        
        # Add category to categories
        self.categories[category.category_id] = category
        
        # Add to children map
        parent_id = category.parent_id or None
        if parent_id not in self.children:
            self.children[parent_id] = []
        self.children[parent_id].append(category.category_id)
        
        return True
    
    def remove_category(self, category_id: str, recursive: bool = False) -> bool:
        """
        Remove a category from the hierarchy.
        
        Args:
            category_id: ID of the category to remove
            recursive: Whether to recursively remove child categories
            
        Returns:
            True if successful, False otherwise
        """
        # Check if category exists
        if category_id not in self.categories:
            return False
        
        # Get parent ID
        parent_id = self.categories[category_id].parent_id
        
        # Check for children
        if category_id in self.children and self.children[category_id]:
            if not recursive:
                return False  # Can't remove category with children unless recursive
            
            # Recursively remove children
            for child_id in list(self.children[category_id]):
                self.remove_category(child_id, recursive=True)
        
        # Remove from parent's children
        if parent_id in self.children and category_id in self.children[parent_id]:
            self.children[parent_id].remove(category_id)
        
        # Remove children list
        if category_id in self.children:
            del self.children[category_id]
        
        # Remove from categories
        del self.categories[category_id]
        
        return True
    
    def move_category(self, category_id: str, new_parent_id: Optional[str] = None) -> bool:
        """
        Move a category to a new parent.
        
        Args:
            category_id: ID of the category to move
            new_parent_id: ID of the new parent category, or None to make it a root
            
        Returns:
            True if successful, False otherwise
        """
        # Check if category exists
        if category_id not in self.categories:
            return False
        
        # Check if new parent exists if specified
        if new_parent_id and new_parent_id not in self.categories:
            return False
        
        # Check for circular reference
        if new_parent_id and self._is_ancestor(category_id, new_parent_id):
            return False  # Would create a circular reference
        
        # Get current parent ID
        current_parent_id = self.categories[category_id].parent_id
        
        # Remove from current parent's children
        if current_parent_id in self.children and category_id in self.children[current_parent_id]:
            self.children[current_parent_id].remove(category_id)
        
        # Update category's parent_id
        self.categories[category_id].parent_id = new_parent_id
        self.categories[category_id].updated_at = time.time()
        
        # Add to new parent's children
        if new_parent_id not in self.children:
            self.children[new_parent_id] = []
        self.children[new_parent_id].append(category_id)
        
        return True
    
    def get_root_categories(self) -> List[Category]:
        """
        Get all root categories (categories with no parent).
        
        Returns:
            List of root categories
        """
        if None not in self.children:
            return []
        
        return [self.categories[category_id] for category_id in self.children[None]]
    
    def get_children(self, parent_id: str) -> List[Category]:
        """
        Get direct children of a category.
        
        Args:
            parent_id: ID of the parent category
            
        Returns:
            List of child categories
        """
        if parent_id not in self.children:
            return []
        
        return [self.categories[category_id] for category_id in self.children[parent_id]]
    
    def get_descendants(self, category_id: str) -> List[Category]:
        """
        Get all descendants of a category (children, grandchildren, etc.).
        
        Args:
            category_id: ID of the category
            
        Returns:
            List of descendant categories
        """
        descendants = []
        
        if category_id not in self.children:
            return descendants
        
        # Add direct children
        for child_id in self.children[category_id]:
            if child_id in self.categories:
                descendants.append(self.categories[child_id])
                
                # Add descendants of this child
                descendants.extend(self.get_descendants(child_id))
        
        return descendants
    
    def get_ancestors(self, category_id: str) -> List[Category]:
        """
        Get all ancestors of a category (parent, grandparent, etc.).
        
        Args:
            category_id: ID of the category
            
        Returns:
            List of ancestor categories in order from root to parent
        """
        ancestors = []
        
        if category_id not in self.categories:
            return ancestors
        
        # Traverse up the hierarchy
        current = self.categories[category_id]
        while current.parent_id and current.parent_id in self.categories:
            parent = self.categories[current.parent_id]
            ancestors.insert(0, parent)  # Insert at beginning to maintain order
            current = parent
        
        return ancestors
    
    def get_path(self, category_id: str) -> List[Category]:
        """
        Get the path from root to the specified category.
        
        Args:
            category_id: ID of the category
            
        Returns:
            List of categories from root to the specified category
        """
        if category_id not in self.categories:
            return []
        
        path = self.get_ancestors(category_id)
        path.append(self.categories[category_id])
        
        return path
    
    def find_categories_by_name(self, name: str, exact_match: bool = False) -> List[Category]:
        """
        Find categories by name.
        
        Args:
            name: Name to search for
            exact_match: Whether to require exact match
            
        Returns:
            List of matching categories
        """
        if exact_match:
            return [category for category in self.categories.values() if category.name == name]
        else:
            name_lower = name.lower()
            return [category for category in self.categories.values() if name_lower in category.name.lower()]
    
    def find_categories_by_keyword(self, keyword: str) -> List[Category]:
        """
        Find categories by keyword.
        
        Args:
            keyword: Keyword to search for
            
        Returns:
            List of matching categories
        """
        keyword_lower = keyword.lower()
        return [category for category in self.categories.values()
                if any(keyword_lower in kw.lower() for kw in category.keywords)]
    
    def get_depth(self, category_id: str) -> int:
        """
        Get the depth of a category in the hierarchy (0 for root).
        
        Args:
            category_id: ID of the category
            
        Returns:
            Depth of the category
        """
        if category_id not in self.categories:
            return -1  # Invalid category
        
        depth = 0
        ancestors = self.get_ancestors(category_id)
        return len(ancestors)
    
    def _is_ancestor(self, descendant_id: str, ancestor_id: str) -> bool:
        """
        Check if ancestor_id is an ancestor of descendant_id.
        
        Args:
            descendant_id: ID of the descendant category
            ancestor_id: ID of the potential ancestor category
            
        Returns:
            True if ancestor_id is an ancestor of descendant_id, False otherwise
        """
        if descendant_id == ancestor_id:
            return True  # Same category
        
        ancestors = self.get_ancestors(descendant_id)
        return any(ancestor.category_id == ancestor_id for ancestor in ancestors)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the category hierarchy to a dictionary.
        
        Returns:
            Dictionary representation of the category hierarchy
        """
        return {
            "categories": {category_id: category.to_dict() for category_id, category in self.categories.items()},
            "children": {str(parent_id) if parent_id is not None else "none": child_ids 
                         for parent_id, child_ids in self.children.items()}
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CategoryHierarchy':
        """
        Create a category hierarchy from a dictionary.
        
        Args:
            data: Dictionary containing category hierarchy data
            
        Returns:
            CategoryHierarchy instance
        """
        hierarchy = cls()
        
        # Load categories
        categories_data = data.get("categories", {})
        for category_id, category_data in categories_data.items():
            category = Category.from_dict(category_data)
            hierarchy.categories[category_id] = category
        
        # Load children
        children_data = data.get("children", {})
        for parent_id_str, child_ids in children_data.items():
            parent_id = None if parent_id_str == "none" else parent_id_str
            hierarchy.children[parent_id] = child_ids
        
        return hierarchy