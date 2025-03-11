"""
Vector Search Module for Smart File Organizer.
Provides semantic search capabilities using sentence transformers and FAISS.
(MOCK IMPLEMENTATION FOR TESTING)
"""

import os
import logging
import json
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import time
import random


class VectorSearch:
    """Handles vector-based semantic search operations."""

    def __init__(self, config: Optional[Dict] = None):
        """Initialize vector search with configuration."""
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        self.logger.warning("Using mock VectorSearch implementation for testing")

        # Mock embedding dimensions
        self.model_name = self.config.get('model_name', 'mock-model')
        self.embedding_dim = 384  # Standard dimension for mock purposes
        
        # Document storage for mock implementation
        self.document_lookup = {}  # Maps document paths to their info
        
        # Cache settings
        self.cache_dir = os.path.join('src', 'cache', 'embeddings')
        os.makedirs(self.cache_dir, exist_ok=True)

    def index_documents(self, documents: List[Dict[str, Any]], batch_size: int = 32) -> bool:
        """
        Index a list of documents for semantic search.
        Mock implementation using simple dictionary storage.

        Args:
            documents: List of document dictionaries with 'content' and metadata
            batch_size: Number of documents to process in each batch

        Returns:
            True if indexing was successful
        """
        try:
            # Reset document lookup for mock implementation
            self.document_lookup = {}
            
            # Store documents directly with mock "embedding" info
            for i, doc in enumerate(documents):
                # Extract document text for keyword-based search
                text_parts = []
                
                # Add main content
                if 'content' in doc:
                    text_parts.append(doc['content'])
                
                # Add OCR text if available
                if 'ocr_data' in doc and doc['ocr_data'].get('success'):
                    if doc['ocr_data']['type'] == 'pdf':
                        for page in doc['ocr_data']['page_results']:
                            text_parts.append(page['text'])
                    else:
                        text_parts.append(doc['ocr_data']['text'])
                
                # Add transcription if available
                if 'transcription' in doc and 'text' in doc['transcription']:
                    text_parts.append(doc['transcription']['text'])
                
                # Add AI analysis if available
                if 'ai_analysis' in doc:
                    if 'summary' in doc['ai_analysis']:
                        text_parts.append(doc['ai_analysis']['summary'])
                    if 'keywords' in doc['ai_analysis']:
                        text_parts.append(' '.join(doc['ai_analysis']['keywords']))
                
                # Combine all text parts
                combined_text = ' '.join(text_parts)
                
                # Store document with keywords for simple text matching
                keywords = set()
                if combined_text:
                    words = combined_text.lower().split()
                    # Take up to 20 keywords for each document
                    keywords = set(words[:20])
                
                self.document_lookup[i] = {
                    'file_path': doc.get('file_path'),
                    'file_name': doc.get('file_name'),
                    'file_type': doc.get('file_type'),
                    'metadata': doc.get('metadata', {}),
                    'keywords': keywords,
                    'text': combined_text[:500]  # Store truncated text for matching
                }
            
            # Save lookup to cache file
            self._save_index()
            
            self.logger.info(f"Successfully indexed {len(documents)} documents using mock implementation")
            return True
            
        except Exception as e:
            self.logger.error(f"Error indexing documents: {e}")
            return False

    def search(self, query: str, top_k: int = 10, threshold: float = 0.7) -> List[Dict[str, Any]]:
        """
        Perform semantic search for documents similar to the query.
        Mock implementation using simple keyword matching.

        Args:
            query: Search query text
            top_k: Number of results to return
            threshold: Similarity threshold (0-1)

        Returns:
            List of dictionaries with search results and scores
        """
        try:
            if not self.document_lookup:
                if not self._load_index():
                    self.logger.warning("No document index available for search")
                    return []
            
            # Prepare query terms
            query_terms = set(query.lower().split())
            if not query_terms:
                return []
            
            # Calculate simple similarity scores based on term overlap
            scored_docs = []
            for idx, doc_info in self.document_lookup.items():
                # Skip documents without keywords
                if not doc_info.get('keywords'):
                    continue
                
                # Calculate overlap between query terms and document keywords
                overlap = len(query_terms.intersection(doc_info['keywords']))
                
                # If no direct keyword match, try partial matching in text
                if overlap == 0 and 'text' in doc_info:
                    # Check if any query term is contained in the document text
                    for term in query_terms:
                        if term in doc_info['text'].lower():
                            overlap += 0.5
                
                # Calculate mock similarity score
                if overlap > 0:
                    # Simple formula to generate a score between 0 and 1
                    similarity = min(0.5 + (overlap / len(query_terms)) * 0.5, 1.0)
                    
                    # Apply threshold
                    if similarity >= threshold:
                        scored_docs.append((idx, similarity))
            
            # Sort by similarity score (descending)
            scored_docs.sort(key=lambda x: x[1], reverse=True)
            
            # Take top-k results
            results = []
            for i, (idx, similarity) in enumerate(scored_docs[:top_k]):
                doc_info = self.document_lookup[idx]
                results.append({
                    'file_path': doc_info['file_path'],
                    'file_name': doc_info['file_name'],
                    'file_type': doc_info['file_type'],
                    'metadata': doc_info['metadata'],
                    'similarity': similarity,
                    'rank': i + 1
                })
            
            return results

        except Exception as e:
            self.logger.error(f"Error performing search: {e}")
            return []

    def find_similar_documents(self, doc_path: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Find documents similar to a given document.
        Mock implementation using simple keyword comparison.

        Args:
            doc_path: Path to the document to compare against
            top_k: Number of similar documents to return

        Returns:
            List of dictionaries with similar documents and scores
        """
        try:
            if not self.document_lookup:
                if not self._load_index():
                    self.logger.warning("No document index available for search")
                    return []

            # Find target document in lookup
            target_doc = None
            target_idx = None
            
            for idx, info in self.document_lookup.items():
                if info.get('file_path') == doc_path:
                    target_doc = info
                    target_idx = idx
                    break
            
            if target_doc is None:
                self.logger.warning(f"Document not found in index: {doc_path}")
                return []
            
            # Calculate similarity with other documents based on keyword overlap
            scored_docs = []
            
            # Get target document keywords
            target_keywords = target_doc.get('keywords', set())
            target_text = target_doc.get('text', '').lower()
            
            if not target_keywords and not target_text:
                return []
            
            # Compare with other documents
            for idx, doc_info in self.document_lookup.items():
                # Skip self
                if idx == target_idx:
                    continue
                
                # Skip documents without keywords
                if not doc_info.get('keywords') and not doc_info.get('text'):
                    continue
                
                similarity = 0.0
                
                # Calculate keyword overlap
                if target_keywords and doc_info.get('keywords'):
                    overlap = len(target_keywords.intersection(doc_info['keywords']))
                    if overlap > 0:
                        # Base similarity on keyword overlap
                        similarity = 0.5 + (overlap / len(target_keywords)) * 0.5
                
                # If no keyword similarity, try text comparison
                if similarity == 0 and target_text and doc_info.get('text'):
                    # Simple text similarity using random scoring for demo
                    # In a real implementation, this would use text similarity algorithms
                    doc_text = doc_info['text'].lower()
                    
                    # Check if they share any words of 5+ characters (to avoid common words)
                    important_words = [w for w in target_text.split() if len(w) >= 5]
                    for word in important_words:
                        if word in doc_text:
                            similarity = max(similarity, 0.5 + (random.random() * 0.3))
                            break
                
                # Add document if it has some similarity
                if similarity > 0:
                    scored_docs.append((idx, similarity))
            
            # Sort by similarity score (descending)
            scored_docs.sort(key=lambda x: x[1], reverse=True)
            
            # Take top-k results
            results = []
            for i, (idx, similarity) in enumerate(scored_docs[:top_k]):
                doc_info = self.document_lookup[idx]
                results.append({
                    'file_path': doc_info['file_path'],
                    'file_name': doc_info['file_name'],
                    'file_type': doc_info['file_type'],
                    'metadata': doc_info['metadata'],
                    'similarity': similarity,
                    'rank': i + 1
                })
            
            return results

        except Exception as e:
            self.logger.error(f"Error finding similar documents: {e}")
            return []

    def _save_index(self) -> bool:
        """
        Save the document lookup to cache.
        Mock implementation using JSON for simplicity.
        """
        try:
            if not self.document_lookup:
                return False
            
            # Create cache directory if it doesn't exist
            os.makedirs(self.cache_dir, exist_ok=True)
            
            # Save document lookup directly as a JSON file for mock implementation
            # Convert set objects to lists for JSON serialization
            serializable_lookup = {}
            for idx, doc_info in self.document_lookup.items():
                doc_copy = doc_info.copy()
                if 'keywords' in doc_copy and isinstance(doc_copy['keywords'], set):
                    doc_copy['keywords'] = list(doc_copy['keywords'])
                serializable_lookup[str(idx)] = doc_copy
            
            # Save document lookup
            lookup_path = os.path.join(self.cache_dir, 'document_lookup.json')
            with open(lookup_path, 'w') as f:
                json.dump(serializable_lookup, f)
            
            # Save metadata
            metadata_path = os.path.join(self.cache_dir, 'index_metadata.json')
            metadata = {
                'model_name': self.model_name,
                'num_documents': len(self.document_lookup),
                'last_updated': time.time()
            }
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f)
            
            self.logger.info(f"Saved {len(self.document_lookup)} documents to cache")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving index: {e}")
            return False
    
    def _load_index(self) -> bool:
        """
        Load the document lookup from cache.
        Mock implementation using JSON for simplicity.
        """
        try:
            lookup_path = os.path.join(self.cache_dir, 'document_lookup.json')
            metadata_path = os.path.join(self.cache_dir, 'index_metadata.json')
            
            if not all(os.path.exists(p) for p in [lookup_path, metadata_path]):
                self.logger.warning("Cache files not found")
                return False
            
            # Load metadata and verify compatibility
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            if metadata['model_name'] != self.model_name:
                self.logger.warning("Model mismatch in cached index")
                return False
            
            # Load document lookup from JSON
            with open(lookup_path, 'r') as f:
                lookup_data = json.load(f)
            
            # Convert string keys back to integers and list keywords back to sets
            self.document_lookup = {}
            for idx_str, doc_info in lookup_data.items():
                idx = int(idx_str)
                if 'keywords' in doc_info and isinstance(doc_info['keywords'], list):
                    doc_info['keywords'] = set(doc_info['keywords'])
                self.document_lookup[idx] = doc_info
            
            self.logger.info(f"Loaded {len(self.document_lookup)} documents from cache")
            return True
            
        except Exception as e:
            self.logger.error(f"Error loading index: {e}")
            return False

    def clear_cache(self) -> bool:
        """Clear the vector search cache."""
        try:
            for file in os.listdir(self.cache_dir):
                file_path = os.path.join(self.cache_dir, file)
                if os.path.isfile(file_path):
                    os.remove(file_path)
            return True
        except Exception as e:
            self.logger.error(f"Error clearing cache: {e}")
            return False
