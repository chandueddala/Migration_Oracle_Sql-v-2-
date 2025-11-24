"""
Database Module
Handles all database connections and operations

Connectors:
    - OracleConnector: Oracle database operations
    - SQLServerConnector: SQL Server operations
    - test_oracle_connection: Test Oracle connection
    - test_sqlserver_connection: Test SQL Server connection

Tools:
    - deploy_to_sqlserver: LangChain tool for deploying SQL to SQL Server

Metadata:
    - metadata_builder: Oracle metadata extraction
    - migration_memory: Memory data structures

Legacy Support:
    - oracle_connection: Context manager for Oracle connections
    - sqlserver_connection: Context manager for SQL Server connections
    - collect_credentials: Collect database credentials from user
    - validate_credentials: Validate database connections
    - discover_oracle_schema: Discover Oracle schema objects
    - discover_oracle_tables: Discover Oracle tables
    - get_oracle_code: Get Oracle code for database objects
    - get_oracle_table_ddl: Get Oracle table DDL
"""

from contextlib import contextmanager
from .oracle_connector import OracleConnector, test_oracle_connection
from .sqlserver_connector import SQLServerConnector, test_sqlserver_connection
from .deploy_tool import deploy_to_sqlserver


# ============================================================================
# Context Managers for Legacy Support
# ============================================================================

@contextmanager
def oracle_connection(credentials):
    """
    Context manager for Oracle connections

    Args:
        credentials: Dictionary with Oracle connection credentials

    Yields:
        Oracle connection object
    """
    conn = OracleConnector(credentials)
    if not conn.connect():
        raise ConnectionError("Failed to connect to Oracle")
    try:
        yield conn.connection
    finally:
        conn.disconnect()


@contextmanager
def sqlserver_connection(credentials):
    """
    Context manager for SQL Server connections

    Args:
        credentials: Dictionary with SQL Server connection credentials

    Yields:
        SQL Server connection object
    """
    conn = SQLServerConnector(credentials)
    if not conn.connect():
        raise ConnectionError("Failed to connect to SQL Server")
    try:
        yield conn.connection
    finally:
        conn.disconnect()


# ============================================================================
# Legacy Support Functions (Import from migration_workflow)
# ============================================================================

def collect_credentials():
    """
    Collect database credentials from user
    Import from utils.migration_workflow for backward compatibility
    """
    from utils.migration_workflow import collect_credentials as _collect
    return _collect()


def validate_credentials(oracle_creds, sqlserver_creds):
    """
    Validate database connections
    Import from utils.migration_workflow for backward compatibility
    """
    from utils.migration_workflow import validate_credentials as _validate
    return _validate(oracle_creds, sqlserver_creds)


def discover_oracle_schema(oracle_creds):
    """
    Discover Oracle schema objects
    Import from utils.migration_workflow for backward compatibility
    """
    from utils.migration_workflow import discover_oracle_schema as _discover
    return _discover(oracle_creds)


def discover_oracle_tables(oracle_creds):
    """
    Discover Oracle tables
    Import from utils.migration_workflow for backward compatibility
    """
    from utils.migration_workflow import discover_oracle_tables as _discover
    return _discover(oracle_creds)


# ============================================================================
# LangChain Tool Wrappers for Legacy Support
# ============================================================================

from langchain_core.tools import tool
import json


@tool
def get_oracle_code(credentials_json: str, object_name: str, object_type: str):
    """
    Get Oracle code for a database object

    Args:
        credentials_json: JSON string with Oracle credentials
        object_name: Name of the database object
        object_type: Type (PROCEDURE, FUNCTION, TRIGGER, PACKAGE)

    Returns:
        Dictionary with status and code
    """
    credentials = json.loads(credentials_json)
    conn = OracleConnector(credentials)
    if not conn.connect():
        return {"status": "error", "message": "Connection failed"}

    try:
        if object_type == "PROCEDURE":
            code = conn.get_procedure_code(object_name)
        elif object_type == "FUNCTION":
            code = conn.get_function_code(object_name)
        elif object_type == "TRIGGER":
            code = conn.get_trigger_code(object_name)
        elif object_type == "PACKAGE":
            code = conn.get_package_code(object_name)
        else:
            return {"status": "error", "message": f"Unsupported object type: {object_type}"}

        return {"status": "success", "code": code}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        conn.disconnect()


@tool
def get_oracle_table_ddl(credentials_json: str, table_name: str):
    """
    Get Oracle table DDL

    Args:
        credentials_json: JSON string with Oracle credentials
        table_name: Name of the table

    Returns:
        Dictionary with status and DDL
    """
    credentials = json.loads(credentials_json)
    conn = OracleConnector(credentials)
    if not conn.connect():
        return {"status": "error", "message": "Connection failed"}

    try:
        ddl = conn.get_table_ddl(table_name)
        return {"status": "success", "ddl": ddl}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        conn.disconnect()


__all__ = [
    'OracleConnector',
    'SQLServerConnector',
    'test_oracle_connection',
    'test_sqlserver_connection',
    'deploy_to_sqlserver',
    'oracle_connection',
    'sqlserver_connection',
    'collect_credentials',
    'validate_credentials',
    'discover_oracle_schema',
    'discover_oracle_tables',
    'get_oracle_code',
    'get_oracle_table_ddl'
]
