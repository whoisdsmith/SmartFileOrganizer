"""
Legal Document Analyzer Plugin for AI Document Organizer V2.
"""

from .legal_analyzer_plugin import LegalDocumentAnalyzerPlugin
from .models.legal_document import LegalDocument, DocumentType
from .models.entity import Entity, EntityType

__all__ = [
    "LegalDocumentAnalyzerPlugin",
    "LegalDocument",
    "DocumentType",
    "Entity",
    "EntityType"
]