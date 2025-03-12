"""
Optimized PostgreSQL Database Connector for AI Document Organizer V2.

This module implements an enhanced database connector for PostgreSQL,
with optimized connection pooling, advanced PostgreSQL features,
query caching, and performance monitoring.
"""

import os
import re
import sys
import logging
import json
import time
import hashlib
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union, Set, Callable
from functools import wraps

try:
    import psycopg2
    from psycopg2 import pool, sql, extensions
    from psycopg2.extras import RealDictCursor, DictCursor, Json, register_default_jsonb
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

from ai_document_organizer_v2.plugins.database.connector_base import (
    DatabaseConnectorPlugin,
    ConnectionError,
    QueryError,
    TransactionError,
    SchemaError
)

from ai_document_organizer_v2.plugins.database.postgresql_connector import PostgreSQLConnectorPlugin

logger = logging.getLogger(__name__)

# Query cache storage
QUERY_CACHE = {}
QUERY_CACHE_METADATA = {}
CACHE_LOCK = threading.RLock()

class PerformanceStats:
    """Class for tracking performance statistics for the database connector."""
    
    def __init__(self):
        """Initialize performance statistics."""
        self.query_times = []  # List of execution times
        self.slow_queries = []  # List of slow queries (query, params, time)
        self.error_counts = {}  # Counter for different error types
        self.cache_hits = 0
        self.cache_misses = 0
        self.connection_times = []
        self.pool_wait_times = []
        self.active_connections = 0
        self.peak_connections = 0
        self.last_reset = time.time()
        
    def reset(self):
        """Reset all statistics."""
        self.__init__()
        
    def record_query_time(self, query: str, params: Any, execution_time: float):
        """Record query execution time and check for slow queries."""
        self.query_times.append(execution_time)
        
        # Track slow queries (> 100ms)
        if execution_time > 0.1:
            self.slow_queries.append({
                'query': query,
                'params': params,
                'time': execution_time,
                'timestamp': time.time()
            })
            
            # Keep only the last 100 slow queries
            if len(self.slow_queries) > 100:
                self.slow_queries.pop(0)
                
    def record_error(self, error_type: str):
        """Record an error by type."""
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        
    def record_cache_hit(self):
        """Record a cache hit."""
        self.cache_hits += 1
        
    def record_cache_miss(self):
        """Record a cache miss."""
        self.cache_misses += 1
        
    def record_connection_time(self, connection_time: float):
        """Record time taken to establish a connection."""
        self.connection_times.append(connection_time)
        
    def record_pool_wait_time(self, wait_time: float):
        """Record time spent waiting for a connection from the pool."""
        self.pool_wait_times.append(wait_time)
        
    def update_connection_count(self, count: int):
        """Update the active connection count."""
        self.active_connections = count
        self.peak_connections = max(self.peak_connections, count)
        
    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        total_queries = len(self.query_times)
        
        if total_queries > 0:
            avg_query_time = sum(self.query_times) / total_queries
            max_query_time = max(self.query_times) if self.query_times else 0
        else:
            avg_query_time = 0
            max_query_time = 0
            
        if self.connection_times:
            avg_connection_time = sum(self.connection_times) / len(self.connection_times)
        else:
            avg_connection_time = 0
            
        if self.pool_wait_times:
            avg_pool_wait_time = sum(self.pool_wait_times) / len(self.pool_wait_times)
            max_pool_wait_time = max(self.pool_wait_times)
        else:
            avg_pool_wait_time = 0
            max_pool_wait_time = 0
            
        total_cache_requests = self.cache_hits + self.cache_misses
        cache_hit_ratio = self.cache_hits / total_cache_requests if total_cache_requests > 0 else 0
        
        return {
            'query_count': total_queries,
            'avg_query_time_ms': avg_query_time * 1000,
            'max_query_time_ms': max_query_time * 1000,
            'slow_query_count': len(self.slow_queries),
            'error_counts': self.error_counts,
            'active_connections': self.active_connections,
            'peak_connections': self.peak_connections,
            'avg_connection_time_ms': avg_connection_time * 1000,
            'avg_pool_wait_time_ms': avg_pool_wait_time * 1000,
            'max_pool_wait_time_ms': max_pool_wait_time * 1000,
            'cache_hit_ratio': cache_hit_ratio,
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'stats_since': datetime.fromtimestamp(self.last_reset).isoformat()
        }


def query_cache(ttl_seconds: int = 60):
    """
    Decorator for caching query results.
    
    Args:
        ttl_seconds: Time to live for cached results in seconds
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, query: str, params: Optional[Union[Dict[str, Any], List[Any], Tuple[Any, ...]]] = None, 
                   use_cache: bool = True, *args, **kwargs):
            # Skip caching if explicitly disabled or in transaction
            if not use_cache or self._in_transaction or not self.config.get("enable_query_cache", True):
                return func(self, query, params, *args, **kwargs)
                
            # Only cache SELECT queries
            if not query.lstrip().upper().startswith("SELECT"):
                return func(self, query, params, *args, **kwargs)
                
            # Generate cache key
            cache_key = _generate_cache_key(query, params)
            
            with CACHE_LOCK:
                # Check if result is in cache and not expired
                if cache_key in QUERY_CACHE and cache_key in QUERY_CACHE_METADATA:
                    metadata = QUERY_CACHE_METADATA[cache_key]
                    if time.time() < metadata['expires']:
                        self.performance_stats.record_cache_hit()
                        return QUERY_CACHE[cache_key]
            
            # Cache miss or expired
            self.performance_stats.record_cache_miss()
            result = func(self, query, params, *args, **kwargs)
            
            # Cache the result
            with CACHE_LOCK:
                QUERY_CACHE[cache_key] = result
                QUERY_CACHE_METADATA[cache_key] = {
                    'created': time.time(),
                    'expires': time.time() + ttl_seconds,
                    'query': query
                }
                
                # Cleanup old cache entries
                _cleanup_cache()
                
            return result
        return wrapper
    return decorator


def _generate_cache_key(query: str, params: Any) -> str:
    """Generate a cache key for a query and parameters."""
    # Normalize query (remove whitespace variations)
    normalized_query = re.sub(r'\s+', ' ', query.strip())
    
    # Create a hash of the query and params
    params_str = str(params) if params is not None else "None"
    key_data = f"{normalized_query}:{params_str}".encode('utf-8')
    return hashlib.md5(key_data).hexdigest()


def _cleanup_cache():
    """Remove expired entries from the query cache."""
    now = time.time()
    expired_keys = [k for k, v in QUERY_CACHE_METADATA.items() if v['expires'] < now]
    
    for key in expired_keys:
        if key in QUERY_CACHE:
            del QUERY_CACHE[key]
        if key in QUERY_CACHE_METADATA:
            del QUERY_CACHE_METADATA[key]


class AdvancedConnectionPool:
    """
    Enhanced connection pool for PostgreSQL with monitoring capabilities.
    """
    
    def __init__(self, minconn, maxconn, stats_callback=None, **kwargs):
        """
        Initialize the advanced connection pool.
        
        Args:
            minconn: Minimum number of connections
            maxconn: Maximum number of connections
            stats_callback: Callback function for updating pool statistics
            **kwargs: Additional arguments for the connection pool
        """
        self.minconn = minconn
        self.maxconn = maxconn
        self.pool = pool.ThreadedConnectionPool(minconn, maxconn, **kwargs)
        self.stats_callback = stats_callback
        self.lock = threading.RLock()
        self.active_connections = set()
        self.connection_metadata = {}
        
    def getconn(self, key=None):
        """
        Get a connection from the pool with monitoring.
        
        Args:
            key: Optional key for the connection
            
        Returns:
            Database connection
        """
        start_time = time.time()
        
        with self.lock:
            conn = self.pool.getconn(key)
            self.active_connections.add(conn)
            self.connection_metadata[conn] = {
                'acquired': time.time(),
                'key': key,
                'last_activity': time.time()
            }
            
            if self.stats_callback:
                wait_time = time.time() - start_time
                self.stats_callback(
                    active_count=len(self.active_connections),
                    wait_time=wait_time
                )
                
            return conn
    
    def putconn(self, conn, key=None, close=False):
        """
        Return a connection to the pool.
        
        Args:
            conn: Connection to return
            key: Optional key for the connection
            close: Whether to close the connection
        """
        with self.lock:
            if conn in self.active_connections:
                self.active_connections.remove(conn)
                
            if conn in self.connection_metadata:
                del self.connection_metadata[conn]
                
            self.pool.putconn(conn, key, close)
            
            if self.stats_callback:
                self.stats_callback(
                    active_count=len(self.active_connections),
                    wait_time=0
                )
    
    def closeall(self):
        """Close all connections in the pool."""
        with self.lock:
            self.active_connections.clear()
            self.connection_metadata.clear()
            self.pool.closeall()
            
            if self.stats_callback:
                self.stats_callback(active_count=0, wait_time=0)
                
    def get_stats(self):
        """Get statistics about the connection pool."""
        with self.lock:
            now = time.time()
            connection_ages = [now - meta['acquired'] for meta in self.connection_metadata.values()]
            avg_age = sum(connection_ages) / len(connection_ages) if connection_ages else 0
            
            return {
                'active_connections': len(self.active_connections),
                'min_connections': self.minconn,
                'max_connections': self.maxconn,
                'pool_utilization': len(self.active_connections) / self.maxconn if self.maxconn > 0 else 0,
                'avg_connection_age_seconds': avg_age
            }


class PostgreSQLOptimizedConnector(PostgreSQLConnectorPlugin):
    """
    Optimized PostgreSQL database connector implementation with advanced features.
    
    This plugin extends the standard PostgreSQL connector with:
    1. Enhanced connection pooling
    2. Query caching
    3. Advanced PostgreSQL features (arrays, JSON querying)
    4. Performance monitoring and diagnostics
    """
    
    plugin_name = "postgresql_optimized_connector"
    plugin_description = "Optimized PostgreSQL database connector with advanced features"
    plugin_version = "1.0.0"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the optimized PostgreSQL connector plugin.
        
        Args:
            config: Optional configuration dictionary
        """
        # Initialize with parent's config
        super().__init__(config)
        
        # Add optimized connector specific settings
        self.config.setdefault("enable_query_cache", True)
        self.config.setdefault("query_cache_size", 100)  # Max number of cached queries
        self.config.setdefault("query_cache_ttl", 60)    # Default TTL in seconds
        self.config.setdefault("monitored_queries", True)
        self.config.setdefault("pool_recycling", 3600)   # Recycle connections after 1 hour
        self.config.setdefault("pool_pre_ping", True)    # Enable pre-ping to detect stale connections
        
        # Performance monitoring
        self.performance_stats = PerformanceStats()
        
        # Advanced connection pool
        self._advanced_pool = None
        
    def connect(self) -> bool:
        """
        Connect to the PostgreSQL database with enhanced connection pooling.
        
        Returns:
            True if connection was successful, False otherwise
            
        Raises:
            ConnectionError: If connection fails
        """
        try:
            # Close any existing connection
            if self._connection or self._connection_pool or self._advanced_pool:
                self.disconnect()
            
            # Extract connection parameters
            host = self.config["host"]
            port = self.config["port"]
            database = self.config["database"]
            user = self.config["user"]
            password = self.config["password"]
            connection_timeout = self.config["connection_timeout"]
            min_connections = self.config["min_connections"]
            max_connections = self.config["max_connections"]
            use_connection_pool = self.config["connection_pool"]
            
            # Create SSL parameters if needed
            ssl_params = {}
            if self.config["ssl_mode"]:
                ssl_params = {
                    "sslmode": self.config["ssl_mode"]
                }
                
                # Add SSL certificates if provided
                for key in ["sslcert", "sslkey", "sslrootcert"]:
                    if key in self.config and self.config[key]:
                        ssl_params[key] = self.config[key]
            
            # Prepare connection parameters
            dsn = f"host={host} port={port} dbname={database} user={user}"
            if password:
                dsn += f" password={password}"
                
            conn_kwargs = {
                "connect_timeout": connection_timeout
            }
            conn_kwargs.update(ssl_params)
            
            start_time = time.time()
            
            # Create connection or advanced connection pool
            if use_connection_pool:
                def stats_callback(active_count, wait_time):
                    self.performance_stats.update_connection_count(active_count)
                    if wait_time > 0:
                        self.performance_stats.record_pool_wait_time(wait_time)
                
                self._advanced_pool = AdvancedConnectionPool(
                    minconn=min_connections,
                    maxconn=max_connections,
                    stats_callback=stats_callback,
                    dsn=dsn,
                    **conn_kwargs
                )
                
                # Get a connection from the pool
                self._connection = self._advanced_pool.getconn()
            else:
                self._connection = psycopg2.connect(
                    dsn=dsn,
                    **conn_kwargs
                )
            
            # Record connection time
            self.performance_stats.record_connection_time(time.time() - start_time)
            
            # Set auto-commit to False for manual transaction control
            self._connection.autocommit = False
            
            # Create a cursor with dictionary cursor if configured
            if self.config["use_dict_cursor"]:
                self._cursor = self._connection.cursor(cursor_factory=RealDictCursor)
            else:
                self._cursor = self._connection.cursor(cursor_factory=DictCursor)
            
            # Enable array and JSON support
            register_default_jsonb(globally=True, loads=json.loads)
            
            if not self._connection:
                logger.error("Failed to create database connection")
                return False
            
            return True
        except Exception as e:
            self.performance_stats.record_error("connection_error")
            logger.error(f"Failed to connect to PostgreSQL database: {e}")
            raise ConnectionError(f"Failed to connect to PostgreSQL database: {e}")
            
    def disconnect(self) -> bool:
        """
        Disconnect from the PostgreSQL database.
        
        Returns:
            True if disconnect was successful, False otherwise
        """
        try:
            # Close cursor if it exists
            if self._cursor:
                self._cursor.close()
                self._cursor = None
            
            # Return connection to pool if using connection pool
            if self._advanced_pool and self._connection:
                self._advanced_pool.putconn(self._connection)
                self._connection = None
            elif self._connection_pool and self._connection:
                self._connection_pool.putconn(self._connection)
                self._connection = None
            # Close connection if not using connection pool
            elif self._connection:
                self._connection.close()
                self._connection = None
            
            # Close connection pools if they exist
            if self._advanced_pool:
                self._advanced_pool.closeall()
                self._advanced_pool = None
            elif self._connection_pool:
                self._connection_pool.closeall()
                self._connection_pool = None
            
            return True
        except Exception as e:
            self.performance_stats.record_error("disconnect_error")
            logger.error(f"Error disconnecting from database: {e}")
            return False
    
    @query_cache()
    def execute_query(self, query: str, params: Optional[Union[Dict[str, Any], List[Any], Tuple[Any, ...]]] = None,
                     use_cache: bool = True) -> Dict[str, Any]:
        """
        Execute a query on the database with caching support.
        
        Args:
            query: SQL query string
            params: Optional parameters for the query
            use_cache: Whether to use query caching (only applies to SELECT queries)
            
        Returns:
            Dictionary containing query results and metadata
            
        Raises:
            QueryError: If query execution fails
        """
        if not self.is_connected():
            self.connect()
        
        start_time = time.time()
        result = {
            "success": False,
            "rows": [],
            "row_count": 0,
            "column_names": [],
            "execution_time": 0,
            "last_row_id": None,
            "affected_rows": 0
        }
        
        try:
            # Set query timeout if supported
            if self.config["query_timeout"] > 0:
                self._cursor.execute(f"SET statement_timeout = {self.config['query_timeout'] * 1000}")
            
            # Execute the query
            if params:
                self._cursor.execute(query, params)
            else:
                self._cursor.execute(query)
            
            # Get column names if available
            if self._cursor.description:
                result["column_names"] = [desc[0] for desc in self._cursor.description]
                
                # Fetch rows if this is a SELECT query
                if query.lstrip().upper().startswith("SELECT"):
                    result["rows"] = self._cursor.fetchall()
                    
                    # Convert RealDictRow to plain dict if using dict cursor
                    if self.config["use_dict_cursor"]:
                        result["rows"] = [dict(row) for row in result["rows"]]
            
            # Get affected row count
            if hasattr(self._cursor, "rowcount") and self._cursor.rowcount >= 0:
                result["affected_rows"] = self._cursor.rowcount
                result["row_count"] = self._cursor.rowcount if not result["rows"] else len(result["rows"])
            
            # Get last inserted ID for INSERT statements
            if query.lstrip().upper().startswith("INSERT") and "RETURNING" in query.upper():
                for row in result["rows"]:
                    if "id" in row:
                        result["last_row_id"] = row["id"]
                        break
            
            # Mark as successful
            result["success"] = True
            
            # Record execution time
            execution_time = time.time() - start_time
            result["execution_time"] = execution_time
            
            # Record query time in performance stats
            self.performance_stats.record_query_time(query, params, execution_time)
            
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            self.performance_stats.record_query_time(query, params, execution_time)
            self.performance_stats.record_error("query_error")
            
            logger.error(f"Failed to execute query: {e}")
            
            # Provide more detailed error message
            error_details = str(e)
            if hasattr(e, "pgcode") and e.pgcode:
                error_details += f" (PostgreSQL Error Code: {e.pgcode})"
            
            raise QueryError(f"Failed to execute query: {error_details}")
    
    def execute_json_query(self, query: str, params: Optional[Union[Dict[str, Any], List[Any], Tuple[Any, ...]]] = None, 
                          json_path: str = None) -> Dict[str, Any]:
        """
        Execute a query with JSON or JSONB operations.
        
        Args:
            query: SQL query string
            params: Optional parameters for the query
            json_path: JSON path expression to extract (if not included in query)
            
        Returns:
            Dictionary containing query results
            
        Raises:
            QueryError: If query execution fails
        """
        # If JSON path is provided but not in query, modify the query
        if json_path and '->>' not in query and '#>' not in query:
            # Find the FROM clause
            from_pos = query.upper().find('FROM')
            if from_pos > 0:
                # Insert JSON path expression before FROM
                select_part = query[:from_pos].strip()
                from_part = query[from_pos:]
                
                # Find the column and add the JSON path
                if select_part.upper().startswith('SELECT '):
                    select_part = select_part[7:].strip()
                    
                # Simple case: single column
                if ',' not in select_part:
                    column = select_part.strip()
                    query = f"SELECT {column}->>{json_path} FROM {from_part}"
                
        # Execute the query using standard method
        return self.execute_query(query, params)
    
    def create_table(self, table_name: str, columns: Dict[str, Dict[str, Any]], 
                    primary_key: Optional[Union[str, List[str]]] = None,
                    if_not_exists: bool = True) -> bool:
        """
        Create a table with enhanced PostgreSQL type support.
        
        Args:
            table_name: Name of the table to create
            columns: Dictionary mapping column names to column definitions
            primary_key: Optional primary key column name or list of column names
            if_not_exists: Whether to add IF NOT EXISTS to the query
            
        Returns:
            True if table was created successfully, False otherwise
            
        Raises:
            SchemaError: If table creation fails
        """
        try:
            # Begin building the SQL query
            exists_clause = "IF NOT EXISTS " if if_not_exists else ""
            query = f"CREATE TABLE {exists_clause}\"{table_name}\" (\n"
            
            # Add column definitions
            column_clauses = []
            for col_name, col_def in columns.items():
                # Get PostgreSQL type from column definition
                if "type" not in col_def:
                    raise SchemaError(f"Column {col_name} is missing type definition")
                
                col_type = col_def["type"].lower()
                pg_type = self._TYPE_MAPPING.get(col_type, col_type.upper())
                
                # Handle array types
                if col_type.endswith("[]") or col_type == "array":
                    base_type = col_type.replace("[]", "")
                    pg_base_type = self._TYPE_MAPPING.get(base_type, base_type.upper())
                    pg_type = f"{pg_base_type}[]"
                
                # Build the column definition clause
                col_clause = f"\"{col_name}\" {pg_type}"
                
                # Add column constraints
                if col_def.get("nullable") is False:
                    col_clause += " NOT NULL"
                    
                if "default" in col_def:
                    default_val = col_def["default"]
                    
                    # Handle different types of default values
                    if isinstance(default_val, str):
                        col_clause += f" DEFAULT '{default_val}'"
                    elif default_val is None:
                        col_clause += " DEFAULT NULL"
                    elif isinstance(default_val, bool):
                        col_clause += f" DEFAULT {str(default_val).upper()}"
                    elif isinstance(default_val, (int, float)):
                        col_clause += f" DEFAULT {default_val}"
                    elif isinstance(default_val, dict) and pg_type in ('JSONB', 'JSON'):
                        json_str = json.dumps(default_val).replace("'", "''")
                        col_clause += f" DEFAULT '{json_str}'::jsonb"
                    else:
                        col_clause += f" DEFAULT '{default_val}'"
                
                # Add unique constraint
                if col_def.get("unique") is True:
                    col_clause += " UNIQUE"
                
                column_clauses.append(col_clause)
            
            # Add primary key definition
            if primary_key:
                if isinstance(primary_key, list):
                    pk_cols = '", "'.join(primary_key)
                    column_clauses.append(f'PRIMARY KEY ("{pk_cols}")')
                else:
                    column_clauses.append(f'PRIMARY KEY ("{primary_key}")')
            
            # Complete the query
            query += ',\n'.join(f"  {clause}" for clause in column_clauses)
            query += "\n);"
            
            # Execute the query
            result = self.execute_query(query)
            return result["success"]
        
        except Exception as e:
            self.performance_stats.record_error("schema_error")
            logger.error(f"Failed to create table {table_name}: {e}")
            raise SchemaError(f"Failed to create table {table_name}: {e}")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Get performance statistics for the database connector.
        
        Returns:
            Dictionary with performance statistics
        """
        stats = self.performance_stats.get_stats()
        
        # Add pool stats if available
        if self._advanced_pool:
            stats['pool'] = self._advanced_pool.get_stats()
            
        # Add cache stats
        with CACHE_LOCK:
            stats['cache_entries'] = len(QUERY_CACHE)
            stats['cache_size'] = sum(sys.getsizeof(str(v)) for v in QUERY_CACHE.values())
            stats['cache_size_kb'] = stats['cache_size'] / 1024
            
        return stats
    
    def reset_stats(self) -> None:
        """Reset all performance statistics."""
        self.performance_stats.reset()
    
    def clear_query_cache(self) -> None:
        """Clear the query cache."""
        with CACHE_LOCK:
            QUERY_CACHE.clear()
            QUERY_CACHE_METADATA.clear()
            
    def get_slow_queries(self) -> List[Dict[str, Any]]:
        """
        Get a list of slow queries.
        
        Returns:
            List of slow query details (query, params, execution time)
        """
        return self.performance_stats.slow_queries
    
    def create_function(self, name: str, parameter_types: List[str], 
                      return_type: str, definition: str,
                      replace: bool = True) -> bool:
        """
        Create or replace a PostgreSQL function/stored procedure.
        
        Args:
            name: Function name
            parameter_types: List of parameter types
            return_type: Return type
            definition: Function definition (body)
            replace: Whether to use CREATE OR REPLACE
            
        Returns:
            True if the function was created successfully, False otherwise
        """
        try:
            replace_text = "OR REPLACE" if replace else ""
            params_text = ", ".join(parameter_types)
            
            query = f"""
            CREATE {replace_text} FUNCTION {name}({params_text})
            RETURNS {return_type} AS
            $$
            {definition}
            $$ LANGUAGE plpgsql;
            """
            
            result = self.execute_query(query)
            return result["success"]
        except Exception as e:
            self.performance_stats.record_error("function_error")
            logger.error(f"Failed to create function {name}: {e}")
            return False
    
    def execute_batch(self, queries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Execute multiple queries in a batch.
        
        Args:
            queries: List of query dictionaries with 'query' and optional 'params' keys
            
        Returns:
            List of query results
        """
        results = []
        
        if not self.is_connected():
            self.connect()
        
        # Begin transaction
        self.begin_transaction()
        
        try:
            for query_item in queries:
                query = query_item.get('query', '')
                params = query_item.get('params', None)
                use_cache = query_item.get('use_cache', True)
                
                # Execute the query
                result = self.execute_query(query, params, use_cache=use_cache)
                results.append(result)
            
            # Commit the transaction
            self.commit()
        except Exception as e:
            # Rollback on error
            self.rollback()
            self.performance_stats.record_error("batch_error")
            raise QueryError(f"Batch execution failed: {e}")
        
        return results
    
    def explain_query(self, query: str, params: Optional[Union[Dict[str, Any], List[Any], Tuple[Any, ...]]] = None,
                     analyze: bool = False) -> Dict[str, Any]:
        """
        Get query execution plan using EXPLAIN.
        
        Args:
            query: SQL query to explain
            params: Optional parameters for the query
            analyze: Whether to include ANALYZE to execute the query
            
        Returns:
            Dictionary with query plan details
        """
        explain_prefix = "EXPLAIN (FORMAT JSON"
        if analyze:
            explain_prefix += ", ANALYZE"
        explain_prefix += ")"
        
        explain_query = f"{explain_prefix} {query}"
        
        try:
            result = self.execute_query(explain_query, params, use_cache=False)
            
            if result["success"] and result["rows"]:
                # Extract the plan from the result
                plan_json = result["rows"][0][0]
                return {
                    "success": True,
                    "plan": plan_json,
                    "query": query
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to retrieve execution plan",
                    "query": query
                }
        except Exception as e:
            logger.error(f"Failed to explain query: {e}")
            return {
                "success": False,
                "error": str(e),
                "query": query
            }
    
    def vacuum_table(self, table_name: str, analyze: bool = True, full: bool = False) -> bool:
        """
        Perform VACUUM operation on a table.
        
        Args:
            table_name: Name of the table to vacuum
            analyze: Whether to include ANALYZE
            full: Whether to perform FULL vacuum
            
        Returns:
            True if vacuum was successful, False otherwise
        """
        try:
            vacuum_type = "FULL" if full else ""
            analyze_clause = "ANALYZE" if analyze else ""
            
            query = f"VACUUM {vacuum_type} {analyze_clause} \"{table_name}\""
            
            # Execute vacuum (needs autocommit mode)
            old_autocommit = self._connection.autocommit
            self._connection.autocommit = True
            self._cursor.execute(query)
            self._connection.autocommit = old_autocommit
            
            return True
        except Exception as e:
            logger.error(f"Failed to vacuum table {table_name}: {e}")
            return False
    
    def create_index(self, table_name: str, column_names: Union[str, List[str]], 
                    index_name: Optional[str] = None,
                    unique: bool = False, using: str = "btree") -> bool:
        """
        Create an index on a table.
        
        Args:
            table_name: Name of the table
            column_names: Column name or list of column names to index
            index_name: Optional name for the index (generated if not provided)
            unique: Whether to create a unique index
            using: Index type (btree, hash, gist, gin)
            
        Returns:
            True if index was created successfully, False otherwise
        """
        try:
            # Normalize column_names to a list
            if isinstance(column_names, str):
                column_names = [column_names]
            
            # Generate index name if not provided
            if not index_name:
                columns_str = '_'.join(column_names)
                index_name = f"idx_{table_name}_{columns_str}"
            
            # Add unique clause if specified
            unique_clause = "UNIQUE" if unique else ""
            
            # Build column list
            columns_str = ', '.join(f'"{col}"' for col in column_names)
            
            query = f"CREATE {unique_clause} INDEX {index_name} ON \"{table_name}\" USING {using} ({columns_str})"
            
            result = self.execute_query(query)
            return result["success"]
        except Exception as e:
            logger.error(f"Failed to create index on {table_name}: {e}")
            return False
    
    def create_json_index(self, table_name: str, column_name: str, 
                         path: Optional[str] = None,
                         index_name: Optional[str] = None) -> bool:
        """
        Create a GIN index on a JSON/JSONB column.
        
        Args:
            table_name: Name of the table
            column_name: JSON/JSONB column to index
            path: Optional JSON path to index specific elements
            index_name: Optional name for the index
            
        Returns:
            True if index was created successfully, False otherwise
        """
        try:
            # Generate index name if not provided
            if not index_name:
                index_name = f"idx_json_{table_name}_{column_name}"
                if path:
                    # Sanitize path for index name
                    safe_path = re.sub(r'[^a-zA-Z0-9]', '_', path)
                    index_name += f"_{safe_path}"
            
            # Build index expression
            if path:
                expression = f"\"{column_name}\"->'{path}'"
            else:
                expression = f"\"{column_name}\""
            
            query = f"CREATE INDEX {index_name} ON \"{table_name}\" USING GIN ({expression})"
            
            result = self.execute_query(query)
            return result["success"]
        except Exception as e:
            logger.error(f"Failed to create JSON index on {table_name}.{column_name}: {e}")
            return False