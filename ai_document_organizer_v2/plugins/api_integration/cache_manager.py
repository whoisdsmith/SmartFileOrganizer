"""
Cache Manager for the API Integration Framework.

This module provides caching capabilities for API responses to improve
performance and reduce the number of external API calls.
"""

import hashlib
import json
import logging
import os
import pickle
import time
from typing import Any, Dict, List, Optional, Union, Callable
from threading import RLock
import shutil

logger = logging.getLogger(__name__)


class CacheKey:
    """
    Represents a cache key for storing and retrieving cache entries.
    
    A cache key is generated based on the API provider, operation,
    and parameters to ensure uniqueness.
    """
    
    def __init__(self, plugin_name: str, operation: str, parameters: Dict[str, Any]):
        """
        Initialize a cache key.
        
        Args:
            plugin_name: Name of the API plugin
            operation: Name of the API operation
            parameters: Parameters for the API operation
        """
        self.plugin_name = plugin_name
        self.operation = operation
        self.parameters = parameters
        
        # Generate a key string and hash
        self._key_string = self._generate_key_string()
        self._key_hash = self._generate_key_hash()
        
    def _generate_key_string(self) -> str:
        """
        Generate a string representation of the cache key.
        
        Returns:
            String representation of the cache key
        """
        # Convert parameters to a serializable format
        params_str = json.dumps(self.parameters, sort_keys=True, default=str)
        return f"{self.plugin_name}:{self.operation}:{params_str}"
        
    def _generate_key_hash(self) -> str:
        """
        Generate a hash of the key string for efficient lookup.
        
        Returns:
            Hash string for the cache key
        """
        hash_obj = hashlib.sha256(self._key_string.encode())
        return hash_obj.hexdigest()
        
    def get_hash(self) -> str:
        """
        Get the hash for this cache key.
        
        Returns:
            Hash string for the cache key
        """
        return self._key_hash
        
    def get_string(self) -> str:
        """
        Get the string representation of this cache key.
        
        Returns:
            String representation of the cache key
        """
        return self._key_string
        
    def __str__(self) -> str:
        """String representation of the cache key."""
        return self._key_string
        
    def __repr__(self) -> str:
        """Detailed representation of the cache key."""
        return f"CacheKey(plugin={self.plugin_name}, operation={self.operation}, hash={self._key_hash})"
        
    def __eq__(self, other: Any) -> bool:
        """Check if two cache keys are equal."""
        if not isinstance(other, CacheKey):
            return False
        return self._key_hash == other._key_hash
        
    def __hash__(self) -> int:
        """Get hash value for the cache key."""
        return hash(self._key_hash)


class CacheEntry:
    """
    Represents a cached API response with metadata.
    
    A cache entry contains the actual API response along with metadata
    such as creation time, expiration time, and access count.
    """
    
    def __init__(self, key: CacheKey, data: Any, ttl: Optional[int] = None):
        """
        Initialize a cache entry.
        
        Args:
            key: Cache key for this entry
            data: The data to cache
            ttl: Time-to-live in seconds (None for no expiration)
        """
        self.key = key
        self.data = data
        self.created_at = time.time()
        self.expires_at = self.created_at + ttl if ttl is not None else None
        self.last_accessed = self.created_at
        self.access_count = 0
        self.byte_size = self._calculate_size()
        
    def _calculate_size(self) -> int:
        """
        Calculate the approximate size of the cached data in bytes.
        
        Returns:
            Size in bytes
        """
        try:
            # Use pickle to get a more accurate size estimate including object overhead
            return len(pickle.dumps(self.data))
        except:
            # Fallback to string representation if pickling fails
            return len(str(self.data))
        
    def is_expired(self) -> bool:
        """
        Check if this cache entry has expired.
        
        Returns:
            True if expired, False otherwise
        """
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at
        
    def access(self) -> None:
        """
        Record an access to this cache entry.
        
        Updates the last accessed time and increments the access count.
        """
        self.last_accessed = time.time()
        self.access_count += 1
        
    def get_age(self) -> float:
        """
        Get the age of this cache entry in seconds.
        
        Returns:
            Age in seconds
        """
        return time.time() - self.created_at
        
    def get_metadata(self) -> Dict[str, Any]:
        """
        Get metadata about this cache entry.
        
        Returns:
            Dictionary with cache entry metadata
        """
        return {
            'key': self.key.get_string(),
            'key_hash': self.key.get_hash(),
            'plugin_name': self.key.plugin_name,
            'operation': self.key.operation,
            'created_at': self.created_at,
            'expires_at': self.expires_at,
            'last_accessed': self.last_accessed,
            'access_count': self.access_count,
            'byte_size': self.byte_size,
            'is_expired': self.is_expired(),
            'age': self.get_age()
        }
        
    def __str__(self) -> str:
        """String representation of the cache entry."""
        return f"CacheEntry(key={self.key.get_hash()}, expired={self.is_expired()}, accesses={self.access_count})"


class CachePolicy:
    """
    Defines caching policies for a cache manager.
    
    Cache policies determine how items are cached, when they expire,
    and how the cache is maintained.
    """
    
    # Cache eviction strategies
    EVICT_LRU = 'lru'  # Least Recently Used
    EVICT_LFU = 'lfu'  # Least Frequently Used
    EVICT_FIFO = 'fifo'  # First In First Out
    
    def __init__(self,
                max_size: Optional[int] = None,
                max_items: Optional[int] = None,
                default_ttl: Optional[int] = 3600,
                eviction_strategy: str = EVICT_LRU,
                auto_refresh_enabled: bool = False,
                refresh_threshold: float = 0.8,
                per_plugin_limits: Optional[Dict[str, int]] = None,
                per_operation_ttl: Optional[Dict[str, int]] = None):
        """
        Initialize a cache policy.
        
        Args:
            max_size: Maximum cache size in bytes (None for unlimited)
            max_items: Maximum number of items in the cache (None for unlimited)
            default_ttl: Default time-to-live in seconds (None for no expiration)
            eviction_strategy: Strategy for evicting items when cache is full
            auto_refresh_enabled: Whether to automatically refresh items
            refresh_threshold: Threshold at which to refresh items (0-1)
            per_plugin_limits: Dictionary of plugin-specific item limits
            per_operation_ttl: Dictionary of operation-specific TTLs
        """
        self.max_size = max_size
        self.max_items = max_items
        self.default_ttl = default_ttl
        self.eviction_strategy = eviction_strategy
        self.auto_refresh_enabled = auto_refresh_enabled
        self.refresh_threshold = refresh_threshold
        self.per_plugin_limits = per_plugin_limits or {}
        self.per_operation_ttl = per_operation_ttl or {}
        
    def get_ttl(self, plugin_name: str, operation: str) -> Optional[int]:
        """
        Get the TTL for a specific plugin and operation.
        
        Args:
            plugin_name: Name of the API plugin
            operation: Name of the API operation
            
        Returns:
            TTL in seconds, or None for no expiration
        """
        # Check for operation-specific TTL
        key = f"{plugin_name}:{operation}"
        if key in self.per_operation_ttl:
            return self.per_operation_ttl[key]
            
        # Check for plugin-specific TTL
        if plugin_name in self.per_operation_ttl:
            return self.per_operation_ttl[plugin_name]
            
        # Use default TTL
        return self.default_ttl
        
    def should_refresh(self, entry: CacheEntry) -> bool:
        """
        Check if a cache entry should be refreshed.
        
        Args:
            entry: Cache entry to check
            
        Returns:
            True if the entry should be refreshed, False otherwise
        """
        if not self.auto_refresh_enabled or entry.expires_at is None:
            return False
            
        # Calculate how much of the TTL has elapsed
        ttl = entry.expires_at - entry.created_at
        elapsed = time.time() - entry.created_at
        
        # If we've passed the threshold, refresh
        return elapsed / ttl > self.refresh_threshold
        
    def get_plugin_limit(self, plugin_name: str) -> Optional[int]:
        """
        Get the item limit for a specific plugin.
        
        Args:
            plugin_name: Name of the API plugin
            
        Returns:
            Item limit for the plugin, or None for no limit
        """
        return self.per_plugin_limits.get(plugin_name)


class CacheManager:
    """
    Manages caching for the API Integration Framework.
    
    The Cache Manager provides caching capabilities for API responses,
    including in-memory caching, disk persistence, and cache policies.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the Cache Manager.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        
        # Initialize cache policy
        policy_config = self.config.get('policy', {})
        self.policy = CachePolicy(
            max_size=policy_config.get('max_size'),
            max_items=policy_config.get('max_items', 10000),
            default_ttl=policy_config.get('default_ttl', 3600),
            eviction_strategy=policy_config.get('eviction_strategy', CachePolicy.EVICT_LRU),
            auto_refresh_enabled=policy_config.get('auto_refresh_enabled', False),
            refresh_threshold=policy_config.get('refresh_threshold', 0.8),
            per_plugin_limits=policy_config.get('per_plugin_limits'),
            per_operation_ttl=policy_config.get('per_operation_ttl')
        )
        
        # Cache directory for persistence
        cache_dir = self.config.get('cache_dir', os.path.join(os.path.dirname(__file__), '..', '..', 'cache', 'api_cache'))
        self.cache_dir = os.path.abspath(cache_dir)
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Cache statistics
        self.stats = {
            'hits': 0,
            'misses': 0,
            'expired_hits': 0,
            'refreshes': 0,
            'evictions': 0,
            'bytes_stored': 0
        }
        
        # In-memory cache
        self.cache = {}  # type: Dict[str, CacheEntry]
        
        # Plugins with custom caching behavior
        self.refresh_handlers = {}  # type: Dict[str, Callable]
        
        # Thread safety
        self._lock = RLock()
        
        # Load cache from disk if enabled
        if self.config.get('persist_cache', True):
            self._load_cache_from_disk()
            
        logger.info(f"Cache Manager initialized with {len(self.cache)} entries")
        
    def get(self, plugin_name: str, operation: str, parameters: Dict[str, Any],
           bypass_cache: bool = False) -> Dict[str, Any]:
        """
        Get a cached response for an API operation.
        
        Args:
            plugin_name: Name of the API plugin
            operation: Name of the API operation
            parameters: Parameters for the API operation
            bypass_cache: Whether to bypass the cache and return a miss
            
        Returns:
            Dictionary with cache information:
            {
                'cache_hit': bool,
                'cache_data': Optional[Any],  # The cached data if hit
                'metadata': Dict[str, Any],   # Cache metadata
            }
        """
        if bypass_cache:
            return {
                'cache_hit': False,
                'cache_data': None,
                'metadata': {
                    'bypass_cache': True
                }
            }
            
        key = CacheKey(plugin_name, operation, parameters)
        key_hash = key.get_hash()
        
        with self._lock:
            # Check if the key exists in the cache
            if key_hash in self.cache:
                entry = self.cache[key_hash]
                
                # Check if the entry is expired
                if entry.is_expired():
                    # Log expired hit
                    self.stats['expired_hits'] += 1
                    
                    # Check if entry should be auto-refreshed
                    if self.policy.should_refresh(entry) and self._can_refresh(entry):
                        # Return the stale entry, but mark for refresh
                        entry.access()
                        return {
                            'cache_hit': True,
                            'cache_data': entry.data,
                            'metadata': {
                                **entry.get_metadata(),
                                'is_stale': True,
                                'needs_refresh': True
                            }
                        }
                    else:
                        # Remove expired entry
                        self._remove_entry(key_hash)
                        self.stats['misses'] += 1
                        return {
                            'cache_hit': False,
                            'cache_data': None,
                            'metadata': {
                                'key_hash': key_hash,
                                'was_expired': True
                            }
                        }
                        
                # Valid cache hit
                entry.access()
                self.stats['hits'] += 1
                return {
                    'cache_hit': True,
                    'cache_data': entry.data,
                    'metadata': entry.get_metadata()
                }
                
            # Cache miss
            self.stats['misses'] += 1
            return {
                'cache_hit': False,
                'cache_data': None,
                'metadata': {
                    'key_hash': key_hash
                }
            }
            
    def put(self, plugin_name: str, operation: str, parameters: Dict[str, Any],
           data: Any, ttl: Optional[int] = None) -> Dict[str, Any]:
        """
        Put a response into the cache.
        
        Args:
            plugin_name: Name of the API plugin
            operation: Name of the API operation
            parameters: Parameters for the API operation
            data: Data to cache
            ttl: Time-to-live in seconds (None to use policy default)
            
        Returns:
            Dictionary with cache operation result:
            {
                'success': bool,
                'key_hash': str,
                'metadata': Dict[str, Any]
            }
        """
        key = CacheKey(plugin_name, operation, parameters)
        key_hash = key.get_hash()
        
        # Use policy TTL if not specified
        if ttl is None:
            ttl = self.policy.get_ttl(plugin_name, operation)
            
        with self._lock:
            # Check if we need to evict items
            self._enforce_cache_limits()
            
            # Create new cache entry
            entry = CacheEntry(key, data, ttl)
            
            # Update stats
            if key_hash in self.cache:
                old_entry = self.cache[key_hash]
                self.stats['bytes_stored'] -= old_entry.byte_size
                
            self.stats['bytes_stored'] += entry.byte_size
            
            # Add to cache
            self.cache[key_hash] = entry
            
            # Persist to disk if enabled
            if self.config.get('persist_cache', True):
                self._persist_entry(entry)
                
            return {
                'success': True,
                'key_hash': key_hash,
                'metadata': entry.get_metadata()
            }
            
    def refresh(self, plugin_name: str, operation: str, parameters: Dict[str, Any],
              force: bool = False) -> Dict[str, Any]:
        """
        Refresh a cached entry using its associated refresh handler.
        
        Args:
            plugin_name: Name of the API plugin
            operation: Name of the API operation
            parameters: Parameters for the API operation
            force: Whether to force refresh even if not expired
            
        Returns:
            Dictionary with refresh operation result
        """
        key = CacheKey(plugin_name, operation, parameters)
        key_hash = key.get_hash()
        
        with self._lock:
            if key_hash not in self.cache:
                return {
                    'success': False,
                    'error': 'Cache entry not found',
                    'key_hash': key_hash
                }
                
            entry = self.cache[key_hash]
            
            # Check if refresh is needed
            if not force and not entry.is_expired() and not self.policy.should_refresh(entry):
                return {
                    'success': False,
                    'error': 'Cache entry does not need refresh',
                    'metadata': entry.get_metadata()
                }
                
            # Check if we have a refresh handler
            if not self._can_refresh(entry):
                return {
                    'success': False,
                    'error': 'No refresh handler available',
                    'metadata': entry.get_metadata()
                }
                
            # Get refresh handler
            handler = self.refresh_handlers.get(plugin_name)
            
            try:
                # Call refresh handler
                refresh_result = handler(operation, parameters, entry.data)
                
                if not refresh_result.get('success', False):
                    return {
                        'success': False,
                        'error': refresh_result.get('error', 'Refresh handler failed'),
                        'metadata': entry.get_metadata(),
                        'handler_result': refresh_result
                    }
                    
                # Update stats
                self.stats['refreshes'] += 1
                
                # Update cache with new data
                new_data = refresh_result.get('data')
                return self.put(plugin_name, operation, parameters, new_data)
                
            except Exception as e:
                logger.error(f"Error refreshing cache entry: {e}")
                return {
                    'success': False,
                    'error': str(e),
                    'metadata': entry.get_metadata()
                }
                
    def invalidate(self, plugin_name: Optional[str] = None, operation: Optional[str] = None,
                 parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Invalidate cache entries that match the given criteria.
        
        Args:
            plugin_name: Optional plugin name filter
            operation: Optional operation name filter
            parameters: Optional parameters filter
            
        Returns:
            Dictionary with invalidation result:
            {
                'success': bool,
                'invalidated_count': int,
                'invalidated_keys': List[str]
            }
        """
        with self._lock:
            invalidated = []
            
            # If all parameters provided, create a specific key
            if plugin_name and operation and parameters:
                key = CacheKey(plugin_name, operation, parameters)
                key_hash = key.get_hash()
                
                if key_hash in self.cache:
                    self._remove_entry(key_hash)
                    invalidated.append(key_hash)
                    
                return {
                    'success': True,
                    'invalidated_count': len(invalidated),
                    'invalidated_keys': invalidated
                }
                
            # Otherwise, find matching entries
            to_remove = []
            
            for key_hash, entry in self.cache.items():
                match = True
                
                if plugin_name and entry.key.plugin_name != plugin_name:
                    match = False
                    
                if operation and entry.key.operation != operation:
                    match = False
                    
                if parameters:
                    # For parameters, we need a more complex check
                    entry_params = entry.key.parameters
                    for k, v in parameters.items():
                        if k not in entry_params or entry_params[k] != v:
                            match = False
                            break
                            
                if match:
                    to_remove.append(key_hash)
                    
            # Remove matching entries
            for key_hash in to_remove:
                self._remove_entry(key_hash)
                invalidated.append(key_hash)
                
            return {
                'success': True,
                'invalidated_count': len(invalidated),
                'invalidated_keys': invalidated
            }
            
    def register_refresh_handler(self, plugin_name: str,
                               handler: Callable[[str, Dict[str, Any], Any], Dict[str, Any]]) -> bool:
        """
        Register a refresh handler for a plugin.
        
        Args:
            plugin_name: Name of the API plugin
            handler: Function to call for refreshing cached entries
                    The function should accept (operation, parameters, old_data)
                    and return a dictionary with 'success' and 'data' keys
            
        Returns:
            True if registration was successful, False otherwise
        """
        with self._lock:
            self.refresh_handlers[plugin_name] = handler
            return True
            
    def unregister_refresh_handler(self, plugin_name: str) -> bool:
        """
        Unregister a refresh handler for a plugin.
        
        Args:
            plugin_name: Name of the API plugin
            
        Returns:
            True if unregistration was successful, False otherwise
        """
        with self._lock:
            if plugin_name in self.refresh_handlers:
                del self.refresh_handlers[plugin_name]
                return True
            return False
            
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        with self._lock:
            stats = dict(self.stats)
            
            # Add derived statistics
            total_requests = stats['hits'] + stats['misses']
            stats['hit_ratio'] = stats['hits'] / total_requests if total_requests > 0 else 0
            stats['miss_ratio'] = stats['misses'] / total_requests if total_requests > 0 else 0
            stats['entry_count'] = len(self.cache)
            
            # Add policy information
            stats['policy'] = {
                'max_size': self.policy.max_size,
                'max_items': self.policy.max_items,
                'default_ttl': self.policy.default_ttl,
                'eviction_strategy': self.policy.eviction_strategy,
                'auto_refresh_enabled': self.policy.auto_refresh_enabled
            }
            
            return stats
            
    def clear(self) -> Dict[str, Any]:
        """
        Clear all cache entries.
        
        Returns:
            Dictionary with clear operation result
        """
        with self._lock:
            entry_count = len(self.cache)
            byte_size = self.stats['bytes_stored']
            
            # Clear in-memory cache
            self.cache.clear()
            
            # Reset statistics
            self.stats['bytes_stored'] = 0
            
            # Clear disk cache if enabled
            if self.config.get('persist_cache', True):
                self._clear_disk_cache()
                
            return {
                'success': True,
                'cleared_entries': entry_count,
                'cleared_bytes': byte_size
            }
            
    def get_all_entries(self) -> List[Dict[str, Any]]:
        """
        Get metadata for all cache entries.
        
        Returns:
            List of dictionaries with cache entry metadata
        """
        with self._lock:
            return [entry.get_metadata() for entry in self.cache.values()]
            
    def _enforce_cache_limits(self) -> None:
        """
        Enforce cache limits by evicting entries if necessary.
        """
        # Check item count limit
        if self.policy.max_items is not None and len(self.cache) >= self.policy.max_items:
            self._evict_entries(1)
            
        # Check size limit
        if self.policy.max_size is not None and self.stats['bytes_stored'] >= self.policy.max_size:
            # Calculate how many bytes to free
            bytes_to_free = int(self.stats['bytes_stored'] * 0.2)  # Free 20%
            self._evict_entries_by_size(bytes_to_free)
            
    def _evict_entries(self, count: int) -> None:
        """
        Evict a number of entries based on the eviction strategy.
        
        Args:
            count: Number of entries to evict
        """
        if not self.cache:
            return
            
        entries = list(self.cache.values())
        
        # Sort entries based on eviction strategy
        if self.policy.eviction_strategy == CachePolicy.EVICT_LRU:
            # Least recently used
            entries.sort(key=lambda e: e.last_accessed)
        elif self.policy.eviction_strategy == CachePolicy.EVICT_LFU:
            # Least frequently used
            entries.sort(key=lambda e: e.access_count)
        elif self.policy.eviction_strategy == CachePolicy.EVICT_FIFO:
            # First in first out
            entries.sort(key=lambda e: e.created_at)
            
        # Evict oldest/least used entries
        for i in range(min(count, len(entries))):
            entry = entries[i]
            self._remove_entry(entry.key.get_hash())
            self.stats['evictions'] += 1
            
    def _evict_entries_by_size(self, bytes_to_free: int) -> None:
        """
        Evict entries to free up a certain number of bytes.
        
        Args:
            bytes_to_free: Number of bytes to free
        """
        if not self.cache:
            return
            
        entries = list(self.cache.values())
        
        # Sort entries based on eviction strategy
        if self.policy.eviction_strategy == CachePolicy.EVICT_LRU:
            # Least recently used
            entries.sort(key=lambda e: e.last_accessed)
        elif self.policy.eviction_strategy == CachePolicy.EVICT_LFU:
            # Least frequently used
            entries.sort(key=lambda e: e.access_count)
        elif self.policy.eviction_strategy == CachePolicy.EVICT_FIFO:
            # First in first out
            entries.sort(key=lambda e: e.created_at)
            
        # Evict entries until we've freed enough bytes
        bytes_freed = 0
        for entry in entries:
            if bytes_freed >= bytes_to_free:
                break
                
            bytes_freed += entry.byte_size
            self._remove_entry(entry.key.get_hash())
            self.stats['evictions'] += 1
            
    def _remove_entry(self, key_hash: str) -> None:
        """
        Remove an entry from the cache.
        
        Args:
            key_hash: Hash of the cache key to remove
        """
        if key_hash in self.cache:
            entry = self.cache[key_hash]
            self.stats['bytes_stored'] -= entry.byte_size
            
            del self.cache[key_hash]
            
            # Remove from disk if enabled
            if self.config.get('persist_cache', True):
                self._remove_persisted_entry(key_hash)
                
    def _can_refresh(self, entry: CacheEntry) -> bool:
        """
        Check if a cache entry can be refreshed.
        
        Args:
            entry: Cache entry to check
            
        Returns:
            True if the entry can be refreshed, False otherwise
        """
        return entry.key.plugin_name in self.refresh_handlers
        
    def _persist_entry(self, entry: CacheEntry) -> bool:
        """
        Persist a cache entry to disk.
        
        Args:
            entry: Cache entry to persist
            
        Returns:
            True if successful, False otherwise
        """
        try:
            key_hash = entry.key.get_hash()
            file_path = os.path.join(self.cache_dir, f"{key_hash}.cache")
            
            with open(file_path, 'wb') as f:
                pickle.dump(entry, f)
                
            return True
        except Exception as e:
            logger.error(f"Error persisting cache entry: {e}")
            return False
            
    def _remove_persisted_entry(self, key_hash: str) -> bool:
        """
        Remove a persisted cache entry from disk.
        
        Args:
            key_hash: Hash of the cache key to remove
            
        Returns:
            True if successful, False otherwise
        """
        try:
            file_path = os.path.join(self.cache_dir, f"{key_hash}.cache")
            
            if os.path.exists(file_path):
                os.remove(file_path)
                
            return True
        except Exception as e:
            logger.error(f"Error removing persisted cache entry: {e}")
            return False
            
    def _load_cache_from_disk(self) -> None:
        """
        Load cache entries from disk.
        """
        if not os.path.exists(self.cache_dir):
            return
            
        try:
            # Get all cache files
            cache_files = [f for f in os.listdir(self.cache_dir) if f.endswith('.cache')]
            
            loaded_count = 0
            expired_count = 0
            error_count = 0
            
            for file_name in cache_files:
                try:
                    file_path = os.path.join(self.cache_dir, file_name)
                    
                    with open(file_path, 'rb') as f:
                        entry = pickle.load(f)
                        
                    # Skip expired entries
                    if entry.is_expired():
                        os.remove(file_path)
                        expired_count += 1
                        continue
                        
                    # Add to in-memory cache
                    self.cache[entry.key.get_hash()] = entry
                    self.stats['bytes_stored'] += entry.byte_size
                    
                    loaded_count += 1
                except Exception as e:
                    logger.error(f"Error loading cache file {file_name}: {e}")
                    error_count += 1
                    
            logger.info(f"Loaded {loaded_count} cache entries from disk, {expired_count} expired, {error_count} errors")
            
        except Exception as e:
            logger.error(f"Error loading cache from disk: {e}")
            
    def _clear_disk_cache(self) -> bool:
        """
        Clear all persisted cache entries from disk.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if os.path.exists(self.cache_dir):
                for file_name in os.listdir(self.cache_dir):
                    if file_name.endswith('.cache'):
                        os.remove(os.path.join(self.cache_dir, file_name))
                        
            return True
        except Exception as e:
            logger.error(f"Error clearing disk cache: {e}")
            return False
            
    def compress_disk_cache(self) -> Dict[str, Any]:
        """
        Compress the disk cache to save space.
        
        Returns:
            Dictionary with compression result
        """
        if not self.config.get('persist_cache', True):
            return {
                'success': False,
                'error': 'Disk cache is not enabled'
            }
            
        try:
            # Create a backup of the cache directory
            backup_dir = f"{self.cache_dir}_backup"
            
            if os.path.exists(backup_dir):
                shutil.rmtree(backup_dir)
                
            # Copy current cache to backup
            shutil.copytree(self.cache_dir, backup_dir)
            
            # Clear the disk cache
            self._clear_disk_cache()
            
            # Persist current in-memory cache
            persisted_count = 0
            for entry in self.cache.values():
                if self._persist_entry(entry):
                    persisted_count += 1
                    
            # Remove backup if successful
            shutil.rmtree(backup_dir)
            
            return {
                'success': True,
                'persisted_count': persisted_count
            }
        except Exception as e:
            logger.error(f"Error compressing disk cache: {e}")
            
            # Restore from backup if possible
            backup_dir = f"{self.cache_dir}_backup"
            if os.path.exists(backup_dir):
                try:
                    if os.path.exists(self.cache_dir):
                        shutil.rmtree(self.cache_dir)
                    shutil.copytree(backup_dir, self.cache_dir)
                except:
                    pass
                    
            return {
                'success': False,
                'error': str(e)
            }