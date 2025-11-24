"""
Hotfix for Data Migration Issues

This script ensures table data is migrated correctly by:
1. Properly establishing database connections
2. Handling all data types correctly
3. Managing identity columns
4. Providing detailed progress feedback
"""

import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


def migrate_table_data_fixed(
    oracle_creds: Dict[str, str],
    sqlserver_creds: Dict[str, str],
    table_name: str
) -> Dict[str, Any]:
    """
    Fixed version of data migration that ensures connections are established

    Args:
        oracle_creds: Oracle connection credentials
        sqlserver_creds: SQL Server connection credentials
        table_name: Name of table to migrate

    Returns:
        Migration result dictionary
    """
    from database.oracle_connector import OracleConnector
    from database.sqlserver_connector import SQLServerConnector
    from database.migration_memory import MigrationMemory

    logger.info(f"Starting data migration for table: {table_name}")
    print(f"\n    📊 Migrating data for table: {table_name}")

    oracle_conn = None
    sqlserver_conn = None

    try:
        # IMPORTANT: Establish connections first!
        oracle_conn = OracleConnector(oracle_creds)
        if not oracle_conn.connect():
            raise ConnectionError("Failed to connect to Oracle database")
        logger.info("✅ Oracle connection established")

        sqlserver_conn = SQLServerConnector(sqlserver_creds)
        if not sqlserver_conn.connect():
            raise ConnectionError("Failed to connect to SQL Server database")
        logger.info("✅ SQL Server connection established")

        # Get identity columns from memory
        memory = MigrationMemory()
        identity_cols = memory.get_identity_columns(table_name)

        # Fetch data from Oracle
        print(f"       📥 Fetching data from Oracle...")
        oracle_data = oracle_conn.fetch_table_data(table_name)

        if not oracle_data or len(oracle_data) == 0:
            logger.warning(f"No data found in Oracle table: {table_name}")
            print(f"       ℹ️  Table is empty (0 rows)")

            # Close connections
            oracle_conn.disconnect()
            sqlserver_conn.disconnect()

            return {
                "status": "success",
                "message": "Table is empty - no data to migrate",
                "rows_migrated": 0,
                "table_name": table_name
            }

        rows_count = len(oracle_data)
        print(f"       ✅ Fetched {rows_count} rows from Oracle")
        logger.info(f"Fetched {rows_count} rows from {table_name}")

        # Get column names
        columns = list(oracle_data[0].keys())
        logger.info(f"Columns: {', '.join(columns)}")

        # Insert data into SQL Server
        print(f"       📤 Inserting into SQL Server...")

        # Handle IDENTITY columns
        if identity_cols:
            print(f"       🔑 Handling IDENTITY columns: {', '.join(identity_cols)}")
            logger.info(f"Identity columns for {table_name}: {identity_cols}")

        # Use bulk insert
        rows_inserted = sqlserver_conn.bulk_insert_data(
            table_name=table_name,
            columns=columns,
            rows=oracle_data,
            identity_columns=identity_cols
        )

        # Close connections
        oracle_conn.disconnect()
        sqlserver_conn.disconnect()

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

    except Exception as e:
        error_msg = f"Data migration failed for {table_name}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        print(f"       ❌ Error: {str(e)}")

        # Clean up connections
        try:
            if oracle_conn:
                oracle_conn.disconnect()
            if sqlserver_conn:
                sqlserver_conn.disconnect()
        except:
            pass

        return {
            "status": "error",
            "message": error_msg,
            "error": str(e),
            "rows_migrated": 0,
            "table_name": table_name
        }


# Update the quick_migrate.py to use this fixed version
if __name__ == "__main__":
    print("This is a hotfix module. Import it in quick_migrate.py:")
    print()
    print("  from hotfix_data_migration import migrate_table_data_fixed as migrate_table_data")
    print()
    print("Then use migrate_table_data() as normal.")
