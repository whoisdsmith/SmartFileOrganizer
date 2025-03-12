"""
Test suite for the optimized PostgreSQL Database Connector.
"""

import unittest
import time
from unittest.mock import patch, MagicMock
import json
import psycopg2
import logging
import os
from typing import Dict, Any, List

from ai_document_organizer_v2.plugins.database.postgresql_optimized import (
    PostgreSQLOptimizedConnector,
    PerformanceStats,
    AdvancedConnectionPool,
    QUERY_CACHE,
    QUERY_CACHE_METADATA
)

# Set up logging
logging.basicConfig(level=logging.INFO)

class TestPostgreSQLOptimizedConnector(unittest.TestCase):
    """Test cases for the optimized PostgreSQL connector."""
    
    def setUp(self):
        """Set up test fixtures before each test method is run."""
        # Mock the psycopg2 module
        self.patcher = patch('ai_document_organizer_v2.plugins.database.postgresql_optimized.psycopg2')
        self.mock_psycopg2 = self.patcher.start()
        
        # Mock the connection and cursor
        self.mock_connection = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_connection.cursor.return_value = self.mock_cursor
        self.mock_psycopg2.connect.return_value = self.mock_connection
        
        # Mock pool module
        self.mock_pool = MagicMock()
        self.mock_psycopg2.pool = self.mock_pool
        
        # Mock RealDictCursor
        self.mock_psycopg2.extras.RealDictCursor = MagicMock()
        self.mock_psycopg2.extras.DictCursor = MagicMock()
        
        # Create test configuration
        self.config = {
            "host": "localhost",
            "port": 5432,
            "database": "test_db",
            "user": "test_user",
            "password": "test_password",
            "min_connections": 1,
            "max_connections": 10,
            "connection_pool": True,
            "query_timeout": 30,
            "use_dict_cursor": True,
            "enable_query_cache": True,
            "query_cache_ttl": 60
        }
        
        # Clear query cache
        QUERY_CACHE.clear()
        QUERY_CACHE_METADATA.clear()
        
        # Create connector instance
        self.connector = PostgreSQLOptimizedConnector(self.config)
        
        # Mock the connection methods
        self.connector._connection = self.mock_connection
        self.connector._cursor = self.mock_cursor
        self.connector._in_transaction = False
    
    def tearDown(self):
        """Clean up after each test method is run."""
        self.patcher.stop()
        
        # Clear query cache
        QUERY_CACHE.clear()
        QUERY_CACHE_METADATA.clear()
    
    def test_init(self):
        """Test connector initialization."""
        connector = PostgreSQLOptimizedConnector(self.config)
        
        # Check default configuration
        self.assertEqual(connector.config["host"], "localhost")
        self.assertEqual(connector.config["port"], 5432)
        self.assertEqual(connector.config["database"], "test_db")
        self.assertEqual(connector.config["user"], "test_user")
        self.assertEqual(connector.config["password"], "test_password")
        self.assertEqual(connector.config["min_connections"], 1)
        self.assertEqual(connector.config["max_connections"], 10)
        self.assertTrue(connector.config["connection_pool"])
        self.assertEqual(connector.config["query_timeout"], 30)
        self.assertTrue(connector.config["use_dict_cursor"])
        self.assertTrue(connector.config["enable_query_cache"])
        self.assertEqual(connector.config["query_cache_ttl"], 60)
        
        # Check performance stats initialization
        self.assertIsInstance(connector.performance_stats, PerformanceStats)
        
    def test_connect(self):
        """Test connection functionality."""
        # Clear previous mocks
        self.mock_psycopg2.connect.reset_mock()
        self.mock_pool.ThreadedConnectionPool.reset_mock()
        
        # Create a fresh connector
        connector = PostgreSQLOptimizedConnector(self.config)
        
        # Mock the advanced pool
        mock_adv_pool = MagicMock()
        mock_adv_pool.getconn.return_value = self.mock_connection
        
        # Use a side effect to simulate advanced pool creation
        def create_pool(*args, **kwargs):
            connector._advanced_pool = mock_adv_pool
            return mock_adv_pool
        
        # Apply the side effect
        with patch('ai_document_organizer_v2.plugins.database.postgresql_optimized.AdvancedConnectionPool', 
                  side_effect=create_pool) as mock_pool_class:
            # Connect to the database
            result = connector.connect()
            
            # Verify connection was established
            self.assertTrue(result)
            
            # Verify pool creation
            mock_pool_class.assert_called_once()
            
            # Verify connection acquisition from pool
            mock_adv_pool.getconn.assert_called_once()
            
            # Verify cursor creation
            self.mock_connection.cursor.assert_called_once()
    
    def test_execute_query(self):
        """Test query execution."""
        # Configure mock cursor
        self.mock_cursor.description = [("id",), ("name",)]
        mock_rows = [{"id": 1, "name": "Test"}]
        self.mock_cursor.fetchall.return_value = mock_rows
        self.mock_cursor.rowcount = 1
        
        # Execute a test query
        query = "SELECT * FROM test WHERE id = %s"
        params = (1,)
        result = self.connector.execute_query(query, params)
        
        # Verify query execution
        self.mock_cursor.execute.assert_called_with(query, params)
        
        # Verify result
        self.assertTrue(result["success"])
        self.assertEqual(result["rows"], mock_rows)
        self.assertEqual(result["row_count"], 1)
        self.assertEqual(result["column_names"], ["id", "name"])
        self.assertEqual(result["affected_rows"], 1)
        self.assertTrue("execution_time" in result)
    
    def test_query_cache(self):
        """Test query caching functionality."""
        # Configure mock cursor
        self.mock_cursor.description = [("id",), ("name",)]
        mock_rows = [{"id": 1, "name": "Test"}]
        self.mock_cursor.fetchall.return_value = mock_rows
        self.mock_cursor.rowcount = 1
        
        # Execute a SELECT query that should be cached
        query = "SELECT * FROM test WHERE id = %s"
        params = (1,)
        
        # First execution should hit the database
        result1 = self.connector.execute_query(query, params)
        
        # Verify first execution
        self.mock_cursor.execute.assert_called_with(query, params)
        self.mock_cursor.execute.reset_mock()
        
        # Second execution should use the cache
        result2 = self.connector.execute_query(query, params)
        
        # Verify second execution used cache
        self.mock_cursor.execute.assert_not_called()
        
        # Results should be identical
        self.assertEqual(result1, result2)
        
        # Check cache hit count
        self.assertEqual(self.connector.performance_stats.cache_hits, 1)
        self.assertEqual(self.connector.performance_stats.cache_misses, 1)
        
        # Verify cache has an entry
        self.assertEqual(len(QUERY_CACHE), 1)
        
        # Test cache invalidation
        self.connector.clear_query_cache()
        self.assertEqual(len(QUERY_CACHE), 0)
        self.assertEqual(len(QUERY_CACHE_METADATA), 0)
    
    def test_non_cached_queries(self):
        """Test non-cached query types."""
        # Configure mock cursor
        self.mock_cursor.description = [("id",), ("name",)]
        self.mock_cursor.fetchall.return_value = []
        self.mock_cursor.rowcount = 1
        
        # Execute an INSERT query that should not be cached
        query = "INSERT INTO test (name) VALUES (%s)"
        params = ("Test",)
        
        # Execute the query
        result = self.connector.execute_query(query, params)
        
        # Verify execution
        self.mock_cursor.execute.assert_called_with(query, params)
        self.mock_cursor.execute.reset_mock()
        
        # Verify cache miss count (but no hit)
        self.assertEqual(self.connector.performance_stats.cache_hits, 0)
        self.assertEqual(self.connector.performance_stats.cache_misses, 0)  # Non-SELECT queries don't count
        
        # Verify cache has no entries
        self.assertEqual(len(QUERY_CACHE), 0)
    
    def test_json_query(self):
        """Test JSON query functionality."""
        # Configure mock cursor
        self.mock_cursor.description = [("data",)]
        mock_rows = [{"data": {"name": "Test", "value": 42}}]
        self.mock_cursor.fetchall.return_value = mock_rows
        self.mock_cursor.rowcount = 1
        
        # Execute a JSON query
        query = "SELECT data->>'name' FROM test WHERE id = %s"
        params = (1,)
        result = self.connector.execute_json_query(query, params)
        
        # Verify query execution
        self.mock_cursor.execute.assert_called_with(query, params)
        
        # Verify result
        self.assertTrue(result["success"])
        self.assertEqual(result["rows"], mock_rows)
        
        # Test automatic JSON path addition
        self.mock_cursor.execute.reset_mock()
        query = "SELECT data FROM test WHERE id = 1"
        result = self.connector.execute_json_query(query, None, json_path="'name'")
        
        # Verify modified query
        expected_query = "SELECT data->>'name' FROM test WHERE id = 1"
        args, _ = self.mock_cursor.execute.call_args
        self.assertIn("->>'name'", args[0])
    
    def test_create_json_index(self):
        """Test creating a JSON index."""
        # Mock cursor execution success
        self.mock_cursor.execute.return_value = None
        
        # Create a JSON index
        result = self.connector.create_json_index("test_table", "data")
        
        # Verify execution
        self.assertTrue(result)
        
        # Verify correct SQL generation
        args, _ = self.mock_cursor.execute.call_args
        self.assertIn("CREATE INDEX", args[0])
        self.assertIn("USING GIN", args[0])
        self.assertIn("\"data\"", args[0])
        
        # Test with JSON path
        self.mock_cursor.execute.reset_mock()
        result = self.connector.create_json_index("test_table", "data", "attributes")
        
        # Verify execution with path
        self.assertTrue(result)
        
        # Verify correct SQL generation with path
        args, _ = self.mock_cursor.execute.call_args
        self.assertIn("\"data\"->", args[0])
        self.assertIn("'attributes'", args[0])
    
    def test_performance_stats(self):
        """Test performance statistics collection."""
        # Configure mock cursor
        self.mock_cursor.description = [("id",), ("name",)]
        self.mock_cursor.fetchall.return_value = [{"id": 1, "name": "Test"}]
        self.mock_cursor.rowcount = 1
        
        # Execute a few queries
        for i in range(5):
            query = f"SELECT * FROM test WHERE id = {i}"
            self.connector.execute_query(query)
        
        # Record an error
        self.connector.performance_stats.record_error("test_error")
        
        # Get performance stats
        stats = self.connector.get_performance_stats()
        
        # Verify stats
        self.assertEqual(stats["query_count"], 5)
        self.assertTrue("avg_query_time_ms" in stats)
        self.assertTrue("max_query_time_ms" in stats)
        self.assertEqual(stats["error_counts"]["test_error"], 1)
        self.assertEqual(stats["cache_hits"], 0)
        self.assertEqual(stats["cache_misses"], 5)
        
        # Verify cache stats
        self.assertTrue("cache_entries" in stats)
        self.assertTrue("cache_size" in stats)
        self.assertTrue("cache_size_kb" in stats)
        
        # Reset stats
        self.connector.reset_stats()
        
        # Verify reset
        stats = self.connector.get_performance_stats()
        self.assertEqual(stats["query_count"], 0)
        self.assertEqual(stats["cache_hits"], 0)
        self.assertEqual(stats["cache_misses"], 0)
    
    def test_batch_execution(self):
        """Test batch query execution."""
        # Configure mock cursor
        self.mock_cursor.description = [("id",), ("name",)]
        self.mock_cursor.fetchall.return_value = [{"id": 1, "name": "Test"}]
        self.mock_cursor.rowcount = 1
        
        # Create batch queries
        queries = [
            {"query": "SELECT * FROM test WHERE id = %s", "params": (1,)},
            {"query": "UPDATE test SET name = %s WHERE id = %s", "params": ("Updated", 1)},
            {"query": "SELECT * FROM test WHERE id = %s", "params": (1,)}
        ]
        
        # Execute batch
        results = self.connector.execute_batch(queries)
        
        # Verify execution
        self.assertEqual(len(results), 3)
        
        # Verify transaction control
        self.mock_cursor.execute.assert_any_call("BEGIN")
        self.mock_connection.commit.assert_called_once()
        
        # Verify query executions
        for i, query_item in enumerate(queries):
            self.mock_cursor.execute.assert_any_call(query_item["query"], query_item["params"])
    
    def test_explain_query(self):
        """Test query explanation."""
        # Configure mock cursor for EXPLAIN
        plan_json = [{"Plan": {"Node Type": "Seq Scan", "Relation": "test"}}]
        self.mock_cursor.description = [("QUERY PLAN",)]
        self.mock_cursor.fetchall.return_value = [[plan_json]]
        
        # Execute EXPLAIN
        result = self.connector.explain_query("SELECT * FROM test WHERE id = 1")
        
        # Verify execution
        self.assertTrue(result["success"])
        self.assertEqual(result["plan"], plan_json)
        
        # Verify correct EXPLAIN query generation
        args, _ = self.mock_cursor.execute.call_args
        self.assertTrue(args[0].startswith("EXPLAIN (FORMAT JSON"))
        
        # Test with ANALYZE
        self.mock_cursor.execute.reset_mock()
        result = self.connector.explain_query("SELECT * FROM test WHERE id = 1", analyze=True)
        
        # Verify ANALYZE inclusion
        args, _ = self.mock_cursor.execute.call_args
        self.assertIn("ANALYZE", args[0])

if __name__ == '__main__':
    unittest.main()