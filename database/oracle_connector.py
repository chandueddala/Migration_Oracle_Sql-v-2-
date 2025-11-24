"""
Oracle Database Connector
Handles all Oracle database connections and operations
"""

import logging
import oracledb
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class OracleConnector:
    """Oracle database connection and operations"""
    
    def __init__(self, credentials: Dict[str, str]):
        """
        Initialize Oracle connector
        
        Args:
            credentials: Dict with host, port, service_name, user, password
        """
        self.credentials = credentials
        self.connection = None
        
    def connect(self) -> bool:
        """Establish connection to Oracle database"""
        try:
            # Support both 'user' and 'username' keys for flexibility
            username = self.credentials.get('user') or self.credentials.get('username')
            if not username:
                raise ValueError("Missing 'user' or 'username' in credentials")

            self.connection = oracledb.connect(
                user=username,
                password=self.credentials['password'],
                dsn=f"{self.credentials['host']}:{self.credentials['port']}/{self.credentials['service_name']}"
            )
            logger.info("✅ Oracle connection established")
            return True
        except KeyError as e:
            logger.error(f"❌ Oracle connection failed - Missing credential: {e}")
            return False
        except ValueError as e:
            logger.error(f"❌ Oracle connection failed - {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Oracle connection failed: {e}")
            return False
    
    def disconnect(self):
        """Close Oracle connection"""
        if self.connection:
            self.connection.close()
            logger.info("Oracle connection closed")
    
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
    
    def get_table_ddl(self, table_name: str) -> str:
        """
        Get DDL for a table
        
        Args:
            table_name: Name of the table
            
        Returns:
            DDL string
        """
        query = f"""
        SELECT DBMS_METADATA.GET_DDL('TABLE', '{table_name}') FROM DUAL
        """
        result = self.execute_query(query)
        if result:
            return result[0][0].read() if hasattr(result[0][0], 'read') else str(result[0][0])
        return ""
    
    def get_package_code(self, package_name: str) -> str:
        """
        Get source code for a package (both spec and body)

        Args:
            package_name: Name of the package

        Returns:
            Combined source code (spec + body)
        """
        query = """
        SELECT TEXT
        FROM USER_SOURCE
        WHERE NAME = :name AND TYPE IN ('PACKAGE', 'PACKAGE BODY')
        ORDER BY TYPE DESC, LINE
        """
        results = self.execute_query(query, (package_name,))
        return ''.join([row[0] for row in results])

    def get_object_code(self, object_name: str, object_type: str) -> str:
        """
        Get source code for procedures, functions, triggers

        Args:
            object_name: Name of the object
            object_type: PROCEDURE, FUNCTION, TRIGGER, PACKAGE

        Returns:
            Source code string
        """
        query = """
        SELECT TEXT
        FROM USER_SOURCE 
        WHERE NAME = :name AND TYPE = :type
        ORDER BY LINE
        """
        results = self.execute_query(query, (object_name, object_type))
        return ''.join([row[0] for row in results])
    
    def list_tables(self) -> List[str]:
        """Get list of all user tables"""
        query = """
        SELECT TABLE_NAME 
        FROM USER_TABLES 
        WHERE TABLE_NAME NOT LIKE 'BIN$%'
        ORDER BY TABLE_NAME
        """
        results = self.execute_query(query)
        return [row[0] for row in results]
    
    def list_procedures(self) -> List[str]:
        """Get list of all procedures"""
        query = """
        SELECT OBJECT_NAME 
        FROM USER_OBJECTS 
        WHERE OBJECT_TYPE = 'PROCEDURE'
        ORDER BY OBJECT_NAME
        """
        results = self.execute_query(query)
        return [row[0] for row in results]
    
    def list_functions(self) -> List[str]:
        """Get list of all functions"""
        query = """
        SELECT OBJECT_NAME 
        FROM USER_OBJECTS 
        WHERE OBJECT_TYPE = 'FUNCTION'
        ORDER BY OBJECT_NAME
        """
        results = self.execute_query(query)
        return [row[0] for row in results]
    
    def list_triggers(self) -> List[str]:
        """Get list of all triggers"""
        query = """
        SELECT TRIGGER_NAME
        FROM USER_TRIGGERS
        ORDER BY TRIGGER_NAME
        """
        results = self.execute_query(query)
        return [row[0] for row in results]

    def list_packages(self) -> List[str]:
        """Get list of all packages"""
        query = """
        SELECT OBJECT_NAME
        FROM USER_OBJECTS
        WHERE OBJECT_TYPE = 'PACKAGE'
        ORDER BY OBJECT_NAME
        """
        results = self.execute_query(query)
        return [row[0] for row in results]
    
    def get_table_data(self, table_name: str, batch_size: int = 1000):
        """
        Generator to fetch table data in batches

        Args:
            table_name: Name of the table
            batch_size: Number of rows per batch

        Yields:
            Batches of rows
        """
        cursor = self.connection.cursor()
        cursor.arraysize = batch_size

        query = f"SELECT * FROM {table_name}"
        cursor.execute(query)

        while True:
            rows = cursor.fetchmany(batch_size)
            if not rows:
                break
            yield rows

        cursor.close()

    def fetch_table_data(self, table_name: str):
        """
        Fetch all table data as a list of dictionaries

        This is different from get_table_data which returns a generator.
        This method loads all data into memory and returns it as a list.

        Args:
            table_name: Name of the table

        Returns:
            List of dictionaries (one per row)
        """
        cursor = self.connection.cursor()

        query = f"SELECT * FROM {table_name}"
        cursor.execute(query)

        # Get column names
        columns = [col[0] for col in cursor.description]

        # Fetch all rows
        rows = cursor.fetchall()
        cursor.close()

        # Convert to list of dictionaries
        result = []
        for row in rows:
            row_dict = dict(zip(columns, row))
            result.append(row_dict)

        return result

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()


def test_oracle_connection(credentials: Dict[str, str]) -> bool:
    """
    Test Oracle database connection
    
    Args:
        credentials: Oracle connection credentials
        
    Returns:
        True if connection successful
    """
    try:
        with OracleConnector(credentials) as conn:
            result = conn.execute_query("SELECT 1 FROM DUAL")
            return len(result) > 0
    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        return False
