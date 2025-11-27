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
            logger.error(f"Failed Query: {query}")
            if params:
                logger.error(f"Parameters: {params}")
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

        results = self.execute_query(query, (object_name, object_type))
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

    def get_code_object(self, object_name: str, object_type: str) -> str:
        """
        Get source code for any object type (wrapper)
        
        Args:
            object_name: Name of the object
            object_type: Object type (SEQUENCE, VIEW, PROCEDURE, etc.)
            
        Returns:
            Source code string
        """
        if object_type == 'SEQUENCE':
            return self.get_sequence_ddl(object_name)
        elif object_type == 'VIEW':
            return self.get_view_ddl(object_name)
        elif object_type == 'TABLE':
            return self.get_table_ddl(object_name)
        elif object_type == 'PACKAGE':
            return self.get_package_code(object_name)
        else:
            return self.get_object_code(object_name, object_type)

    def get_sequence_ddl(self, sequence_name: str) -> str:
        """
        Get DDL for a sequence
        
        Skips internal Oracle identity sequences (ISEQ$$_%) as they are
        automatically handled via IDENTITY columns in SQL Server.
        
        Args:
            sequence_name: Name of the sequence
            
        Returns:
            DDL string, or skip message for internal sequences
        """
        # Check if this is an internal Oracle identity sequence
        if sequence_name.startswith('ISEQ$$_'):
            logger.info(f"⏭️  Skipping internal Oracle identity sequence {sequence_name} – handled via IDENTITY column in SQL Server")
            return "-- SKIP: Internal Oracle identity sequence - handled via IDENTITY column in SQL Server"
        
        try:
            query = f"SELECT DBMS_METADATA.GET_DDL('SEQUENCE', '{sequence_name}') FROM DUAL"
            result = self.execute_query(query)
            if result:
                return result[0][0].read() if hasattr(result[0][0], 'read') else str(result[0][0])
            return ""
        except Exception as e:
            error_str = str(e)
            # ORA-31603: object "sequence_name" of type SEQUENCE not found in schema "user"
            # This can happen for internal sequences that aren't accessible via DBMS_METADATA
            if 'ORA-31603' in error_str:
                logger.warning(f"⏭️  Skipping sequence {sequence_name} (ORA-31603 - likely internal identity sequence)")
                return "-- SKIP: Internal Oracle sequence (ORA-31603) - handled via IDENTITY column in SQL Server"
            else:
                # Re-raise other errors
                logger.error(f"Failed to get DDL for sequence {sequence_name}: {e}")
                raise

    def get_view_ddl(self, view_name: str) -> str:
        """Get DDL for a view"""
        query = f"SELECT DBMS_METADATA.GET_DDL('VIEW', '{view_name}') FROM DUAL"
        result = self.execute_query(query)
        if result:
            return result[0][0].read() if hasattr(result[0][0], 'read') else str(result[0][0])
        return ""


    
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
    
    def list_sequences(self) -> List[str]:
        """
        Get list of all user-created sequences

        Excludes Oracle system-generated sequences:
        - ISEQ$$_ prefix (Oracle 12c+ IDENTITY column sequences)
        """
        query = """
        SELECT SEQUENCE_NAME
        FROM USER_SEQUENCES
        WHERE SEQUENCE_NAME NOT LIKE 'ISEQ$$_%'
        ORDER BY SEQUENCE_NAME
        """
        results = self.execute_query(query)
        return [row[0] for row in results]
    
    def list_views(self) -> List[str]:
        """Get list of all views"""
        query = """
        SELECT VIEW_NAME
        FROM USER_VIEWS
        ORDER BY VIEW_NAME
        """
        results = self.execute_query(query)
        return [row[0] for row in results]
    
    def discover_foreign_keys(self, schema: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Discover all foreign key constraints from Oracle
        
        Queries ALL_CONSTRAINTS and ALL_CONS_COLUMNS to get complete FK metadata
        including child table, child columns, parent table, parent columns, and delete rules.
        
        Args:
            schema: Optional schema name (default: current user)
            
        Returns:
            List of dictionaries with FK metadata:
            {
                'constraint_name': str,
                'child_schema': str,
                'child_table': str,
                'child_columns': List[str],
                'parent_schema': str,
                'parent_table': str,
                'parent_columns': List[str],
                'delete_rule': str,  # CASCADE, SET NULL, NO ACTION
                'status': str  # ENABLED, DISABLED
            }
        """
        # Use current user schema if not specified
        schema_clause = "ac.owner = :schema" if schema else "ac.owner = USER"
        schema_param = {'schema': schema.upper()} if schema else {}
        
        # Query to get FK constraints with child and parent info
        query = f"""
        WITH fk_constraints AS (
            SELECT 
                ac.owner as child_schema,
                ac.constraint_name,
                ac.table_name as child_table,
                ac.r_constraint_name as parent_constraint,
                ac.delete_rule,
                ac.status
            FROM all_constraints ac
            WHERE {schema_clause}
              AND ac.constraint_type = 'R'
        ),
        child_columns AS (
            SELECT 
                constraint_name,
                LISTAGG(column_name, ',') WITHIN GROUP (ORDER BY position) as columns
            FROM all_cons_columns
            WHERE owner = :schema OR owner = USER
            GROUP BY constraint_name
        ),
        parent_info AS (
            SELECT 
                ac.constraint_name,
                ac.owner as parent_schema,
                ac.table_name as parent_table
            FROM all_constraints ac
        )
        SELECT 
            fk.child_schema,
            fk.constraint_name,
            fk.child_table,
            cc.columns as child_columns,
            pi.parent_schema,
            pi.parent_table,
            pc.columns as parent_columns,
            fk.delete_rule,
            fk.status
        FROM fk_constraints fk
        JOIN child_columns cc ON fk.constraint_name = cc.constraint_name
        JOIN parent_info pi ON fk.parent_constraint = pi.constraint_name
        JOIN child_columns pc ON fk.parent_constraint = pc.constraint_name
        ORDER BY fk.constraint_name
        """
        
        try:
            results = self.execute_query(query, tuple(schema_param.values()) if schema_param else None)
            
            foreign_keys = []
            for row in results:
                fk = {
                    'constraint_name': row[1],
                    'child_schema': row[0],
                    'child_table': row[2],
                    'child_columns': row[3].split(',') if row[3] else [],
                    'parent_schema': row[4],
                    'parent_table': row[5],
                    'parent_columns': row[6].split(',') if row[6] else [],
                    'delete_rule': row[7] if row[7] else 'NO ACTION',
                    'status': row[8]
                }
                foreign_keys.append(fk)
            
            logger.info(f"✅ Discovered {len(foreign_keys)} foreign key constraint(s)")
            return foreign_keys
            
        except Exception as e:
            logger.error(f"Failed to discover foreign keys: {e}")
            return []
    
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
        # Set arraysize for efficient batch fetching (does NOT limit total rows)
        cursor.arraysize = 1000

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
            # Convert LOB objects to strings/bytes
            converted_row = []
            for value in row:
                if value is not None and hasattr(value, 'read'):
                    # This is a LOB object (CLOB/BLOB)
                    try:
                        lob_data = value.read()
                        converted_row.append(lob_data)
                    except:
                        converted_row.append(None)
                else:
                    converted_row.append(value)

            row_dict = dict(zip(columns, converted_row))
            result.append(row_dict)

        return result

    def get_table_row_count(self, table_name: str) -> int:
        """
        Get the number of rows in a table

        Args:
            table_name: Name of the table

        Returns:
            Number of rows
        """
        try:
            cursor = self.connection.cursor()
            query = f"SELECT COUNT(*) FROM {table_name}"
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
