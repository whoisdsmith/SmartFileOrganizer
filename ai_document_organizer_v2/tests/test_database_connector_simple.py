"""
Simple test script for SQLite database connector.
"""

import os
import sys
import logging
import sqlite3

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_database_simple")

# Import our database connector modules
from ai_document_organizer_v2.core.settings import SettingsManager
from ai_document_organizer_v2.plugins.database.sqlite_connector import SQLiteConnectorPlugin

def print_separator(title: str):
    """Print a separator with a title."""
    width = 80
    print("\n" + "=" * width)
    print(f"{title.center(width)}")
    print("=" * width + "\n")

def main():
    """Main function."""
    try:
        print_separator("Testing SQLite Database Connector")
        
        # Create settings manager
        settings = SettingsManager()
        
        # Create connector
        connector = SQLiteConnectorPlugin({
            "database_path": "test_database.db"
        })
        
        # Set settings manager
        connector.settings_manager = settings
        
        # Initialize connector
        if not connector.initialize():
            raise RuntimeError("Failed to initialize SQLite connector")
        
        # Test connection
        print("Testing database connection...")
        if connector.connect():
            print("Successfully connected to the database!")
        else:
            print("Failed to connect to the database!")
            return
        
        # Test creating a table
        print("\nCreating test table...")
        
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
        connector.create_table(table_name, columns)
        print("Table created successfully!")
        
        # Test inserting data with different parameter formats
        print("\nInserting test data with different parameter formats...")
        
        # Using positional parameters with tuple
        print("\n1. Using positional parameters with tuple:")
        result = connector.execute_query(
            f"INSERT INTO {table_name} (name, description, score) VALUES (?, ?, ?)",
            ("Item 1", "Test item 1", 95.5)
        )
        print(f"Inserted item with ID: {result.get('last_row_id')}")
        
        # Using positional parameters with list
        print("\n2. Using positional parameters with list:")
        result = connector.execute_query(
            f"INSERT INTO {table_name} (name, description, score) VALUES (?, ?, ?)",
            ["Item 2", "Test item 2", 88.0]
        )
        print(f"Inserted item with ID: {result.get('last_row_id')}")
        
        # Using named parameters with dictionary
        print("\n3. Using named parameters with dictionary:")
        result = connector.execute_query(
            f"INSERT INTO {table_name} (name, description, score) VALUES (:name, :description, :score)",
            {"name": "Item 3", "description": None, "score": 75.2}
        )
        print(f"Inserted item with ID: {result.get('last_row_id')}")
        
        # Test querying data with different parameter formats
        print("\nQuerying data with different parameter formats:")
        
        # Query with positional parameters (tuple)
        print("\n1. Querying with positional parameters (tuple):")
        result1 = connector.execute_query(
            f"SELECT * FROM {table_name} WHERE name = ?",
            ("Item 1",)
        )
        for row in result1["rows"]:
            print(f"ID: {row['id']}, Name: {row['name']}, Score: {row['score']}")
        
        # Query with positional parameters (list)
        print("\n2. Querying with positional parameters (list):")
        result2 = connector.execute_query(
            f"SELECT * FROM {table_name} WHERE name = ?",
            ["Item 2"]
        )
        for row in result2["rows"]:
            print(f"ID: {row['id']}, Name: {row['name']}, Score: {row['score']}")
        
        # Query with named parameters
        print("\n3. Querying with named parameters:")
        result3 = connector.execute_query(
            f"SELECT * FROM {table_name} WHERE name = :name",
            {"name": "Item 3"}
        )
        for row in result3["rows"]:
            print(f"ID: {row['id']}, Name: {row['name']}, Score: {row['score']}")
        
        # Query all data
        print("\nQuerying all data:")
        result = connector.execute_query(f"SELECT * FROM {table_name}")
        
        for row in result["rows"]:
            print(f"ID: {row['id']}, Name: {row['name']}, Score: {row['score']}")
        
        # Clean up
        print("\nCleaning up...")
        connector.drop_table(table_name)
        connector.disconnect()
        
        # Remove test database file
        if os.path.exists("test_database.db"):
            os.remove("test_database.db")
            print("Test database file removed")
        
        print_separator("Tests Completed Successfully")
        
    except Exception as e:
        logger.error(f"Error running tests: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()