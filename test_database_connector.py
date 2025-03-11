"""
Test script for the database connector plugins.

This script tests the functionality of the database connector plugins,
focusing on SQLite integration, basic CRUD operations, and schema manipulation.

Usage:
    python test_database_connector.py [options]
    
Options:
    --connector CONNECTOR     Database connector to test (default: sqlite)
    --database PATH           Path to database file (SQLite only)
    --operation OPERATION     Specific operation to test
"""

import os
import sys
import argparse
import logging
import json
from datetime import datetime
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_database_connector")

# Import our database connector modules
from ai_document_organizer_v2.core.settings import SettingsManager
from ai_document_organizer_v2.plugins.database.connector_base import DatabaseConnectorPlugin, DatabaseError
from ai_document_organizer_v2.plugins.database.sqlite_connector import SQLiteConnectorPlugin

def print_separator(title: str):
    """Print a separator with a title."""
    width = 80
    print("\n" + "=" * width)
    print(f"{title.center(width)}")
    print("=" * width + "\n")

def print_query_result(result: Dict[str, Any]):
    """Print query result in a formatted way."""
    if not result["success"]:
        print("Query failed!")
        return
    
    print(f"Query executed in {result['execution_time']:.6f} seconds")
    
    if "rows" in result and result["rows"]:
        print(f"Returned {result['row_count']} rows:")
        
        # Print column headers
        if result["column_names"]:
            header = " | ".join(result["column_names"])
            print("-" * len(header))
            print(header)
            print("-" * len(header))
        
        # Print rows
        for row in result["rows"]:
            values = []
            for col in result["column_names"]:
                val = row[col]
                if isinstance(val, (dict, list)):
                    val = json.dumps(val, default=str)
                values.append(str(val))
            
            print(" | ".join(values))
    else:
        if "last_row_id" in result and result["last_row_id"]:
            print(f"Last inserted row ID: {result['last_row_id']}")
        
        if "affected_rows" in result:
            print(f"Affected rows: {result['affected_rows']}")

def test_connection(connector: DatabaseConnectorPlugin):
    """Test connection to the database."""
    print_separator("Testing Database Connection")
    
    try:
        # Connect to the database
        connected = connector.connect()
        
        if connected:
            print("Successfully connected to the database!")
            
            # Check if actually connected
            is_connected = connector.is_connected()
            print(f"Connection status: {'Connected' if is_connected else 'Disconnected'}")
            
            # Get connection information
            connection_string = connector.get_connection_string()
            print(f"Connection string: {connection_string}")
            
            # Get database information
            db_info = connector.get_database_info()
            print("\nDatabase Information:")
            print(f"  Type: {db_info.get('type', 'Unknown')}")
            print(f"  Version: {db_info.get('version', 'Unknown')}")
            
            if 'size' in db_info and db_info['size'] > 0:
                size_mb = db_info['size'] / (1024 * 1024)
                print(f"  Size: {size_mb:.2f} MB")
            
            if 'tables' in db_info:
                print(f"  Tables: {', '.join(db_info['tables']) if db_info['tables'] else 'None'}")
            
            # Disconnect
            print("\nDisconnecting from database...")
            disconnected = connector.disconnect()
            print(f"Disconnection {'successful' if disconnected else 'failed'}")
            
            return True
        else:
            print("Failed to connect to the database!")
            return False
    except DatabaseError as e:
        logger.error(f"Database error: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False

def test_basic_operations(connector: DatabaseConnectorPlugin):
    """Test basic CRUD operations."""
    print_separator("Testing Basic CRUD Operations")
    
    try:
        # Connect to the database
        connector.connect()
        
        # Create a test table
        print("Creating test table...")
        
        table_name = "test_table"
        
        # Drop table if exists
        if connector.table_exists(table_name):
            print(f"Table {table_name} already exists, dropping it...")
            connector.drop_table(table_name)
        
        # Define columns
        columns = {
            "id": {
                "type": "integer",
                "primary_key": True,
                "autoincrement": True,
                "nullable": False
            },
            "name": {
                "type": "text",
                "nullable": False
            },
            "description": {
                "type": "text",
                "nullable": True
            },
            "created_at": {
                "type": "datetime",
                "nullable": False,
                "default": "CURRENT_TIMESTAMP"
            },
            "active": {
                "type": "boolean",
                "nullable": False,
                "default": True
            },
            "score": {
                "type": "float",
                "nullable": True
            }
        }
        
        # Create the table
        created = connector.create_table(table_name, columns)
        print(f"Table creation {'successful' if created else 'failed'}")
        
        # Check if table exists
        exists = connector.table_exists(table_name)
        print(f"Table {table_name} {'exists' if exists else 'does not exist'}")
        
        # Get table schema
        if exists:
            print("\nTable Schema:")
            schema = connector.get_table_schema(table_name)
            
            for col_name, col_info in schema["columns"].items():
                nullable = "NULL" if col_info.get("nullable") else "NOT NULL"
                default = f"DEFAULT {col_info.get('default')}" if col_info.get("default") else ""
                pk = "PRIMARY KEY" if col_info.get("primary_key") else ""
                
                print(f"  {col_name}: {col_info.get('type')} {nullable} {default} {pk}".strip())
        
        # Insert data
        print("\nInserting test data...")
        
        insert_query = f"""
        INSERT INTO {table_name} (name, description, score, active)
        VALUES (?, ?, ?, ?)
        """
        
        test_data = [
            {"name": "Item 1", "description": "This is the first test item", "score": 95.5, "active": True},
            {"name": "Item 2", "description": "This is the second test item", "score": 88.0, "active": True},
            {"name": "Item 3", "description": None, "score": 75.2, "active": False},
            {"name": "Item 4", "description": "This is the fourth test item", "score": None, "active": True},
            {"name": "Item 5", "description": "This is the fifth test item", "score": 50.0, "active": False}
        ]
        
        for i, item in enumerate(test_data):
            params = {
                "1": item["name"],
                "2": item["description"],
                "3": item["score"],
                "4": item["active"]
            }
            
            result = connector.execute_query(insert_query, params)
            print(f"  Inserted item {i+1}, ID: {result.get('last_row_id')}")
        
        # Query data
        print("\nQuerying all data:")
        result = connector.execute_query(f"SELECT * FROM {table_name}")
        print_query_result(result)
        
        # Query with filter
        print("\nQuerying active items with score > 80:")
        result = connector.execute_query(
            f"SELECT * FROM {table_name} WHERE active = ? AND score > ?",
            {"1": True, "2": 80.0}
        )
        print_query_result(result)
        
        # Update data
        print("\nUpdating Item 3...")
        update_result = connector.execute_query(
            f"UPDATE {table_name} SET description = ?, score = ? WHERE name = ?",
            {"1": "Updated description", "2": 78.5, "3": "Item 3"}
        )
        print(f"Updated {update_result.get('affected_rows', 0)} rows")
        
        # Query updated item
        result = connector.execute_query(
            f"SELECT * FROM {table_name} WHERE name = ?",
            {"1": "Item 3"}
        )
        print("\nUpdated item:")
        print_query_result(result)
        
        # Delete data
        print("\nDeleting Item 5...")
        delete_result = connector.execute_query(
            f"DELETE FROM {table_name} WHERE name = ?",
            {"1": "Item 5"}
        )
        print(f"Deleted {delete_result.get('affected_rows', 0)} rows")
        
        # Count remaining items
        count_result = connector.execute_query(f"SELECT COUNT(*) as count FROM {table_name}")
        if count_result["rows"]:
            print(f"Remaining items: {count_result['rows'][0]['count']}")
        
        # Test transactions
        print("\nTesting transactions...")
        
        try:
            # Start transaction
            connector.begin_transaction()
            print("Transaction started")
            
            # Insert a new item
            connector.execute_query(
                f"INSERT INTO {table_name} (name, description, score, active) VALUES (?, ?, ?, ?)",
                {"1": "Transaction Item", "2": "This item was added in a transaction", "3": 99.9, "4": True}
            )
            print("Inserted 'Transaction Item'")
            
            # Update an existing item
            connector.execute_query(
                f"UPDATE {table_name} SET score = score + 5 WHERE name = ?",
                {"1": "Item 1"}
            )
            print("Updated 'Item 1'")
            
            # Commit the transaction
            connector.commit()
            print("Transaction committed")
            
            # Verify changes
            result = connector.execute_query(f"SELECT * FROM {table_name}")
            print("\nAfter transaction:")
            print_query_result(result)
            
            # Test rollback
            print("\nTesting transaction rollback...")
            
            # Start another transaction
            connector.begin_transaction()
            print("Transaction started")
            
            # Delete all items
            connector.execute_query(f"DELETE FROM {table_name}")
            print("Deleted all items (temporary)")
            
            # Verify deletion (inside transaction)
            count_result = connector.execute_query(f"SELECT COUNT(*) as count FROM {table_name}")
            if count_result["rows"]:
                print(f"Items in transaction: {count_result['rows'][0]['count']}")
            
            # Rollback the transaction
            connector.rollback()
            print("Transaction rolled back")
            
            # Verify rollback
            count_result = connector.execute_query(f"SELECT COUNT(*) as count FROM {table_name}")
            if count_result["rows"]:
                print(f"Items after rollback: {count_result['rows'][0]['count']}")
            
            return True
        except DatabaseError as e:
            logger.error(f"Transaction error: {e}")
            connector.rollback()  # Ensure rollback on error
            return False
        finally:
            # Disconnect
            connector.disconnect()
    except DatabaseError as e:
        logger.error(f"Database error: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False

def test_backup_restore(connector: DatabaseConnectorPlugin):
    """Test database backup and restore."""
    print_separator("Testing Backup and Restore")
    
    try:
        # Connect to the database
        connector.connect()
        
        # Create a timestamp for the backup file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"test_backup_{timestamp}.db"
        
        # Create a backup
        print(f"Creating backup to {backup_path}...")
        backup_success = connector.backup_database(backup_path)
        
        if backup_success:
            print("Backup created successfully!")
            
            # Get file size
            if os.path.exists(backup_path):
                size_kb = os.path.getsize(backup_path) / 1024
                print(f"Backup file size: {size_kb:.2f} KB")
            
            # Test restore
            print("\nTesting database restore...")
            restore_success = connector.restore_database(backup_path)
            
            if restore_success:
                print("Database restored successfully!")
            else:
                print("Database restore failed!")
            
            # Clean up
            print("\nCleaning up backup file...")
            os.remove(backup_path)
            print("Backup file removed")
            
            return True
        else:
            print("Failed to create backup!")
            return False
    except Exception as e:
        logger.error(f"Backup/restore error: {e}")
        return False
    finally:
        # Disconnect
        connector.disconnect()

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Test database connector plugins")
    
    # Connector selection
    parser.add_argument('--connector', default='sqlite',
                      choices=['sqlite'],
                      help='Database connector to test')
    
    # Operations
    parser.add_argument('--operation', 
                      choices=['connection', 'basic', 'backup', 'all'],
                      default='all',
                      help='Operation to test')
    
    # SQLite-specific options
    parser.add_argument('--database', default='test_database.db',
                      help='Path to the database file (SQLite only)')
    
    return parser.parse_args()

def create_connector(connector_name: str, args):
    """Create the appropriate connector instance."""
    if connector_name == 'sqlite':
        connector = SQLiteConnectorPlugin({
            "database_path": args.database
        })
    else:
        raise ValueError(f"Unsupported connector: {connector_name}")
    
    # Create settings manager
    settings = SettingsManager()
    connector.settings_manager = settings
    
    # Initialize the connector
    if not connector.initialize():
        raise RuntimeError(f"Failed to initialize {connector_name} connector")
    
    return connector

def main():
    """Main function."""
    args = parse_args()
    
    try:
        # Create the connector
        connector = create_connector(args.connector, args)
        
        print_separator(f"Testing {connector.plugin_name} Database Connector")
        
        # Run the requested operation
        if args.operation == 'connection' or args.operation == 'all':
            test_connection(connector)
        
        if args.operation == 'basic' or args.operation == 'all':
            test_basic_operations(connector)
        
        if args.operation == 'backup' or args.operation == 'all':
            test_backup_restore(connector)
        
        print_separator("Tests Completed Successfully")
        
    except Exception as e:
        logger.error(f"Error running tests: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()