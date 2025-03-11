"""
PostgreSQL Database Connector for AI Document Organizer V2.

This module implements a database connector for PostgreSQL, providing
a robust, full-featured relational database solution.
"""

import os
import re
import sys
import logging
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Union

try:
    import psycopg2
    from psycopg2 import pool
    from psycopg2.extras import RealDictCursor, DictCursor
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

logger = logging.getLogger(__name__)

class PostgreSQLConnectorPlugin(DatabaseConnectorPlugin):
    """
    PostgreSQL database connector implementation.
    
    This plugin provides database operations for PostgreSQL, a powerful,
    enterprise-class, open-source object-relational database system.
    """
    
    plugin_name = "postgresql_connector"
    plugin_description = "PostgreSQL database connector for robust relational database operations"
    plugin_version = "1.0.0"
    
    # PostgreSQL type mapping
    _TYPE_MAPPING = {
        "text": "TEXT",
        "string": "VARCHAR",
        "varchar": "VARCHAR",
        "char": "CHAR",
        "integer": "INTEGER",
        "int": "INTEGER",
        "float": "REAL",
        "real": "REAL",
        "double": "DOUBLE PRECISION",
        "decimal": "DECIMAL",
        "boolean": "BOOLEAN",
        "bool": "BOOLEAN",
        "datetime": "TIMESTAMP",
        "timestamp": "TIMESTAMP",
        "date": "DATE",
        "time": "TIME",
        "blob": "BYTEA",
        "binary": "BYTEA",
        "json": "JSONB",
        "jsonb": "JSONB",
        "uuid": "UUID",
        "array": "ARRAY",
        "hstore": "HSTORE",
        "inet": "INET",
        "cidr": "CIDR",
        "macaddr": "MACADDR",
        "xml": "XML",
        "tsvector": "TSVECTOR"
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the PostgreSQL connector plugin.
        
        Args:
            config: Optional configuration dictionary
        """
        super().__init__(config)
        
        if not PSYCOPG2_AVAILABLE:
            logger.error("psycopg2 is not installed. Please install it with: pip install psycopg2-binary")
            raise ImportError("psycopg2 is required for PostgreSQL connector but it is not installed.")
        
        # Set PostgreSQL-specific defaults
        self.config.setdefault("host", "localhost")
        self.config.setdefault("port", 5432)
        self.config.setdefault("database", None)
        self.config.setdefault("user", None)
        self.config.setdefault("password", None)
        self.config.setdefault("connection_timeout", 30)
        self.config.setdefault("query_timeout", 60)
        self.config.setdefault("min_connections", 1)
        self.config.setdefault("max_connections", 5)
        self.config.setdefault("connection_pool", True)
        self.config.setdefault("schema", "public")
        self.config.setdefault("ssl_mode", None)
        self.config.setdefault("use_dict_cursor", True)
        
        # Initialize connection pool and cursor
        self._connection_pool = None
        self._connection = None
        self._cursor = None
    
    def initialize(self) -> bool:
        """
        Initialize the PostgreSQL connector.
        
        Returns:
            True if initialization was successful, False otherwise
        """
        try:
            # Check if required configuration is provided
            if not self.config.get("database"):
                logger.error("Database name must be provided for PostgreSQL connector")
                return False
            
            if not self.config.get("user"):
                logger.error("User must be provided for PostgreSQL connector")
                return False
                
            return True
        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL connector: {e}")
            return False
    
    def connect(self) -> bool:
        """
        Connect to the PostgreSQL database.
        
        Returns:
            True if connection was successful, False otherwise
            
        Raises:
            ConnectionError: If connection fails
        """
        try:
            # Close any existing connection
            if self._connection or self._connection_pool:
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
            
            # Create connection or connection pool
            if use_connection_pool:
                self._connection_pool = pool.ThreadedConnectionPool(
                    minconn=min_connections,
                    maxconn=max_connections,
                    dsn=dsn,
                    **conn_kwargs
                )
                # Get a connection from the pool
                self._connection = self._connection_pool.getconn()
            else:
                self._connection = psycopg2.connect(
                    dsn=dsn,
                    **conn_kwargs
                )
            
            # Set auto-commit to False for manual transaction management
            self._connection.autocommit = False
            
            # Create cursor
            cursor_factory = RealDictCursor if self.config["use_dict_cursor"] else DictCursor
            self._cursor = self._connection.cursor(cursor_factory=cursor_factory)
            
            self._connected = True
            return True
        except Exception as e:
            self._connected = False
            logger.error(f"Failed to connect to PostgreSQL database: {e}")
            raise ConnectionError(f"Failed to connect to PostgreSQL database: {e}")
    
    def disconnect(self) -> bool:
        """
        Disconnect from the PostgreSQL database.
        
        Returns:
            True if disconnection was successful, False otherwise
        """
        try:
            if self._cursor:
                self._cursor.close()
                self._cursor = None
                
            if self._connection_pool:
                if self._connection:
                    self._connection_pool.putconn(self._connection)
                self._connection_pool.closeall()
                self._connection_pool = None
                self._connection = None
            elif self._connection:
                self._connection.close()
                self._connection = None
                
            self._connected = False
            self._in_transaction = False
            return True
        except Exception as e:
            logger.error(f"Error disconnecting from PostgreSQL database: {e}")
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
                result["column_names"] = [col.name for col in self._cursor.description]
            
            # Check if query contains RETURNING clause
            has_returning = "RETURNING" in query.upper()
            
            # For queries that return rows (SELECT, INSERT...RETURNING, etc.)
            if query.strip().upper().startswith(("SELECT", "SHOW", "WITH", "EXPLAIN", "ANALYZE")) or has_returning:
                try:
                    # Fetch all rows
                    rows = self._cursor.fetchall()
                    
                    # Convert rows to list of dicts
                    if rows:
                        if isinstance(rows[0], dict):
                            # Already a dict (RealDictCursor)
                            result["rows"] = rows
                        else:
                            # Convert to dict
                            column_names = result["column_names"]
                            result["rows"] = [dict(zip(column_names, row)) for row in rows]
                        
                        # For INSERT...RETURNING, set the last_row_id
                        if query.strip().upper().startswith("INSERT") and has_returning and rows:
                            if 'id' in result["rows"][0]:
                                result["last_row_id"] = result["rows"][0]['id']
                    else:
                        # No rows returned
                        result["rows"] = []
                        
                    result["row_count"] = len(result["rows"])
                except Exception as e:
                    logger.error(f"Error fetching query results: {e}")
                    result["rows"] = []
                    result["row_count"] = 0
            else:
                # For non-returning queries
                result["affected_rows"] = self._cursor.rowcount
            
            result["success"] = True
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            logger.debug(f"Query: {query}")
            logger.debug(f"Params: {params}")
            raise QueryError(f"Query execution failed: {e}")
        finally:
            result["execution_time"] = time.time() - start_time
            
        return result
    
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
        if not self.is_connected():
            self.connect()
        
        results = []
        
        try:
            # Use transaction for batch execution
            with self.transaction():
                for i, query in enumerate(queries):
                    params = None
                    if params_list and i < len(params_list):
                        params = params_list[i]
                    
                    # Check if the query contains RETURNING clause
                    has_returning = "RETURNING" in query.upper()
                    
                    try:
                        result = self.execute_query(query, params)
                        results.append(result)
                        
                        # For INSERT with RETURNING, make sure we have the ID in the results
                        if query.strip().upper().startswith("INSERT") and has_returning and result.get('rows'):
                            logger.debug(f"Batch operation {i} returned ID: {result['rows'][0].get('id')}")
                    except Exception as e:
                        logger.error(f"Error executing batch query {i}: {e}")
                        logger.debug(f"Query: {query}")
                        logger.debug(f"Params: {params}")
                        # Add a failed result and continue
                        results.append({
                            "success": False,
                            "rows": [],
                            "row_count": 0,
                            "column_names": [],
                            "execution_time": 0,
                            "last_row_id": None,
                            "affected_rows": 0,
                            "error": str(e)
                        })
                
        except Exception as e:
            logger.error(f"Batch execution failed: {e}")
            raise QueryError(f"Batch execution failed: {e}")
                
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
                self._cursor.execute("BEGIN")
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
        schema = self.config["schema"]
        result = self.execute_query(
            """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = %s 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
            """, 
            (schema,)
        )
        return [row['table_name'] for row in result['rows']]
    
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
            schema = self.config["schema"]
            
            # Get column information
            column_result = self.execute_query(
                """
                SELECT column_name, data_type, is_nullable, column_default,
                       character_maximum_length, numeric_precision, numeric_scale
                FROM information_schema.columns
                WHERE table_schema = %s AND table_name = %s
                ORDER BY ordinal_position
                """,
                (schema, table_name)
            )
            
            if not column_result['rows']:
                raise SchemaError(f"Table not found: {table_name}")
            
            columns = {}
            
            for col in column_result['rows']:
                data_type = col['data_type'].upper()
                
                # Add length/precision if applicable
                if col['character_maximum_length'] is not None:
                    data_type += f"({col['character_maximum_length']})"
                elif col['numeric_precision'] is not None and col['numeric_scale'] is not None:
                    data_type += f"({col['numeric_precision']},{col['numeric_scale']})"
                elif col['numeric_precision'] is not None:
                    data_type += f"({col['numeric_precision']})"
                
                columns[col['column_name']] = {
                    "type": data_type,
                    "nullable": col['is_nullable'] == 'YES',
                    "default": col['column_default']
                }
            
            # Get primary key information
            pk_result = self.execute_query(
                """
                SELECT c.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.constraint_column_usage AS ccu USING (constraint_schema, constraint_name)
                JOIN information_schema.columns AS c 
                     ON c.table_schema = tc.constraint_schema
                    AND c.table_name = tc.table_name
                    AND c.column_name = ccu.column_name
                WHERE tc.constraint_type = 'PRIMARY KEY'
                AND tc.table_schema = %s
                AND tc.table_name = %s
                """,
                (schema, table_name)
            )
            
            primary_keys = [row['column_name'] for row in pk_result['rows']]
            
            # Mark primary keys in column info
            for pk in primary_keys:
                if pk in columns:
                    columns[pk]["primary_key"] = True
            
            # Get foreign key information
            fk_result = self.execute_query(
                """
                SELECT
                    kcu.column_name,
                    ccu.table_schema AS foreign_table_schema,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                    AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage AS ccu
                    ON ccu.constraint_name = tc.constraint_name
                    AND ccu.table_schema = tc.table_schema
                WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_schema = %s
                AND tc.table_name = %s
                """,
                (schema, table_name)
            )
            
            foreign_keys = []
            
            for fk in fk_result['rows']:
                foreign_keys.append({
                    "column": fk['column_name'],
                    "references": {
                        "schema": fk['foreign_table_schema'],
                        "table": fk['foreign_table_name'],
                        "column": fk['foreign_column_name']
                    }
                })
            
            # Get index information
            index_result = self.execute_query(
                """
                SELECT
                    i.relname AS index_name,
                    a.attname AS column_name,
                    ix.indisunique AS is_unique,
                    ix.indisprimary AS is_primary
                FROM
                    pg_class t,
                    pg_class i,
                    pg_index ix,
                    pg_attribute a,
                    pg_namespace n
                WHERE
                    t.oid = ix.indrelid
                    AND i.oid = ix.indexrelid
                    AND a.attrelid = t.oid
                    AND a.attnum = ANY(ix.indkey)
                    AND t.relkind = 'r'
                    AND t.relnamespace = n.oid
                    AND n.nspname = %s
                    AND t.relname = %s
                ORDER BY
                    i.relname, a.attnum
                """,
                (schema, table_name)
            )
            
            # Process index information
            indexes = {}
            for idx_row in index_result['rows']:
                idx_name = idx_row['index_name']
                if idx_name not in indexes:
                    indexes[idx_name] = {
                        "columns": [],
                        "unique": idx_row['is_unique'],
                        "primary": idx_row['is_primary']
                    }
                indexes[idx_name]["columns"].append(idx_row['column_name'])
                
            # Get check constraints
            check_result = self.execute_query(
                """
                SELECT con.conname AS constraint_name,
                       pg_get_constraintdef(con.oid) AS constraint_definition
                FROM pg_constraint con
                JOIN pg_namespace ns ON con.connamespace = ns.oid
                JOIN pg_class cls ON con.conrelid = cls.oid
                WHERE ns.nspname = %s
                  AND cls.relname = %s
                  AND con.contype = 'c'
                """,
                (schema, table_name)
            )
            
            check_constraints = {}
            for check_row in check_result['rows']:
                check_constraints[check_row['constraint_name']] = {
                    "definition": check_row['constraint_definition']
                }
            
            # Construct schema information
            schema_info = {
                "table_name": table_name,
                "schema": schema,
                "columns": columns,
                "primary_keys": primary_keys,
                "foreign_keys": foreign_keys,
                "indexes": indexes,
                "check_constraints": check_constraints
            }
            
            return schema_info
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
        schema = self.config["schema"]
        result = self.execute_query(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = %s
                AND table_name = %s
            )
            """,
            (schema, table_name)
        )
        return result['rows'][0]['exists'] if result['rows'] else False
    
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
            primary_keys = []
            
            for col_name, col_def in columns.items():
                # Get type (convert to PostgreSQL type)
                col_type = col_def.get("type", "text").lower()
                
                # Special handling for serial/autoincrement fields
                if col_type == "serial" or (col_type in ["integer", "int"] and col_def.get("autoincrement")):
                    # For primary key with autoincrement, use SERIAL type
                    pg_type = "SERIAL"
                    if col_def.get("primary_key"):
                        pg_type = "SERIAL PRIMARY KEY"
                        # Add to primary keys list but will be handled specially
                        primary_keys.append(col_name)
                else:
                    pg_type = self._TYPE_MAPPING.get(col_type, "TEXT")
                    
                    # Add length/precision if specified
                    if "length" in col_def:
                        pg_type += f"({col_def['length']})"
                    elif "precision" in col_def and "scale" in col_def:
                        pg_type += f"({col_def['precision']},{col_def['scale']})"
                    elif "precision" in col_def:
                        pg_type += f"({col_def['precision']})"
                
                # Build column definition
                col_parts = [f'"{col_name}" {pg_type}']
                
                # NOT NULL constraint
                if col_def.get("nullable") is False:
                    col_parts.append("NOT NULL")
                
                # Default value
                if "default" in col_def:
                    default_val = col_def["default"]
                    
                    # Handle special values
                    if default_val == "CURRENT_TIMESTAMP":
                        col_parts.append("DEFAULT CURRENT_TIMESTAMP")
                    elif default_val is None:
                        col_parts.append("DEFAULT NULL")
                    elif isinstance(default_val, bool):
                        col_parts.append(f"DEFAULT {str(default_val).upper()}")
                    elif isinstance(default_val, (int, float)):
                        col_parts.append(f"DEFAULT {default_val}")
                    else:
                        col_parts.append(f"DEFAULT '{default_val}'")
                
                # Check for primary key
                if col_def.get("primary_key"):
                    primary_keys.append(col_name)
                
                # Check for unique constraint
                if col_def.get("unique"):
                    col_parts.append("UNIQUE")
                
                # Add complete column definition
                column_defs.append(" ".join(col_parts))
            
            # Add primary key constraint if there are any primary keys
            # Only add an explicit PRIMARY KEY constraint if we have primary keys that are not SERIAL PRIMARY KEY
            non_serial_primary_keys = []
            for pk in primary_keys:
                col_def = columns.get(pk, {})
                col_type = col_def.get("type", "").lower()
                # Skip if this is a SERIAL PRIMARY KEY as it's already handled
                if not (col_type == "serial" or (col_type in ["integer", "int"] and col_def.get("autoincrement"))):
                    non_serial_primary_keys.append(pk)
                    
            if non_serial_primary_keys:
                pk_columns = ", ".join([f'"{pk}"' for pk in non_serial_primary_keys])
                column_defs.append(f"PRIMARY KEY ({pk_columns})")
            
            # Construct full CREATE TABLE statement
            exists_clause = "IF NOT EXISTS " if if_not_exists else ""
            schema = self.config["schema"]
            query = f'CREATE TABLE {exists_clause}"{schema}"."{table_name}" (\n  '
            query += ",\n  ".join(column_defs)
            query += "\n)"
            
            # Execute query
            result = self.execute_query(query)
            return result["success"]
            
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
            # Construct DROP TABLE statement
            exists_clause = "IF EXISTS " if if_exists else ""
            schema = self.config["schema"]
            query = f'DROP TABLE {exists_clause}"{schema}"."{table_name}"'
            
            # Execute query
            result = self.execute_query(query)
            return result["success"]
        except Exception as e:
            logger.error(f"Failed to drop table {table_name}: {e}")
            raise SchemaError(f"Failed to drop table {table_name}: {e}")
    
    def get_database_info(self) -> Dict[str, Any]:
        """
        Get information about the database.
        
        Returns:
            Dictionary containing database information (version, type, size, etc.)
        """
        try:
            # Get PostgreSQL version
            version_result = self.execute_query("SELECT version()")
            version = version_result['rows'][0]['version'] if version_result['rows'] else "Unknown"
            
            # Get database size
            db_name = self.config["database"]
            size_result = self.execute_query(
                "SELECT pg_size_pretty(pg_database_size(%s)) as size",
                (db_name,)
            )
            size = size_result['rows'][0]['size'] if size_result['rows'] else "Unknown"
            
            # Get active connections
            conn_result = self.execute_query(
                """
                SELECT count(*) as connections
                FROM pg_stat_activity
                WHERE datname = %s
                """,
                (db_name,)
            )
            connections = conn_result['rows'][0]['connections'] if conn_result['rows'] else 0
            
            # Get database encoding
            encoding_result = self.execute_query(
                """
                SELECT pg_encoding_to_char(encoding) as encoding
                FROM pg_database
                WHERE datname = %s
                """,
                (db_name,)
            )
            encoding = encoding_result['rows'][0]['encoding'] if encoding_result['rows'] else "Unknown"
            
            return {
                "database_type": "PostgreSQL",
                "version": version,
                "database_name": db_name,
                "size": size,
                "active_connections": connections,
                "encoding": encoding,
                "schema": self.config["schema"],
                "host": self.config["host"],
                "port": self.config["port"],
                "user": self.config["user"]
            }
        except Exception as e:
            logger.error(f"Failed to get database information: {e}")
            return {
                "database_type": "PostgreSQL",
                "error": str(e)
            }
    
    def backup_database(self, backup_path: str, tables: Optional[List[str]] = None) -> bool:
        """
        Create a backup of the database.
        Note: This is a basic implementation that generates SQL statements.
        For production use, consider using pg_dump through subprocess.
        
        Args:
            backup_path: Path to save the backup file
            tables: Optional list of specific tables to backup. If None, backs up all tables.
            
        Returns:
            True if backup was successful, False otherwise
        """
        try:
            schema = self.config["schema"]
            
            # Get list of tables to backup
            if tables is None:
                tables = self.get_tables()
            
            with open(backup_path, 'w') as backup_file:
                # Write header
                backup_file.write(f"-- PostgreSQL Database Backup\n")
                backup_file.write(f"-- Date: {datetime.now().isoformat()}\n")
                backup_file.write(f"-- Database: {self.config['database']}\n")
                backup_file.write(f"-- Schema: {schema}\n\n")
                
                # Create schema if it doesn't exist
                backup_file.write(f"CREATE SCHEMA IF NOT EXISTS {schema};\n\n")
                
                # Backup each table
                for table in tables:
                    # Get table schema
                    table_schema = self.get_table_schema(table)
                    
                    # Write table structure
                    backup_file.write(f"-- Table: {schema}.{table}\n")
                    
                    # Generate CREATE TABLE statement
                    backup_file.write(f"DROP TABLE IF EXISTS {schema}.{table} CASCADE;\n")
                    
                    # First, identify any sequences needed for auto-increment fields and create them
                    sequences_to_create = []
                    
                    for col_name, col_info in table_schema['columns'].items():
                        default_value = col_info.get("default")
                        if default_value and 'nextval' in str(default_value):
                            # Extract sequence name from nextval expression
                            # Example: nextval('table_id_seq'::regclass)
                            match = re.search(r"nextval\('([^']+)'", str(default_value))
                            if match:
                                sequence_name = match.group(1)
                                # Only add non-duplicate sequences
                                if sequence_name not in [seq['name'] for seq in sequences_to_create]:
                                    sequences_to_create.append({
                                        'name': sequence_name,
                                        'column': col_name,
                                        'type': col_info["type"].split('(')[0]  # Use base type
                                    })
                    
                    # Create sequences before the table
                    for seq in sequences_to_create:
                        backup_file.write(f"CREATE SEQUENCE IF NOT EXISTS {seq['name']};\n")
                    backup_file.write("\n")
                    
                    columns_list = []
                    for col_name, col_info in table_schema['columns'].items():
                        # Get PostgreSQL compatible type
                        col_type = col_info["type"]
                        
                        # Fix type format for PostgreSQL
                        # Convert INTEGER(32,0) to INTEGER, etc.
                        if '(' in col_type:
                            base_type = col_type.split('(')[0]
                            # Map to proper PostgreSQL types
                            if base_type in ['INTEGER', 'BIGINT', 'SMALLINT']:
                                col_type = base_type
                            elif base_type == 'CHARACTER VARYING':
                                # Keep the length for VARCHAR
                                pass
                            elif base_type == 'NUMERIC' or base_type == 'DECIMAL':
                                # Keep precision and scale for NUMERIC/DECIMAL
                                pass
                        
                        col_def = f'"{col_name}" {col_type}'
                        
                        if not col_info.get("nullable", True):
                            col_def += " NOT NULL"
                            
                        if col_info.get("default") is not None:
                            col_def += f" DEFAULT {col_info['default']}"
                            
                        columns_list.append(col_def)
                    
                    # Add primary key constraint
                    if table_schema['primary_keys']:
                        pk_cols = ", ".join([f'"{pk}"' for pk in table_schema['primary_keys']])
                        columns_list.append(f"PRIMARY KEY ({pk_cols})")
                    
                    create_table = f"CREATE TABLE {schema}.{table} (\n  "
                    create_table += ",\n  ".join(columns_list)
                    create_table += "\n);\n\n"
                    
                    backup_file.write(create_table)
                    
                    # Get table data
                    # First, identify JSON/JSONB columns in the table
                    json_columns = {}
                    for column_name, column_info in table_schema['columns'].items():
                        column_type = column_info['type'].lower()
                        if column_type in ('json', 'jsonb'):
                            json_columns[column_name] = column_type
                    
                    # Get the table data
                    data_result = self.execute_query(f'SELECT * FROM "{schema}"."{table}"')
                    
                    if data_result['rows']:
                        backup_file.write(f"-- Data for table: {schema}.{table}\n")
                        
                        for row in data_result['rows']:
                            # Generate INSERT statement
                            column_names = list(row.keys())
                            columns = ", ".join([f'"{col}"' for col in column_names])
                            
                            # Format values appropriately
                            values = []
                            for i, (col_name, val) in enumerate(row.items()):
                                if val is None:
                                    values.append("NULL")
                                elif isinstance(val, (int, float)):
                                    values.append(str(val))
                                elif isinstance(val, bool):
                                    values.append(str(val).upper())
                                else:
                                    # Check if this is a JSON column or has JSON data
                                    is_json_col = col_name in json_columns
                                    is_json_data = isinstance(val, (dict, list))
                                    
                                    if is_json_col or is_json_data:
                                        # For JSON columns or data, use proper JSON formatting
                                        if isinstance(val, (dict, list)):
                                            # Serialize the dict or list to proper JSON
                                            json_str = json.dumps(val).replace("'", "''")
                                            values.append(f"'{json_str}'::jsonb")
                                        else:
                                            # It might be a JSON string already
                                            try:
                                                # Validate it's properly formatted JSON
                                                json.loads(val)
                                                values.append(f"'{val}'::jsonb")
                                            except:
                                                # Not valid JSON, treat as string
                                                val_str = str(val).replace("'", "''")
                                                values.append(f"'{val_str}'")
                                    else:
                                        # Escape single quotes in string values
                                        val_str = str(val).replace("'", "''")
                                        values.append(f"'{val_str}'")
                            
                            values_str = ", ".join(values)
                            backup_file.write(f"INSERT INTO {schema}.{table} ({columns}) VALUES ({values_str});\n")
                        
                        backup_file.write("\n")
                    
                    # Add foreign key constraints
                    if table_schema['foreign_keys']:
                        backup_file.write(f"-- Foreign keys for table: {schema}.{table}\n")
                        
                        for i, fk in enumerate(table_schema['foreign_keys']):
                            fk_name = f"fk_{table}_{i}"
                            ref_schema = fk['references']['schema']
                            ref_table = fk['references']['table']
                            ref_column = fk['references']['column']
                            
                            backup_file.write(
                                f"ALTER TABLE {schema}.{table} ADD CONSTRAINT {fk_name} "
                                f"FOREIGN KEY (\"{fk['column']}\") REFERENCES "
                                f"{ref_schema}.{ref_table} (\"{ref_column}\");\n"
                            )
                        
                        backup_file.write("\n")
                    
                    # Add indexes
                    if table_schema['indexes']:
                        backup_file.write(f"-- Indexes for table: {schema}.{table}\n")
                        
                        for idx_name, idx_info in table_schema['indexes'].items():
                            # Skip primary key indexes as they're already created
                            if idx_info.get('primary'):
                                continue
                                
                            unique = "UNIQUE " if idx_info.get('unique') else ""
                            columns = ", ".join([f'"{col}"' for col in idx_info['columns']])
                            
                            backup_file.write(
                                f"CREATE {unique}INDEX {idx_name} ON {schema}.{table} ({columns});\n"
                            )
                        
                        backup_file.write("\n")
            
            return True
        except Exception as e:
            logger.error(f"Failed to backup database: {e}")
            return False
    
    def restore_database(self, backup_path: str) -> bool:
        """
        Restore the database from a backup.
        
        Args:
            backup_path: Path to the backup file
            
        Returns:
            True if restore was successful, False otherwise
        """
        try:
            if not os.path.exists(backup_path):
                logger.error(f"Backup file not found: {backup_path}")
                return False
            
            # Read backup file
            with open(backup_path, 'r') as backup_file:
                sql_script = backup_file.read()
            
            # Log some basic info about the backup file
            logger.info(f"Backup file size: {os.path.getsize(backup_path)} bytes")
            logger.info(f"First 500 characters of backup file: {sql_script[:500]}...")
            
            # Split script into statements while preserving comments
            # This is a simple approach and may not work for all SQL scripts
            statements = []
            current_statement = []
            for line in sql_script.split('\n'):
                line = line.strip()
                if not line or line.startswith('--'):
                    # Skip empty lines and comments
                    continue
                    
                current_statement.append(line)
                if line.endswith(';'):
                    statements.append(' '.join(current_statement))
                    current_statement = []
            
            # Add the last statement if there's one without semicolon
            if current_statement:
                statements.append(' '.join(current_statement))
                
            # Log some info about what we extracted
            if len(statements) == 0:
                logger.warning("No SQL statements found in backup file!")
            else:
                logger.info(f"First statement: {statements[0][:200]}...")
            
            # Make sure sequences are created before they are referenced in tables
            # and tables are created before inserts
            sequence_statements = []
            table_statements = []
            insert_statements = []
            other_statements = []
            
            logger.info(f"Total SQL statements from backup: {len(statements)}")
            
            for statement in statements:
                stmt_upper = statement.strip().upper()
                if stmt_upper.startswith('CREATE SEQUENCE'):
                    sequence_statements.append(statement)
                elif stmt_upper.startswith('CREATE TABLE'):
                    table_statements.append(statement)
                elif stmt_upper.startswith('INSERT INTO'):
                    insert_statements.append(statement)
                else:
                    other_statements.append(statement)
                    
            logger.info(f"Categorized statements - Sequences: {len(sequence_statements)}, Tables: {len(table_statements)}, Inserts: {len(insert_statements)}, Other: {len(other_statements)}")
            
            # Execute statements in separate transactions for better error handling
            # First, execute schema and sequence statements, which should be outside transactions
            for statement in other_statements:
                if "CREATE SCHEMA" in statement.upper():
                    statement = statement.strip()
                    if statement:
                        try:
                            # Remove trailing semicolon for execution
                            if statement.endswith(';'):
                                statement = statement[:-1]
                            self.execute_query(statement)
                            logger.info(f"Successfully executed schema statement")
                        except Exception as stmt_error:
                            # Schema statements might fail if schema already exists, that's ok
                            logger.warning(f"Schema statement warning: {stmt_error}")
                            logger.warning(f"Statement: {statement}")
            
            # Execute sequence statements
            logger.info(f"Executing {len(sequence_statements)} sequence statements")
            for i, statement in enumerate(sequence_statements):
                statement = statement.strip()
                if statement:
                    try:
                        # Remove trailing semicolon for execution
                        if statement.endswith(';'):
                            statement = statement[:-1]
                        result = self.execute_query(statement)
                        logger.info(f"Sequence statement {i+1}/{len(sequence_statements)} executed successfully")
                    except Exception as stmt_error:
                        logger.error(f"Error executing sequence statement: {stmt_error}")
                        logger.error(f"Statement: {statement}")
                        # Don't raise, try to continue with other statements
            
            # Execute DROP TABLE statements first 
            drop_statements = [stmt for stmt in other_statements if stmt.upper().startswith('DROP TABLE')]
            logger.info(f"Executing {len(drop_statements)} DROP TABLE statements")
            for i, statement in enumerate(drop_statements):
                statement = statement.strip()
                if statement:
                    try:
                        # Remove trailing semicolon for execution
                        if statement.endswith(';'):
                            statement = statement[:-1]
                        result = self.execute_query(statement)
                        logger.info(f"DROP TABLE statement {i+1}/{len(drop_statements)} executed successfully")
                    except Exception as stmt_error:
                        logger.error(f"Error executing DROP TABLE statement: {stmt_error}")
                        logger.error(f"Statement: {statement}")
                        # Don't raise, try to continue with other statements
            
            # Execute table creation statements
            logger.info(f"Executing {len(table_statements)} table statements")
            for i, statement in enumerate(table_statements):
                statement = statement.strip()
                if statement:
                    try:
                        # Remove trailing semicolon for execution
                        if statement.endswith(';'):
                            statement = statement[:-1]
                        result = self.execute_query(statement)
                        logger.info(f"Table statement {i+1}/{len(table_statements)} executed successfully")
                    except Exception as stmt_error:
                        logger.error(f"Error executing table statement: {stmt_error}")
                        logger.error(f"Statement: {statement}")
                        # Don't raise, try to continue with other statements
            
            # Execute INSERT statements in a transaction
            if insert_statements:
                logger.info(f"Executing {len(insert_statements)} INSERT statements in transaction")
                try:
                    with self.transaction():
                        for i, statement in enumerate(insert_statements):
                            statement = statement.strip()
                            if statement:
                                try:
                                    # Remove trailing semicolon for execution
                                    if statement.endswith(';'):
                                        statement = statement[:-1]
                                    self.execute_query(statement)
                                    logger.info(f"INSERT statement {i+1}/{len(insert_statements)} executed successfully")
                                except Exception as stmt_error:
                                    logger.error(f"Error executing insert statement {i+1}: {stmt_error}")
                                    logger.error(f"Statement: {statement}")
                                    raise
                except Exception as tx_error:
                    logger.error(f"Transaction error during INSERT statements: {tx_error}")
                    # We don't re-raise here to allow the restore process to continue
                    # even if some data couldn't be inserted
                    logger.warning("Continuing restore process despite INSERT errors")
            
            # Execute remaining statements (indexes, constraints, etc.)
            remaining_statements = [stmt for stmt in other_statements 
                                   if not stmt.upper().startswith('DROP TABLE') 
                                   and not "CREATE SCHEMA" in stmt.upper()]
            
            logger.info(f"Executing {len(remaining_statements)} other statements")
            for i, statement in enumerate(remaining_statements):
                statement = statement.strip()
                if statement:
                    try:
                        # Remove trailing semicolon for execution
                        if statement.endswith(';'):
                            statement = statement[:-1]
                        self.execute_query(statement)
                    except Exception as stmt_error:
                        logger.error(f"Error executing statement: {stmt_error}")
                        logger.error(f"Statement: {statement}")
                        # Don't raise, try to continue with other statements
            
            # Verify that tables were actually created
            restored_tables = []
            for statement in table_statements:
                # Extract table name from CREATE TABLE statement
                match = re.search(r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:public\.)?([^\s\(]+)', statement, re.IGNORECASE)
                if match:
                    table_name = match.group(1).strip('"')
                    restored_tables.append(table_name)
            
            # Check if tables exist now
            existing_tables = self.get_tables()
            missing_tables = [table for table in restored_tables if table not in existing_tables]
            
            if missing_tables:
                logger.error(f"Tables not created after restore: {missing_tables}")
                return False
                
            logger.info(f"Successfully restored {len(restored_tables)} tables: {restored_tables}")
            return True
        except Exception as e:
            logger.error(f"Failed to restore database: {e}")
            logger.error(f"Exception type: {type(e).__name__}")
            logger.error(f"Exception details: {str(e)}")
            return False
    
    def get_connection_string(self) -> str:
        """
        Get a sanitized connection string (with password removed).
        
        Returns:
            Sanitized connection string
        """
        host = self.config["host"]
        port = self.config["port"]
        database = self.config["database"]
        user = self.config["user"]
        
        return f"postgresql://{user}@{host}:{port}/{database}"