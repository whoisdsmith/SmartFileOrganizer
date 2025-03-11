"""
Database Connector Base Module for AI Document Organizer V2.

This module defines the base classes and interfaces for database connectors,
providing a standardized way to interact with various database systems.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple, Union

from ai_document_organizer_v2.core.plugin_base import PluginBase

logger = logging.getLogger(__name__)

class DatabaseError(Exception):
    """Base exception for database-related errors."""
    pass

class ConnectionError(DatabaseError):
    """Exception raised for connection errors."""
    pass

class QueryError(DatabaseError):
    """Exception raised for query errors."""
    pass

class TransactionError(DatabaseError):
    """Exception raised for transaction errors."""
    pass

class SchemaError(DatabaseError):
    """Exception raised for schema-related errors."""
    pass

class DatabaseConnectorPlugin(PluginBase, ABC):
    """
    Base class for database connector plugins.
    
    This abstract class defines the common interface that all database
    connector implementations must provide, ensuring consistent behavior
    across different database systems.
    """
    
    plugin_type = "database_connector"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the database connector plugin.
        
        Args:
            config: Optional configuration dictionary
        """
        super().__init__(config)
        self._connection = None
        self._connected = False
        self._transaction_active = False
        self._in_transaction = False
        
        # Set default configuration values
        if not self.config:
            self.config = {}
            
        # Default connection parameters
        self.config.setdefault("host", "localhost")
        self.config.setdefault("port", None)  # Will be set by specific implementations
        self.config.setdefault("database", None)
        self.config.setdefault("user", None)
        self.config.setdefault("password", None)
        self.config.setdefault("connection_timeout", 30)
        self.config.setdefault("query_timeout", 60)
        self.config.setdefault("max_connections", 5)
        self.config.setdefault("connection_pool", True)
        
        # Initialize database-specific settings in the subclass
    
    @abstractmethod
    def connect(self) -> bool:
        """
        Connect to the database using the configured parameters.
        
        Returns:
            True if connection was successful, False otherwise
        
        Raises:
            ConnectionError: If connection fails
        """
        pass
        
    @abstractmethod
    def disconnect(self) -> bool:
        """
        Disconnect from the database.
        
        Returns:
            True if disconnection was successful, False otherwise
        """
        pass
        
    @abstractmethod
    def is_connected(self) -> bool:
        """
        Check if the connection to the database is active.
        
        Returns:
            True if connected, False otherwise
        """
        pass
        
    @abstractmethod
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
        pass
        
    @abstractmethod
    def execute_batch(self, queries: List[str], 
                     params_list: Optional[List[Union[Dict[str, Any], List[Any], Tuple[Any, ...]]]] = None) -> List[Dict[str, Any]]:
        """
        Execute multiple queries in batch mode.
        
        Args:
            queries: List of SQL query strings
            params_list: Optional list of parameter sets for each query.
                         Each parameter set can be a dictionary with named parameters
                         or a tuple/list with positional parameters.
            
        Returns:
            List of dictionaries containing query results and metadata
            
        Raises:
            QueryError: If batch execution fails
        """
        pass
        
    @abstractmethod
    def begin_transaction(self) -> bool:
        """
        Begin a database transaction.
        
        Returns:
            True if transaction was successfully started, False otherwise
            
        Raises:
            TransactionError: If transaction cannot be started
        """
        pass
        
    @abstractmethod
    def commit(self) -> bool:
        """
        Commit the current transaction.
        
        Returns:
            True if transaction was successfully committed, False otherwise
            
        Raises:
            TransactionError: If commit fails
        """
        pass
        
    @abstractmethod
    def rollback(self) -> bool:
        """
        Rollback the current transaction.
        
        Returns:
            True if transaction was successfully rolled back, False otherwise
            
        Raises:
            TransactionError: If rollback fails
        """
        pass
        
    @abstractmethod
    def get_tables(self) -> List[str]:
        """
        Get a list of all tables in the database.
        
        Returns:
            List of table names
        """
        pass
        
    @abstractmethod
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
        pass
        
    @abstractmethod
    def table_exists(self, table_name: str) -> bool:
        """
        Check if a table exists in the database.
        
        Args:
            table_name: Name of the table
            
        Returns:
            True if table exists, False otherwise
        """
        pass
        
    @abstractmethod
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
        pass
        
    @abstractmethod
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
        pass
        
    @abstractmethod
    def get_database_info(self) -> Dict[str, Any]:
        """
        Get information about the database.
        
        Returns:
            Dictionary containing database information (version, type, size, etc.)
        """
        pass
        
    @abstractmethod
    def backup_database(self, backup_path: str) -> bool:
        """
        Create a backup of the database.
        
        Args:
            backup_path: Path to save the backup file
            
        Returns:
            True if backup was successful, False otherwise
        """
        pass
        
    @abstractmethod
    def restore_database(self, backup_path: str) -> bool:
        """
        Restore the database from a backup.
        
        Args:
            backup_path: Path to the backup file
            
        Returns:
            True if restore was successful, False otherwise
        """
        pass
    
    def transaction(self):
        """
        Context manager for database transactions.
        
        Example:
            with db_connector.transaction():
                db_connector.execute_query("INSERT INTO ...")
                db_connector.execute_query("UPDATE ...")
        
        Returns:
            Transaction context manager
        """
        return _TransactionContextManager(self)
    
    def get_connection_string(self) -> str:
        """
        Get a sanitized connection string (with password removed).
        
        Returns:
            Sanitized connection string
        """
        # Implementation will depend on the database type
        # This is a placeholder that should be overridden by subclasses
        return "database://<connection_details_hidden>"

class _TransactionContextManager:
    """Context manager for database transactions."""
    
    def __init__(self, connector):
        """Initialize with database connector."""
        self.connector = connector
    
    def __enter__(self):
        """Begin transaction when entering context."""
        self.connector.begin_transaction()
        return self.connector
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Commit or rollback transaction when exiting context."""
        if exc_type is not None:
            # An exception occurred, rollback the transaction
            self.connector.rollback()
            return False
        else:
            # No exception, commit the transaction
            self.connector.commit()
            return True