"""
Advanced Duplicate Detector Module for Smart File Organizer.
Provides AI-powered duplicate detection using embeddings and perceptual hashing.
(MOCK IMPLEMENTATION FOR TESTING)
"""

import os
import logging
from typing import Dict, List, Optional, Tuple, Any
import hashlib
from pathlib import Path
import json
from PIL import Image
from collections import defaultdict
import mimetypes

# Mock implementation - no external dependencies
from .ocr_service import OCRService

# Mock VectorSearch class
class VectorSearch:
    """Mock vector search for semantic document similarity."""
    
    def __init__(self, config=None):
        self.logger = logging.getLogger(__name__)
        self.logger.warning("Using mock VectorSearch for testing")
        
    def index_documents(self, documents):
        """Mock indexing documents."""
        return True
        
    def find_similar_documents(self, file_path, threshold=0.8):
        """Mock finding similar documents."""
        return []


class DuplicateDetector:
    """Handles advanced duplicate detection using AI and perceptual hashing."""

    def __init__(self, config: Optional[Dict] = None):
        """Initialize duplicate detector with configuration."""
        self.config = config or {}
        self.logger = logging.getLogger(__name__)

        # Initialize vector search for content-based similarity
        self.vector_search = VectorSearch(self.config.get('vector_search', {}))

        # Initialize OCR service for image-based documents
        self.ocr_service = OCRService(self.config.get('ocr_config', {}))

        # Default settings
        self.settings = {
            # Threshold for content similarity (0-1)
            'content_similarity_threshold': 0.85,
            # Threshold for image similarity (0-1)
            'image_similarity_threshold': 0.90,
            'hash_size': 16,                      # Size of perceptual hash for images
            # Minimum file size to consider (bytes)
            'min_file_size': 1024,
            # Maximum content size to analyze (10MB)
            'max_content_size': 10 * 1024 * 1024,
            'batch_size': 100,                    # Number of files to process in batch
            'cache_enabled': True,                # Enable caching of analysis results
            'cache_dir': os.path.join('src', 'cache', 'duplicates')
        }
        self.settings.update(self.config.get('duplicate_detection', {}))

        # Create cache directory
        if self.settings['cache_enabled']:
            os.makedirs(self.settings['cache_dir'], exist_ok=True)

    def find_duplicates(self, files: List[Dict[str, Any]], callback=None) -> Dict[str, Any]:
        """
        Find duplicate files using multiple detection methods.

        Args:
            files: List of file dictionaries with paths and metadata
            callback: Optional progress callback function

        Returns:
            Dictionary with duplicate groups and statistics
        """
        try:
            total_files = len(files)
            if callback:
                callback(0, total_files, "Starting duplicate detection...")

            # Group files by size first (quick filter)
            size_groups = self._group_by_size(files)

            # Initialize results
            duplicate_groups = []
            stats = {
                'total_files': total_files,
                'duplicate_groups': 0,
                'total_duplicates': 0,
                'space_savings': 0
            }

            processed = 0
            for size, group in size_groups.items():
                if len(group) < 2:  # Skip unique files
                    continue

                # Update progress
                if callback:
                    callback(processed, total_files,
                             f"Analyzing group of {len(group)} files...")

                # Find duplicates within size group
                group_duplicates = self._analyze_group(group)

                # Add non-empty groups to results
                for dup_group in group_duplicates:
                    if len(dup_group) > 1:
                        duplicate_groups.append(dup_group)
                        stats['duplicate_groups'] += 1
                        stats['total_duplicates'] += len(dup_group) - 1
                        stats['space_savings'] += size * (len(dup_group) - 1)

                processed += len(group)

            if callback:
                callback(total_files, total_files,
                         "Duplicate detection complete")

            return {
                'duplicate_groups': duplicate_groups,
                'stats': stats
            }

        except Exception as e:
            self.logger.error(f"Error detecting duplicates: {e}")
            return {
                'error': str(e),
                'duplicate_groups': [],
                'stats': {}
            }

    def _analyze_group(self, files: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """Analyze a group of files for duplicates using multiple methods."""
        try:
            # First, group by file type
            type_groups = self._group_by_type(files)

            duplicate_groups = []
            for file_type, group in type_groups.items():
                if len(group) < 2:
                    continue

                if self._is_image_type(file_type):
                    # Use perceptual hashing for images
                    duplicates = self._find_image_duplicates(group)
                elif self._is_text_type(file_type):
                    # Use content analysis for text files
                    duplicates = self._find_text_duplicates(group)
                elif file_type.endswith('pdf'):
                    # Special handling for PDFs (may contain text or images)
                    duplicates = self._find_pdf_duplicates(group)
                else:
                    # Default to binary comparison
                    duplicates = self._find_binary_duplicates(group)

                duplicate_groups.extend(duplicates)

            return duplicate_groups

        except Exception as e:
            self.logger.error(f"Error analyzing group: {e}")
            return []

    def _find_image_duplicates(self, files: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """Find duplicate images using perceptual hashing (mock implementation)."""
        self.logger.info("Using mock image duplicate detection")
        try:
            # For mock purposes, just use a simple hash of the filename
            hash_groups = defaultdict(list)

            for file_info in files:
                try:
                    # Use file size and name for mock grouping
                    file_size = os.path.getsize(file_info['file_path'])
                    file_name = os.path.basename(file_info['file_path'])
                    
                    # Simple mock hash
                    hash_key = f"{file_size % 1000}_{len(file_name)}"
                    hash_groups[hash_key].append(file_info)

                except Exception as e:
                    self.logger.warning(
                        f"Error processing image {file_info['file_path']}: {e}")
                    continue

            # Convert groups to list and filter single files
            return [group for group in hash_groups.values() if len(group) > 1]

        except Exception as e:
            self.logger.error(f"Error finding image duplicates: {e}")
            return []

    def _find_text_duplicates(self, files: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """Find duplicate text files using content analysis."""
        try:
            # First pass: group by content hash
            hash_groups = defaultdict(list)

            for file_info in files:
                try:
                    with open(file_info['file_path'], 'rb') as f:
                        content = f.read()
                        if len(content) > self.settings['max_content_size']:
                            content = content[:self.settings['max_content_size']]
                        content_hash = hashlib.md5(content).hexdigest()
                        hash_groups[content_hash].append(file_info)
                except Exception as e:
                    self.logger.warning(
                        f"Error reading file {file_info['file_path']}: {e}")
                    continue

            # Second pass: analyze near-duplicates using vector similarity
            duplicate_groups = []

            # Process exact duplicates
            for group in hash_groups.values():
                if len(group) > 1:
                    duplicate_groups.append(group)

            # Process potential near-duplicates
            unique_files = [group[0]
                            for group in hash_groups.values() if len(group) == 1]
            if len(unique_files) > 1:
                # Index files for similarity search
                self.vector_search.index_documents(unique_files)

                # Find similar files
                processed = set()
                for file_info in unique_files:
                    if file_info['file_path'] in processed:
                        continue

                    similar = self.vector_search.find_similar_documents(
                        file_info['file_path'],
                        threshold=self.settings['content_similarity_threshold']
                    )

                    if similar:
                        group = [file_info]
                        for match in similar:
                            if match['file_path'] not in processed:
                                group.append(match)
                                processed.add(match['file_path'])

                        if len(group) > 1:
                            duplicate_groups.append(group)

                    processed.add(file_info['file_path'])

            return duplicate_groups

        except Exception as e:
            self.logger.error(f"Error finding text duplicates: {e}")
            return []

    def _find_pdf_duplicates(self, files: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """Find duplicate PDFs using content and OCR analysis."""
        try:
            # First, try text extraction
            text_duplicates = self._find_text_duplicates(files)

            # For files not in text duplicates, try OCR
            processed_files = {
                file_info['file_path']
                for group in text_duplicates
                for file_info in group
            }

            remaining_files = [
                f for f in files
                if f['file_path'] not in processed_files
            ]

            if not remaining_files:
                return text_duplicates

            # Process remaining files with OCR
            ocr_results = []
            for file_info in remaining_files:
                try:
                    result = self.ocr_service.process_pdf(
                        file_info['file_path'])
                    if result:
                        # Combine OCR text from all pages
                        text = ' '.join(page['text'] for page in result)
                        file_info['ocr_text'] = text
                        ocr_results.append(file_info)
                except Exception as e:
                    self.logger.warning(
                        f"OCR failed for {file_info['file_path']}: {e}")
                    continue

            # Find duplicates in OCR results using vector similarity
            if len(ocr_results) > 1:
                self.vector_search.index_documents(ocr_results)

                ocr_duplicates = []
                processed = set()

                for file_info in ocr_results:
                    if file_info['file_path'] in processed:
                        continue

                    similar = self.vector_search.find_similar_documents(
                        file_info['file_path'],
                        threshold=self.settings['content_similarity_threshold']
                    )

                    if similar:
                        group = [file_info]
                        for match in similar:
                            if match['file_path'] not in processed:
                                group.append(match)
                                processed.add(match['file_path'])

                        if len(group) > 1:
                            ocr_duplicates.append(group)

                    processed.add(file_info['file_path'])

                text_duplicates.extend(ocr_duplicates)

            return text_duplicates

        except Exception as e:
            self.logger.error(f"Error finding PDF duplicates: {e}")
            return []

    def _find_binary_duplicates(self, files: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """Find duplicate binary files using hash comparison."""
        try:
            # Group files by hash
            hash_groups = defaultdict(list)

            for file_info in files:
                try:
                    with open(file_info['file_path'], 'rb') as f:
                        content = f.read()
                        content_hash = hashlib.md5(content).hexdigest()
                        hash_groups[content_hash].append(file_info)
                except Exception as e:
                    self.logger.warning(
                        f"Error reading file {file_info['file_path']}: {e}")
                    continue

            # Convert groups to list and filter single files
            return [group for group in hash_groups.values() if len(group) > 1]

        except Exception as e:
            self.logger.error(f"Error finding binary duplicates: {e}")
            return []

    def _group_by_size(self, files: List[Dict[str, Any]]) -> Dict[int, List[Dict[str, Any]]]:
        """Group files by size."""
        size_groups = defaultdict(list)
        for file_info in files:
            try:
                size = os.path.getsize(file_info['file_path'])
                if size >= self.settings['min_file_size']:
                    size_groups[size].append(file_info)
            except Exception as e:
                self.logger.warning(
                    f"Error getting size for {file_info['file_path']}: {e}")
                continue
        return size_groups

    def _group_by_type(self, files: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group files by MIME type."""
        type_groups = defaultdict(list)
        for file_info in files:
            try:
                # Simple mock implementation using file extension
                file_path = file_info['file_path']
                extension = os.path.splitext(file_path)[1].lower()
                
                # Map common extensions to mime types
                mime_mapping = {
                    '.jpg': 'image/jpeg',
                    '.jpeg': 'image/jpeg',
                    '.png': 'image/png',
                    '.gif': 'image/gif',
                    '.bmp': 'image/bmp',
                    '.txt': 'text/plain',
                    '.html': 'text/html',
                    '.htm': 'text/html',
                    '.pdf': 'application/pdf',
                    '.doc': 'application/msword',
                    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                    '.xls': 'application/vnd.ms-excel',
                    '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    '.csv': 'text/csv',
                    '.json': 'application/json',
                    '.xml': 'application/xml',
                    '.mp3': 'audio/mpeg',
                    '.mp4': 'video/mp4',
                    '.avi': 'video/x-msvideo',
                    '.py': 'application/x-python'
                }
                
                mime = mime_mapping.get(extension, 'application/octet-stream')
                type_groups[mime].append(file_info)
            except Exception as e:
                self.logger.warning(
                    f"Error getting type for {file_info['file_path']}: {e}")
                continue
        return type_groups

    def _is_image_type(self, mime_type: str) -> bool:
        """Check if MIME type is an image type."""
        return mime_type.startswith('image/')

    def _is_text_type(self, mime_type: str) -> bool:
        """Check if MIME type is a text type."""
        return mime_type.startswith('text/') or mime_type in [
            'application/json',
            'application/xml',
            'application/javascript',
            'application/x-python',
            'application/x-yaml'
        ]

    def clear_cache(self) -> bool:
        """Clear duplicate detection cache."""
        try:
            if self.settings['cache_enabled']:
                import shutil
                shutil.rmtree(self.settings['cache_dir'])
                os.makedirs(self.settings['cache_dir'])
            return True
        except Exception as e:
            self.logger.error(f"Error clearing cache: {e}")
            return False
