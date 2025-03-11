"""
OCR Service Module for Smart File Organizer.
Provides OCR capabilities for image-based PDFs and scanned documents.
"""

import os
import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import pytesseract
import easyocr
from langdetect import detect
from pdf2image import convert_from_path
from PIL import Image
import numpy as np


class OCRService:
    """Handles OCR operations with support for multiple engines and languages."""

    def __init__(self, config: Optional[Dict] = None):
        """Initialize OCR service with configuration."""
        self.config = config or {}
        self.logger = logging.getLogger(__name__)

        # Initialize OCR engines
        self.tesseract_path = self.config.get('tesseract_path', 'tesseract')
        if os.name == 'nt':  # Windows specific configuration
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_path

        self.easyocr_reader = None  # Lazy initialization
        self.supported_languages = self._get_supported_languages()

    def _get_supported_languages(self) -> List[str]:
        """Get list of supported languages by the OCR engines."""
        try:
            # Get Tesseract supported languages
            langs = pytesseract.get_languages()
            return [lang for lang in langs if lang != 'osd']
        except Exception as e:
            self.logger.warning(f"Could not get supported languages: {e}")
            return ['eng']  # Default to English

    def _initialize_easyocr(self, langs: List[str]) -> None:
        """Initialize EasyOCR reader with specified languages."""
        if not self.easyocr_reader:
            try:
                self.easyocr_reader = easyocr.Reader(langs)
            except Exception as e:
                self.logger.error(f"Failed to initialize EasyOCR: {e}")
                raise

    def preprocess_image(self, image: Image.Image) -> Image.Image:
        """Preprocess image for better OCR results."""
        # Convert to grayscale
        if image.mode != 'L':
            image = image.convert('L')

        # Basic image enhancement
        image = Image.fromarray(np.array(image))
        return image

    def detect_language(self, text: str) -> str:
        """Detect the language of the text."""
        try:
            return detect(text)
        except:
            return 'eng'  # Default to English if detection fails

    def process_pdf(self, pdf_path: str, **kwargs) -> List[Dict[str, any]]:
        """Process a PDF file and extract text using OCR."""
        results = []
        try:
            # Convert PDF to images
            images = convert_from_path(pdf_path)

            for i, image in enumerate(images):
                # Process each page
                page_result = self.process_image(image, **kwargs)
                results.append({
                    'page': i + 1,
                    'text': page_result['text'],
                    'confidence': page_result['confidence'],
                    'language': page_result['language']
                })

        except Exception as e:
            self.logger.error(f"Error processing PDF {pdf_path}: {e}")
            raise

        return results

    def process_image(self, image: Image.Image, engine: str = 'auto',
                      lang: Optional[str] = None) -> Dict[str, any]:
        """Process an image and extract text using specified OCR engine."""
        # Preprocess the image
        processed_image = self.preprocess_image(image)

        if engine == 'auto':
            # Try Tesseract first, fall back to EasyOCR if needed
            try:
                result = self._process_with_tesseract(processed_image, lang)
            except Exception as e:
                self.logger.warning(
                    f"Tesseract failed, falling back to EasyOCR: {e}")
                result = self._process_with_easyocr(processed_image, lang)
        elif engine == 'tesseract':
            result = self._process_with_tesseract(processed_image, lang)
        elif engine == 'easyocr':
            result = self._process_with_easyocr(processed_image, lang)
        else:
            raise ValueError(f"Unsupported OCR engine: {engine}")

        # Detect language if not provided
        if not lang:
            result['language'] = self.detect_language(result['text'])

        return result

    def _process_with_tesseract(self, image: Image.Image,
                                lang: Optional[str] = None) -> Dict[str, any]:
        """Process image using Tesseract OCR."""
        try:
            lang = lang or 'eng'
            data = pytesseract.image_to_data(
                image, lang=lang, output_type=pytesseract.Output.DICT)

            # Combine text and calculate confidence
            text = ' '.join(word for word in data['text'] if word.strip())
            confidence = sum(
                conf for conf in data['conf'] if conf > 0) / len(data['conf'])

            return {
                'text': text,
                'confidence': confidence,
                'language': lang,
                'engine': 'tesseract'
            }
        except Exception as e:
            self.logger.error(f"Tesseract OCR failed: {e}")
            raise

    def _process_with_easyocr(self, image: Image.Image,
                              lang: Optional[str] = None) -> Dict[str, any]:
        """Process image using EasyOCR."""
        try:
            langs = [lang] if lang else ['en']
            self._initialize_easyocr(langs)

            result = self.easyocr_reader.readtext(np.array(image))

            # Combine text and calculate confidence
            text_parts = []
            confidence_sum = 0

            for detection in result:
                text_parts.append(detection[1])
                confidence_sum += detection[2]

            text = ' '.join(text_parts)
            confidence = confidence_sum / len(result) if result else 0

            return {
                'text': text,
                'confidence': confidence,
                'language': langs[0],
                'engine': 'easyocr'
            }
        except Exception as e:
            self.logger.error(f"EasyOCR failed: {e}")
            raise
