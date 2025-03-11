"""
Test script for SQLite connector parameter format handling (enhanced version).

This script tests the SQLite connector's ability to handle various parameter formats
including positional parameters (tuples/lists) and named parameters (dictionaries).
It also tests batch operations with mixed parameter formats.
"""

import os
import sys
import logging
import json
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Union

# Check if module path is in sys.path or add it
sys.path.append(os.path.abspath('.'))

# Import SQLite connector
from ai_document_organizer_v2.plugins.database.sqlite_connector import SQLiteConnectorPlugin
from ai_document_organizer_v2.plugins.database.connector_base import (
    DatabaseConnectorPlugin,
    ConnectionError,
    QueryError,
    TransactionError,
    SchemaError
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def print_separator(title: str):
    """Print a separator with a title."""
    print("\n" + "=" * 80)
    print(f"{title.center(80)}")
    print("=" * 80 + "\n")

def test_single_queries():
    """Test different parameter formats with single queries."""
    print_separator("Testing Single Queries with Different Parameter Formats")
    
    connector = SQLiteConnectorPlugin({
        "database_path": "test_parameter_formats.db"
    })
    
    try:
        # Connect and initialize
        connector.initialize()
        connector.connect()
        print("Connected to test database successfully")
        
        # Create a test table
        columns = {
            "id": {"type": "integer", "primary_key": True, "autoincrement": True},
            "name": {"type": "text", "nullable": False},
            "value": {"type": "real", "default": 0.0},
            "is_active": {"type": "boolean", "default": True},
            "created_at": {"type": "datetime", "default": "CURRENT_TIMESTAMP"}
        }
        
        table_name = "test_parameters"
        connector.create_table(table_name, columns)
        print(f"Created table '{table_name}' successfully")
        
        # Test 1: Positional parameters with tuple
        print("\n1. Testing positional parameters with tuple:")
        result1 = connector.execute_query(
            f"INSERT INTO {table_name} (name, value, is_active) VALUES (?, ?, ?)",
            ("Item A", 10.5, 1)
        )
        print(f"Inserted row with ID: {result1.get('last_row_id')}")
        
        # Test 2: Positional parameters with list
        print("\n2. Testing positional parameters with list:")
        result2 = connector.execute_query(
            f"INSERT INTO {table_name} (name, value, is_active) VALUES (?, ?, ?)",
            ["Item B", 20.75, 0]
        )
        print(f"Inserted row with ID: {result2.get('last_row_id')}")
        
        # Test 3: Named parameters with dictionary
        print("\n3. Testing named parameters with dictionary:")
        result3 = connector.execute_query(
            f"INSERT INTO {table_name} (name, value, is_active) VALUES (:name, :value, :status)",
            {"name": "Item C", "value": 30.25, "status": 1}
        )
        print(f"Inserted row with ID: {result3.get('last_row_id')}")
        
        # Test querying with different parameter formats
        print("\nTesting SELECT queries with different parameter formats:")
        
        # Query with positional parameters (tuple)
        print("\n1. SELECT with positional parameters (tuple):")
        select1 = connector.execute_query(
            f"SELECT * FROM {table_name} WHERE name = ?",
            ("Item A",)
        )
        for row in select1["rows"]:
            print(f"ID: {row['id']}, Name: {row['name']}, Value: {row['value']}, Active: {row['is_active']}")
        
        # Query with positional parameters (list)
        print("\n2. SELECT with positional parameters (list):")
        select2 = connector.execute_query(
            f"SELECT * FROM {table_name} WHERE name = ?",
            ["Item B"]
        )
        for row in select2["rows"]:
            print(f"ID: {row['id']}, Name: {row['name']}, Value: {row['value']}, Active: {row['is_active']}")
        
        # Query with named parameters
        print("\n3. SELECT with named parameters:")
        select3 = connector.execute_query(
            f"SELECT * FROM {table_name} WHERE name = :item_name",
            {"item_name": "Item C"}
        )
        for row in select3["rows"]:
            print(f"ID: {row['id']}, Name: {row['name']}, Value: {row['value']}, Active: {row['is_active']}")
        
        # Query with multiple positional parameters
        print("\n4. SELECT with multiple positional parameters:")
        select4 = connector.execute_query(
            f"SELECT * FROM {table_name} WHERE value > ? AND is_active = ?",
            (15.0, 0)
        )
        for row in select4["rows"]:
            print(f"ID: {row['id']}, Name: {row['name']}, Value: {row['value']}, Active: {row['is_active']}")
        
        # Query with multiple named parameters
        print("\n5. SELECT with multiple named parameters:")
        select5 = connector.execute_query(
            f"SELECT * FROM {table_name} WHERE value > :min_value AND is_active = :status",
            {"min_value": 25.0, "status": 1}
        )
        for row in select5["rows"]:
            print(f"ID: {row['id']}, Name: {row['name']}, Value: {row['value']}, Active: {row['is_active']}")
        
        # Query all data
        print("\nAll data in the table:")
        all_data = connector.execute_query(f"SELECT * FROM {table_name}")
        for row in all_data["rows"]:
            print(f"ID: {row['id']}, Name: {row['name']}, Value: {row['value']}, Active: {row['is_active']}")
            
    except Exception as e:
        logger.error(f"Error during single query tests: {e}")
        raise
        
    finally:
        # Clean up
        if connector.is_connected():
            connector.drop_table(table_name)
            connector.disconnect()
        
        if os.path.exists("test_parameter_formats.db"):
            os.remove("test_parameter_formats.db")
            print("\nTest database removed")

def test_batch_operations():
    """Test batch operations with different parameter formats."""
    print_separator("Testing Batch Operations with Different Parameter Formats")
    
    connector = SQLiteConnectorPlugin({
        "database_path": "test_batch_operations.db"
    })
    
    try:
        # Connect and initialize
        connector.initialize()
        connector.connect()
        print("Connected to test database successfully")
        
        # Create a test table
        columns = {
            "id": {"type": "integer", "primary_key": True, "autoincrement": True},
            "name": {"type": "text", "nullable": False},
            "category": {"type": "text", "nullable": True},
            "price": {"type": "real", "default": 0.0},
            "in_stock": {"type": "boolean", "default": True},
            "added_date": {"type": "datetime", "default": "CURRENT_TIMESTAMP"}
        }
        
        table_name = "test_batch"
        connector.create_table(table_name, columns)
        print(f"Created table '{table_name}' successfully")
        
        # Prepare batch queries and parameters with mixed formats
        queries = [
            f"INSERT INTO {table_name} (name, category, price, in_stock) VALUES (?, ?, ?, ?)",
            f"INSERT INTO {table_name} (name, category, price, in_stock) VALUES (?, ?, ?, ?)",
            f"INSERT INTO {table_name} (name, category, price, in_stock) VALUES (:name, :category, :price, :in_stock)",
            f"UPDATE {table_name} SET price = ? WHERE name = ?",
            f"UPDATE {table_name} SET in_stock = :status WHERE category = :cat"
        ]
        
        params_list = [
            ("Product A", "Electronics", 299.99, 1),  # Tuple params
            ["Product B", "Books", 24.95, 1],         # List params
            {"name": "Product C", "category": "Clothing", "price": 49.95, "in_stock": 0},  # Dict params
            (399.99, "Product A"),  # Tuple params for UPDATE
            {"status": 0, "cat": "Books"}   # Dict params for UPDATE
        ]
        
        print("\nExecuting batch operations with mixed parameter formats...")
        results = connector.execute_batch(queries, params_list)
        
        for i, result in enumerate(results):
            print(f"\nBatch operation {i+1}:")
            print(f"Success: {result['success']}")
            print(f"Affected rows: {result['affected_rows']}")
            print(f"Last row ID: {result['last_row_id']}")
            print(f"Execution time: {result['execution_time']:.6f} seconds")
        
        # Query all data
        print("\nAll data in the table after batch operations:")
        all_data = connector.execute_query(f"SELECT * FROM {table_name}")
        for row in all_data["rows"]:
            print(f"ID: {row['id']}, Name: {row['name']}, Category: {row['category']}, "
                  f"Price: {row['price']}, In Stock: {row['in_stock']}")
            
    except Exception as e:
        logger.error(f"Error during batch operation tests: {e}")
        raise
        
    finally:
        # Clean up
        if connector.is_connected():
            connector.drop_table(table_name)
            connector.disconnect()
        
        if os.path.exists("test_batch_operations.db"):
            os.remove("test_batch_operations.db")
            print("\nTest database removed")

def test_transaction_with_mixed_parameters():
    """Test transactions with different parameter formats."""
    print_separator("Testing Transactions with Different Parameter Formats")
    
    connector = SQLiteConnectorPlugin({
        "database_path": "test_transactions.db"
    })
    
    try:
        # Connect and initialize
        connector.initialize()
        connector.connect()
        print("Connected to test database successfully")
        
        # Create a test table
        columns = {
            "id": {"type": "integer", "primary_key": True, "autoincrement": True},
            "account": {"type": "text", "nullable": False},
            "balance": {"type": "real", "default": 0.0},
            "last_updated": {"type": "datetime", "default": "CURRENT_TIMESTAMP"}
        }
        
        table_name = "test_accounts"
        connector.create_table(table_name, columns)
        print(f"Created table '{table_name}' successfully")
        
        # Insert initial data
        connector.execute_query(
            f"INSERT INTO {table_name} (account, balance) VALUES (?, ?), (?, ?)",
            ("Account1", 1000.0, "Account2", 500.0)
        )
        print("Inserted initial account data")
        
        # Show initial balances
        print("\nInitial account balances:")
        balances = connector.execute_query(f"SELECT * FROM {table_name}")
        for row in balances["rows"]:
            print(f"Account: {row['account']}, Balance: ${row['balance']:.2f}")
        
        print("\nPerforming transaction with mixed parameter formats...")
        
        # Test transaction with context manager
        with connector.transaction():
            # Update using positional parameters
            connector.execute_query(
                f"UPDATE {table_name} SET balance = balance - ? WHERE account = ?",
                (200.0, "Account1")
            )
            print("Deducted $200 from Account1 (using positional parameters)")
            
            # Update using named parameters
            connector.execute_query(
                f"UPDATE {table_name} SET balance = balance + :amount WHERE account = :acc",
                {"amount": 200.0, "acc": "Account2"}
            )
            print("Added $200 to Account2 (using named parameters)")
        
        # Show final balances
        print("\nFinal account balances after transaction:")
        balances = connector.execute_query(f"SELECT * FROM {table_name}")
        for row in balances["rows"]:
            print(f"Account: {row['account']}, Balance: ${row['balance']:.2f}")
            
    except Exception as e:
        logger.error(f"Error during transaction tests: {e}")
        raise
        
    finally:
        # Clean up
        if connector.is_connected():
            connector.drop_table(table_name)
            connector.disconnect()
        
        if os.path.exists("test_transactions.db"):
            os.remove("test_transactions.db")
            print("\nTest database removed")

def main():
    """Main function."""
    print_separator("SQLite Parameter Format Handling Tests")
    
    try:
        # Run tests
        test_single_queries()
        test_batch_operations()
        test_transaction_with_mixed_parameters()
        
        print_separator("All Tests Completed Successfully")
            
    except Exception as e:
        logger.error(f"Error during tests: {e}")
        print(f"\nTest failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()