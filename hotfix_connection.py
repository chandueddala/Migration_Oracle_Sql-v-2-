"""
HOT-FIX: Patch migrate_table_data to ensure connections are established
"""
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

def migrate_table_data_fixed(
    oracle_creds: Dict[str, str],
    sqlserver_creds: Dict[str, str],
    table_name: str
) -> Dict[str, Any]:
    """
    FIXED version: Migrate data from Oracle table to SQL Server table
    This version ensures connections are established before use
    """
    logger.info(f"Starting data migration for table: {table_name}")
    print(f"\n    📊 Migrating data for table: {table_name}")

    try:
        # Import connectors
        from database.oracle_connector import OracleConnector
        from database.sqlserver_connector import SQLServerConnector
        from database.migration_memory import MigrationMemory

        # Initialize connectors
        oracle_conn = OracleConnector(oracle_creds)
        sqlserver_conn = SQLServerConnector(sqlserver_creds)
        memory = MigrationMemory()

        # ✅ CONNECT TO ORACLE
        if not oracle_conn.connect():
            logger.error(f"Failed to connect to Oracle for data migration")
            return {
                "status": "error",
                "message": "Failed to connect to Oracle",
                "rows_migrated": 0
            }

        # ✅ CONNECT TO SQL SERVER
        if not sqlserver_conn.connect():
            oracle_conn.disconnect()
            logger.error(f"Failed to connect to SQL Server for data migration")
            return {
                "status": "error",
                "message": "Failed to connect to SQL Server",
                "rows_migrated": 0
            }

        # Get identity columns (need special handling)
        identity_cols = memory.get_identity_columns(table_name)

        # Fetch data from Oracle
        print(f"       📥 Fetching data from Oracle...")
        oracle_data = oracle_conn.fetch_table_data(table_name)

        if not oracle_data:
            logger.warning(f"No data found in Oracle table: {table_name}")
            oracle_conn.disconnect()
            sqlserver_conn.disconnect()
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

        # Handle IDENTITY columns
        if identity_cols:
            print(f"       🔑 Handling IDENTITY columns: {', '.join(identity_cols)}")

        rows_inserted = sqlserver_conn.bulk_insert_data(
            table_name=table_name,
            data=oracle_data,
            identity_columns=identity_cols
        )

        # Clean up connections
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

        # Try to disconnect
        try:
            oracle_conn.disconnect()
        except:
            pass
        try:
            sqlserver_conn.disconnect()
        except:
            pass

        return {
            "status": "error",
            "message": error_msg,
            "rows_migrated": 0,
            "table_name": table_name
        }


# Apply monkey patch
try:
    import utils.migration_engine as migration_engine
    migration_engine.migrate_table_data = migrate_table_data_fixed
    print("✅ Hot-fix applied: migrate_table_data now establishes connections properly")
except Exception as e:
    print(f"⚠️  Hot-fix failed: {e}")
