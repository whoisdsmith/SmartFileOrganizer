"""
Test script for SQLite parameter format handling.

This script tests the SQLite connector's ability to handle both positional
and named parameters, and verifies correct operation with both formats.
"""

import os
import sys
import logging
import pprint

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SQLiteParameterTest")

# Import the required modules
from ai_document_organizer_v2.plugins.database.sqlite_connector import SQLiteConnectorPlugin

def test_parameter_formats():
    """Test different parameter formats with SQLite connector."""
    
    logger.info("=== Testing SQLite Parameter Format Handling ===")
    
    # Create a temporary database
    db_path = "test_parameters.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    
    # Initialize the connector
    config = {"database_path": db_path}
    connector = SQLiteConnectorPlugin(config)
    connector.initialize()
    connector.connect()
    
    try:
        # Create test table
        logger.info("Creating test table...")
        connector.execute_query("""
            CREATE TABLE test_parameters (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                value REAL,
                notes TEXT
            )
        """)
        
        # Test positional parameters with tuple format
        logger.info("\n\n=== Testing positional parameters with tuple format ===")
        result1 = connector.execute_query(
            "INSERT INTO test_parameters (name, value, notes) VALUES (?, ?, ?)",
            ("tuple_format", 42.5, "Inserted with tuple parameters")
        )
        logger.info(f"Insert result with tuple format: {result1}")
        
        # Test positional parameters with list format
        logger.info("\n\n=== Testing positional parameters with list format ===")
        result2 = connector.execute_query(
            "INSERT INTO test_parameters (name, value, notes) VALUES (?, ?, ?)",
            ["list_format", 43.5, "Inserted with list parameters"]
        )
        logger.info(f"Insert result with list format: {result2}")
        
        # Test named parameters with dictionary format
        logger.info("\n\n=== Testing named parameters with dictionary format ===")
        result3 = connector.execute_query(
            "INSERT INTO test_parameters (name, value, notes) VALUES (:name, :value, :notes)",
            {"name": "named_params", "value": 44.5, "notes": "Inserted with named parameters"}
        )
        logger.info(f"Insert result with named parameters: {result3}")
        
        # Query the data with different parameter formats
        logger.info("\n\n=== Querying with positional parameters (tuple) ===")
        query1 = connector.execute_query(
            "SELECT * FROM test_parameters WHERE name = ?",
            ("tuple_format",)
        )
        logger.info("Query result with positional parameter (tuple):")
        pprint.pprint(query1)
        
        logger.info("\n\n=== Querying with positional parameters (list) ===")
        query2 = connector.execute_query(
            "SELECT * FROM test_parameters WHERE name = ?",
            ["list_format"]
        )
        logger.info("Query result with positional parameter (list):")
        pprint.pprint(query2)
        
        logger.info("\n\n=== Querying with named parameters ===")
        query3 = connector.execute_query(
            "SELECT * FROM test_parameters WHERE name = :name",
            {"name": "named_params"}
        )
        logger.info("Query result with named parameter:")
        pprint.pprint(query3)
        
        # Verify all rows
        logger.info("\n\n=== All rows in table ===")
        all_rows = connector.execute_query("SELECT * FROM test_parameters")
        logger.info("All rows:")
        pprint.pprint(all_rows)
        
        # Test batch execution with mixed parameter types
        logger.info("\n\n=== Testing batch execution with mixed parameter types ===")
        batch_queries = [
            "INSERT INTO test_parameters (name, value, notes) VALUES (?, ?, ?)",
            "INSERT INTO test_parameters (name, value, notes) VALUES (:name, :value, :notes)",
            "UPDATE test_parameters SET notes = ? WHERE name = ?"
        ]
        
        batch_params = [
            ("batch_tuple", 50.0, "Batch inserted with tuple"),
            {"name": "batch_dict", "value": 51.0, "notes": "Batch inserted with dict"},
            ("Updated in batch", "tuple_format")
        ]
        
        batch_results = connector.execute_batch(batch_queries, batch_params)
        logger.info("Batch execution results:")
        for i, result in enumerate(batch_results):
            logger.info(f"Batch query {i+1} result: {result}")
        
        # Verify all rows after batch
        logger.info("\n\n=== All rows after batch execution ===")
        all_rows_after_batch = connector.execute_query("SELECT * FROM test_parameters")
        logger.info("All rows after batch:")
        pprint.pprint(all_rows_after_batch)
        
        # Test parameter error handling
        logger.info("\n\n=== Testing parameter error handling ===")
        try:
            connector.execute_query(
                "INSERT INTO test_parameters (name, value) VALUES (?, ?)",
                {"wrong": "format"}  # Wrong parameter format for query
            )
        except Exception as e:
            logger.info(f"Expected error with wrong parameter format: {e}")
        
    except Exception as e:
        logger.error(f"Error during testing: {e}")
        raise
    finally:
        # Clean up
        connector.disconnect()
        if os.path.exists(db_path):
            os.remove(db_path)
    
    logger.info("=== Test completed successfully ===")

if __name__ == "__main__":
    test_parameter_formats()