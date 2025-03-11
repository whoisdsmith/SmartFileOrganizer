"""
OCR Service Module for Smart File Organizer.
Provides OCR capabilities for image-based PDFs and scanned documents.
(TEMPORARY MOCK VERSION FOR TESTING)
"""

import os
import logging
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from PIL import Image


class OCRService:
    """Handles OCR operations with support for multiple engines and languages."""

    def __init__(self, config: Optional[Dict] = None):
        """Initialize OCR service with configuration."""
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        self.supported_languages = ['eng']
        self.logger.warning("Using mock OCR service for testing")

    def _get_supported_languages(self) -> List[str]:
        """Get list of supported languages by the OCR engines."""
        return ['eng']  # Default to English

    def preprocess_image(self, image: Image.Image) -> Image.Image:
        """Preprocess image for better OCR results."""
        return image  # No preprocessing in mock version

    def detect_language(self, text: str) -> str:
        """Detect the language of the text."""
        return 'eng'  # Default to English in mock version

    def process_pdf(self, pdf_path: str, **kwargs) -> List[Dict[str, Any]]:
        """Process a PDF file and extract text using OCR."""
        self.logger.info(f"Mock OCR processing PDF: {pdf_path}")
        
        # Return mock result
        return [{
            'page': 1,
            'text': "[OCR Text Extraction Placeholder - PDF]",
            'confidence': 100.0,
            'language': 'eng'
        }]

    def process_image(self, image: Image.Image, engine: str = 'auto',
                      lang: Optional[str] = None) -> Dict[str, Any]:
        """Process an image and extract text using specified OCR engine."""
        self.logger.info("Mock OCR processing image")
        
        # Return mock result
        return {
            'text': "[OCR Text Extraction Placeholder - Image]",
            'confidence': 100.0,
            'language': 'eng',
            'engine': 'mock'
        }

    def _process_with_tesseract(self, image: Image.Image,
                                lang: Optional[str] = None) -> Dict[str, Any]:
        """Process image using Tesseract OCR."""
        # Mock implementation
        return {
            'text': "[OCR Text Extraction Placeholder - Tesseract]",
            'confidence': 100.0,
            'language': 'eng',
            'engine': 'tesseract'
        }

    def _process_with_easyocr(self, image: Image.Image,
                              lang: Optional[str] = None) -> Dict[str, Any]:
        """Process image using EasyOCR."""
        # Mock implementation
        return {
            'text': "[OCR Text Extraction Placeholder - EasyOCR]",
            'confidence': 100.0,
            'language': 'eng',
            'engine': 'easyocr'
        }
