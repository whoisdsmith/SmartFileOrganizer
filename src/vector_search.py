"""
Vector Search Module for Smart File Organizer.
Provides semantic search capabilities using sentence transformers and FAISS.
"""

import os
import logging
import numpy as np
import faiss
import json
from typing import Dict, List, Optional, Tuple, Any
from sentence_transformers import SentenceTransformer
from pathlib import Path
import time
import pickle


class VectorSearch:
    """Handles vector-based semantic search operations."""

    def __init__(self, config: Optional[Dict] = None):
        """Initialize vector search with configuration."""
        self.config = config or {}
        self.logger = logging.getLogger(__name__)

        # Initialize embedding model
        self.model_name = self.config.get('model_name', 'all-MiniLM-L6-v2')
        try:
            self.model = SentenceTransformer(self.model_name)
            self.embedding_dim = self.model.get_sentence_embedding_dimension()
        except Exception as e:
            self.logger.error(f"Failed to initialize embedding model: {e}")
            raise

        # Initialize FAISS index
        self.index = None
        self.document_lookup = {}  # Maps index positions to document info

        # Cache settings
        self.cache_dir = os.path.join('src', 'cache', 'embeddings')
        os.makedirs(self.cache_dir, exist_ok=True)

    def index_documents(self, documents: List[Dict[str, Any]], batch_size: int = 32) -> bool:
        """
        Index a list of documents for semantic search.

        Args:
            documents: List of document dictionaries with 'content' and metadata
            batch_size: Number of documents to process in each batch

        Returns:
            True if indexing was successful
        """
        try:
            # Initialize a new FAISS index
            self.index = faiss.IndexFlatL2(self.embedding_dim)
            self.document_lookup = {}

            total_docs = len(documents)
            embeddings = []

            # Process documents in batches
            for i in range(0, total_docs, batch_size):
                batch = documents[i:i + batch_size]

                # Extract text content for embedding
                texts = []
                for doc in batch:
                    # Combine various text fields for better semantic understanding
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
                            text_parts.append(
                                ' '.join(doc['ai_analysis']['keywords']))

                    # Combine all text parts
                    combined_text = ' '.join(text_parts)
                    texts.append(combined_text)

                # Generate embeddings for batch
                batch_embeddings = self.model.encode(
                    texts, show_progress_bar=False)
                embeddings.extend(batch_embeddings)

                # Update document lookup
                for j, doc in enumerate(batch):
                    doc_index = i + j
                    self.document_lookup[doc_index] = {
                        'file_path': doc.get('file_path'),
                        'file_name': doc.get('file_name'),
                        'file_type': doc.get('file_type'),
                        'metadata': doc.get('metadata', {})
                    }

            # Add all embeddings to index
            embeddings_array = np.array(embeddings).astype('float32')
            self.index.add(embeddings_array)

            # Save index and lookup
            self._save_index()

            self.logger.info(f"Successfully indexed {total_docs} documents")
            return True

        except Exception as e:
            self.logger.error(f"Error indexing documents: {e}")
            return False

    def search(self, query: str, top_k: int = 10, threshold: float = 0.7) -> List[Dict[str, Any]]:
        """
        Perform semantic search for documents similar to the query.

        Args:
            query: Search query text
            top_k: Number of results to return
            threshold: Similarity threshold (0-1)

        Returns:
            List of dictionaries with search results and scores
        """
        try:
            if not self.index:
                if not self._load_index():
                    raise ValueError("No search index available")

            # Generate query embedding
            query_embedding = self.model.encode(
                [query])[0].reshape(1, -1).astype('float32')

            # Search index
            distances, indices = self.index.search(query_embedding, top_k)

            # Process results
            results = []
            for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
                if idx < 0:  # Invalid index
                    continue

                # Convert distance to similarity score (0-1)
                # Normalize distance to similarity
                similarity = 1 - (distance / 2)
                if similarity < threshold:
                    continue

                # Get document info
                doc_info = self.document_lookup.get(int(idx), {})
                if doc_info:
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

        Args:
            doc_path: Path to the document to compare against
            top_k: Number of similar documents to return

        Returns:
            List of dictionaries with similar documents and scores
        """
        try:
            if not self.index:
                if not self._load_index():
                    raise ValueError("No search index available")

            # Find document in lookup
            target_idx = None
            target_embedding = None

            for idx, info in self.document_lookup.items():
                if info['file_path'] == doc_path:
                    target_idx = idx
                    # Get embedding from index
                    target_embedding = self.index.reconstruct(
                        idx).reshape(1, -1)
                    break

            if target_embedding is None:
                raise ValueError(f"Document not found in index: {doc_path}")

            # Search for similar documents
            distances, indices = self.index.search(
                target_embedding, top_k + 1)  # +1 to account for self

            # Process results
            results = []
            for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
                if idx < 0 or idx == target_idx:  # Skip invalid index and self
                    continue

                # Convert distance to similarity score (0-1)
                similarity = 1 - (distance / 2)

                # Get document info
                doc_info = self.document_lookup.get(int(idx), {})
                if doc_info:
                    results.append({
                        'file_path': doc_info['file_path'],
                        'file_name': doc_info['file_name'],
                        'file_type': doc_info['file_type'],
                        'metadata': doc_info['metadata'],
                        'similarity': similarity,
                        'rank': i
                    })

            return results

        except Exception as e:
            self.logger.error(f"Error finding similar documents: {e}")
            return []

    def _save_index(self) -> bool:
        """Save the FAISS index and document lookup to cache."""
        try:
            if not self.index:
                return False

            # Save FAISS index
            index_path = os.path.join(self.cache_dir, 'faiss_index.bin')
            faiss.write_index(self.index, index_path)

            # Save document lookup
            lookup_path = os.path.join(self.cache_dir, 'document_lookup.pkl')
            with open(lookup_path, 'wb') as f:
                pickle.dump(self.document_lookup, f)

            # Save metadata
            metadata_path = os.path.join(self.cache_dir, 'index_metadata.json')
            metadata = {
                'model_name': self.model_name,
                'embedding_dim': self.embedding_dim,
                'num_documents': len(self.document_lookup),
                'last_updated': time.time()
            }
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f)

            return True

        except Exception as e:
            self.logger.error(f"Error saving index: {e}")
            return False

    def _load_index(self) -> bool:
        """Load the FAISS index and document lookup from cache."""
        try:
            index_path = os.path.join(self.cache_dir, 'faiss_index.bin')
            lookup_path = os.path.join(self.cache_dir, 'document_lookup.pkl')
            metadata_path = os.path.join(self.cache_dir, 'index_metadata.json')

            if not all(os.path.exists(p) for p in [index_path, lookup_path, metadata_path]):
                return False

            # Load metadata and verify compatibility
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)

            if metadata['model_name'] != self.model_name:
                self.logger.warning("Model mismatch in cached index")
                return False

            # Load FAISS index
            self.index = faiss.read_index(index_path)

            # Load document lookup
            with open(lookup_path, 'rb') as f:
                self.document_lookup = pickle.load(f)

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
