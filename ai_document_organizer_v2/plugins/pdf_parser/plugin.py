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
        
        # Register default settings if not already present
        if self.settings_manager is not None:
            # Use get_setting/set_setting to access settings manager
            extract_images = self.get_setting("pdf_parser.extract_images", None)
            if extract_images is None:
                self.set_setting("pdf_parser.extract_images", False)
                
            ocr_enabled = self.get_setting("pdf_parser.ocr_enabled", None)
            if ocr_enabled is None:
                self.set_setting("pdf_parser.ocr_enabled", False)
                
            ocr_language = self.get_setting("pdf_parser.ocr_language", None)
            if ocr_language is None:
                self.set_setting("pdf_parser.ocr_language", "eng")
                
            logger.info("PDF parser settings initialized")
        
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
        # Get settings - using BasePlugin convenience methods
        extract_images = self.get_setting("pdf_parser.extract_images", False)
        ocr_enabled = self.get_setting("pdf_parser.ocr_enabled", False)
        ocr_language = self.get_setting("pdf_parser.ocr_language", "eng")
        
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
        # Get settings through BasePlugin convenience methods
        extract_images = self.get_setting("pdf_parser.extract_images", False)
        ocr_enabled = self.get_setting("pdf_parser.ocr_enabled", False)
        ocr_language = self.get_setting("pdf_parser.ocr_language", "eng")
        
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
                'file_type': 'pdf',
                'settings': {
                    'extract_images': extract_images,
                    'ocr_enabled': ocr_enabled,
                    'ocr_language': ocr_language
                }
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
            
            # Process with OCR if enabled and text is empty or very small
            ocr_enabled = self.get_setting("pdf_parser.ocr_enabled", False)
            ocr_language = self.get_setting("pdf_parser.ocr_language", "eng")
            
            if ocr_enabled and (not text or len(text.split()) < 50):
                logger.info(f"Text extraction produced limited results, attempting OCR with language: {ocr_language}")
                
                try:
                    # We'd call the OCR service here in a real implementation
                    # This is a placeholder for the OCR integration
                    metadata['ocr_used'] = True
                    metadata['ocr_language'] = ocr_language
                    
                    # In a real implementation, we'd process each page with OCR
                    # For now, we'll just log the intent
                    logger.info(f"OCR would be applied to PDF: {file_path} with language: {ocr_language}")
                    
                    # If we had actual OCR results, we'd replace or augment the text here
                    if not text:
                        text = f"[OCR processing would extract text in {ocr_language} language]"
                        metadata['ocr_note'] = "This is a placeholder for actual OCR processing"
                except Exception as e:
                    logger.error(f"Error during OCR processing: {e}")
                    metadata['ocr_error'] = str(e)
            
            # Extract images if enabled
            extract_images = self.get_setting("pdf_parser.extract_images", False)
            if extract_images:
                logger.info(f"Extracting images from PDF: {file_path}")
                
                try:
                    images_info = self._extract_images(file_path)
                    if images_info:
                        metadata['images'] = images_info
                except Exception as e:
                    logger.error(f"Error extracting images from PDF: {e}")
                    metadata['image_extraction_error'] = str(e)
            
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
    
    def _extract_images(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Extract images from a PDF file.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            List of image information dictionaries
        """
        images_info = []
        
        try:
            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                return images_info
                
            if PDF_LIBRARY == "pypdf":
                with open(file_path, 'rb') as file:
                    reader = pypdf.PdfReader(file)
                    
                    # Get base filename for extracted images
                    base_filename = os.path.splitext(os.path.basename(file_path))[0]
                    
                    # Create images directory if needed - in same location as PDF
                    parent_dir = os.path.dirname(file_path)
                    images_dir = os.path.join(parent_dir, f"{base_filename}_images")
                    
                    # In a real implementation, we would extract the images here
                    # For now, we'll just log the intent
                    logger.info(f"Would create image directory: {images_dir}")
                    
                    for i, page in enumerate(reader.pages):
                        # In an actual implementation, we'd extract images from each page
                        # and save them to the images directory
                        logger.info(f"Would extract images from page {i+1}")
                        
                        # Add placeholder info about images that would be extracted
                        images_info.append({
                            'page': i+1,
                            'would_save_to': f"{images_dir}/page_{i+1}_img_1.png",
                            'placeholder': True
                        })
                
            elif PDF_LIBRARY == "PyPDF2":
                with open(file_path, 'rb') as file:
                    reader = PyPDF2.PdfReader(file)
                    
                    # Similar implementation as above would be here
                    base_filename = os.path.splitext(os.path.basename(file_path))[0]
                    parent_dir = os.path.dirname(file_path)
                    images_dir = os.path.join(parent_dir, f"{base_filename}_images")
                    
                    logger.info(f"Would create image directory: {images_dir}")
                    
                    for i in range(len(reader.pages)):
                        logger.info(f"Would extract images from page {i+1}")
                        
                        images_info.append({
                            'page': i+1,
                            'would_save_to': f"{images_dir}/page_{i+1}_img_1.png",
                            'placeholder': True
                        })
            
            return images_info
            
        except Exception as e:
            logger.error(f"Error extracting images from PDF: {e}")
            return images_info
            
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