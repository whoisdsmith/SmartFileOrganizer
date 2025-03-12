"""
Legal document models for the Legal Document Analyzer Plugin.
"""

import enum
import time
from typing import Any, Dict, List, Optional, Set, Tuple


class DocumentType(enum.Enum):
    """Legal document type enumeration."""
    CONTRACT = "contract"           # Legal agreement between parties
    AGREEMENT = "agreement"         # Generic agreement
    POLICY = "policy"               # Policy document
    TERMS = "terms"                 # Terms and conditions
    REGULATION = "regulation"       # Regulatory document
    STATUTE = "statute"             # Statutory document
    CASE_LAW = "case_law"           # Court case
    OPINION = "opinion"             # Legal opinion
    BRIEF = "brief"                 # Legal brief
    LETTER = "letter"               # Legal letter
    MEMO = "memo"                   # Legal memorandum
    MINUTES = "minutes"             # Meeting minutes
    FILING = "filing"               # Legal filing
    REPORT = "report"               # Legal report
    PATENT = "patent"               # Patent document
    TRADEMARK = "trademark"         # Trademark document
    LICENSE = "license"             # License agreement
    NDA = "nda"                     # Non-disclosure agreement
    OTHER = "other"                 # Other legal document


class LegalDocument:
    """
    Represents a legal document with analysis results.
    """
    
    def __init__(self,
                file_path: str,
                doc_type: DocumentType,
                legal_doc_id: Optional[str] = None,
                title: Optional[str] = None,
                date: Optional[str] = None,
                parties: Optional[List[Dict[str, Any]]] = None,
                entities: Optional[List[Dict[str, Any]]] = None,
                clauses: Optional[List[Dict[str, Any]]] = None,
                keywords: Optional[List[str]] = None,
                summary: Optional[str] = None,
                jurisdiction: Optional[str] = None,
                governing_law: Optional[str] = None,
                effective_date: Optional[str] = None,
                expiration_date: Optional[str] = None,
                metadata: Optional[Dict[str, Any]] = None,
                analyzed_at: Optional[float] = None,
                risk_factors: Optional[List[Dict[str, Any]]] = None,
                sentiment_analysis: Optional[Dict[str, Any]] = None):
        """
        Initialize a legal document.
        
        Args:
            file_path: Path to the document file
            doc_type: Document type
            legal_doc_id: Optional document ID
            title: Optional document title
            date: Optional document date
            parties: Optional list of parties
            entities: Optional list of named entities
            clauses: Optional list of clauses
            keywords: Optional list of keywords
            summary: Optional document summary
            jurisdiction: Optional jurisdiction information
            governing_law: Optional governing law
            effective_date: Optional effective date
            expiration_date: Optional expiration date
            metadata: Optional metadata dictionary
            analyzed_at: Optional timestamp when analysis was performed
            risk_factors: Optional list of risk factors
            sentiment_analysis: Optional sentiment analysis results
        """
        self.file_path = file_path
        self.doc_type = doc_type if isinstance(doc_type, DocumentType) else DocumentType(doc_type)
        self.legal_doc_id = legal_doc_id or f"legal_{int(time.time())}"
        self.title = title
        self.date = date
        self.parties = parties or []
        self.entities = entities or []
        self.clauses = clauses or []
        self.keywords = keywords or []
        self.summary = summary
        self.jurisdiction = jurisdiction
        self.governing_law = governing_law
        self.effective_date = effective_date
        self.expiration_date = expiration_date
        self.metadata = metadata or {}
        self.analyzed_at = analyzed_at or time.time()
        self.risk_factors = risk_factors or []
        self.sentiment_analysis = sentiment_analysis or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary.
        
        Returns:
            Dictionary representation of legal document
        """
        return {
            "file_path": self.file_path,
            "doc_type": self.doc_type.value,
            "legal_doc_id": self.legal_doc_id,
            "title": self.title,
            "date": self.date,
            "parties": self.parties,
            "entities": self.entities,
            "clauses": self.clauses,
            "keywords": self.keywords,
            "summary": self.summary,
            "jurisdiction": self.jurisdiction,
            "governing_law": self.governing_law,
            "effective_date": self.effective_date,
            "expiration_date": self.expiration_date,
            "metadata": self.metadata,
            "analyzed_at": self.analyzed_at,
            "risk_factors": self.risk_factors,
            "sentiment_analysis": self.sentiment_analysis
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LegalDocument':
        """
        Create from dictionary.
        
        Args:
            data: Dictionary with legal document data
            
        Returns:
            LegalDocument instance
        """
        return cls(
            file_path=data.get("file_path", ""),
            doc_type=data.get("doc_type", "other"),
            legal_doc_id=data.get("legal_doc_id"),
            title=data.get("title"),
            date=data.get("date"),
            parties=data.get("parties", []),
            entities=data.get("entities", []),
            clauses=data.get("clauses", []),
            keywords=data.get("keywords", []),
            summary=data.get("summary"),
            jurisdiction=data.get("jurisdiction"),
            governing_law=data.get("governing_law"),
            effective_date=data.get("effective_date"),
            expiration_date=data.get("expiration_date"),
            metadata=data.get("metadata", {}),
            analyzed_at=data.get("analyzed_at", time.time()),
            risk_factors=data.get("risk_factors", []),
            sentiment_analysis=data.get("sentiment_analysis", {})
        )
    
    def add_party(self, party: Dict[str, Any]) -> None:
        """
        Add a party to the document.
        
        Args:
            party: Party information dictionary
        """
        self.parties.append(party)
    
    def add_entity(self, entity: Dict[str, Any]) -> None:
        """
        Add an entity to the document.
        
        Args:
            entity: Entity information dictionary
        """
        self.entities.append(entity)
    
    def add_clause(self, clause: Dict[str, Any]) -> None:
        """
        Add a clause to the document.
        
        Args:
            clause: Clause information dictionary
        """
        self.clauses.append(clause)
    
    def add_keyword(self, keyword: str) -> None:
        """
        Add a keyword to the document.
        
        Args:
            keyword: Keyword to add
        """
        if keyword not in self.keywords:
            self.keywords.append(keyword)
    
    def add_risk_factor(self, risk: Dict[str, Any]) -> None:
        """
        Add a risk factor to the document.
        
        Args:
            risk: Risk factor information dictionary
        """
        self.risk_factors.append(risk)
    
    def update_metadata(self, key: str, value: Any) -> None:
        """
        Update metadata.
        
        Args:
            key: Metadata key
            value: Metadata value
        """
        self.metadata[key] = value
    
    def get_party_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get a party by name.
        
        Args:
            name: Party name
            
        Returns:
            Party dictionary or None if not found
        """
        for party in self.parties:
            if party.get("name") == name:
                return party
        return None
    
    def get_clauses_by_type(self, clause_type: str) -> List[Dict[str, Any]]:
        """
        Get clauses by type.
        
        Args:
            clause_type: Type of clause
            
        Returns:
            List of matching clauses
        """
        return [clause for clause in self.clauses if clause.get("type") == clause_type]
    
    def get_entities_by_type(self, entity_type: str) -> List[Dict[str, Any]]:
        """
        Get entities by type.
        
        Args:
            entity_type: Type of entity
            
        Returns:
            List of matching entities
        """
        return [entity for entity in self.entities if entity.get("entity_type") == entity_type]