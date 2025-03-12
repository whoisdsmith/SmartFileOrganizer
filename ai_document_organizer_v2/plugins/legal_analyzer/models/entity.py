"""
Entity models for the Legal Document Analyzer Plugin.
"""

import enum
import time
from typing import Any, Dict, List, Optional, Set, Tuple


class EntityType(enum.Enum):
    """Entity type enumeration."""
    PERSON = "person"           # Person name
    ORGANIZATION = "organization"  # Organization or company
    LOCATION = "location"       # Geographic location
    DATE = "date"               # Date reference
    MONEY = "money"             # Monetary amount
    PERCENTAGE = "percentage"   # Percentage value
    LAW = "law"                 # Reference to law, act, etc.
    REGULATION = "regulation"   # Regulation reference
    COURT = "court"             # Court name
    JUDGE = "judge"             # Judge name
    PARTY = "party"             # Party to agreement
    CLAUSE = "clause"           # Contract clause
    TERM = "term"               # Defined term
    OBLIGATION = "obligation"   # Legal obligation
    RIGHT = "right"             # Legal right
    DEADLINE = "deadline"       # Deadline or timeframe
    CONDITION = "condition"     # Condition for agreement
    OTHER = "other"             # Other entity type


class Entity:
    """
    Represents a named entity in a legal document.
    """
    
    def __init__(self,
                text: str,
                entity_type: EntityType,
                start_pos: int,
                end_pos: int,
                entity_id: Optional[str] = None,
                confidence: float = 1.0,
                normalized_value: Optional[str] = None,
                metadata: Optional[Dict[str, Any]] = None):
        """
        Initialize an entity.
        
        Args:
            text: Original text of the entity
            entity_type: Type of entity
            start_pos: Start position in the document
            end_pos: End position in the document
            entity_id: Optional entity ID
            confidence: Confidence score (0-1)
            normalized_value: Optional normalized value
            metadata: Optional metadata dictionary
        """
        self.text = text
        self.entity_type = entity_type if isinstance(entity_type, EntityType) else EntityType(entity_type)
        self.start_pos = start_pos
        self.end_pos = end_pos
        self.entity_id = entity_id or f"{self.entity_type.value}_{start_pos}_{end_pos}"
        self.confidence = confidence
        self.normalized_value = normalized_value
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary.
        
        Returns:
            Dictionary representation of entity
        """
        return {
            "text": self.text,
            "entity_type": self.entity_type.value,
            "start_pos": self.start_pos,
            "end_pos": self.end_pos,
            "entity_id": self.entity_id,
            "confidence": self.confidence,
            "normalized_value": self.normalized_value,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Entity':
        """
        Create from dictionary.
        
        Args:
            data: Dictionary with entity data
            
        Returns:
            Entity instance
        """
        return cls(
            text=data.get("text", ""),
            entity_type=data.get("entity_type", "other"),
            start_pos=data.get("start_pos", 0),
            end_pos=data.get("end_pos", 0),
            entity_id=data.get("entity_id"),
            confidence=data.get("confidence", 1.0),
            normalized_value=data.get("normalized_value"),
            metadata=data.get("metadata", {})
        )
    
    def update_metadata(self, key: str, value: Any) -> None:
        """
        Update metadata.
        
        Args:
            key: Metadata key
            value: Metadata value
        """
        self.metadata[key] = value
    
    def get_context(self, text: str, context_size: int = 50) -> str:
        """
        Get context around the entity in the document.
        
        Args:
            text: Full document text
            context_size: Number of characters for context on each side
            
        Returns:
            Context string
        """
        start = max(0, self.start_pos - context_size)
        end = min(len(text), self.end_pos + context_size)
        
        return text[start:end]