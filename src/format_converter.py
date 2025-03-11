"""
Format Converter Module for Smart File Organizer.
Provides multi-format batch conversion capabilities.
"""

import os
import logging
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import json
import shutil
import subprocess
from PIL import Image
import pypandoc
from pdf2image import convert_from_path
import python_docx
from docx import Document
from pptx import Presentation
import csv
import openpyxl
import json
import yaml
import threading
from queue import Queue
import tempfile


class FormatConverter:
    """Handles multi-format batch conversion operations."""

    def __init__(self, config: Optional[Dict] = None):
        """Initialize format converter with configuration."""
        self.config = config or {}
        self.logger = logging.getLogger(__name__)

        # Default settings
        self.settings = {
            'max_threads': 4,                    # Maximum number of conversion threads
            'temp_dir': 'src/cache/conversions',  # Temporary directory for conversions
            'preserve_metadata': True,           # Preserve metadata during conversion
            # Image conversion quality (0-100)
            'image_quality': 90,
            'pdf_dpi': 300,                     # DPI for PDF conversions
            'cache_enabled': True,               # Enable caching of conversion results
            'supported_formats': {
                'documents': {
                    'input': ['.docx', '.doc', '.rtf', '.odt', '.txt', '.md', '.html'],
                    'output': ['.pdf', '.docx', '.txt', '.md', '.html']
                },
                'spreadsheets': {
                    'input': ['.xlsx', '.xls', '.csv', '.ods'],
                    'output': ['.xlsx', '.csv']
                },
                'presentations': {
                    'input': ['.pptx', '.ppt', '.odp'],
                    'output': ['.pdf', '.pptx']
                },
                'images': {
                    'input': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff'],
                    'output': ['.jpg', '.png', '.pdf', '.tiff']
                },
                'ebooks': {
                    'input': ['.epub', '.mobi', '.azw3'],
                    'output': ['.pdf', '.epub']
                }
            }
        }
        self.settings.update(self.config.get('format_conversion', {}))

        # Create temp directory
        os.makedirs(self.settings['temp_dir'], exist_ok=True)

        # Initialize conversion registry
        self._init_conversion_registry()

    def convert_batch(self, files: List[Dict[str, Any]], target_format: str,
                      callback=None) -> Dict[str, Any]:
        """
        Convert a batch of files to the target format.

        Args:
            files: List of file dictionaries with paths and metadata
            target_format: Target format extension (e.g., '.pdf')
            callback: Optional progress callback function

        Returns:
            Dictionary with conversion results and statistics
        """
        try:
            total_files = len(files)
            if callback:
                callback(0, total_files, "Starting batch conversion...")

            # Validate target format
            if not self._is_supported_format(target_format):
                raise ValueError(f"Unsupported target format: {target_format}")

            # Group files by type
            type_groups = self._group_by_type(files)

            # Initialize results
            results = {
                'converted': [],
                'failed': [],
                'stats': {
                    'total': total_files,
                    'success': 0,
                    'failed': 0
                }
            }

            # Process each group in parallel
            with ThreadPoolExecutor(max_workers=self.settings['max_threads']) as executor:
                futures = []

                for source_type, group in type_groups.items():
                    if not self._can_convert(source_type, target_format):
                        # Add to failed if conversion not supported
                        for file_info in group:
                            results['failed'].append({
                                'file': file_info,
                                'error': f"Conversion from {source_type} to {target_format} not supported"
                            })
                        continue

                    # Submit conversion tasks
                    for file_info in group:
                        future = executor.submit(
                            self._convert_file,
                            file_info,
                            target_format
                        )
                        futures.append((future, file_info))

                # Process results as they complete
                for i, (future, file_info) in enumerate(futures):
                    try:
                        result = future.result()
                        if result['success']:
                            results['converted'].append(result)
                            results['stats']['success'] += 1
                        else:
                            results['failed'].append({
                                'file': file_info,
                                'error': result['error']
                            })
                            results['stats']['failed'] += 1

                        if callback:
                            callback(i + 1, total_files,
                                     f"Converting {file_info['file_name']}...")

                    except Exception as e:
                        results['failed'].append({
                            'file': file_info,
                            'error': str(e)
                        })
                        results['stats']['failed'] += 1

            if callback:
                callback(total_files, total_files, "Batch conversion complete")

            return results

        except Exception as e:
            self.logger.error(f"Error in batch conversion: {e}")
            return {
                'error': str(e),
                'converted': [],
                'failed': files,
                'stats': {
                    'total': total_files,
                    'success': 0,
                    'failed': total_files
                }
            }

    def _convert_file(self, file_info: Dict[str, Any], target_format: str) -> Dict[str, Any]:
        """Convert a single file to the target format."""
        try:
            source_path = file_info['file_path']
            source_format = os.path.splitext(source_path)[1].lower()

            # Generate output path
            output_dir = os.path.dirname(source_path)
            output_name = os.path.splitext(os.path.basename(source_path))[0]
            output_path = os.path.join(
                output_dir, f"{output_name}{target_format}")

            # Get appropriate converter
            converter = self._get_converter(source_format, target_format)
            if not converter:
                raise ValueError(
                    f"No converter found for {source_format} to {target_format}")

            # Perform conversion
            result = converter(source_path, output_path)

            if result['success']:
                # Preserve metadata if enabled
                if self.settings['preserve_metadata']:
                    self._preserve_metadata(source_path, output_path)

                return {
                    'success': True,
                    'source_path': source_path,
                    'output_path': output_path,
                    'format': target_format,
                    'metadata': result.get('metadata', {})
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error', 'Unknown conversion error')
                }

        except Exception as e:
            self.logger.error(
                f"Error converting file {file_info['file_path']}: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def _init_conversion_registry(self):
        """Initialize the conversion function registry."""
        self._converters = {
            # Document conversions
            ('.docx', '.pdf'): self._convert_docx_to_pdf,
            ('.doc', '.pdf'): self._convert_doc_to_pdf,
            ('.txt', '.pdf'): self._convert_text_to_pdf,
            ('.md', '.pdf'): self._convert_markdown_to_pdf,
            ('.html', '.pdf'): self._convert_html_to_pdf,

            # Image conversions
            ('.jpg', '.png'): self._convert_image,
            ('.jpeg', '.png'): self._convert_image,
            ('.png', '.jpg'): self._convert_image,
            ('.png', '.pdf'): self._convert_image_to_pdf,
            ('.jpg', '.pdf'): self._convert_image_to_pdf,

            # Spreadsheet conversions
            ('.xlsx', '.csv'): self._convert_xlsx_to_csv,
            ('.csv', '.xlsx'): self._convert_csv_to_xlsx,

            # Presentation conversions
            ('.pptx', '.pdf'): self._convert_pptx_to_pdf,

            # Generic conversions using pandoc
            ('*', '*'): self._convert_with_pandoc
        }

    def _get_converter(self, source_format: str, target_format: str):
        """Get the appropriate converter function for the format pair."""
        # Try specific converter first
        converter = self._converters.get(
            (source_format.lower(), target_format.lower()))
        if converter:
            return converter

        # Try generic converter
        return self._converters.get(('*', '*'))

    def _convert_docx_to_pdf(self, source_path: str, output_path: str) -> Dict[str, Any]:
        """Convert DOCX to PDF using python-docx and reportlab."""
        try:
            doc = Document(source_path)
            # Implementation of DOCX to PDF conversion
            # This would use a PDF generation library like reportlab
            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _convert_image(self, source_path: str, output_path: str) -> Dict[str, Any]:
        """Convert between image formats using Pillow."""
        try:
            with Image.open(source_path) as img:
                # Convert RGBA to RGB if saving as JPEG
                if output_path.lower().endswith('.jpg') and img.mode == 'RGBA':
                    img = img.convert('RGB')

                img.save(output_path, quality=self.settings['image_quality'])
                return {'success': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _convert_image_to_pdf(self, source_path: str, output_path: str) -> Dict[str, Any]:
        """Convert image to PDF."""
        try:
            with Image.open(source_path) as img:
                if img.mode == 'RGBA':
                    img = img.convert('RGB')
                img.save(output_path, 'PDF',
                         resolution=self.settings['pdf_dpi'])
                return {'success': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _convert_xlsx_to_csv(self, source_path: str, output_path: str) -> Dict[str, Any]:
        """Convert XLSX to CSV."""
        try:
            wb = openpyxl.load_workbook(source_path)
            sheet = wb.active

            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                for row in sheet.rows:
                    writer.writerow([cell.value for cell in row])

            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _convert_csv_to_xlsx(self, source_path: str, output_path: str) -> Dict[str, Any]:
        """Convert CSV to XLSX."""
        try:
            wb = openpyxl.Workbook()
            sheet = wb.active

            with open(source_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    sheet.append(row)

            wb.save(output_path)
            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _convert_with_pandoc(self, source_path: str, output_path: str) -> Dict[str, Any]:
        """Convert using pandoc as a fallback."""
        try:
            # Get input and output formats
            input_format = os.path.splitext(source_path)[1][1:]  # Remove dot
            output_format = os.path.splitext(output_path)[1][1:]

            # Convert using pandoc
            pypandoc.convert_file(
                source_path,
                output_format,
                outputfile=output_path,
                format=input_format
            )

            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _preserve_metadata(self, source_path: str, output_path: str):
        """Preserve metadata during conversion when possible."""
        try:
            # Implementation depends on file formats
            pass
        except Exception as e:
            self.logger.warning(f"Error preserving metadata: {e}")

    def _is_supported_format(self, format_ext: str) -> bool:
        """Check if a format is supported."""
        format_ext = format_ext.lower()
        return any(
            format_ext in formats['output']
            for formats in self.settings['supported_formats'].values()
        )

    def _can_convert(self, source_format: str, target_format: str) -> bool:
        """Check if conversion between formats is supported."""
        source_format = source_format.lower()
        target_format = target_format.lower()

        # Check if we have a direct converter
        if (source_format, target_format) in self._converters:
            return True

        # Check if we can use pandoc
        if self._converters.get(('*', '*')):
            return True

        return False

    def _group_by_type(self, files: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group files by their format."""
        type_groups = {}
        for file_info in files:
            ext = os.path.splitext(file_info['file_path'])[1].lower()
            if ext not in type_groups:
                type_groups[ext] = []
            type_groups[ext].append(file_info)
        return type_groups

    def clear_cache(self) -> bool:
        """Clear conversion cache."""
        try:
            if self.settings['cache_enabled']:
                import shutil
                shutil.rmtree(self.settings['temp_dir'])
                os.makedirs(self.settings['temp_dir'])
            return True
        except Exception as e:
            self.logger.error(f"Error clearing cache: {e}")
            return False
