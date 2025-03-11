"""
Test script for the PostgreSQL Database Connector.

This script tests the functionality of the PostgreSQL database connector,
focusing on connection, CRUD operations, and schema manipulation.

Note: This requires a PostgreSQL database to be available. The test will
use environment variables for connection details.
"""

import os
import sys
import logging
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import PostgreSQL connector
from ai_document_organizer_v2.plugins.database.postgresql_connector import PostgreSQLConnectorPlugin

def print_separator(title: str):
    """Print a separator with a title."""
    print("\n" + "=" * 80)
    print(f"{title.center(80)}")
    print("=" * 80 + "\n")

def get_connection_config():
    """Get connection configuration from environment variables."""
    return {
        "host": os.environ.get("PGHOST", "localhost"),
        "port": int(os.environ.get("PGPORT", 5432)),
        "database": os.environ.get("PGDATABASE", "postgres"),
        "user": os.environ.get("PGUSER", "postgres"),
        "password": os.environ.get("PGPASSWORD", ""),
        "schema": "public",
        "connection_pool": True,
        "min_connections": 1,
        "max_connections": 3,
        "use_dict_cursor": True
    }

def test_connection():
    """Test basic connection to PostgreSQL."""
    print_separator("Testing PostgreSQL Connection")
    
    config = get_connection_config()
    print(f"Connecting to PostgreSQL: {config['host']}:{config['port']}/{config['database']} as {config['user']}")
    
    connector = PostgreSQLConnectorPlugin(config)
    
    try:
        connector.initialize()
        connector.connect()
        print("Successfully connected to PostgreSQL!")
        
        print("\nDatabase Information:")
        db_info = connector.get_database_info()
        for key, value in db_info.items():
            print(f"  {key}: {value}")
        
        connector.disconnect()
        print("\nSuccessfully disconnected from PostgreSQL")
        return True
    except Exception as e:
        logger.error(f"Error testing PostgreSQL connection: {e}")
        return False

def test_table_operations():
    """Test table creation, schema, and drop operations."""
    print_separator("Testing Table Operations")
    
    config = get_connection_config()
    connector = PostgreSQLConnectorPlugin(config)
    
    try:
        connector.initialize()
        connector.connect()
        print("Connected to PostgreSQL successfully")
        
        # Create test table
        table_name = "test_table_operations"
        
        # Drop table if it exists from previous tests
        if connector.table_exists(table_name):
            print(f"Table {table_name} exists from previous test, dropping it")
            connector.drop_table(table_name)
        
        # Define columns
        columns = {
            "id": {"type": "serial", "primary_key": True, "autoincrement": True},
            "name": {"type": "varchar", "length": 100, "nullable": False},
            "description": {"type": "text", "nullable": True},
            "created_at": {"type": "timestamp", "default": "CURRENT_TIMESTAMP"},
            "is_active": {"type": "boolean", "default": True},
            "score": {"type": "decimal", "precision": 5, "scale": 2, "default": 0}
        }
        
        print(f"\nCreating table {table_name}...")
        result = connector.create_table(table_name, columns)
        print(f"Table creation result: {result}")
        
        # Check if table exists
        exists = connector.table_exists(table_name)
        print(f"Table {table_name} exists: {exists}")
        
        # Get table schema
        print(f"\nGetting schema for table {table_name}...")
        schema = connector.get_table_schema(table_name)
        
        print("\nTable columns:")
        for col_name, col_info in schema['columns'].items():
            print(f"  {col_name}: {col_info['type']}" + 
                  (", NOT NULL" if not col_info.get('nullable', True) else "") +
                  (f", DEFAULT: {col_info['default']}" if col_info.get('default') else ""))
        
        print("\nPrimary keys:", schema['primary_keys'])
        
        # List all tables
        print("\nAll tables in database:")
        tables = connector.get_tables()
        for table in tables:
            print(f"  {table}")
        
        # Drop the table
        print(f"\nDropping table {table_name}...")
        drop_result = connector.drop_table(table_name)
        print(f"Table drop result: {drop_result}")
        
        # Verify table was dropped
        exists = connector.table_exists(table_name)
        print(f"Table {table_name} exists after drop: {exists}")
        
        connector.disconnect()
        return True
    except Exception as e:
        logger.error(f"Error testing table operations: {e}")
        return False

def test_crud_operations():
    """Test CRUD operations with different parameter formats."""
    print_separator("Testing CRUD Operations")
    
    config = get_connection_config()
    connector = PostgreSQLConnectorPlugin(config)
    
    try:
        connector.initialize()
        connector.connect()
        print("Connected to PostgreSQL successfully")
        
        # Create test table
        table_name = "test_crud_operations"
        
        # Drop table if it exists from previous tests
        if connector.table_exists(table_name):
            print(f"Table {table_name} exists from previous test, dropping it")
            connector.drop_table(table_name)
        
        # Define columns
        columns = {
            "id": {"type": "serial", "primary_key": True, "autoincrement": True},
            "name": {"type": "varchar", "length": 100, "nullable": False},
            "category": {"type": "varchar", "length": 50, "nullable": True},
            "amount": {"type": "decimal", "precision": 10, "scale": 2, "default": 0},
            "is_active": {"type": "boolean", "default": True},
            "created_at": {"type": "timestamp", "default": "CURRENT_TIMESTAMP"}
        }
        
        print(f"\nCreating table {table_name}...")
        connector.create_table(table_name, columns)
        
        # Test INSERT with positional parameters (tuple)
        print("\n1. Testing INSERT with positional parameters (tuple):")
        insert1 = connector.execute_query(
            f"INSERT INTO {table_name} (name, category, amount) VALUES (%s, %s, %s) RETURNING id",
            ("Product A", "Electronics", 99.99)
        )
        print(f"Inserted row with ID: {insert1['rows'][0]['id']}")
        
        # Test INSERT with positional parameters (list)
        print("\n2. Testing INSERT with positional parameters (list):")
        insert2 = connector.execute_query(
            f"INSERT INTO {table_name} (name, category, amount, is_active) VALUES (%s, %s, %s, %s) RETURNING id",
            ["Product B", "Books", 29.99, False]
        )
        print(f"Inserted row with ID: {insert2['rows'][0]['id']}")
        
        # Test INSERT with named parameters (dictionary)
        print("\n3. Testing INSERT with named parameters (dictionary):")
        insert3 = connector.execute_query(
            f"INSERT INTO {table_name} (name, category, amount) VALUES (%(name)s, %(category)s, %(amount)s) RETURNING id",
            {"name": "Product C", "category": "Clothing", "amount": 49.95}
        )
        print(f"Inserted row with ID: {insert3['rows'][0]['id']}")
        
        # Test SELECT with different parameter formats
        print("\nTesting SELECT queries with different parameter formats:")
        
        # Query with positional parameters (tuple)
        print("\n1. SELECT with positional parameters (tuple):")
        select1 = connector.execute_query(
            f"SELECT * FROM {table_name} WHERE category = %s",
            ("Electronics",)
        )
        for row in select1["rows"]:
            print(f"ID: {row['id']}, Name: {row['name']}, Category: {row['category']}, Amount: {row['amount']}")
        
        # Query with positional parameters (list)
        print("\n2. SELECT with positional parameters (list):")
        select2 = connector.execute_query(
            f"SELECT * FROM {table_name} WHERE amount > %s AND is_active = %s",
            [40.0, False]
        )
        for row in select2["rows"]:
            print(f"ID: {row['id']}, Name: {row['name']}, Category: {row['category']}, Amount: {row['amount']}")
        
        # Query with named parameters
        print("\n3. SELECT with named parameters:")
        select3 = connector.execute_query(
            f"SELECT * FROM {table_name} WHERE category = %(cat)s",
            {"cat": "Clothing"}
        )
        for row in select3["rows"]:
            print(f"ID: {row['id']}, Name: {row['name']}, Category: {row['category']}, Amount: {row['amount']}")
        
        # Test UPDATE with different parameter formats
        print("\nTesting UPDATE with different parameter formats:")
        
        # Update with positional parameters
        print("\n1. UPDATE with positional parameters:")
        update1 = connector.execute_query(
            f"UPDATE {table_name} SET amount = %s WHERE name = %s",
            (129.99, "Product A")
        )
        print(f"Rows affected: {update1['affected_rows']}")
        
        # Update with named parameters
        print("\n2. UPDATE with named parameters:")
        update2 = connector.execute_query(
            f"UPDATE {table_name} SET amount = %(amount)s, is_active = %(active)s WHERE category = %(cat)s",
            {"amount": 19.99, "active": True, "cat": "Books"}
        )
        print(f"Rows affected: {update2['affected_rows']}")
        
        # Query all data
        print("\nAll data after updates:")
        all_data = connector.execute_query(f"SELECT * FROM {table_name}")
        for row in all_data["rows"]:
            print(f"ID: {row['id']}, Name: {row['name']}, Category: {row['category']}, "
                  f"Amount: {row['amount']}, Active: {row['is_active']}")
        
        # Test DELETE with different parameter formats
        print("\nTesting DELETE with different parameter formats:")
        
        # Delete with positional parameters
        print("\n1. DELETE with positional parameters:")
        delete1 = connector.execute_query(
            f"DELETE FROM {table_name} WHERE name = %s",
            ("Product C",)
        )
        print(f"Rows affected: {delete1['affected_rows']}")
        
        # Delete with named parameters
        print("\n2. DELETE with named parameters:")
        delete2 = connector.execute_query(
            f"DELETE FROM {table_name} WHERE amount > %(min_amount)s",
            {"min_amount": 100.0}
        )
        print(f"Rows affected: {delete2['affected_rows']}")
        
        # Query all data after deletes
        print("\nAll data after deletes:")
        all_data = connector.execute_query(f"SELECT * FROM {table_name}")
        for row in all_data["rows"]:
            print(f"ID: {row['id']}, Name: {row['name']}, Category: {row['category']}, "
                  f"Amount: {row['amount']}, Active: {row['is_active']}")
        
        # Drop the table
        connector.drop_table(table_name)
        connector.disconnect()
        return True
    except Exception as e:
        logger.error(f"Error testing CRUD operations: {e}")
        return False

def test_batch_operations():
    """Test batch operations with different parameter formats."""
    print_separator("Testing Batch Operations")
    
    config = get_connection_config()
    connector = PostgreSQLConnectorPlugin(config)
    
    try:
        connector.initialize()
        connector.connect()
        print("Connected to PostgreSQL successfully")
        
        # Create test table
        table_name = "test_batch_operations"
        
        # Drop table if it exists from previous tests
        if connector.table_exists(table_name):
            print(f"Table {table_name} exists from previous test, dropping it")
            connector.drop_table(table_name)
        
        # Define columns
        columns = {
            "id": {"type": "serial", "primary_key": True, "autoincrement": True},
            "product_name": {"type": "varchar", "length": 100, "nullable": False},
            "category": {"type": "varchar", "length": 50, "nullable": True},
            "price": {"type": "decimal", "precision": 10, "scale": 2, "default": 0},
            "in_stock": {"type": "boolean", "default": True},
            "created_at": {"type": "timestamp", "default": "CURRENT_TIMESTAMP"}
        }
        
        print(f"\nCreating table {table_name}...")
        connector.create_table(table_name, columns)
        
        # Prepare batch queries and parameters with mixed formats
        queries = [
            f"INSERT INTO {table_name} (product_name, category, price, in_stock) VALUES (%s, %s, %s, %s) RETURNING id",
            f"INSERT INTO {table_name} (product_name, category, price, in_stock) VALUES (%s, %s, %s, %s) RETURNING id",
            f"INSERT INTO {table_name} (product_name, category, price, in_stock) VALUES (%(name)s, %(category)s, %(price)s, %(in_stock)s) RETURNING id",
            f"UPDATE {table_name} SET price = %s WHERE product_name = %s",
            f"UPDATE {table_name} SET in_stock = %(status)s WHERE category = %(cat)s"
        ]
        
        params_list = [
            ("Laptop", "Electronics", 1299.99, True),  # Tuple params
            ["Book", "Media", 24.95, True],         # List params
            {"name": "T-shirt", "category": "Clothing", "price": 19.95, "in_stock": False},  # Dict params
            (1499.99, "Laptop"),  # Tuple params for UPDATE
            {"status": False, "cat": "Media"}   # Dict params for UPDATE
        ]
        
        print("\nExecuting batch operations with mixed parameter formats...")
        results = connector.execute_batch(queries, params_list)
        
        for i, result in enumerate(results):
            print(f"\nBatch operation {i+1}:")
            print(f"Success: {result['success']}")
            
            if 'rows' in result and result['rows']:
                print(f"Rows: {result['rows']}")
                
            print(f"Affected rows: {result['affected_rows']}")
            
            if result.get('last_row_id'):
                print(f"Last row ID: {result['last_row_id']}")
                
            print(f"Execution time: {result['execution_time']:.6f} seconds")
        
        # Query all data
        print("\nAll data in the table after batch operations:")
        all_data = connector.execute_query(f"SELECT * FROM {table_name}")
        for row in all_data["rows"]:
            print(f"ID: {row['id']}, Name: {row['product_name']}, Category: {row['category']}, "
                  f"Price: {row['price']}, In Stock: {row['in_stock']}")
        
        # Drop the table
        connector.drop_table(table_name)
        connector.disconnect()
        return True
    except Exception as e:
        logger.error(f"Error testing batch operations: {e}")
        return False

def test_transaction_operations():
    """Test transaction operations."""
    print_separator("Testing Transaction Operations")
    
    config = get_connection_config()
    connector = PostgreSQLConnectorPlugin(config)
    
    try:
        connector.initialize()
        connector.connect()
        print("Connected to PostgreSQL successfully")
        
        # Create test table
        table_name = "test_transactions"
        
        # Drop table if it exists from previous tests
        if connector.table_exists(table_name):
            print(f"Table {table_name} exists from previous test, dropping it")
            connector.drop_table(table_name)
        
        # Define columns
        columns = {
            "id": {"type": "serial", "primary_key": True, "autoincrement": True},
            "account": {"type": "varchar", "length": 50, "nullable": False},
            "balance": {"type": "decimal", "precision": 10, "scale": 2, "default": 0},
            "updated_at": {"type": "timestamp", "default": "CURRENT_TIMESTAMP"}
        }
        
        print(f"\nCreating table {table_name}...")
        connector.create_table(table_name, columns)
        
        # Insert initial data
        print("\nInserting initial data...")
        connector.execute_query(
            f"INSERT INTO {table_name} (account, balance) VALUES (%s, %s), (%s, %s)",
            ("Account1", 1000.0, "Account2", 500.0)
        )
        
        # Show initial balances
        print("\nInitial account balances:")
        balances = connector.execute_query(f"SELECT * FROM {table_name}")
        for row in balances["rows"]:
            print(f"Account: {row['account']}, Balance: ${row['balance']:.2f}")
        
        print("\nTesting successful transaction...")
        
        # Test successful transaction
        connector.begin_transaction()
        print("Transaction started")
        
        # Update first account balance
        connector.execute_query(
            f"UPDATE {table_name} SET balance = balance - %s, updated_at = CURRENT_TIMESTAMP WHERE account = %s",
            (200.0, "Account1")
        )
        print("Deducted $200 from Account1")
        
        # Update second account balance
        connector.execute_query(
            f"UPDATE {table_name} SET balance = balance + %s, updated_at = CURRENT_TIMESTAMP WHERE account = %s",
            (200.0, "Account2")
        )
        print("Added $200 to Account2")
        
        # Commit the transaction
        connector.commit()
        print("Transaction committed")
        
        # Show balances after transaction
        print("\nBalances after successful transaction:")
        balances = connector.execute_query(f"SELECT * FROM {table_name}")
        for row in balances["rows"]:
            print(f"Account: {row['account']}, Balance: ${row['balance']:.2f}, Updated: {row['updated_at']}")
        
        print("\nTesting transaction rollback...")
        
        # Test transaction rollback
        connector.begin_transaction()
        print("Transaction started")
        
        # Update first account balance
        connector.execute_query(
            f"UPDATE {table_name} SET balance = balance - %s, updated_at = CURRENT_TIMESTAMP WHERE account = %s",
            (1000.0, "Account1")
        )
        print("Deducted $1000 from Account1")
        
        # Check balance during transaction
        during_tx = connector.execute_query(f"SELECT * FROM {table_name} WHERE account = %s", ("Account1",))
        print(f"Account1 balance during transaction: ${during_tx['rows'][0]['balance']:.2f}")
        
        # Rollback the transaction
        connector.rollback()
        print("Transaction rolled back")
        
        # Show balances after rollback
        print("\nBalances after rollback:")
        balances = connector.execute_query(f"SELECT * FROM {table_name}")
        for row in balances["rows"]:
            print(f"Account: {row['account']}, Balance: ${row['balance']:.2f}, Updated: {row['updated_at']}")
        
        print("\nTesting transaction with context manager...")
        
        # Test transaction with context manager
        with connector.transaction():
            print("Transaction started with context manager")
            
            # Update first account balance
            connector.execute_query(
                f"UPDATE {table_name} SET balance = balance - %s, updated_at = CURRENT_TIMESTAMP WHERE account = %s",
                (100.0, "Account1")
            )
            print("Deducted $100 from Account1")
            
            # Update second account balance
            connector.execute_query(
                f"UPDATE {table_name} SET balance = balance + %s, updated_at = CURRENT_TIMESTAMP WHERE account = %s",
                (100.0, "Account2")
            )
            print("Added $100 to Account2")
            
            print("Exiting context manager (should auto-commit)")
        
        # Show balances after context manager transaction
        print("\nBalances after context manager transaction:")
        balances = connector.execute_query(f"SELECT * FROM {table_name}")
        for row in balances["rows"]:
            print(f"Account: {row['account']}, Balance: ${row['balance']:.2f}, Updated: {row['updated_at']}")
        
        print("\nTesting context manager with exception (should rollback)...")
        
        try:
            with connector.transaction():
                print("Transaction started with context manager")
                
                # Update first account balance
                connector.execute_query(
                    f"UPDATE {table_name} SET balance = balance - %s, updated_at = CURRENT_TIMESTAMP WHERE account = %s",
                    (50.0, "Account1")
                )
                print("Deducted $50 from Account1")
                
                # Simulate error
                print("Simulating error during transaction...")
                raise ValueError("Simulated error to test rollback")
                
                # This should not execute
                connector.execute_query(
                    f"UPDATE {table_name} SET balance = balance + %s, updated_at = CURRENT_TIMESTAMP WHERE account = %s",
                    (50.0, "Account2")
                )
        except ValueError as e:
            print(f"Caught exception: {e}")
            print("Exiting context manager with exception (should auto-rollback)")
        
        # Show balances after failed transaction
        print("\nBalances after failed transaction (should be unchanged from previous check):")
        balances = connector.execute_query(f"SELECT * FROM {table_name}")
        for row in balances["rows"]:
            print(f"Account: {row['account']}, Balance: ${row['balance']:.2f}, Updated: {row['updated_at']}")
        
        # Drop the table
        connector.drop_table(table_name)
        connector.disconnect()
        return True
    except Exception as e:
        logger.error(f"Error testing transaction operations: {e}")
        return False

def test_backup_restore():
    """Test database backup and restore functionality."""
    print_separator("Testing Backup and Restore")
    
    config = get_connection_config()
    connector = PostgreSQLConnectorPlugin(config)
    backup_file = "test_pg_backup.sql"
    
    try:
        connector.initialize()
        connector.connect()
        print("Connected to PostgreSQL successfully")
        
        # Create test table
        table_name = "test_backup_restore"
        
        # Drop table if it exists from previous tests
        if connector.table_exists(table_name):
            print(f"Table {table_name} exists from previous test, dropping it")
            connector.drop_table(table_name)
        
        # Define columns
        columns = {
            "id": {"type": "serial", "primary_key": True, "autoincrement": True},
            "name": {"type": "varchar", "length": 100, "nullable": False},
            "data": {"type": "jsonb", "nullable": True},
            "created_at": {"type": "timestamp", "default": "CURRENT_TIMESTAMP"}
        }
        
        print(f"\nCreating table {table_name}...")
        connector.create_table(table_name, columns)
        
        # Insert test data
        print("\nInserting test data...")
        for i in range(5):
            data = {
                "value": i * 10,
                "tags": [f"tag{i}", f"category{i%3}"],
                "metadata": {
                    "source": "test",
                    "priority": i % 3 + 1
                }
            }
            
            connector.execute_query(
                f"INSERT INTO {table_name} (name, data) VALUES (%s, %s::jsonb)",
                (f"Item {i+1}", json.dumps(data))
            )
        
        # Query data before backup
        print("\nData before backup:")
        original_data = connector.execute_query(f"SELECT * FROM {table_name}")
        for row in original_data["rows"]:
            print(f"ID: {row['id']}, Name: {row['name']}, Data: {row['data']}")
        
        # Create backup (only for this specific table)
        print(f"\nCreating backup to {backup_file}...")
        backup_result = connector.backup_database(backup_file, tables=[table_name])
        print(f"Backup result: {backup_result}")
        
        # Drop the table
        print(f"\nDropping table {table_name} to test restore...")
        connector.drop_table(table_name)
        
        table_exists = connector.table_exists(table_name)
        print(f"Table exists after drop: {table_exists}")
        
        # Restore from backup
        print(f"\nRestoring from backup {backup_file}...")
        restore_result = connector.restore_database(backup_file)
        print(f"Restore result: {restore_result}")
        
        # Check if table was restored
        table_exists = connector.table_exists(table_name)
        print(f"Table exists after restore: {table_exists}")
        
        if table_exists:
            # Query data after restore
            print("\nData after restore:")
            restored_data = connector.execute_query(f"SELECT * FROM {table_name}")
            for row in restored_data["rows"]:
                print(f"ID: {row['id']}, Name: {row['name']}, Data: {row['data']}")
            
            # Compare row count
            print(f"\nOriginal row count: {len(original_data['rows'])}")
            print(f"Restored row count: {len(restored_data['rows'])}")
        
        # Clean up
        connector.drop_table(table_name)
        connector.disconnect()
        
        # Remove backup file
        if os.path.exists(backup_file):
            os.remove(backup_file)
            print(f"\nRemoved backup file: {backup_file}")
        
        return True
    except Exception as e:
        logger.error(f"Error testing backup and restore: {e}")
        
        # Clean up
        if os.path.exists(backup_file):
            os.remove(backup_file)
        
        return False

def main():
    """Main entry point for the test script."""
    print_separator("PostgreSQL Connector Tests")
    
    # Check if required environment variables are set
    if not os.environ.get("PGHOST") or not os.environ.get("PGDATABASE"):
        logger.error("PostgreSQL environment variables (PGHOST, PGDATABASE, etc.) are not set.")
        logger.info("Please set the following environment variables:")
        logger.info("  PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD")
        sys.exit(1)
    
    # Run tests
    tests = [
        ("Connection Test", test_connection),
        ("Table Operations Test", test_table_operations),
        ("CRUD Operations Test", test_crud_operations),
        ("Batch Operations Test", test_batch_operations),
        ("Transaction Operations Test", test_transaction_operations),
        ("Backup and Restore Test", test_backup_restore)
    ]
    
    overall_result = True
    
    for test_name, test_func in tests:
        print(f"\nRunning {test_name}...")
        try:
            test_result = test_func()
            if test_result:
                print(f"{test_name} PASSED")
            else:
                print(f"{test_name} FAILED")
                overall_result = False
        except Exception as e:
            logger.error(f"Exception in {test_name}: {e}")
            print(f"{test_name} FAILED with exception")
            overall_result = False
    
    print_separator("Test Results")
    if overall_result:
        print("All tests PASSED!")
    else:
        print("Some tests FAILED. Check the logs for details.")
    
    return 0 if overall_result else 1

if __name__ == "__main__":
    sys.exit(main())