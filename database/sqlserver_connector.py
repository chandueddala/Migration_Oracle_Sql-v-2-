"""
SQL Server Database Connector
Handles all SQL Server database connections and operations
"""

import logging
import pyodbc
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class SQLServerConnector:
    """SQL Server database connection and operations"""
    
    def __init__(self, credentials: Dict[str, str]):
        """
        Initialize SQL Server connector
        
        Args:
            credentials: Dict with server, database, user, password, driver
        """
        self.credentials = credentials
        self.connection = None
        
    def connect(self) -> bool:
        """Establish connection to SQL Server database"""
        try:
            # Support both 'user' and 'username' keys for flexibility
            username = self.credentials.get('user') or self.credentials.get('username')
            if not username:
                raise ValueError("Missing 'user' or 'username' in credentials")

            driver = self.credentials.get('driver', 'ODBC Driver 18 for SQL Server')
            conn_str = (
                f"DRIVER={{{driver}}};"
                f"SERVER={self.credentials['server']};"
                f"DATABASE={self.credentials['database']};"
                f"UID={username};"
                f"PWD={self.credentials['password']};"
                f"TrustServerCertificate=yes;"
            )

            self.connection = pyodbc.connect(conn_str)
            logger.info("✅ SQL Server connection established")
            return True
        except KeyError as e:
            logger.error(f"❌ SQL Server connection failed - Missing credential: {e}")
            return False
        except ValueError as e:
            logger.error(f"❌ SQL Server connection failed - {e}")
            return False
        except Exception as e:
            logger.error(f"❌ SQL Server connection failed: {e}")
            return False
    
    def disconnect(self):
        """Close SQL Server connection"""
        if self.connection:
            self.connection.close()
            logger.info("SQL Server connection closed")
    
    def execute_query(self, query: str, params: Optional[tuple] = None) -> List[tuple]:
        """
        Execute SELECT query and return results
        
        Args:
            query: SQL query string
            params: Optional query parameters
            
        Returns:
            List of result tuples
        """
        try:
            cursor = self.connection.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            results = cursor.fetchall()
            cursor.close()
            return results
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise
    
    def execute_ddl(self, ddl: str) -> Dict[str, Any]:
        """
        Execute DDL statement (CREATE, ALTER, DROP)

        Handles GO batch separators by splitting and executing each batch separately.

        Args:
            ddl: DDL statement string

        Returns:
            Dict with status and message
        """
        try:
            cursor = self.connection.cursor()

            # Remove markdown code blocks if present
            ddl = ddl.strip()
            if ddl.startswith('```'):
                lines = ddl.split('\n')
                ddl = '\n'.join(lines[1:-1]) if len(lines) > 2 else ddl

            # Split by GO statements (batch separator)
            # GO must be on its own line
            import re
            batches = re.split(r'^\s*GO\s*$', ddl, flags=re.IGNORECASE | re.MULTILINE)

            # Execute each batch
            for batch in batches:
                batch = batch.strip()
                if batch:  # Skip empty batches
                    cursor.execute(batch)
                    self.connection.commit()

            cursor.close()

            logger.info("✅ DDL executed successfully")
            return {"status": "success", "message": "DDL executed successfully"}

        except pyodbc.Error as e:
            self.connection.rollback()
            error_msg = str(e)
            logger.error(f"❌ DDL execution failed: {error_msg}")
            return {"status": "error", "message": error_msg}
        except Exception as e:
            self.connection.rollback()
            error_msg = str(e)
            logger.error(f"❌ Unexpected error: {error_msg}")
            return {"status": "error", "message": error_msg}
    
    def table_exists(self, table_name: str, schema: str = "dbo") -> bool:
        """
        Check if table exists
        
        Args:
            table_name: Name of the table
            schema: Schema name (default: dbo)
            
        Returns:
            True if table exists
        """
        query = """
        SELECT COUNT(*) 
        FROM INFORMATION_SCHEMA.TABLES 
        WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?
        """
        result = self.execute_query(query, (schema, table_name))
        return result[0][0] > 0 if result else False
    
    def object_exists(self, object_name: str, object_type: str) -> bool:
        """
        Check if database object exists
        
        Args:
            object_name: Name of the object
            object_type: P (procedure), FN (function), TR (trigger)
            
        Returns:
            True if object exists
        """
        query = """
        SELECT COUNT(*) 
        FROM sys.objects 
        WHERE name = ? AND type = ?
        """
        result = self.execute_query(query, (object_name, object_type))
        return result[0][0] > 0 if result else False
    
    def create_schema(self, schema_name: str) -> bool:
        """
        Create schema if it doesn't exist
        
        Args:
            schema_name: Name of the schema
            
        Returns:
            True if successful
        """
        # Check if schema exists
        query = """
        SELECT COUNT(*) 
        FROM sys.schemas 
        WHERE name = ?
        """
        result = self.execute_query(query, (schema_name,))
        
        if result[0][0] > 0:
            logger.info(f"Schema [{schema_name}] already exists")
            return True
        
        # Create schema
        ddl = f"CREATE SCHEMA [{schema_name}]"
        result = self.execute_ddl(ddl)
        return result['status'] == 'success'
    
    def insert_batch(self, table_name: str, columns: List[str], rows: List[tuple]) -> int:
        """
        Insert batch of rows into table
        
        Args:
            table_name: Name of the table
            columns: List of column names
            rows: List of row tuples
            
        Returns:
            Number of rows inserted
        """
        try:
            cursor = self.connection.cursor()
            
            placeholders = ','.join(['?' for _ in columns])
            column_names = ','.join([f'[{col}]' for col in columns])
            
            query = f"INSERT INTO {table_name} ({column_names}) VALUES ({placeholders})"
            
            cursor.executemany(query, rows)
            self.connection.commit()

            # Note: cursor.rowcount returns -1 with executemany() in pyodbc
            # Use the actual number of rows processed
            row_count = len(rows)
            cursor.close()

            logger.info(f"✅ Inserted {row_count} rows into {table_name}")
            return row_count
            
        except Exception as e:
            self.connection.rollback()
            logger.error(f"❌ Batch insert failed: {e}")
            raise
    
    def get_table_columns(self, table_name: str, schema: str = "dbo") -> List[Dict]:
        """
        Get table column information
        
        Args:
            table_name: Name of the table
            schema: Schema name (default: dbo)
            
        Returns:
            List of column dictionaries
        """
        query = """
        SELECT 
            COLUMN_NAME,
            DATA_TYPE,
            CHARACTER_MAXIMUM_LENGTH,
            IS_NULLABLE,
            COLUMN_DEFAULT,
            COLUMNPROPERTY(OBJECT_ID(TABLE_SCHEMA + '.' + TABLE_NAME), 
                         COLUMN_NAME, 'IsIdentity') as IS_IDENTITY
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?
        ORDER BY ORDINAL_POSITION
        """
        results = self.execute_query(query, (schema, table_name))
        
        columns = []
        for row in results:
            columns.append({
                'name': row[0],
                'type': row[1],
                'max_length': row[2],
                'nullable': row[3] == 'YES',
                'default': row[4],
                'is_identity': bool(row[5])
            })
        
        return columns
    
    def set_identity_insert(self, table_name: str, enabled: bool) -> bool:
        """
        Enable or disable IDENTITY_INSERT for a table

        Args:
            table_name: Name of the table
            enabled: True to enable, False to disable

        Returns:
            True if successful
        """
        try:
            status = "ON" if enabled else "OFF"
            cursor = self.connection.cursor()
            cursor.execute(f"SET IDENTITY_INSERT {table_name} {status}")
            cursor.close()
            logger.info(f"IDENTITY_INSERT {status} for {table_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to set IDENTITY_INSERT: {e}")
            return False

    def bulk_insert_data(self, table_name: str, data: List[Dict], identity_columns: List[str] = None) -> int:
        """
        Bulk insert data into table from list of dictionaries

        Args:
            table_name: Name of the table
            data: List of dictionaries (one per row)
            identity_columns: List of IDENTITY column names (optional)

        Returns:
            Number of rows inserted
        """
        if not data:
            return 0

        try:
            # Enable IDENTITY_INSERT if needed
            if identity_columns:
                self.set_identity_insert(table_name, True)

            # Get column names from first row
            columns = list(data[0].keys())

            # Convert list of dicts to list of tuples
            rows = []
            for row_dict in data:
                row_tuple = tuple(row_dict.get(col) for col in columns)
                rows.append(row_tuple)

            # Use insert_batch method
            row_count = self.insert_batch(table_name, columns, rows)

            # Disable IDENTITY_INSERT if it was enabled
            if identity_columns:
                self.set_identity_insert(table_name, False)

            return row_count

        except Exception as e:
            # Make sure to disable IDENTITY_INSERT even if error occurs
            if identity_columns:
                try:
                    self.set_identity_insert(table_name, False)
                except:
                    pass
            logger.error(f"Bulk insert failed for {table_name}: {e}")
            raise

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()


def test_sqlserver_connection(credentials: Dict[str, str]) -> bool:
    """
    Test SQL Server database connection
    
    Args:
        credentials: SQL Server connection credentials
        
    Returns:
        True if connection successful
    """
    try:
        with SQLServerConnector(credentials) as conn:
            result = conn.execute_query("SELECT 1")
            return len(result) > 0
    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        return False
