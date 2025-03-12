"""
Legal Document Analyzer Plugin for AI Document Organizer V2.
"""

import json
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional, Set, Tuple, Union, Callable

from ai_document_organizer_v2.core.plugin_base import PluginBase
from ai_document_organizer_v2.plugins.legal_analyzer.models.legal_document import LegalDocument, DocumentType
from ai_document_organizer_v2.plugins.legal_analyzer.models.entity import Entity, EntityType


logger = logging.getLogger(__name__)


class LegalDocumentAnalyzerPlugin(PluginBase):
    """
    Legal Document Analyzer Plugin for AI Document Organizer V2.
    
    This plugin provides:
    - Legal document type classification
    - Entity extraction
    - Contract clause analysis
    - Risk assessment
    - Jurisdiction and governing law identification
    - Legal document summarization
    """
    
    plugin_name = "legal_analyzer"
    plugin_version = "1.0.0"
    plugin_description = "Specialized analyzer for legal documents and contracts"
    plugin_author = "AI Document Organizer Team"
    
    # Document type patterns
    DOCUMENT_TYPE_PATTERNS = {
        DocumentType.CONTRACT: [
            r"contract",
            r"agreement",
            r"between\s+.+?\s+and\s+.+?\s+for",
            r"parties\s+agree",
            r"terms\s+and\s+conditions"
        ],
        DocumentType.AGREEMENT: [
            r"agreement",
            r"memorandum\s+of\s+understanding",
            r"binding\s+agreement"
        ],
        DocumentType.POLICY: [
            r"policy",
            r"guidelines",
            r"procedures"
        ],
        DocumentType.TERMS: [
            r"terms\s+of\s+(use|service)",
            r"terms\s+and\s+conditions",
            r"user\s+agreement"
        ],
        DocumentType.REGULATION: [
            r"regulation",
            r"regulatory",
            r"compliance"
        ],
        DocumentType.STATUTE: [
            r"statute",
            r"act\s+of\s+",
            r"public\s+law"
        ],
        DocumentType.CASE_LAW: [
            r"v\.",
            r"versus",
            r"plaintiff",
            r"defendant",
            r"court\s+of\s+appeals",
            r"supreme\s+court"
        ],
        DocumentType.OPINION: [
            r"opinion",
            r"in\s+the\s+matter\s+of",
            r"legal\s+opinion"
        ],
        DocumentType.LICENSE: [
            r"licen[sc]e",
            r"licen[sc]ing\s+agreement",
            r"permission\s+to\s+use"
        ],
        DocumentType.NDA: [
            r"non.?disclosure",
            r"confidential",
            r"confidentiality\s+agreement"
        ]
    }
    
    # Entity extraction patterns
    ENTITY_PATTERNS = {
        EntityType.PERSON: [
            r"Mr\.\s+[A-Z][a-zA-Z\-]+",
            r"Mrs\.\s+[A-Z][a-zA-Z\-]+",
            r"Ms\.\s+[A-Z][a-zA-Z\-]+",
            r"Dr\.\s+[A-Z][a-zA-Z\-]+"
        ],
        EntityType.ORGANIZATION: [
            r"[A-Z][a-zA-Z]+\s+Inc\.?",
            r"[A-Z][a-zA-Z]+\s+Corp\.?",
            r"[A-Z][a-zA-Z]+\s+LLC",
            r"[A-Z][a-zA-Z]+\s+Ltd\.?"
        ],
        EntityType.DATE: [
            r"\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}",
            r"January|February|March|April|May|June|July|August|September|October|November|December\s+\d{1,2},\s+\d{4}"
        ],
        EntityType.MONEY: [
            r"\$\d+(?:,\d{3})*(?:\.\d{2})?",
            r"\d+(?:,\d{3})*(?:\.\d{2})?\s+dollars"
        ],
        EntityType.PERCENTAGE: [
            r"\d+(?:\.\d+)?\s*%",
            r"\d+(?:\.\d+)?\s+percent"
        ],
        EntityType.LAW: [
            r"U\.S\.C\.\s+§\s+\d+",
            r"Code\s+of\s+Federal\s+Regulations",
            r"CFR\s+\d+"
        ],
        EntityType.COURT: [
            r"Court\s+of\s+[A-Za-z\s]+",
            r"District\s+Court",
            r"Supreme\s+Court"
        ]
    }
    
    # Clause types
    CLAUSE_TYPES = [
        "definitions",
        "term",
        "termination",
        "payment",
        "confidentiality",
        "indemnification",
        "warranty",
        "limitation_of_liability",
        "governing_law",
        "dispute_resolution",
        "force_majeure",
        "assignment",
        "severability",
        "entire_agreement",
        "amendment",
        "notice",
        "waiver",
        "counterparts",
        "survival",
        "compliance",
        "non_compete",
        "non_solicitation",
        "intellectual_property",
        "privacy",
        "security",
        "audit",
        "insurance",
        "taxes",
        "escrow",
        "remedies",
        "damages",
        "representation",
        "covenant",
        "condition",
        "standard_of_care",
        "term_extension",
        "renewal"
    ]
    
    # Clause identification patterns
    CLAUSE_PATTERNS = {
        "definitions": [
            r"definitions",
            r"defined terms",
            r"meaning of terms"
        ],
        "term": [
            r"term of (this|the) agreement",
            r"term and termination",
            r"agreement term"
        ],
        "termination": [
            r"termination",
            r"termination rights",
            r"termination for cause",
            r"termination for convenience"
        ],
        "payment": [
            r"payment",
            r"payment terms",
            r"fees",
            r"compensation"
        ],
        "confidentiality": [
            r"confidentiality",
            r"confidential information",
            r"non-disclosure"
        ],
        "indemnification": [
            r"indemnification",
            r"indemnity",
            r"hold harmless"
        ],
        "warranty": [
            r"warranty",
            r"warranties",
            r"warranty disclaimer"
        ],
        "limitation_of_liability": [
            r"limitation of liability",
            r"limited liability",
            r"liability limitation"
        ],
        "governing_law": [
            r"governing law",
            r"choice of law",
            r"applicable law"
        ],
        "dispute_resolution": [
            r"dispute resolution",
            r"arbitration",
            r"mediation",
            r"resolution of disputes"
        ],
        "force_majeure": [
            r"force majeure",
            r"act of god",
            r"events beyond control"
        ]
    }
    
    # Risk factor patterns
    RISK_FACTOR_PATTERNS = {
        "high_liability": [
            r"unlimited liability",
            r"joint and several liability",
            r"strict liability"
        ],
        "unreasonable_indemnity": [
            r"indemnify for all claims",
            r"broad indemnification",
            r"uncapped indemnity"
        ],
        "perpetual_term": [
            r"perpetual",
            r"indefinite term",
            r"no expiration"
        ],
        "unilateral_termination": [
            r"terminate at any time",
            r"unilateral termination",
            r"immediate termination"
        ],
        "automatic_renewal": [
            r"automatically renew",
            r"auto-renewal",
            r"renewal without notice"
        ],
        "unfavorable_jurisdiction": [
            r"exclusive jurisdiction",
            r"venue shall be",
            r"forum selection"
        ],
        "unclear_deliverables": [
            r"reasonable efforts",
            r"commercially reasonable",
            r"to be determined"
        ],
        "missing_clause": []  # Logic handled separately
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the legal document analyzer plugin.
        
        Args:
            config: Optional configuration dictionary
        """
        super().__init__(config)
        
        # Configuration
        self.config = config or {}
        self.data_dir = self.config.get("data_dir", "data/legal_analysis")
        
        # State
        self.legal_documents = {}  # file_path -> LegalDocument
        
        # AI analysis settings
        self.use_ai_analysis = self.config.get("use_ai_analysis", True)
        self.ai_confidence_threshold = self.config.get("ai_confidence_threshold", 0.7)
        
        # Analysis settings
        self.extract_entities = self.config.get("extract_entities", True)
        self.detect_clauses = self.config.get("detect_clauses", True)
        self.assess_risks = self.config.get("assess_risks", True)
        self.summarize_documents = self.config.get("summarize_documents", True)
        
        # Compiled regex patterns
        self._compile_patterns()
    
    def _compile_patterns(self) -> None:
        """Compile regex patterns for performance."""
        # Compile document type patterns
        self.compiled_doc_patterns = {}
        for doc_type, patterns in self.DOCUMENT_TYPE_PATTERNS.items():
            self.compiled_doc_patterns[doc_type] = [re.compile(p, re.IGNORECASE) for p in patterns]
        
        # Compile entity patterns
        self.compiled_entity_patterns = {}
        for entity_type, patterns in self.ENTITY_PATTERNS.items():
            self.compiled_entity_patterns[entity_type] = [re.compile(p, re.IGNORECASE) for p in patterns]
        
        # Compile clause patterns
        self.compiled_clause_patterns = {}
        for clause_type, patterns in self.CLAUSE_PATTERNS.items():
            self.compiled_clause_patterns[clause_type] = [re.compile(p, re.IGNORECASE) for p in patterns]
        
        # Compile risk factor patterns
        self.compiled_risk_patterns = {}
        for risk_type, patterns in self.RISK_FACTOR_PATTERNS.items():
            self.compiled_risk_patterns[risk_type] = [re.compile(p, re.IGNORECASE) for p in patterns]
    
    def initialize(self) -> bool:
        """
        Initialize the plugin.
        
        Returns:
            True if initialization was successful, False otherwise
        """
        logger.info("Initializing LegalDocumentAnalyzerPlugin")
        
        # Create data directory if it doesn't exist
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Load legal documents
        self._load_legal_documents()
        
        return True
    
    def activate(self) -> bool:
        """
        Activate the plugin.
        
        Returns:
            True if activation was successful, False otherwise
        """
        logger.info("Activating LegalDocumentAnalyzerPlugin")
        return True
    
    def deactivate(self) -> bool:
        """
        Deactivate the plugin.
        
        Returns:
            True if deactivation was successful, False otherwise
        """
        logger.info("Deactivating LegalDocumentAnalyzerPlugin")
        return True
    
    def shutdown(self) -> bool:
        """
        Shutdown the plugin and clean up resources.
        
        Returns:
            True if shutdown was successful, False otherwise
        """
        logger.info("Shutting down LegalDocumentAnalyzerPlugin")
        
        # Save legal documents
        self._save_legal_documents()
        
        return True
    
    def get_info(self) -> Dict[str, Any]:
        """
        Get information about the plugin.
        
        Returns:
            Dictionary with plugin information
        """
        info = super().get_info()
        info.update({
            "legal_documents_count": len(self.legal_documents),
            "document_types_supported": len(DocumentType),
            "entity_types_supported": len(EntityType),
            "use_ai_analysis": self.use_ai_analysis
        })
        return info
    
    def get_type(self) -> str:
        """
        Get the plugin type.
        
        Returns:
            Plugin type
        """
        return "legal_analyzer"
    
    def get_capabilities(self) -> List[str]:
        """
        Get the plugin capabilities.
        
        Returns:
            List of capabilities
        """
        return [
            "legal_document_classification",
            "entity_extraction",
            "clause_analysis",
            "risk_assessment",
            "jurisdiction_identification",
            "legal_document_summarization"
        ]
    
    def _load_legal_documents(self) -> None:
        """Load legal documents from file."""
        legal_doc_file = os.path.join(self.data_dir, 'legal_documents.json')
        if os.path.exists(legal_doc_file):
            try:
                with open(legal_doc_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                self.legal_documents = {}
                for doc_data in data.get('legal_documents', []):
                    doc = LegalDocument.from_dict(doc_data)
                    self.legal_documents[doc.file_path] = doc
                
                logger.info(f"Loaded {len(self.legal_documents)} legal documents")
            except Exception as e:
                logger.error(f"Error loading legal documents: {e}")
                self.legal_documents = {}
        else:
            logger.info("No legal documents file found, starting with empty documents")
            self.legal_documents = {}
    
    def _save_legal_documents(self) -> None:
        """Save legal documents to file."""
        os.makedirs(self.data_dir, exist_ok=True)
        
        legal_doc_file = os.path.join(self.data_dir, 'legal_documents.json')
        try:
            data = {
                'legal_documents': [doc.to_dict() for doc in self.legal_documents.values()]
            }
            
            with open(legal_doc_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved {len(self.legal_documents)} legal documents")
        except Exception as e:
            logger.error(f"Error saving legal documents: {e}")
    
    def analyze_document(self,
                       file_path: str,
                       content: Optional[str] = None,
                       use_ai: Optional[bool] = None) -> Dict[str, Any]:
        """
        Analyze a legal document.
        
        Args:
            file_path: Path to the legal document
            content: Optional document content (read from file if not provided)
            use_ai: Whether to use AI for analysis (default: config setting)
            
        Returns:
            Dictionary with analysis results
        """
        # Default use_ai to config setting
        if use_ai is None:
            use_ai = self.use_ai_analysis
        
        # Read content if not provided
        if content is None:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
            except Exception as e:
                logger.error(f"Error reading file {file_path}: {e}")
                return {"error": f"Error reading file: {str(e)}"}
        
        # Detect document type
        doc_type = self._detect_document_type(content)
        
        # Extract entities
        entities = self._extract_entities(content) if self.extract_entities else []
        
        # Detect clauses
        clauses = self._detect_clauses(content) if self.detect_clauses else []
        
        # Identify parties
        parties = self._identify_parties(content, entities)
        
        # Identify jurisdiction and governing law
        jurisdiction, governing_law = self._identify_jurisdiction_and_law(content, clauses)
        
        # Extract dates
        effective_date, expiration_date, document_date = self._extract_dates(content, entities)
        
        # Extract keywords
        keywords = self._extract_keywords(content)
        
        # Assess risks
        risk_factors = self._assess_risks(content, clauses) if self.assess_risks else []
        
        # Generate summary using AI if enabled
        summary = None
        if use_ai and self.summarize_documents:
            summary = self._generate_summary(content, doc_type)
        
        # Perform sentiment analysis if enabled
        sentiment_analysis = {}
        if use_ai:
            sentiment_analysis = self._analyze_sentiment(content)
        
        # Create title from content if not found in metadata
        title = self._extract_title(content)
        
        # Create legal document object
        legal_doc = LegalDocument(
            file_path=file_path,
            doc_type=doc_type,
            title=title,
            date=document_date,
            parties=parties,
            entities=entities,
            clauses=clauses,
            keywords=keywords,
            summary=summary,
            jurisdiction=jurisdiction,
            governing_law=governing_law,
            effective_date=effective_date,
            expiration_date=expiration_date,
            risk_factors=risk_factors,
            sentiment_analysis=sentiment_analysis
        )
        
        # Store in legal documents
        self.legal_documents[file_path] = legal_doc
        
        # Save
        self._save_legal_documents()
        
        return legal_doc.to_dict()
    
    def analyze_documents(self,
                        file_paths: List[str],
                        use_ai: Optional[bool] = None,
                        callback: Optional[Callable[[int, int, str], None]] = None) -> List[Dict[str, Any]]:
        """
        Analyze multiple legal documents.
        
        Args:
            file_paths: List of file paths to analyze
            use_ai: Whether to use AI for analysis (default: config setting)
            callback: Optional progress callback function
            
        Returns:
            List of analysis results
        """
        results = []
        
        for i, file_path in enumerate(file_paths):
            if callback:
                callback(i, len(file_paths), file_path)
            
            result = self.analyze_document(file_path, use_ai=use_ai)
            results.append(result)
        
        return results
    
    def get_legal_document(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Get a legal document by path.
        
        Args:
            file_path: Path to the legal document
            
        Returns:
            Dictionary with legal document information or None if not found
        """
        if file_path not in self.legal_documents:
            return None
        
        return self.legal_documents[file_path].to_dict()
    
    def get_all_legal_documents(self) -> List[Dict[str, Any]]:
        """
        Get all legal documents.
        
        Returns:
            List of legal document dictionaries
        """
        return [doc.to_dict() for doc in self.legal_documents.values()]
    
    def get_legal_documents_by_type(self, doc_type: Union[str, DocumentType]) -> List[Dict[str, Any]]:
        """
        Get legal documents by type.
        
        Args:
            doc_type: Document type (string or DocumentType enum)
            
        Returns:
            List of legal document dictionaries
        """
        if isinstance(doc_type, str):
            try:
                doc_type = DocumentType(doc_type)
            except ValueError:
                logger.error(f"Invalid document type: {doc_type}")
                return []
        
        return [doc.to_dict() for doc in self.legal_documents.values()
                if doc.doc_type == doc_type]
    
    def get_document_types(self) -> List[Dict[str, str]]:
        """
        Get supported document types.
        
        Returns:
            List of document type dictionaries
        """
        return [{"id": dt.value, "name": dt.name} for dt in DocumentType]
    
    def get_entity_types(self) -> List[Dict[str, str]]:
        """
        Get supported entity types.
        
        Returns:
            List of entity type dictionaries
        """
        return [{"id": et.value, "name": et.name} for et in EntityType]
    
    def get_clause_types(self) -> List[str]:
        """
        Get supported clause types.
        
        Returns:
            List of clause types
        """
        return self.CLAUSE_TYPES
    
    def _detect_document_type(self, content: str) -> DocumentType:
        """
        Detect the type of legal document.
        
        Args:
            content: Document content
            
        Returns:
            DocumentType enum
        """
        # Count matches for each document type
        type_scores = {}
        for doc_type, patterns in self.compiled_doc_patterns.items():
            score = 0
            for pattern in patterns:
                matches = pattern.findall(content)
                score += len(matches)
            
            type_scores[doc_type] = score
        
        # Sort by score
        if not type_scores:
            return DocumentType.OTHER
        
        # Find type with highest score
        best_type = max(type_scores.items(), key=lambda x: x[1])
        
        # If no significant matches, return OTHER
        if best_type[1] == 0:
            return DocumentType.OTHER
        
        return best_type[0]
    
    def _extract_entities(self, content: str) -> List[Dict[str, Any]]:
        """
        Extract named entities from the document.
        
        Args:
            content: Document content
            
        Returns:
            List of entity dictionaries
        """
        entities = []
        
        # Extract entities using regex patterns
        for entity_type, patterns in self.compiled_entity_patterns.items():
            for pattern in patterns:
                for match in pattern.finditer(content):
                    text = match.group(0)
                    start_pos = match.start()
                    end_pos = match.end()
                    
                    # Create entity
                    entity = Entity(
                        text=text,
                        entity_type=entity_type,
                        start_pos=start_pos,
                        end_pos=end_pos,
                        confidence=0.8  # Default confidence for regex matches
                    )
                    
                    # Normalize values for certain entity types
                    if entity_type == EntityType.DATE:
                        # Attempt to standardize date format
                        try:
                            # Naive date normalization, more sophisticated in real implementation
                            if re.match(r"\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}", text):
                                parts = re.split(r'[\/\-\.]', text)
                                if len(parts) == 3:
                                    m, d, y = parts
                                    if len(y) == 2:
                                        y = '20' + y if int(y) < 50 else '19' + y
                                    entity.normalized_value = f"{y}-{m:0>2}-{d:0>2}"
                        except Exception:
                            pass
                    
                    elif entity_type == EntityType.MONEY:
                        # Normalize monetary values
                        try:
                            cleaned = text.replace(',', '').replace('$', '')
                            if 'dollars' in cleaned:
                                cleaned = cleaned.replace('dollars', '').strip()
                            
                            if re.match(r"\d+(\.\d+)?", cleaned):
                                entity.normalized_value = float(cleaned)
                        except Exception:
                            pass
                    
                    # Add entity to list (as dictionary)
                    entities.append(entity.to_dict())
        
        return entities
    
    def _detect_clauses(self, content: str) -> List[Dict[str, Any]]:
        """
        Detect clauses in the document.
        
        Args:
            content: Document content
            
        Returns:
            List of clause dictionaries
        """
        clauses = []
        
        # Detect clauses using regex patterns
        for clause_type, patterns in self.compiled_clause_patterns.items():
            for pattern in patterns:
                for match in pattern.finditer(content):
                    # Find the whole clause
                    section_start = match.start()
                    
                    # Look for the next section heading or end of document
                    next_section = None
                    for ct, pts in self.compiled_clause_patterns.items():
                        if ct == clause_type:
                            continue  # Skip the current clause type
                        
                        for p in pts:
                            next_match = p.search(content, section_start + 1)
                            if next_match:
                                if next_section is None or next_match.start() < next_section:
                                    next_section = next_match.start()
                    
                    # If no next section found, use a reasonable amount of text or end of document
                    if next_section is None:
                        # Look for 2-3 paragraphs or 2000 chars, whichever is less
                        para_count = 0
                        pos = section_start
                        for _ in range(3):  # Look for up to 3 paragraph breaks
                            next_para = content.find("\n\n", pos + 1)
                            if next_para == -1 or next_para > section_start + 2000:
                                break
                            para_count += 1
                            pos = next_para
                        
                        if para_count > 0:
                            next_section = pos
                        else:
                            next_section = min(section_start + 2000, len(content))
                    
                    # Extract clause text
                    clause_text = content[section_start:next_section].strip()
                    
                    # Create clause dictionary
                    clause = {
                        "type": clause_type,
                        "text": clause_text,
                        "start_pos": section_start,
                        "end_pos": next_section,
                        "heading": match.group(0)
                    }
                    
                    # Check for duplicate clauses (same position)
                    if not any(c for c in clauses if c["start_pos"] == section_start):
                        clauses.append(clause)
        
        return clauses
    
    def _identify_parties(self, content: str, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Identify parties to the agreement.
        
        Args:
            content: Document content
            entities: List of extracted entities
            
        Returns:
            List of party dictionaries
        """
        parties = []
        
        # Look for organizations in entities
        org_entities = [e for e in entities if e.get("entity_type") == EntityType.ORGANIZATION.value]
        
        # Look for party indicators in the document
        party_indicators = [
            r"(party of the first part)",
            r"(party of the second part)",
            r"\"?(seller|vendor|provider|licensor|lessor|consultant|contractor)\"?",
            r"\"?(buyer|customer|client|licensee|lessee|company)\"?",
            r"\"?(employer|employee)\"?",
            r"\"?(landlord|tenant)\"?"
        ]
        
        for indicator_pattern in party_indicators:
            pattern = re.compile(fr"([A-Z][A-Za-z\s,\.]+?)\s+(?:{indicator_pattern})", re.IGNORECASE)
            for match in pattern.finditer(content):
                party_name = match.group(1).strip()
                party_role = match.group(2).strip()
                
                # Add party
                party = {
                    "name": party_name,
                    "role": party_role,
                    "party_id": f"party_{len(parties) + 1}"
                }
                
                # Check for duplicates (same name)
                if not any(p for p in parties if p["name"] == party_name):
                    parties.append(party)
        
        # If no parties found with indicators, use organizations
        if not parties and org_entities:
            # Use the first few organizations as parties
            for i, org in enumerate(org_entities[:2]):  # Assume max 2 parties
                party = {
                    "name": org["text"],
                    "role": "party" if i == 0 else "counterparty",
                    "party_id": f"party_{i + 1}"
                }
                parties.append(party)
        
        return parties
    
    def _identify_jurisdiction_and_law(self, content: str, clauses: List[Dict[str, Any]]) -> Tuple[Optional[str], Optional[str]]:
        """
        Identify jurisdiction and governing law.
        
        Args:
            content: Document content
            clauses: List of clauses
            
        Returns:
            Tuple of (jurisdiction, governing_law)
        """
        jurisdiction = None
        governing_law = None
        
        # Look for governing law clause
        gov_law_clauses = [c for c in clauses if c["type"] == "governing_law"]
        
        if gov_law_clauses:
            clause_text = gov_law_clauses[0]["text"]
            
            # Look for jurisdiction
            jurisdiction_patterns = [
                r"jurisdiction\s+of\s+(?:the\s+)?(courts\s+of\s+)?([A-Za-z\s]+)",
                r"exclusive\s+jurisdiction\s+(?:of\s+)?(?:the\s+)?(courts\s+of\s+)?([A-Za-z\s]+)"
            ]
            
            for pattern in jurisdiction_patterns:
                jurisdiction_match = re.search(pattern, clause_text, re.IGNORECASE)
                if jurisdiction_match:
                    jurisdiction = jurisdiction_match.group(2).strip()
                    break
            
            # Look for governing law
            gov_law_patterns = [
                r"governed\s+by\s+(?:the\s+)?laws\s+of\s+(?:the\s+)?([A-Za-z\s]+)",
                r"law\s+of\s+(?:the\s+)?([A-Za-z\s]+)\s+shall\s+govern",
                r"governed\s+by\s+(?:the\s+)?([A-Za-z\s]+)\s+law"
            ]
            
            for pattern in gov_law_patterns:
                gov_law_match = re.search(pattern, clause_text, re.IGNORECASE)
                if gov_law_match:
                    governing_law = gov_law_match.group(1).strip()
                    break
        
        # If not found in clauses, search the entire document
        if not jurisdiction:
            jurisdiction_patterns = [
                r"jurisdiction\s+of\s+(?:the\s+)?(courts\s+of\s+)?([A-Za-z\s]+)",
                r"exclusive\s+jurisdiction\s+(?:of\s+)?(?:the\s+)?(courts\s+of\s+)?([A-Za-z\s]+)"
            ]
            
            for pattern in jurisdiction_patterns:
                jurisdiction_match = re.search(pattern, content, re.IGNORECASE)
                if jurisdiction_match:
                    jurisdiction = jurisdiction_match.group(2).strip()
                    break
        
        if not governing_law:
            gov_law_patterns = [
                r"governed\s+by\s+(?:the\s+)?laws\s+of\s+(?:the\s+)?([A-Za-z\s]+)",
                r"law\s+of\s+(?:the\s+)?([A-Za-z\s]+)\s+shall\s+govern",
                r"governed\s+by\s+(?:the\s+)?([A-Za-z\s]+)\s+law"
            ]
            
            for pattern in gov_law_patterns:
                gov_law_match = re.search(pattern, content, re.IGNORECASE)
                if gov_law_match:
                    governing_law = gov_law_match.group(1).strip()
                    break
        
        return jurisdiction, governing_law
    
    def _extract_dates(self, content: str, entities: List[Dict[str, Any]]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Extract relevant dates from the document.
        
        Args:
            content: Document content
            entities: List of extracted entities
            
        Returns:
            Tuple of (effective_date, expiration_date, document_date)
        """
        effective_date = None
        expiration_date = None
        document_date = None
        
        # Look for date entities
        date_entities = [e for e in entities if e.get("entity_type") == EntityType.DATE.value]
        
        # Look for document date indicators
        doc_date_patterns = [
            r"(dated|executed|signed)(?:\s+as)?(?:\s+of)?\s+([A-Za-z]+\s+\d{1,2},?\s+\d{4}|\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})",
            r"(?:this|the)\s+(?:agreement|contract).*?dated\s+([A-Za-z]+\s+\d{1,2},?\s+\d{4}|\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})"
        ]
        
        for pattern in doc_date_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                document_date = match.group(2) if len(match.groups()) > 1 else match.group(1)
                break
        
        # Look for effective date indicators
        effective_date_patterns = [
            r"effective\s+(?:date|as\s+of)(?:\s+this\s+agreement\s+is)?\s+([A-Za-z]+\s+\d{1,2},?\s+\d{4}|\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})",
            r"effective\s+(?:date|as\s+of).*?\"([A-Za-z]+\s+\d{1,2},?\s+\d{4}|\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})\"",
            r"shall\s+(?:be|become)\s+effective\s+(?:on|as\s+of)\s+([A-Za-z]+\s+\d{1,2},?\s+\d{4}|\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})"
        ]
        
        for pattern in effective_date_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                effective_date = match.group(1)
                break
        
        # Look for expiration date indicators
        expiration_date_patterns = [
            r"(?:expires|expire|expiration|termination)\s+(?:date|on)\s+([A-Za-z]+\s+\d{1,2},?\s+\d{4}|\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})",
            r"shall\s+(?:expire|terminate)\s+(?:on|as\s+of)\s+([A-Za-z]+\s+\d{1,2},?\s+\d{4}|\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})",
            r"until\s+([A-Za-z]+\s+\d{1,2},?\s+\d{4}|\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})"
        ]
        
        for pattern in expiration_date_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                expiration_date = match.group(1)
                break
        
        # If dates not found but date entities exist, make educated guesses
        if date_entities and (not document_date or not effective_date):
            # If only one date entity, use it as document date
            if len(date_entities) == 1:
                document_date = document_date or date_entities[0]["text"]
            
            # If multiple dates, use the earliest as effective date and document date
            elif len(date_entities) > 1:
                # This would require proper date parsing and comparison in a real implementation
                document_date = document_date or date_entities[0]["text"]
                effective_date = effective_date or date_entities[0]["text"]
        
        return effective_date, expiration_date, document_date
    
    def _extract_keywords(self, content: str) -> List[str]:
        """
        Extract keywords from the document.
        
        Args:
            content: Document content
            
        Returns:
            List of keywords
        """
        keywords = []
        
        # Extract defined terms (often in quotes or ALL CAPS)
        defined_terms_patterns = [
            r'"([A-Z][a-zA-Z\s]+)"',
            r'"([A-Za-z][a-zA-Z\s]+)"(?:\s+means)',
            r'the term\s+"([A-Za-z][a-zA-Z\s]+)"',
            r'([A-Z][A-Z\s]{2,})'  # All caps words (3+ chars)
        ]
        
        for pattern in defined_terms_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                term = match.strip()
                if len(term) > 2 and term not in keywords:
                    keywords.append(term)
        
        # Extract common legal terms
        legal_terms = [
            "indemnification", "warranty", "liability", "confidentiality",
            "termination", "jurisdiction", "arbitration", "compliance",
            "breach", "damages", "intellectual property", "payment terms",
            "force majeure", "governing law", "representations", "warranties"
        ]
        
        for term in legal_terms:
            if term.lower() in content.lower() and term not in keywords:
                keywords.append(term)
        
        return keywords[:20]  # Limit to top 20 keywords
    
    def _assess_risks(self, content: str, clauses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Assess legal risks in the document.
        
        Args:
            content: Document content
            clauses: List of clauses
            
        Returns:
            List of risk factor dictionaries
        """
        risks = []
        
        # Check for risk patterns
        for risk_type, patterns in self.compiled_risk_patterns.items():
            for pattern in patterns:
                if pattern.search(content):
                    risks.append({
                        "risk_type": risk_type,
                        "severity": "high" if risk_type in ["high_liability", "unreasonable_indemnity"] else "medium",
                        "description": self._get_risk_description(risk_type)
                    })
                    break  # Only report each risk type once
        
        # Check for missing clauses
        essential_clauses = [
            "termination", "limitation_of_liability", "indemnification",
            "confidentiality", "governing_law", "dispute_resolution"
        ]
        
        existing_clause_types = [c["type"] for c in clauses]
        for clause_type in essential_clauses:
            if clause_type not in existing_clause_types:
                risks.append({
                    "risk_type": "missing_clause",
                    "severity": "high" if clause_type in ["termination", "limitation_of_liability"] else "medium",
                    "description": f"Missing {clause_type.replace('_', ' ')} clause",
                    "clause_type": clause_type
                })
        
        return risks
    
    def _get_risk_description(self, risk_type: str) -> str:
        """
        Get a description for a risk type.
        
        Args:
            risk_type: Risk type identifier
            
        Returns:
            Risk description
        """
        descriptions = {
            "high_liability": "High liability risk due to unlimited or strict liability terms",
            "unreasonable_indemnity": "Unreasonable indemnification terms that create unbalanced risk",
            "perpetual_term": "Perpetual term with no clear end date or termination rights",
            "unilateral_termination": "Unilateral termination rights that favor one party",
            "automatic_renewal": "Automatic renewal without notice which may create ongoing obligations",
            "unfavorable_jurisdiction": "Unfavorable jurisdiction or venue selection",
            "unclear_deliverables": "Unclear deliverables or performance standards",
            "missing_clause": "Missing essential clause"
        }
        
        return descriptions.get(risk_type, "Unknown risk")
    
    def _extract_title(self, content: str) -> Optional[str]:
        """
        Extract document title from content.
        
        Args:
            content: Document content
            
        Returns:
            Document title or None
        """
        # Look for title at the beginning of the document
        lines = content.splitlines()
        if not lines:
            return None
        
        # Check the first few non-empty lines
        candidate_lines = []
        for line in lines[:10]:
            line = line.strip()
            if line:
                candidate_lines.append(line)
                if len(candidate_lines) >= 3:
                    break
        
        if not candidate_lines:
            return None
        
        # Look for typical title patterns
        title_patterns = [
            # All caps line
            r'^([A-Z][A-Z\s\d.,_-]{5,})$',
            # Title case with "agreement" or "contract"
            r'^([A-Z][a-zA-Z\d\s.,_-]*(AGREEMENT|CONTRACT|TERMS|POLICY)[a-zA-Z\d\s.,_-]*)$',
            r'^([A-Z][a-zA-Z\d\s.,_-]*(Agreement|Contract|Terms|Policy)[a-zA-Z\d\s.,_-]*)$'
        ]
        
        for line in candidate_lines:
            for pattern in title_patterns:
                match = re.match(pattern, line)
                if match:
                    return match.group(1)
        
        # If no match found, use the first line if it's reasonably short
        if len(candidate_lines[0]) <= 100:
            return candidate_lines[0]
        
        return None
    
    def _generate_summary(self, content: str, doc_type: DocumentType) -> Optional[str]:
        """
        Generate a summary of the document using AI.
        
        Args:
            content: Document content
            doc_type: Document type
            
        Returns:
            Summary string or None if AI is not available
        """
        # This is a placeholder for AI integration
        # In a real implementation, this would:
        # 1. Truncate content if it's too long
        # 2. Send to AI service for summarization
        # 3. Return the generated summary
        
        # For now, return a basic summary
        doc_type_str = doc_type.name.replace('_', ' ').title()
        
        lines = content.splitlines()
        content_start = ""
        
        # Get first 5 non-empty lines
        count = 0
        for line in lines:
            line = line.strip()
            if line:
                content_start += line + " "
                count += 1
                if count >= 5:
                    break
        
        content_start = content_start.strip()
        if len(content_start) > 200:
            content_start = content_start[:197] + "..."
        
        return f"{doc_type_str} document. {content_start}"
    
    def _analyze_sentiment(self, content: str) -> Dict[str, Any]:
        """
        Analyze sentiment in the document.
        
        Args:
            content: Document content
            
        Returns:
            Dictionary with sentiment analysis results
        """
        # This is a placeholder for AI sentiment analysis
        # In a real implementation, this would use NLP to analyze sentiment
        
        # For now, return basic metrics
        words = re.findall(r'\b\w+\b', content.lower())
        
        # Count positive and negative terms
        positive_terms = ["agree", "consent", "accept", "approve", "grant", "permit", "allow"]
        negative_terms = ["dispute", "breach", "terminate", "violation", "penalty", "damages", "liability"]
        
        positive_count = sum(1 for word in words if word in positive_terms)
        negative_count = sum(1 for word in words if word in negative_terms)
        
        # Calculate a basic sentiment score (-1 to 1)
        total = positive_count + negative_count
        sentiment_score = 0
        if total > 0:
            sentiment_score = (positive_count - negative_count) / total
        
        return {
            "sentiment_score": sentiment_score,
            "positive_terms": positive_count,
            "negative_terms": negative_count,
            "balanced": abs(sentiment_score) < 0.3  # Consider balanced if score is near zero
        }