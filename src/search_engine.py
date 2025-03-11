import os
import re
import sqlite3
import time
from datetime import datetime
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
import json

from .vector_search import VectorSearch

logger = logging.getLogger("AIDocumentOrganizer")


class SearchEngine:
    """
    Class for indexing and searching files
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize the search engine

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.logger = logging.getLogger(__name__)

        # Initialize vector search
        self.vector_search = VectorSearch(self.config.get('vector_search', {}))

        # Search settings
        self.default_settings = {
            'use_semantic_search': True,
            'semantic_weight': 0.6,  # Weight for semantic search vs keyword search
            'min_similarity': 0.3,   # Minimum similarity score for semantic results
            'max_results': 100,      # Maximum number of results to return
            # How to combine semantic and keyword scores
            'combine_method': 'weighted_average'
        }
        self.settings = {**self.default_settings,
                         **self.config.get('search', {})}

        # Database settings
        # Determine database path based on platform
        if os.name == 'nt':  # Windows
            db_dir = os.path.join(os.path.expanduser("~"), "AppData", "Local", "AIDocumentOrganizer")
        else:  # macOS/Linux
            db_dir = os.path.join(os.path.expanduser("~"), ".config", "AIDocumentOrganizer")
            
        # Create database directory if it doesn't exist
        os.makedirs(db_dir, exist_ok=True)
        
        # Set database path
        self.db_path = os.path.join(db_dir, "document_index.db")
        
        self.progress_callback = None
        self._initialize_database()

    def _initialize_database(self):
        """
        Initialize the SQLite database schema
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Create files table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS files (
                    id INTEGER PRIMARY KEY,
                    path TEXT UNIQUE,
                    filename TEXT,
                    extension TEXT,
                    size INTEGER,
                    created_time REAL,
                    modified_time REAL,
                    indexed_time REAL,
                    category TEXT,
                    content_hash TEXT
                )
            ''')

            # Create content table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS content (
                    file_id INTEGER,
                    content TEXT,
                    FOREIGN KEY (file_id) REFERENCES files (id) ON DELETE CASCADE
                )
            ''')

            # Create metadata table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS metadata (
                    file_id INTEGER,
                    key TEXT,
                    value TEXT,
                    FOREIGN KEY (file_id) REFERENCES files (id) ON DELETE CASCADE
                )
            ''')

            # Create tags table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tags (
                    file_id INTEGER,
                    tag TEXT,
                    FOREIGN KEY (file_id) REFERENCES files (id) ON DELETE CASCADE
                )
            ''')

            # Create indexes for faster searching
            cursor.execute(
                'CREATE INDEX IF NOT EXISTS idx_files_path ON files (path)')
            cursor.execute(
                'CREATE INDEX IF NOT EXISTS idx_files_filename ON files (filename)')
            cursor.execute(
                'CREATE INDEX IF NOT EXISTS idx_files_extension ON files (extension)')
            cursor.execute(
                'CREATE INDEX IF NOT EXISTS idx_files_category ON files (category)')
            cursor.execute(
                'CREATE INDEX IF NOT EXISTS idx_metadata_key ON metadata (key)')
            cursor.execute(
                'CREATE INDEX IF NOT EXISTS idx_metadata_value ON metadata (value)')
            cursor.execute(
                'CREATE INDEX IF NOT EXISTS idx_tags_tag ON tags (tag)')

            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error initializing database: {str(e)}")
            raise

    def index_files(self, files: List[Dict[str, Any]], callback=None) -> Dict[str, Any]:
        """
        Index files for both keyword and semantic search.

        Args:
            files: List of file dictionaries with content and metadata
            callback: Optional progress callback function

        Returns:
            Dictionary with indexing results
        """
        try:
            total_files = len(files)
            if callback:
                callback(0, total_files, "Starting indexing...")

            # Index for semantic search
            if self.settings['use_semantic_search']:
                if callback:
                    callback(0, total_files, "Building semantic index...")
                success = self.vector_search.index_documents(files)
                if not success:
                    raise Exception("Failed to build semantic index")

            # Build keyword index
            if callback:
                callback(total_files // 2, total_files,
                         "Building keyword index...")

            self._build_keyword_index(files)

            if callback:
                callback(total_files, total_files, "Indexing complete")

            return {
                'success': True,
                'indexed_files': total_files,
                'semantic_index': self.settings['use_semantic_search']
            }

        except Exception as e:
            self.logger.error(f"Error indexing files: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def search(self, query: str, filters: Optional[Dict] = None, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Perform hybrid search combining keyword and semantic search.

        Args:
            query: Search query text
            filters: Optional filters for results
            top_k: Maximum number of results to return

        Returns:
            List of search results with scores
        """
        try:
            results = []

            # Perform semantic search if enabled
            if self.settings['use_semantic_search']:
                semantic_results = self.vector_search.search(
                    query,
                    top_k=top_k * 2,  # Get more results for combining
                    threshold=self.settings['min_similarity']
                )

                # Convert semantic results to common format
                for result in semantic_results:
                    results.append({
                        'file_path': result['file_path'],
                        'file_name': result['file_name'],
                        'file_type': result['file_type'],
                        'metadata': result['metadata'],
                        'semantic_score': result['similarity'],
                        'keyword_score': 0.0,
                        'rank': result['rank']
                    })

            # Perform keyword search
            keyword_results = self._keyword_search(query, top_k * 2)

            # Add keyword results or update scores for existing results
            for kr in keyword_results:
                existing = next(
                    (r for r in results if r['file_path'] == kr['file_path']), None)
                if existing:
                    existing['keyword_score'] = kr['score']
                else:
                    results.append({
                        'file_path': kr['file_path'],
                        'file_name': kr['file_name'],
                        'file_type': kr['file_type'],
                        'metadata': kr['metadata'],
                        'semantic_score': 0.0,
                        'keyword_score': kr['score'],
                        'rank': len(results) + 1
                    })

            # Combine scores
            for result in results:
                if self.settings['combine_method'] == 'weighted_average':
                    semantic_weight = self.settings['semantic_weight']
                    keyword_weight = 1 - semantic_weight
                    result['score'] = (
                        result['semantic_score'] * semantic_weight +
                        result['keyword_score'] * keyword_weight
                    )
                elif self.settings['combine_method'] == 'max':
                    result['score'] = max(
                        result['semantic_score'],
                        result['keyword_score']
                    )
                else:  # Default to average
                    result['score'] = (
                        result['semantic_score'] +
                        result['keyword_score']
                    ) / 2

            # Sort by combined score
            results.sort(key=lambda x: x['score'], reverse=True)

            # Apply filters
            if filters:
                results = self._apply_filters(results, filters)

            # Limit results
            results = results[:top_k]

            # Update ranks
            for i, result in enumerate(results):
                result['rank'] = i + 1

            return results

        except Exception as e:
            self.logger.error(f"Error performing search: {e}")
            return []

    def find_similar(self, file_path: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Find documents similar to a given document.

        Args:
            file_path: Path to the document to compare against
            top_k: Number of similar documents to return

        Returns:
            List of similar documents with scores
        """
        try:
            if not self.settings['use_semantic_search']:
                raise ValueError("Semantic search is disabled")

            return self.vector_search.find_similar_documents(file_path, top_k)

        except Exception as e:
            self.logger.error(f"Error finding similar documents: {e}")
            return []

    def _build_keyword_index(self, files: List[Dict[str, Any]]) -> None:
        """Build keyword search index."""
        self.keyword_index = {}

        for file_info in files:
            terms = self._extract_search_terms(file_info)

            for term in terms:
                if term not in self.keyword_index:
                    self.keyword_index[term] = []
                self.keyword_index[term].append(file_info)

    def _keyword_search(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """Perform keyword-based search."""
        if not hasattr(self, 'keyword_index'):
            return []

        # Extract search terms from query
        query_terms = self._extract_search_terms({'content': query})

        # Find matching documents
        matches = {}
        for term in query_terms:
            if term in self.keyword_index:
                for doc in self.keyword_index[term]:
                    if doc['file_path'] not in matches:
                        matches[doc['file_path']] = {
                            'doc': doc,
                            'matches': 0
                        }
                    matches[doc['file_path']]['matches'] += 1

        # Calculate scores
        results = []
        for file_path, match_info in matches.items():
            score = match_info['matches'] / len(query_terms)
            results.append({
                'file_path': file_path,
                'file_name': match_info['doc']['file_name'],
                'file_type': match_info['doc']['file_type'],
                'metadata': match_info['doc'].get('metadata', {}),
                'score': score
            })

        # Sort by score
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:top_k]

    def _extract_search_terms(self, doc: Dict[str, Any]) -> List[str]:
        """Extract search terms from document."""
        terms = set()

        # Extract from content
        if 'content' in doc:
            words = re.findall(r'\w+', doc['content'].lower())
            terms.update(words)

        # Extract from metadata
        if 'metadata' in doc:
            for key, value in doc['metadata'].items():
                if isinstance(value, str):
                    words = re.findall(r'\w+', value.lower())
                    terms.update(words)

        # Extract from OCR text
        if 'ocr_data' in doc and doc['ocr_data'].get('success'):
            if doc['ocr_data']['type'] == 'pdf':
                for page in doc['ocr_data']['page_results']:
                    words = re.findall(r'\w+', page['text'].lower())
                    terms.update(words)
            else:
                words = re.findall(r'\w+', doc['ocr_data']['text'].lower())
                terms.update(words)

        return list(terms)

    def _apply_filters(self, results: List[Dict[str, Any]], filters: Dict) -> List[Dict[str, Any]]:
        """Apply filters to search results."""
        filtered = results.copy()

        # File type filter
        if 'file_type' in filters:
            filtered = [r for r in filtered if r['file_type']
                        == filters['file_type']]

        # Category filter
        if 'category' in filters:
            filtered = [r for r in filtered if r['metadata'].get(
                'category') == filters['category']]

        # Date range filter
        if 'date_range' in filters:
            date_range = filters['date_range']

            if 'start' in date_range:
                start_date = datetime.strptime(date_range['start'], '%Y-%m-%d')
                filtered = [r for r in filtered if datetime.fromtimestamp(
                    r['metadata'].get('modified_time', 0)) >= start_date]

            if 'end' in date_range:
                end_date = datetime.strptime(date_range['end'], '%Y-%m-%d')
                filtered = [r for r in filtered if datetime.fromtimestamp(
                    r['metadata'].get('modified_time', 0)) <= end_date]

        return filtered

    def clear_cache(self) -> bool:
        """Clear search cache."""
        try:
            success = self.vector_search.clear_cache()
            if hasattr(self, 'keyword_index'):
                delattr(self, 'keyword_index')
            return success
        except Exception as e:
            self.logger.error(f"Error clearing cache: {e}")
            return False

    def remove_missing_files(self, existing_paths):
        """
        Remove files from the index that no longer exist

        Args:
            existing_paths: List of existing file paths

        Returns:
            Number of files removed from the index
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get all indexed file paths
        cursor.execute('SELECT id, path FROM files')
        indexed_files = cursor.fetchall()

        # Convert existing_paths to a set for faster lookups
        existing_paths_set = set(existing_paths)

        removed_count = 0

        for file_id, file_path in indexed_files:
            if file_path not in existing_paths_set:
                # File no longer exists, remove from index
                cursor.execute('DELETE FROM files WHERE id = ?', (file_id,))
                removed_count += 1

        conn.commit()
        conn.close()

        return removed_count

    def _parse_query(self, query):
        """
        Parse search query string into components

        Args:
            query: Search query string

        Returns:
            Dictionary with parsed query components
        """
        result = {
            'terms': [],
            'exact_phrases': [],
            'file_types': [],
            'date_range': None,
            'size_range': None,
            'tags': [],
            'exclude_tags': []
        }

        if not query or not query.strip():
            return result

        # Extract exact phrases (quoted text)
        exact_phrases = re.findall(r'"([^"]+)"', query)
        for phrase in exact_phrases:
            result['exact_phrases'].append(phrase)
            # Remove the phrase from the query
            query = query.replace(f'"{phrase}"', '', 1)

        # Extract file type filters
        file_type_matches = re.findall(r'type:(\w+)', query)
        for file_type in file_type_matches:
            result['file_types'].append(file_type.lower())
            # Remove the file type filter from the query
            query = query.replace(f'type:{file_type}', '', 1)

        # Extract date range filters
        date_range_match = re.search(
            r'date:(\d{4}-\d{2}-\d{2})\.\.(\d{4}-\d{2}-\d{2})', query)
        if date_range_match:
            start_date = date_range_match.group(1)
            end_date = date_range_match.group(2)
            result['date_range'] = (start_date, end_date)
            # Remove the date range filter from the query
            query = query.replace(f'date:{start_date}..{end_date}', '', 1)
        else:
            # Check for single date filter
            date_match = re.search(r'date:(\d{4}-\d{2}-\d{2})', query)
            if date_match:
                date = date_match.group(1)
                result['date_range'] = (date, date)
                # Remove the date filter from the query
                query = query.replace(f'date:{date}', '', 1)

        # Extract size range filters (in KB, MB, or GB)
        size_pattern = r'size:(\d+(?:\.\d+)?(?:kb|mb|gb)?)\.\.(\d+(?:\.\d+)?(?:kb|mb|gb)?)'
        size_range_match = re.search(size_pattern, query, re.IGNORECASE)
        if size_range_match:
            min_size = self._parse_size(size_range_match.group(1))
            max_size = self._parse_size(size_range_match.group(2))
            result['size_range'] = (min_size, max_size)
            # Remove the size range filter from the query
            query = query.replace(size_range_match.group(0), '', 1)
        else:
            # Check for single size filter
            size_match = re.search(
                r'size:([><]?)(\d+(?:\.\d+)?(?:kb|mb|gb)?)', query, re.IGNORECASE)
            if size_match:
                operator = size_match.group(1)
                size = self._parse_size(size_match.group(2))

                if operator == '>':
                    result['size_range'] = (size, None)
                elif operator == '<':
                    result['size_range'] = (None, size)
                else:
                    # Exact size match with a small range
                    result['size_range'] = (size * 0.95, size * 1.05)

                # Remove the size filter from the query
                query = query.replace(size_match.group(0), '', 1)

        # Extract tag filters
        tag_matches = re.findall(r'tag:([^\s]+)', query)
        for tag in tag_matches:
            if tag.startswith('-'):
                result['exclude_tags'].append(tag[1:])
            else:
                result['tags'].append(tag)
            # Remove the tag filter from the query
            query = query.replace(f'tag:{tag}', '', 1)

        # Process remaining terms
        terms = query.split()
        for term in terms:
            if term.strip():
                result['terms'].append(term.strip())

        return result

    def _parse_size(self, size_str):
        """
        Parse size string to bytes

        Args:
            size_str: Size string (e.g., "10kb", "5.2mb", "1gb")

        Returns:
            Size in bytes
        """
        size_str = size_str.lower()

        # Extract numeric value and unit
        match = re.match(r'(\d+(?:\.\d+)?)([kmg]?b)?', size_str)
        if not match:
            return 0

        value = float(match.group(1))
        unit = match.group(2) or 'b'

        # Convert to bytes
        if unit == 'kb':
            return value * 1024
        elif unit == 'mb':
            return value * 1024 * 1024
        elif unit == 'gb':
            return value * 1024 * 1024 * 1024
        else:  # bytes
            return value

    def _date_to_timestamp(self, date_str):
        """
        Convert date string to timestamp

        Args:
            date_str: Date string in format YYYY-MM-DD

        Returns:
            Timestamp
        """
        try:
            dt = datetime.strptime(date_str, '%Y-%m-%d')
            return dt.timestamp()
        except:
            return 0

    def _format_file_size(self, size_bytes):
        """
        Format file size in human-readable format

        Args:
            size_bytes: File size in bytes

        Returns:
            Formatted file size string
        """
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
