"""
SQLite Database Connector for AI Document Organizer V2.

This module implements a database connector for SQLite, providing
a lightweight, file-based database solution.
"""

import os
import sqlite3
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Union

from ai_document_organizer_v2.plugins.database.connector_base import (
    DatabaseConnectorPlugin,
    ConnectionError,
    QueryError,
    TransactionError,
    SchemaError
)

logger = logging.getLogger(__name__)

class SQLiteConnectorPlugin(DatabaseConnectorPlugin):
    """
    SQLite database connector implementation.
    
    This plugin provides database operations for SQLite, a lightweight,
    file-based SQL database that's ideal for single-user applications.
    """
    
    plugin_name = "sqlite_connector"
    plugin_description = "SQLite database connector for local file-based database operations"
    plugin_version = "1.0.0"
    
    # SQLite type mapping
    _TYPE_MAPPING = {
        "text": "TEXT",
        "string": "TEXT",
        "integer": "INTEGER",
        "int": "INTEGER",
        "float": "REAL",
        "real": "REAL",
        "double": "REAL",
        "boolean": "INTEGER",  # SQLite doesn't have a boolean type
        "bool": "INTEGER",
        "datetime": "TEXT",    # Store as ISO format string
        "date": "TEXT",
        "time": "TEXT",
        "blob": "BLOB",
        "binary": "BLOB",
        "json": "TEXT"         # Store JSON as a string
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the SQLite connector plugin.
        
        Args:
            config: Optional configuration dictionary
        """
        super().__init__(config)
        
        # Set SQLite-specific defaults
        self.config.setdefault("database_path", ":memory:")  # In-memory database by default
        self.config.setdefault("timeout", 5.0)  # Connection timeout in seconds
        self.config.setdefault("detect_types", sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
        self.config.setdefault("isolation_level", None)  # Autocommit mode by default
        self.config.setdefault("check_same_thread", True)
        self.config.setdefault("uri", False)
        self.config.setdefault("create_db_dir", True)
        
        # Initialize connection and cursor
        self._connection = None
        self._cursor = None
    
    def initialize(self) -> bool:
        """
        Initialize the SQLite connector.
        
        Returns:
            True if initialization was successful, False otherwise
        """
        try:
            # Create database directory if it doesn't exist and not using memory
            db_path = self.config["database_path"]
            if db_path != ":memory:" and self.config["create_db_dir"]:
                db_dir = os.path.dirname(db_path)
                if db_dir and not os.path.exists(db_dir):
                    os.makedirs(db_dir, exist_ok=True)
            
            return True
        except Exception as e:
            logger.error(f"Failed to initialize SQLite connector: {e}")
            return False
    
    def connect(self) -> bool:
        """
        Connect to the SQLite database.
        
        Returns:
            True if connection was successful, False otherwise
            
        Raises:
            ConnectionError: If connection fails
        """
        try:
            # Close any existing connection
            if self._connection:
                self.disconnect()
            
            # Extract connection parameters
            db_path = self.config["database_path"]
            timeout = self.config["timeout"]
            detect_types = self.config["detect_types"]
            isolation_level = self.config["isolation_level"]
            check_same_thread = self.config["check_same_thread"]
            uri = self.config["uri"]
            
            # Connect to the database
            self._connection = sqlite3.connect(
                database=db_path,
                timeout=timeout,
                detect_types=detect_types,
                isolation_level=isolation_level,
                check_same_thread=check_same_thread,
                uri=uri
            )
            
            # Enable foreign keys
            self._connection.execute("PRAGMA foreign_keys = ON")
            
            # Configure connection
            self._connection.row_factory = sqlite3.Row
            
            # Create cursor
            self._cursor = self._connection.cursor()
            
            self._connected = True
            return True
        except Exception as e:
            self._connected = False
            logger.error(f"Failed to connect to SQLite database: {e}")
            raise ConnectionError(f"Failed to connect to SQLite database: {e}")
    
    def disconnect(self) -> bool:
        """
        Disconnect from the SQLite database.
        
        Returns:
            True if disconnection was successful, False otherwise
        """
        try:
            if self._connection:
                if self._cursor:
                    self._cursor.close()
                self._connection.close()
                self._connection = None
                self._cursor = None
                self._connected = False
            return True
        except Exception as e:
            logger.error(f"Error disconnecting from SQLite database: {e}")
            return False
    
    def is_connected(self) -> bool:
        """
        Check if the connection to the database is active.
        
        Returns:
            True if connected, False otherwise
        """
        if not self._connection:
            return False
        
        try:
            # Execute a simple query to check connection
            self._cursor.execute("SELECT 1")
            return True
        except Exception:
            return False
    
    def execute_query(self, query: str, params: Optional[Union[Dict[str, Any], List[Any], Tuple[Any, ...]]] = None) -> Dict[str, Any]:
        """
        Execute a query on the database.
        
        Args:
            query: SQL query string
            params: Optional parameters for the query. Can be a dictionary with named parameters
                   or a tuple/list with positional parameters.
            
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
            # Execute the query
            if params:
                # Convert dictionary parameters to the format SQLite expects
                # SQLite can handle both tuples for positional params and dicts for named params
                self._cursor.execute(query, params)
            else:
                self._cursor.execute(query)
            
            # Get column names
            if self._cursor.description:
                result["column_names"] = [col[0] for col in self._cursor.description]
            
            # Fetch results if there are any
            if query.strip().upper().startswith(("SELECT", "PRAGMA", "EXPLAIN")):
                rows = self._cursor.fetchall()
                # Convert to list of dicts
                result["rows"] = [dict(row) for row in rows]
                result["row_count"] = len(result["rows"])
            else:
                # For non-SELECT queries
                result["affected_rows"] = self._cursor.rowcount
                result["last_row_id"] = self._cursor.lastrowid
            
            result["success"] = True
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            logger.debug(f"Query: {query}")
            logger.debug(f"Params: {params}")
            raise QueryError(f"Query execution failed: {e}")
        finally:
            result["execution_time"] = time.time() - start_time
            
        return result
    
    def execute_batch(self, queries: List[str], params_list: Optional[List[Union[Dict[str, Any], List[Any], Tuple[Any, ...]]]] = None) -> List[Dict[str, Any]]:
        """
        Execute multiple queries in batch mode.
        
        Args:
            queries: List of SQL query strings
            params_list: Optional list of parameters for each query (can be dictionaries for named parameters,
                        or tuples/lists for positional parameters)
            
        Returns:
            List of dictionaries containing query results and metadata
            
        Raises:
            QueryError: If batch execution fails
        """
        if not self.is_connected():
            self.connect()
        
        results = []
        
        # Use transaction for batch execution
        with self.transaction():
            for i, query in enumerate(queries):
                params = None
                if params_list and i < len(params_list):
                    params = params_list[i]
                
                result = self.execute_query(query, params)
                results.append(result)
                
        return results
    
    def begin_transaction(self) -> bool:
        """
        Begin a database transaction.
        
        Returns:
            True if transaction was successfully started, False otherwise
            
        Raises:
            TransactionError: If transaction cannot be started
        """
        if not self.is_connected():
            self.connect()
        
        try:
            if not self._in_transaction:
                self._connection.execute("BEGIN")
                self._in_transaction = True
            return True
        except Exception as e:
            logger.error(f"Failed to begin transaction: {e}")
            raise TransactionError(f"Failed to begin transaction: {e}")
    
    def commit(self) -> bool:
        """
        Commit the current transaction.
        
        Returns:
            True if transaction was successfully committed, False otherwise
            
        Raises:
            TransactionError: If commit fails
        """
        if not self.is_connected():
            return False
        
        try:
            if self._in_transaction:
                self._connection.commit()
                self._in_transaction = False
            return True
        except Exception as e:
            logger.error(f"Failed to commit transaction: {e}")
            raise TransactionError(f"Failed to commit transaction: {e}")
    
    def rollback(self) -> bool:
        """
        Rollback the current transaction.
        
        Returns:
            True if transaction was successfully rolled back, False otherwise
            
        Raises:
            TransactionError: If rollback fails
        """
        if not self.is_connected():
            return False
        
        try:
            if self._in_transaction:
                self._connection.rollback()
                self._in_transaction = False
            return True
        except Exception as e:
            logger.error(f"Failed to rollback transaction: {e}")
            raise TransactionError(f"Failed to rollback transaction: {e}")
    
    def get_tables(self) -> List[str]:
        """
        Get a list of all tables in the database.
        
        Returns:
            List of table names
        """
        result = self.execute_query("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        return [row['name'] for row in result['rows']]
    
    def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """
        Get the schema information for a table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            Dictionary containing table schema information
            
        Raises:
            SchemaError: If schema information cannot be retrieved
        """
        try:
            # Get table info
            result = self.execute_query(f"PRAGMA table_info({table_name})")
            
            if not result['rows']:
                raise SchemaError(f"Table not found: {table_name}")
            
            columns = {}
            primary_keys = []
            
            for col in result['rows']:
                column_info = {
                    "type": col['type'],
                    "nullable": not col['notnull'],
                    "default": col['dflt_value'],
                    "primary_key": bool(col['pk'])
                }
                
                if col['pk']:
                    primary_keys.append(col['name'])
                
                columns[col['name']] = column_info
            
            # Get foreign keys
            fk_result = self.execute_query(f"PRAGMA foreign_key_list({table_name})")
            foreign_keys = []
            
            for fk in fk_result['rows']:
                foreign_keys.append({
                    "column": fk['from'],
                    "references": {
                        "table": fk['table'],
                        "column": fk['to']
                    },
                    "on_update": fk['on_update'],
                    "on_delete": fk['on_delete']
                })
            
            # Get index information
            index_result = self.execute_query(
                "SELECT name, sql FROM sqlite_master WHERE type='index' AND tbl_name=?",
                (table_name,)
            )
            
            indexes = {}
            for idx in index_result['rows']:
                indexes[idx['name']] = {
                    "sql": idx['sql']
                }
            
            # Construct schema information
            schema = {
                "table_name": table_name,
                "columns": columns,
                "primary_keys": primary_keys,
                "foreign_keys": foreign_keys,
                "indexes": indexes
            }
            
            return schema
        except Exception as e:
            if not isinstance(e, SchemaError):
                logger.error(f"Failed to get schema for table {table_name}: {e}")
                raise SchemaError(f"Failed to get schema for table {table_name}: {e}")
            raise
    
    def table_exists(self, table_name: str) -> bool:
        """
        Check if a table exists in the database.
        
        Args:
            table_name: Name of the table
            
        Returns:
            True if table exists, False otherwise
        """
        result = self.execute_query(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,)
        )
        return len(result['rows']) > 0
    
    def create_table(self, table_name: str, columns: Dict[str, Dict[str, Any]], 
                    if_not_exists: bool = True) -> bool:
        """
        Create a new table in the database.
        
        Args:
            table_name: Name of the table to create
            columns: Dictionary mapping column names to their definitions
            if_not_exists: If True, use IF NOT EXISTS clause
            
        Returns:
            True if table was created successfully, False otherwise
            
        Raises:
            SchemaError: If table creation fails
        """
        try:
            # Construct column definitions
            column_defs = []
            
            for col_name, col_def in columns.items():
                # Get type (convert to SQLite type)
                col_type = col_def.get('type', 'TEXT').lower()
                sqlite_type = self._TYPE_MAPPING.get(col_type, 'TEXT')
                
                # Build column definition
                col_str = f"{col_name} {sqlite_type}"
                
                # Add constraints
                if col_def.get('primary_key'):
                    col_str += " PRIMARY KEY"
                    
                    if col_def.get('autoincrement') and sqlite_type == 'INTEGER':
                        col_str += " AUTOINCREMENT"
                
                if not col_def.get('nullable', True):
                    col_str += " NOT NULL"
                
                if 'default' in col_def:
                    default_val = col_def['default']
                    if isinstance(default_val, str):
                        col_str += f" DEFAULT '{default_val}'"
                    elif default_val is None:
                        col_str += " DEFAULT NULL"
                    else:
                        col_str += f" DEFAULT {default_val}"
                
                if col_def.get('unique'):
                    col_str += " UNIQUE"
                
                column_defs.append(col_str)
            
            # Add primary key constraint if multi-column
            primary_keys = [col_name for col_name, col_def in columns.items() 
                           if col_def.get('primary_key') and not col_def.get('autoincrement')]
            
            if len(primary_keys) > 1:
                pk_constraint = f"PRIMARY KEY ({', '.join(primary_keys)})"
                column_defs.append(pk_constraint)
            
            # Add foreign key constraints
            for col_name, col_def in columns.items():
                if 'references' in col_def:
                    ref = col_def['references']
                    fk_constraint = f"FOREIGN KEY ({col_name}) REFERENCES {ref['table']}({ref['column']})"
                    
                    # Add ON DELETE/UPDATE actions if specified
                    if 'on_delete' in col_def:
                        fk_constraint += f" ON DELETE {col_def['on_delete']}"
                    
                    if 'on_update' in col_def:
                        fk_constraint += f" ON UPDATE {col_def['on_update']}"
                    
                    column_defs.append(fk_constraint)
            
            # Build CREATE TABLE statement
            exists_clause = "IF NOT EXISTS " if if_not_exists else ""
            query = f"CREATE TABLE {exists_clause}{table_name} (\n  "
            query += ",\n  ".join(column_defs)
            query += "\n)"
            
            # Execute the statement
            self.execute_query(query)
            
            return True
        except Exception as e:
            logger.error(f"Failed to create table {table_name}: {e}")
            raise SchemaError(f"Failed to create table {table_name}: {e}")
    
    def drop_table(self, table_name: str, if_exists: bool = True) -> bool:
        """
        Drop a table from the database.
        
        Args:
            table_name: Name of the table to drop
            if_exists: If True, use IF EXISTS clause
            
        Returns:
            True if table was dropped successfully, False otherwise
            
        Raises:
            SchemaError: If table drop fails
        """
        try:
            exists_clause = "IF EXISTS " if if_exists else ""
            query = f"DROP TABLE {exists_clause}{table_name}"
            
            # Execute the statement
            self.execute_query(query)
            
            return True
        except Exception as e:
            logger.error(f"Failed to drop table {table_name}: {e}")
            raise SchemaError(f"Failed to drop table {table_name}: {e}")
    
    def get_database_info(self) -> Dict[str, Any]:
        """
        Get information about the database.
        
        Returns:
            Dictionary containing database information (version, type, size, etc.)
        """
        info = {
            "type": "SQLite",
            "version": None,
            "file_path": self.config["database_path"],
            "size": 0,
            "page_size": 0,
            "page_count": 0,
            "tables": [],
            "in_memory": self.config["database_path"] == ":memory:"
        }
        
        try:
            # Get SQLite version
            version_result = self.execute_query("SELECT sqlite_version()")
            if version_result['rows']:
                info["version"] = version_result['rows'][0]['sqlite_version()']
            
            # Get database statistics
            if not info["in_memory"]:
                try:
                    file_size = os.path.getsize(self.config["database_path"])
                    info["size"] = file_size
                except OSError:
                    pass
            
            # Get page information
            page_result = self.execute_query("PRAGMA page_size")
            if page_result['rows']:
                info["page_size"] = page_result['rows'][0]['page_size']
            
            page_count_result = self.execute_query("PRAGMA page_count")
            if page_count_result['rows']:
                info["page_count"] = page_count_result['rows'][0]['page_count']
            
            # Get tables
            info["tables"] = self.get_tables()
            
            return info
        except Exception as e:
            logger.error(f"Failed to get database info: {e}")
            return info
    
    def backup_database(self, backup_path: str) -> bool:
        """
        Create a backup of the database.
        
        Args:
            backup_path: Path to save the backup file
            
        Returns:
            True if backup was successful, False otherwise
        """
        if self.config["database_path"] == ":memory:":
            logger.warning("Cannot backup in-memory database to a file")
            return False
        
        try:
            # Create backup directory if it doesn't exist
            backup_dir = os.path.dirname(backup_path)
            if backup_dir and not os.path.exists(backup_dir):
                os.makedirs(backup_dir, exist_ok=True)
            
            # Connect to the backup database
            backup_conn = sqlite3.connect(backup_path)
            
            # Perform backup
            with backup_conn:
                self._connection.backup(backup_conn)
            
            backup_conn.close()
            return True
        except Exception as e:
            logger.error(f"Failed to create database backup: {e}")
            return False
    
    def restore_database(self, backup_path: str) -> bool:
        """
        Restore the database from a backup.
        
        Args:
            backup_path: Path to the backup file
            
        Returns:
            True if restore was successful, False otherwise
        """
        if not os.path.exists(backup_path):
            logger.error(f"Backup file not found: {backup_path}")
            return False
        
        try:
            # If using in-memory database, create a temporary database
            if self.config["database_path"] == ":memory:":
                logger.warning("Restoring to in-memory database - data will be lost when connection is closed")
            
            # Disconnect current database
            self.disconnect()
            
            # Connect to the backup database
            backup_conn = sqlite3.connect(backup_path)
            
            # Reconnect to the main database
            self.connect()
            
            # Perform restore
            with backup_conn:
                backup_conn.backup(self._connection)
            
            backup_conn.close()
            return True
        except Exception as e:
            logger.error(f"Failed to restore database from backup: {e}")
            return False
    
    def get_connection_string(self) -> str:
        """
        Get a sanitized connection string.
        
        Returns:
            Sanitized connection string
        """
        return f"sqlite://{self.config['database_path']}"