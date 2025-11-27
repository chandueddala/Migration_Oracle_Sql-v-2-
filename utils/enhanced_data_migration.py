"""
Enhanced Data Migration Module
Robust table data migration with validation, verification, and detailed reporting
"""

import logging
from typing import Dict, List, Tuple, Optional
from database.oracle_connector import OracleConnector
from database.sqlserver_connector import SQLServerConnector

logger = logging.getLogger(__name__)


class DataMigrationResult:
    """Data migration result with detailed metrics"""

    def __init__(self, table_name: str):
        self.table_name = table_name
        self.status = "pending"  # pending, success, failed, partial
        self.oracle_row_count = 0
        self.sqlserver_row_count = 0
        self.rows_migrated = 0
        self.has_identity = False
        self.identity_columns = []
        self.duration_seconds = 0
        self.error_message = None
        self.validation_passed = False

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "table_name": self.table_name,
            "status": self.status,
            "oracle_row_count": self.oracle_row_count,
            "sqlserver_row_count": self.sqlserver_row_count,
            "rows_migrated": self.rows_migrated,
            "has_identity": self.has_identity,
            "identity_columns": self.identity_columns,
            "duration_seconds": self.duration_seconds,
            "error_message": self.error_message,
            "validation_passed": self.validation_passed,
            "row_count_match": self.oracle_row_count == self.sqlserver_row_count
        }


def validate_table_data(
    oracle_conn: OracleConnector,
    sqlserver_conn: SQLServerConnector,
    table_name: str
) -> Tuple[bool, str]:
    """
    Validate that data was migrated correctly

    Returns:
        (success, message)
    """
    try:
        # Get row counts
        oracle_count = oracle_conn.get_table_row_count(table_name)
        sqlserver_count = sqlserver_conn.get_table_row_count(table_name)

        if oracle_count == sqlserver_count:
            return True, f"Row count matches: {oracle_count:,} rows"
        else:
            return False, f"Row count mismatch: Oracle={oracle_count:,}, SQL Server={sqlserver_count:,}"

    except Exception as e:
        return False, f"Validation error: {str(e)}"


def migrate_table_data_enhanced(
    oracle_creds: Dict,
    sqlserver_creds: Dict,
    table_name: str,
    batch_size: int = 1000,
    validate_after: bool = True
) -> DataMigrationResult:
    """
    Enhanced table data migration with validation and detailed reporting

    Args:
        oracle_creds: Oracle database credentials
        sqlserver_creds: SQL Server database credentials
        table_name: Name of table to migrate
        batch_size: Number of rows per batch
        validate_after: Whether to validate row counts after migration

    Returns:
        DataMigrationResult object
    """
    import time

    result = DataMigrationResult(table_name)
    start_time = time.time()

    oracle_conn = None
    sqlserver_conn = None

    try:
        # Step 1: Connect to databases
        logger.info(f"Starting data migration for table: {table_name}")

        oracle_conn = OracleConnector(oracle_creds)
        sqlserver_conn = SQLServerConnector(sqlserver_creds)

        if not oracle_conn.connect():
            raise Exception("Failed to connect to Oracle database")
        if not sqlserver_conn.connect():
            raise Exception("Failed to connect to SQL Server database")

        # Step 2: Get Oracle row count
        logger.info(f"Counting rows in Oracle table {table_name}...")
        result.oracle_row_count = oracle_conn.get_table_row_count(table_name)
        logger.info(f"Oracle table has {result.oracle_row_count:,} rows")

        if result.oracle_row_count == 0:
            logger.warning(f"Table {table_name} is empty in Oracle")
            result.status = "success"
            result.duration_seconds = time.time() - start_time
            return result

        # Step 3: Detect IDENTITY columns in SQL Server
        logger.info(f"Detecting IDENTITY columns in SQL Server table {table_name}...")
        try:
            table_info = sqlserver_conn.get_table_columns(table_name)
            result.identity_columns = [col['name'] for col in table_info if col.get('is_identity')]
            result.has_identity = len(result.identity_columns) > 0

            if result.has_identity:
                logger.info(f"✅ Detected IDENTITY columns: {result.identity_columns}")
            else:
                logger.info("No IDENTITY columns detected")
        except Exception as e:
            logger.warning(f"Could not detect IDENTITY columns: {e}")

        # Step 4: Fetch data from Oracle
        logger.info(f"Fetching data from Oracle table {table_name}...")
        oracle_data = oracle_conn.fetch_table_data(table_name)

        if not oracle_data:
            logger.warning(f"No data fetched from Oracle table {table_name}")
            result.status = "success"
            result.duration_seconds = time.time() - start_time
            return result

        logger.info(f"✅ Fetched {len(oracle_data):,} rows from Oracle")

        # Step 5: Insert data into SQL Server (with IDENTITY handling)
        logger.info(f"Inserting data into SQL Server table {table_name}...")

        if result.has_identity:
            logger.info(f"🔑 Enabling IDENTITY_INSERT for columns: {result.identity_columns}")

        rows_inserted = sqlserver_conn.bulk_insert_data(
            table_name=table_name,
            data=oracle_data,
            identity_columns=result.identity_columns if result.has_identity else None
        )

        result.rows_migrated = rows_inserted
        logger.info(f"✅ Successfully inserted {rows_inserted:,} rows into SQL Server")

        # Step 6: Validate data
        if validate_after:
            logger.info(f"Validating data migration for {table_name}...")
            result.sqlserver_row_count = sqlserver_conn.get_table_row_count(table_name)

            if result.oracle_row_count == result.sqlserver_row_count:
                result.validation_passed = True
                result.status = "success"
                logger.info(f"✅ Validation passed: {result.sqlserver_row_count:,} rows match")
            else:
                result.validation_passed = False
                result.status = "partial"
                logger.warning(
                    f"⚠️ Row count mismatch: Oracle={result.oracle_row_count:,}, "
                    f"SQL Server={result.sqlserver_row_count:,}"
                )
        else:
            result.status = "success"

        result.duration_seconds = time.time() - start_time
        logger.info(f"✅ Data migration completed in {result.duration_seconds:.2f} seconds")

        return result

    except Exception as e:
        result.status = "failed"
        result.error_message = str(e)
        result.duration_seconds = time.time() - start_time

        logger.error(f"❌ Data migration failed for {table_name}: {e}", exc_info=True)
        return result

    finally:
        # Cleanup connections
        if oracle_conn:
            try:
                oracle_conn.disconnect()
            except:
                pass
        if sqlserver_conn:
            try:
                sqlserver_conn.disconnect()
            except:
                pass


def get_table_preview(
    oracle_creds: Dict,
    table_name: str,
    limit: int = 5
) -> List[Dict]:
    """
    Get preview of table data from Oracle

    Args:
        oracle_creds: Oracle credentials
        table_name: Table name
        limit: Number of rows to preview

    Returns:
        List of row dictionaries
    """
    try:
        oracle_conn = OracleConnector(oracle_creds)
        if not oracle_conn.connect():
            return []

        query = f"SELECT * FROM {table_name} WHERE ROWNUM <= {limit}"
        results = oracle_conn.execute_query(query)

        # Get column names
        columns = [desc[0] for desc in oracle_conn.connection.cursor().description] if results else []

        # Convert to list of dicts
        preview = []
        for row in results[:limit]:
            preview.append(dict(zip(columns, row)))

        oracle_conn.disconnect()
        return preview

    except Exception as e:
        logger.error(f"Failed to get table preview: {e}")
        return []


def compare_table_schemas(
    oracle_conn: OracleConnector,
    sqlserver_conn: SQLServerConnector,
    table_name: str
) -> Dict:
    """
    Compare schemas between Oracle and SQL Server

    Returns:
        Dict with comparison results
    """
    try:
        # Get Oracle columns
        oracle_query = f"""
            SELECT column_name, data_type, nullable
            FROM user_tab_columns
            WHERE table_name = UPPER('{table_name}')
            ORDER BY column_id
        """
        oracle_cols = oracle_conn.execute_query(oracle_query)

        # Get SQL Server columns
        sqlserver_cols = sqlserver_conn.get_table_columns(table_name)

        return {
            "oracle_column_count": len(oracle_cols),
            "sqlserver_column_count": len(sqlserver_cols),
            "column_count_match": len(oracle_cols) == len(sqlserver_cols),
            "oracle_columns": [col[0] for col in oracle_cols],
            "sqlserver_columns": [col['name'] for col in sqlserver_cols]
        }

    except Exception as e:
        logger.error(f"Schema comparison failed: {e}")
        return {
            "error": str(e)
        }
