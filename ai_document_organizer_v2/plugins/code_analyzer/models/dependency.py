"""
Dependency model for the Code Analyzer Plugin.
"""

import time
from typing import Any, Dict, List, Optional, Set


class Dependency:
    """
    Represents a code dependency (library, package, module).
    """
    
    def __init__(self,
                name: str,
                dependency_id: Optional[str] = None,
                version: Optional[str] = None,
                dependency_type: str = "library",
                language: Optional[str] = None,
                is_direct: bool = True,
                source_files: Optional[List[str]] = None,
                description: Optional[str] = None,
                license_type: Optional[str] = None,
                homepage: Optional[str] = None,
                last_updated: Optional[float] = None,
                metadata: Optional[Dict[str, Any]] = None):
        """
        Initialize a dependency.
        
        Args:
            name: Dependency name
            dependency_id: Optional dependency ID (defaults to name)
            version: Optional version string
            dependency_type: Type of dependency (library, package, module, etc.)
            language: Programming language
            is_direct: Whether this is a direct dependency or transitive
            source_files: List of source files that reference this dependency
            description: Optional description
            license_type: Optional license type
            homepage: Optional homepage URL
            last_updated: Optional timestamp for last update
            metadata: Optional additional metadata
        """
        self.name = name
        self.dependency_id = dependency_id or name
        self.version = version
        self.dependency_type = dependency_type
        self.language = language
        self.is_direct = is_direct
        self.source_files = source_files or []
        self.description = description
        self.license_type = license_type
        self.homepage = homepage
        self.last_updated = last_updated or time.time()
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary.
        
        Returns:
            Dictionary representation of dependency
        """
        return {
            "name": self.name,
            "dependency_id": self.dependency_id,
            "version": self.version,
            "dependency_type": self.dependency_type,
            "language": self.language,
            "is_direct": self.is_direct,
            "source_files": self.source_files,
            "description": self.description,
            "license_type": self.license_type,
            "homepage": self.homepage,
            "last_updated": self.last_updated,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Dependency':
        """
        Create from dictionary.
        
        Args:
            data: Dictionary with dependency data
            
        Returns:
            Dependency instance
        """
        return cls(
            name=data.get("name", ""),
            dependency_id=data.get("dependency_id"),
            version=data.get("version"),
            dependency_type=data.get("dependency_type", "library"),
            language=data.get("language"),
            is_direct=data.get("is_direct", True),
            source_files=data.get("source_files", []),
            description=data.get("description"),
            license_type=data.get("license_type"),
            homepage=data.get("homepage"),
            last_updated=data.get("last_updated", time.time()),
            metadata=data.get("metadata", {})
        )
    
    def add_source_file(self, file_path: str) -> None:
        """
        Add a source file that references this dependency.
        
        Args:
            file_path: Path to the source file
        """
        if file_path not in self.source_files:
            self.source_files.append(file_path)
    
    def update_metadata(self, key: str, value: Any) -> None:
        """
        Update metadata.
        
        Args:
            key: Metadata key
            value: Metadata value
        """
        self.metadata[key] = value
        self.last_updated = time.time()
    
    def update_version(self, version: str) -> None:
        """
        Update version.
        
        Args:
            version: New version string
        """
        self.version = version
        self.last_updated = time.time()