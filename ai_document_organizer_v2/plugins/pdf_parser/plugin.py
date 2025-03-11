"""
PDF Parser Plugin for AI Document Organizer V2.

This plugin provides PDF parsing capabilities for extracting text and metadata from PDF files.
"""

import os
import io
import logging
import re
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

# Import plugin base class
from ai_document_organizer_v2.core.plugin_base import FileParserPlugin

# Try importing PyPDF2/PyPDF
try:
    import pypdf
    PDF_LIBRARY = "pypdf"
except ImportError:
    try:
        import PyPDF2
        PDF_LIBRARY = "PyPDF2"
    except ImportError:
        PDF_LIBRARY = None

logger = logging.getLogger("AIDocumentOrganizerV2.PDFParser")

class PDFParserPlugin(FileParserPlugin):
    """
    Plugin for parsing PDF files.
    
    This plugin extracts text content and metadata from PDF files.
    """
    
    # Plugin metadata
    name = "PDF Parser"
    version = "1.0.0"
    description = "Extracts text content and metadata from PDF files"
    author = "AI Document Organizer Team"
    dependencies = ["pypdf or PyPDF2"]
    
    # File extensions supported by this plugin
    supported_extensions = [".pdf"]
    
    def __init__(self, plugin_id: str, name: Optional[str] = None, version: Optional[str] = None,
                 description: Optional[str] = None):
        """
        Initialize the PDF parser plugin.
        
        Args:
            plugin_id: Unique identifier for the plugin
            name: Plugin name (if None, uses class attribute)
            version: Plugin version (if None, uses class attribute)
            description: Plugin description (if None, uses class attribute)
        """
        super().__init__(plugin_id, name, version, description)
        
        # Check if PDF library is available
        self.pdf_library_available = PDF_LIBRARY is not None
        if not self.pdf_library_available:
            logger.warning("No PDF library (pypdf or PyPDF2) available. PDF parsing will be limited.")
        else:
            logger.info(f"Using {PDF_LIBRARY} for PDF parsing")
    
    def initialize(self) -> bool:
        """
        Initialize the plugin.
        
        Returns:
            True if initialization was successful, False otherwise
        """
        # Check dependencies
        if not self.pdf_library_available:
            logger.warning("PDF library not available. Install pypdf for full functionality.")
            # Return True anyway to allow partial functionality
        
        return True
    
    def parse_file(self, file_path: str) -> Dict[str, Any]:
        """
        Parse a PDF file and extract content and metadata.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Dictionary containing:
            - 'content': Extracted text content
            - 'metadata': Dictionary with file metadata
            - 'success': Boolean indicating success/failure
            - 'error': Error message if parsing failed
        """
        if not os.path.exists(file_path):
            return {
                'content': '',
                'metadata': {},
                'success': False,
                'error': f"File not found: {file_path}"
            }
        
        if not self.pdf_library_available:
            # Basic file info without content extraction
            file_stat = os.stat(file_path)
            return {
                'content': f"[PDF content extraction not available - install pypdf]",
                'metadata': {
                    'filename': os.path.basename(file_path),
                    'filepath': file_path,
                    'file_size': file_stat.st_size,
                    'created_time': datetime.fromtimestamp(file_stat.st_ctime).isoformat(),
                    'modified_time': datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
                    'file_type': 'pdf',
                    'pages': 0,
                    'error': 'PDF library not available'
                },
                'success': False,
                'error': "PDF library not available"
            }
        
        try:
            # Extract text and metadata
            text, metadata = self._extract_pdf_content(file_path)
            
            return {
                'content': text,
                'metadata': metadata,
                'success': True,
                'error': ''
            }
        except Exception as e:
            logger.error(f"Error parsing PDF file {file_path}: {e}")
            return {
                'content': '',
                'metadata': {'error': str(e)},
                'success': False,
                'error': str(e)
            }
    
    def _extract_pdf_content(self, file_path: str) -> Tuple[str, Dict[str, Any]]:
        """
        Extract text content and metadata from a PDF file.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Tuple of (extracted text, metadata dictionary)
        """
        text = ""
        metadata = {}
        
        try:
            # Get basic file information
            file_stat = os.stat(file_path)
            metadata = {
                'filename': os.path.basename(file_path),
                'filepath': file_path,
                'file_size': file_stat.st_size,
                'created_time': datetime.fromtimestamp(file_stat.st_ctime).isoformat(),
                'modified_time': datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
                'file_type': 'pdf'
            }
            
            # Extract text content based on available library
            if PDF_LIBRARY == "pypdf":
                with open(file_path, 'rb') as file:
                    reader = pypdf.PdfReader(file)
                    num_pages = len(reader.pages)
                    metadata['pages'] = num_pages
                    
                    # Extract document info
                    if reader.metadata:
                        info = reader.metadata
                        metadata.update({
                            'title': info.title if info.title else '',
                            'author': info.author if info.author else '',
                            'subject': info.subject if info.subject else '',
                            'creator': info.creator if info.creator else '',
                            'producer': info.producer if info.producer else '',
                        })
                    
                    # Extract text from each page
                    for i in range(num_pages):
                        page = reader.pages[i]
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n\n"
            
            elif PDF_LIBRARY == "PyPDF2":
                with open(file_path, 'rb') as file:
                    reader = PyPDF2.PdfReader(file)
                    num_pages = len(reader.pages)
                    metadata['pages'] = num_pages
                    
                    # Extract document info
                    if reader.metadata:
                        info = reader.metadata
                        metadata.update({
                            'title': info.get('/Title', ''),
                            'author': info.get('/Author', ''),
                            'subject': info.get('/Subject', ''),
                            'creator': info.get('/Creator', ''),
                            'producer': info.get('/Producer', ''),
                        })
                    
                    # Extract text from each page
                    for i in range(num_pages):
                        page = reader.pages[i]
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n\n"
            
            # Clean up the text
            text = self._clean_text(text)
            
            # Add text stats to metadata
            metadata['word_count'] = len(text.split())
            metadata['char_count'] = len(text)
            
            return text, metadata
        
        except Exception as e:
            logger.error(f"Error extracting PDF content: {e}")
            raise
    
    def _clean_text(self, text: str) -> str:
        """
        Clean extracted text from PDF.
        
        Args:
            text: Raw text extracted from PDF
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove excessive line breaks (keeping paragraph breaks)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Trim leading/trailing whitespace
        text = text.strip()
        
        return text
    
    def get_config_schema(self) -> Dict[str, Any]:
        """
        Get JSON schema for plugin configuration.
        
        Returns:
            Dictionary with JSON schema for plugin configuration
        """
        return {
            "type": "object",
            "properties": {
                "extract_images": {
                    "type": "boolean",
                    "title": "Extract Images",
                    "description": "Extract images from PDF files",
                    "default": False
                },
                "ocr_enabled": {
                    "type": "boolean",
                    "title": "Enable OCR",
                    "description": "Enable OCR for scanned PDF documents",
                    "default": False
                },
                "ocr_language": {
                    "type": "string",
                    "title": "OCR Language",
                    "description": "Language code for OCR (e.g., 'eng' for English)",
                    "default": "eng"
                }
            },
            "required": []
        }