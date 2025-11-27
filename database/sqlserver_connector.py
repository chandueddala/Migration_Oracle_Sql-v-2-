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
            driver = self.credentials.get('driver', 'ODBC Driver 18 for SQL Server')

            # Check if using Windows Authentication
            trusted = self.credentials.get('trusted_connection', '').lower() in ('yes', 'true', '1')

            if trusted:
                # Windows Authentication
                conn_str = (
                    f"DRIVER={{{driver}}};"
                    f"SERVER={self.credentials['server']};"
                    f"DATABASE={self.credentials['database']};"
                    f"Trusted_Connection=yes;"
                    f"TrustServerCertificate=yes;"
                )
            else:
                # SQL Server Authentication
                username = self.credentials.get('user') or self.credentials.get('username')
                if not username:
                    raise ValueError("Missing 'user' or 'username' in credentials for SQL Server authentication")

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
            logger.error(f"Failed Query: {query}")
            if params:
                logger.error(f"Parameters: {params}")
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
        Get column information for a table
        
        Args:
            table_name: Name of the table
            schema: Schema name
            
        Returns:
            List of dictionaries with column info
        """
        query = """
        SELECT 
            COLUMN_NAME,
            DATA_TYPE,
            IS_NULLABLE,
            COLUMN_DEFAULT,
            CHARACTER_MAXIMUM_LENGTH,
            COLUMNPROPERTY(OBJECT_ID(TABLE_SCHEMA + '.' + TABLE_NAME), 
                         COLUMN_NAME, 'IsIdentity') as IS_IDENTITY
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = ?
          AND TABLE_SCHEMA = ?
        ORDER BY ORDINAL_POSITION
        """
        
        cursor = self.connection.cursor()
        cursor.execute(query, (table_name, schema))
        
        columns = []
        for row in cursor.fetchall():
            columns.append({
                'name': row[0],
                'type': row[1],
                'nullable': row[2] == 'YES',
                'default': row[3],
                'max_length': row[4],
                'is_identity': bool(row[5])
            })
        
        cursor.close()
        return columns
    
    def get_computed_columns(self, table_name: str, schema: str = "dbo") -> List[str]:
        """
        Get list of computed column names for a table
        
        Computed columns in SQL Server are auto-calculated and cannot have values inserted.
        This method identifies them so they can be excluded from INSERT statements.
        
        Args:
            table_name: Name of the table
            schema: Schema name (default: dbo)
            
        Returns:
            List of computed column names
        """
        query = """
        SELECT c.name as column_name
        FROM sys.columns c
        INNER JOIN sys.tables t ON c.object_id = t.object_id
        INNER JOIN sys.schemas s ON t.schema_id = s.schema_id
        WHERE t.name = ?
          AND s.name = ?
          AND c.is_computed = 1
        """
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(query, (table_name, schema))
            
            computed_cols = [row[0] for row in cursor.fetchall()]
            cursor.close()
            
            if computed_cols:
                logger.info(f"🔍 Found {len(computed_cols)} computed column(s) in {table_name}: {computed_cols}")
            
            return computed_cols
            
        except Exception as e:
            logger.warning(f"Could not detect computed columns for {table_name}: {e}")
            return []
    
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

    def bulk_insert_data(self, table_name: str, rows: List[tuple], 
                         identity_columns: List[str] = None) -> int:
        """
        Insert multiple rows into table, handling IDENTITY columns and computed columns
        
        Args:
            table_name: Name of the table
            rows: List of row tuples
            identity_columns: List of IDENTITY column names (optional)
            
        Returns:
            Number of rows inserted
        """
        if not rows:
            logger.warning(f"No data to insert into {table_name}")
            return 0
        
        try:
            # Get all table columns
            all_columns_info = self.get_table_columns(table_name)
            all_columns = [col['name'] for col in all_columns_info]
            
            # Detect computed columns (cannot be inserted)
            computed_columns = self.get_computed_columns(table_name)
            
            # Filter out computed columns from columns and data
            if computed_columns:
                logger.info(f"⏭️  Excluding {len(computed_columns)} computed column(s) from INSERT: {computed_columns}")
                
                # Filter columns list to exclude computed ones
                insertable_columns = [col for col in all_columns if col not in computed_columns]
                
                # Convert dictionary rows to tuples with only insertable columns
                filtered_rows = []
                for row in rows:
                    if isinstance(row, dict):
                        # Dictionary from Oracle - extract only insertable columns
                        filtered_row = tuple(row.get(col) for col in insertable_columns)
                    else:
                        # Already a tuple - filter by index
                        non_computed_indices = [idx for idx, col in enumerate(all_columns) if col not in computed_columns]
                        filtered_row = tuple(row[idx] for idx in non_computed_indices if idx < len(row))
                    filtered_rows.append(filtered_row)
                
                columns = insertable_columns
                rows = filtered_rows
            else:
                # No computed columns - convert dicts to tuples if needed
                columns = all_columns
                if rows and isinstance(rows[0], dict):
                    rows = [tuple(row.get(col) for col in columns) for row in rows]
            
            logger.info(f"Inserting data with columns: {columns}") 
            
            # Handle IDENTITY columns
            identity_enabled = False
            if identity_columns:
                logger.info(f"🔑 IDENTITY columns provided for {table_name}: {identity_columns}")
                identity_enabled = self.set_identity_insert(table_name, True)
                
                if not identity_enabled:
                    logger.warning(f"Could not enable IDENTITY_INSERT for {table_name}")
            
            try:
                # Execute batch insert
                logger.info(f"Executing batch insert of {len(rows)} rows...")
                row_count = self.insert_batch(table_name, columns, rows)
                
                # Note: IDENTITY reseeding is automatic in SQL Server after insert
                
                return row_count
                
            finally:
                # Always disable IDENTITY_INSERT if it was enabled
                if identity_enabled:
                    self.set_identity_insert(table_name, False)
                    
        except Exception as e:
            logger.error(f"Bulk insert failed for {table_name}: {e}")
            # Disable IDENTITY_INSERT in case of error
            if identity_columns:
                try:
                    self.set_identity_insert(table_name, False)
                except:
                    pass
            raise

    def get_table_row_count(self, table_name: str, schema: str = "dbo") -> int:
        """
        Get the number of rows in a table

        Args:
            table_name: Name of the table
            schema: Schema name (default: dbo)

        Returns:
            Number of rows
        """
        try:
            query = f"SELECT COUNT(*) FROM [{schema}].[{table_name}]"
            cursor = self.connection.cursor()
            cursor.execute(query)
            count = cursor.fetchone()[0]
            cursor.close()
            return count
        except Exception as e:
            logger.error(f"Failed to get row count for {table_name}: {e}")
            return 0

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
