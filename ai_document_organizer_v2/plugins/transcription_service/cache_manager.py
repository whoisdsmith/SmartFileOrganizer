"""
Cache Manager for TranscriptionServicePlugin.

Provides caching functionality to store and retrieve transcription results,
reducing redundant processing and improving performance.
"""

import os
import json
import hashlib
import logging
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger("AIDocumentOrganizerV2.TranscriptionService.Cache")

class TranscriptionCache:
    """
    Manages caching of transcription results to avoid redundant processing.
    """
    
    def __init__(self, cache_dir: Optional[str] = None):
        """
        Initialize the transcription cache.
        
        Args:
            cache_dir: Directory to store cache files (default: ~/.ai_doc_organizer/cache/transcription)
        """
        if cache_dir is None:
            # Default cache directory in user's home folder
            home_dir = os.path.expanduser("~")
            self.cache_dir = os.path.join(home_dir, ".ai_doc_organizer", "cache", "transcription")
        else:
            self.cache_dir = cache_dir
            
        # Create cache directory if it doesn't exist
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Keep track of cache statistics
        self.hits = 0
        self.misses = 0
        
        logger.info(f"Transcription cache initialized at: {self.cache_dir}")
    
    def _get_file_hash(self, file_path: str) -> str:
        """
        Generate a unique hash for a file based on its path, size, and modification time.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Hash string that uniquely identifies the file and its state
        """
        if not os.path.exists(file_path):
            return ""
        
        # Get file stats
        file_stat = os.stat(file_path)
        file_size = file_stat.st_size
        mtime = file_stat.st_mtime
        
        # Create a unique string based on path, size and mtime
        unique_str = f"{file_path}:{file_size}:{mtime}"
        
        # Generate hash
        hash_obj = hashlib.md5(unique_str.encode())
        return hash_obj.hexdigest()
    
    def _get_cache_path(self, file_hash: str) -> str:
        """
        Get the cache file path for a given file hash.
        
        Args:
            file_hash: Hash string for the file
            
        Returns:
            Path to the cache file
        """
        return os.path.join(self.cache_dir, f"{file_hash}.json")
    
    def get(self, file_path: str, provider: str = None, language: str = None) -> Optional[Dict[str, Any]]:
        """
        Get cached transcription results for a file.
        
        Args:
            file_path: Path to the audio file
            provider: Optional transcription provider name
            language: Optional language code
            
        Returns:
            Cached transcription results or None if not found
        """
        # Generate file hash
        file_hash = self._get_file_hash(file_path)
        if not file_hash:
            self.misses += 1
            return None
        
        # Add provider and language to hash if specified
        if provider:
            file_hash = f"{file_hash}_{provider}"
        if language:
            file_hash = f"{file_hash}_{language}"
        
        # Check if cache file exists
        cache_path = self._get_cache_path(file_hash)
        if not os.path.exists(cache_path):
            self.misses += 1
            return None
        
        try:
            # Load cached results
            with open(cache_path, 'r') as f:
                cached_data = json.load(f)
            
            # Check if cache is expired
            cache_time = cached_data.get('cache_time', 0)
            current_time = datetime.now().timestamp()
            
            # Cache expiration logic can be added here if needed
            # if current_time - cache_time > cache_expiration:
            #     self.misses += 1
            #     return None
            
            logger.info(f"Cache hit for: {file_path}")
            self.hits += 1
            return cached_data.get('transcription_results')
            
        except Exception as e:
            logger.warning(f"Error reading cache for {file_path}: {e}")
            self.misses += 1
            return None
    
    def put(self, file_path: str, transcription_results: Dict[str, Any], 
            provider: str = None, language: str = None) -> bool:
        """
        Store transcription results in cache.
        
        Args:
            file_path: Path to the audio file
            transcription_results: Transcription results to cache
            provider: Optional transcription provider name
            language: Optional language code
            
        Returns:
            True if successful, False otherwise
        """
        # Generate file hash
        file_hash = self._get_file_hash(file_path)
        if not file_hash:
            return False
        
        # Add provider and language to hash if specified
        if provider:
            file_hash = f"{file_hash}_{provider}"
        if language:
            file_hash = f"{file_hash}_{language}"
        
        # Create cache entry
        cache_entry = {
            'file_path': file_path,
            'file_hash': file_hash,
            'provider': provider,
            'language': language,
            'cache_time': datetime.now().timestamp(),
            'transcription_results': transcription_results
        }
        
        try:
            # Save to cache file
            cache_path = self._get_cache_path(file_hash)
            with open(cache_path, 'w') as f:
                json.dump(cache_entry, f, indent=2)
                
            logger.info(f"Cached transcription results for: {file_path}")
            return True
            
        except Exception as e:
            logger.warning(f"Error caching results for {file_path}: {e}")
            return False
    
    def invalidate(self, file_path: str, provider: str = None, language: str = None) -> bool:
        """
        Invalidate cache entry for a file.
        
        Args:
            file_path: Path to the audio file
            provider: Optional transcription provider name
            language: Optional language code
            
        Returns:
            True if successful, False otherwise
        """
        # Generate file hash
        file_hash = self._get_file_hash(file_path)
        if not file_hash:
            return False
        
        # Add provider and language to hash if specified
        if provider:
            file_hash = f"{file_hash}_{provider}"
        if language:
            file_hash = f"{file_hash}_{language}"
        
        # Check if cache file exists
        cache_path = self._get_cache_path(file_hash)
        if not os.path.exists(cache_path):
            return False
        
        try:
            # Delete cache file
            os.remove(cache_path)
            logger.info(f"Invalidated cache for: {file_path}")
            return True
            
        except Exception as e:
            logger.warning(f"Error invalidating cache for {file_path}: {e}")
            return False
    
    def clear(self) -> bool:
        """
        Clear all cache entries.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Delete all cache files
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.json'):
                    os.remove(os.path.join(self.cache_dir, filename))
                    
            # Reset statistics
            self.hits = 0
            self.misses = 0
            
            logger.info("Cleared transcription cache")
            return True
            
        except Exception as e:
            logger.warning(f"Error clearing cache: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests) * 100 if total_requests > 0 else 0
        
        try:
            # Count cache files
            cache_files = [f for f in os.listdir(self.cache_dir) if f.endswith('.json')]
            cache_size = sum(os.path.getsize(os.path.join(self.cache_dir, f)) for f in cache_files)
            
            return {
                'hits': self.hits,
                'misses': self.misses,
                'total_requests': total_requests,
                'hit_rate': hit_rate,
                'cache_entries': len(cache_files),
                'cache_size_bytes': cache_size
            }
            
        except Exception as e:
            logger.warning(f"Error getting cache stats: {e}")
            return {
                'hits': self.hits,
                'misses': self.misses,
                'total_requests': total_requests,
                'hit_rate': hit_rate,
                'error': str(e)
            }