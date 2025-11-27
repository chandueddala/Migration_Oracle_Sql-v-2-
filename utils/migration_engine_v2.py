"""
Migration Engine - Core functions for data migration and user selection
"""

import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def get_user_selection(object_type: str, items: List[str]) -> List[str]:
    """
    Allow user to select which objects to migrate
    
    Args:
        object_type: Type of objects (Tables, Procedures, Functions, etc.)
        items: List of object names
        
    Returns:
        List of selected object names
    """
    if not items:
        print(f"\n  ℹ️  No {object_type} found to migrate")
        return []
    
    print(f"\n{'='*70}")
    print(f"  SELECT {object_type.upper()} TO MIGRATE")
    print(f"{'='*70}")
    print(f"\n  Found {len(items)} {object_type.lower()}:\n")
    
    for idx, item in enumerate(items, 1):
        print(f"    {idx:2d}. {item}")
    
    print(f"\n  Options:")
    print(f"    - Enter numbers (e.g., 1,3,5)")
    print(f"    - Enter range (e.g., 1-5)")
    print(f"    - Enter 'all' for all {object_type.lower()}")
    print(f"    - Press Enter to skip")
    
    while True:
        selection = input(f"\n  Select {object_type.lower()} to migrate: ").strip()
        
        if not selection:
            print(f"  ⏭️  Skipping {object_type.lower()}")
            return []
        
        if selection.lower() == 'all':
            print(f"  ✅ Selected all {len(items)} {object_type.lower()}")
            return items
        
        try:
            selected_items = []
            
            # Handle comma-separated values and ranges
            parts = selection.split(',')
            for part in parts:
                part = part.strip()
                
                if '-' in part:
                    # Range (e.g., 1-5)
                    start, end = map(int, part.split('-'))
                    if 1 <= start <= len(items) and 1 <= end <= len(items):
                        selected_items.extend(items[start-1:end])
                    else:
                        raise ValueError(f"Range {start}-{end} out of bounds")
                else:
                    # Single number
                    idx = int(part)
                    if 1 <= idx <= len(items):
                        selected_items.append(items[idx-1])
                    else:
                        raise ValueError(f"Index {idx} out of bounds")
            
            if selected_items:
                print(f"  ✅ Selected {len(selected_items)} {object_type.lower()}:")
                for item in selected_items:
                    print(f"     - {item}")
                return selected_items
            else:
                print(f"  ⚠️  No valid selection made")
                return []
        
        except ValueError as e:
            print(f"  ❌ Invalid selection: {e}")
            print(f"     Please try again")


def migrate_table_data(
    oracle_creds: Dict[str, str],
    sqlserver_creds: Dict[str, str],
    table_name: str
) -> Dict[str, Any]:
    """
    Migrate data from Oracle table to SQL Server table
    
    Args:
        oracle_creds: Oracle connection credentials
        sqlserver_creds: SQL Server connection credentials
        table_name: Name of table to migrate
        
    Returns:
        Migration result dictionary
    """
    logger.info(f"Starting data migration for table: {table_name}")
    print(f"\n    📊 Migrating data for table: {table_name}")
    
    try:
        # Import connectors
        from database.oracle_connector import OracleConnector
        from database.sqlserver_connector import SQLServerConnector
        from database.migration_memory import MigrationMemory
        
        # Initialize
        oracle_conn = OracleConnector(oracle_creds)
        sqlserver_conn = SQLServerConnector(sqlserver_creds)
        
        # Connect to databases
        if not oracle_conn.connect():
            raise Exception("Failed to connect to Oracle database")
        if not sqlserver_conn.connect():
            raise Exception("Failed to connect to SQL Server database")
            
        memory = MigrationMemory()

        # Get identity columns directly from SQL Server metadata
        identity_cols = []
        try:
            logger.info(f"Querying SQL Server for IDENTITY columns in {table_name}...")
            table_info = sqlserver_conn.get_table_columns(table_name)
            logger.info(f"Retrieved {len(table_info)} columns from SQL Server")

            identity_cols = [col['name'] for col in table_info if col.get('is_identity')]

            if identity_cols:
                logger.info(f"✅ Detected IDENTITY columns for {table_name}: {identity_cols}")
                print(f"       🔑 IDENTITY columns detected: {', '.join(identity_cols)}")
            else:
                logger.info(f"No IDENTITY columns detected for {table_name}")
        except Exception as e:
            logger.error(f"❌ Could not detect identity columns: {e}", exc_info=True)
        
        # Fetch data from Oracle
        print(f"       📥 Fetching data from Oracle...")
        oracle_data = oracle_conn.fetch_table_data(table_name)
        
        if not oracle_data:
            logger.warning(f"No data found in Oracle table: {table_name}")
            return {
                "status": "success",
                "message": "No data to migrate (table is empty)",
                "rows_migrated": 0
            }
        
        rows_count = len(oracle_data)
        print(f"       ✅ Fetched {rows_count} rows from Oracle")
        
        # Get column names
        if rows_count > 0:
            columns = list(oracle_data[0].keys())
        else:
            columns = []
        
        # Insert data into SQL Server
        print(f"       📤 Inserting into SQL Server...")
        if identity_cols:
            print(f"       🔑 Handling IDENTITY columns: {', '.join(identity_cols)}")
        
        rows_inserted = sqlserver_conn.bulk_insert_data(
            table_name=table_name,
            rows=oracle_data,
            identity_columns=identity_cols
        )
        
        if rows_inserted == rows_count:
            print(f"       ✅ Successfully migrated {rows_inserted} rows")
            logger.info(f"Data migration completed for {table_name}: {rows_inserted} rows")
            
            return {
                "status": "success",
                "message": f"Successfully migrated {rows_inserted} rows",
                "rows_migrated": rows_inserted,
                "table_name": table_name
            }
        else:
            print(f"       ⚠️  Partial migration: {rows_inserted}/{rows_count} rows")
            logger.warning(f"Partial data migration for {table_name}: {rows_inserted}/{rows_count}")
            
            return {
                "status": "partial",
                "message": f"Migrated {rows_inserted} of {rows_count} rows",
                "rows_migrated": rows_inserted,
                "rows_expected": rows_count,
                "table_name": table_name
            }
    
    except Exception as  e:
        error_msg = f"Data migration failed for {table_name}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        print(f"       ❌ Error: {str(e)}")
        
        return {
            "status": "error",
            "message": error_msg,
            "error": str(e),
            "rows_migrated": 0,
            "table_name": table_name
        }


def validate_migration(
    sqlserver_creds: Dict[str, str],
    table_name: str,
    expected_rows: int
) -> Dict[str, Any]:
    """
    Validate that data was migrated correctly
    
    Args:
        sqlserver_creds: SQL Server connection credentials
        table_name: Name of table to validate
        expected_rows: Expected number of rows
        
    Returns:
        Validation result dictionary
    """
    try:
        from database.sqlserver_connector import SQLServerConnector
        
        sqlserver_conn = SQLServerConnector(sqlserver_creds)
        actual_rows = sqlserver_conn.get_row_count(table_name)
        
        if actual_rows == expected_rows:
            return {
                "status": "valid",
                "message": f"Row count matches: {actual_rows}",
                "expected": expected_rows,
                "actual": actual_rows
            }
        else:
            return {
                "status": "mismatch",
                "message": f"Row count mismatch: expected {expected_rows}, found {actual_rows}",
                "expected": expected_rows,
                "actual": actual_rows
            }
    
    except Exception as e:
        return {
            "status": "error",
            "message": f"Validation failed: {str(e)}",
            "error": str(e)
        }
