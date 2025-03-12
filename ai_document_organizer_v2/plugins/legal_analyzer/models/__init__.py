"""
Models for Legal Document Analyzer Plugin.
"""

from .legal_document import LegalDocument, DocumentType
from .entity import Entity, EntityType

__all__ = [
    "LegalDocument",
    "DocumentType",
    "Entity",
    "EntityType"
]