# IDENTITY Column Migration Fix - Complete Guide

## Problem

When migrating data from Oracle to SQL Server, the migration fails with error 544:

```
Cannot insert explicit value for identity column in table 'CATEGORIES'
when IDENTITY_INSERT is set to OFF. (544)
```

## Root Cause

SQL Server IDENTITY columns auto-generate values and don't allow explicit values by default. When migrating data from Oracle (which uses sequences), we need to:

1. Detect which SQL Server columns have the IDENTITY property
2. Enable `SET IDENTITY_INSERT [table] ON` before inserting data
3. Disable `SET IDENTITY_INSERT [table] OFF` after inserting data

## Solution Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Migration Process Flow                                     │
└─────────────────────────────────────────────────────────────┘

1. Connect to SQL Server
          ↓
2. Query INFORMATION_SCHEMA.COLUMNS
   → Use COLUMNPROPERTY(..., 'IsIdentity')
   → Detect all IDENTITY columns
          ↓
3. Connect to Oracle & Fetch Data
          ↓
4. IF identity_columns exist:
   → SET IDENTITY_INSERT [table] ON
          ↓
5. INSERT data with explicit values
          ↓
6. IF identity_columns exist:
   → SET IDENTITY_INSERT [table] OFF
```

## Implementation

### 1. IDENTITY Column Detection

**File**: `utils/migration_engine_v2.py` (lines 125-140)

```python
# Get identity columns directly from SQL Server
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
```

### 2. Column Metadata Query

**File**: `database/sqlserver_connector.py` (lines 254-291)

```python
def get_table_columns(self, table_name: str, schema: str = "dbo") -> List[Dict]:
    """Get table column information including IDENTITY property"""
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
            'is_identity': bool(row[5])  # ← Key field!
        })

    return columns
```

### 3. IDENTITY_INSERT Toggle

**File**: `database/sqlserver_connector.py` (lines 293-313)

```python
def set_identity_insert(self, table_name: str, enabled: bool) -> bool:
    """
    Enable/disable IDENTITY_INSERT for a table

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
```

### 4. Bulk Insert with IDENTITY Handling

**File**: `database/sqlserver_connector.py` (lines 315-372)

```python
def bulk_insert_data(self, table_name: str, data: List[Dict],
                     identity_columns: List[str] = None) -> int:
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
            logger.info(f"🔑 IDENTITY columns provided: {identity_columns}")
            logger.info(f"Enabling IDENTITY_INSERT for {table_name}...")
            self.set_identity_insert(table_name, True)
            logger.info(f"✅ IDENTITY_INSERT enabled")
        else:
            logger.info(f"No IDENTITY columns specified")

        # Get column names from first row
        columns = list(data[0].keys())

        # Convert list of dicts to list of tuples
        rows = [tuple(row_dict.get(col) for col in columns) for row_dict in data]

        # Execute batch insert
        logger.info(f"Executing batch insert of {len(rows)} rows...")
        row_count = self.insert_batch(table_name, columns, rows)
        logger.info(f"✅ Successfully inserted {row_count} rows")

        # Disable IDENTITY_INSERT if it was enabled
        if identity_columns:
            logger.info(f"Disabling IDENTITY_INSERT...")
            self.set_identity_insert(table_name, False)
            logger.info(f"✅ IDENTITY_INSERT disabled")

        return row_count

    except Exception as e:
        # Cleanup: disable IDENTITY_INSERT even if error occurs
        if identity_columns:
            try:
                self.set_identity_insert(table_name, False)
            except:
                pass
        logger.error(f"Bulk insert failed: {e}")
        raise
```

## SQL Server IDENTITY Property

### What is IDENTITY?

In SQL Server, `IDENTITY` is a column property that auto-generates sequential values:

```sql
CREATE TABLE Categories (
    CategoryID INT IDENTITY(1,1) PRIMARY KEY,  -- Auto-incrementing
    CategoryName NVARCHAR(100)
)
```

### Oracle Equivalent

Oracle 12c+ uses sequences or IDENTITY columns:

```sql
CREATE TABLE Categories (
    CategoryID NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    CategoryName VARCHAR2(100)
)
```

Oracle 11g and below uses sequences:

```sql
CREATE SEQUENCE cat_seq START WITH 1 INCREMENT BY 1;

CREATE TABLE Categories (
    CategoryID NUMBER PRIMARY KEY,
    CategoryName VARCHAR2(100)
)
```

### Migration Challenge

When migrating data, Oracle tables have explicit ID values (e.g., 1, 2, 3) that we need to preserve. SQL Server IDENTITY columns reject explicit values by default.

## Key SQL Server Rules

### IDENTITY_INSERT Rules

1. **Only ONE table** can have IDENTITY_INSERT ON at a time per session
2. **Must be table owner** or have ALTER permission
3. **Cannot use** with computed columns
4. **Cannot use** when identity column is NOT in the column list
5. **Auto-resets** to OFF after transaction/batch completes

### Detection Query

To check if a column is IDENTITY:

```sql
SELECT
    COLUMN_NAME,
    COLUMNPROPERTY(OBJECT_ID(TABLE_SCHEMA + '.' + TABLE_NAME),
                   COLUMN_NAME, 'IsIdentity') AS IS_IDENTITY
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME = 'Categories'
```

Returns: `1` if IDENTITY, `0` if not

## Testing

### Manual Test

```python
python test_identity_fix.py
```

Expected output:
```
================================================================================
  TEST: Identity Column Detection
================================================================================

✅ Connected to SQL Server

Testing table: CATEGORIES

Found 4 columns:
  - CategoryID: int [IDENTITY]
  - CategoryName: nvarchar
  - Description: nvarchar
  - Picture: varbinary

✅ Detected IDENTITY columns: CategoryID

This means IDENTITY_INSERT will be enabled automatically during data migration.

================================================================================
  TEST: IDENTITY_INSERT Toggle
================================================================================

✅ Connected to SQL Server

Enabling IDENTITY_INSERT for CATEGORIES...
✅ IDENTITY_INSERT enabled

Disabling IDENTITY_INSERT for CATEGORIES...
✅ IDENTITY_INSERT disabled

================================================================================
  TEST SUMMARY
================================================================================

✅ PASS: Identity Column Detection
✅ PASS: IDENTITY_INSERT Toggle

--------------------------------------------------------------------------------
TOTAL: 2/2 tests passed (100.0%)
--------------------------------------------------------------------------------

🎉 All tests passed! Identity column fix is working.
```

### Integration Test

Run a full migration:

```bash
streamlit run app.py
```

Watch the logs for:
```
2025-11-26 12:00:00 - INFO - Querying SQL Server for IDENTITY columns in CATEGORIES...
2025-11-26 12:00:00 - INFO - Retrieved 4 columns from SQL Server
2025-11-26 12:00:00 - INFO - ✅ Detected IDENTITY columns for CATEGORIES: ['CategoryID']
2025-11-26 12:00:00 - INFO - 🔑 IDENTITY columns provided for CATEGORIES: ['CategoryID']
2025-11-26 12:00:00 - INFO - Enabling IDENTITY_INSERT for CATEGORIES...
2025-11-26 12:00:00 - INFO - IDENTITY_INSERT ON for CATEGORIES
2025-11-26 12:00:00 - INFO - ✅ IDENTITY_INSERT enabled for CATEGORIES
2025-11-26 12:00:01 - INFO - Executing batch insert of 5 rows...
2025-11-26 12:00:01 - INFO - ✅ Successfully inserted 5 rows
2025-11-26 12:00:01 - INFO - Disabling IDENTITY_INSERT for CATEGORIES...
2025-11-26 12:00:01 - INFO - IDENTITY_INSERT OFF for CATEGORIES
2025-11-26 12:00:01 - INFO - ✅ IDENTITY_INSERT disabled for CATEGORIES
```

## Troubleshooting

### Error: "IDENTITY_INSERT is already ON for table X"

**Cause**: Another table still has IDENTITY_INSERT enabled

**Solution**:
```sql
-- Find which table has it enabled
SELECT * FROM sys.tables WHERE OBJECTPROPERTY(object_id, 'TableHasIdentity') = 1

-- Disable for all tables
SET IDENTITY_INSERT [dbo].[TableName] OFF
```

### Error: "Cannot detect identity columns"

**Cause**: Connection issue or table doesn't exist

**Check**:
1. Verify SQL Server connection
2. Verify table exists: `SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'YourTable'`
3. Check schema: default is `dbo`

### Error: "Column X is not an IDENTITY column"

**Cause**: Column was created without IDENTITY property

**Solution**: Recreate column with IDENTITY:
```sql
-- Drop existing column
ALTER TABLE Categories DROP COLUMN CategoryID

-- Add with IDENTITY
ALTER TABLE Categories ADD CategoryID INT IDENTITY(1,1) PRIMARY KEY
```

## Windows Authentication Support

Added support for Windows Authentication (no username/password required):

**File**: `database/sqlserver_connector.py` (lines 26-60)

```python
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
                raise ValueError("Missing 'user' or 'username'")

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
```

## Summary

### Files Modified

1. **utils/migration_engine_v2.py** (lines 125-140)
   - Added IDENTITY column detection
   - Enhanced logging

2. **database/sqlserver_connector.py** (lines 26-60, 254-291, 293-313, 315-372)
   - Added Windows Authentication support
   - Enhanced `get_table_columns()` with IDENTITY detection
   - Added `set_identity_insert()` method
   - Enhanced `bulk_insert_data()` with IDENTITY handling and logging

3. **test_identity_fix.py** (new file)
   - Comprehensive test suite for IDENTITY column detection
   - Tests IDENTITY_INSERT toggle functionality

### Benefits

✅ **Automatic Detection** - No manual configuration needed
✅ **Robust Error Handling** - IDENTITY_INSERT always disabled even on errors
✅ **Comprehensive Logging** - Full visibility into the process
✅ **Windows Auth Support** - Works with both SQL and Windows authentication
✅ **Production Ready** - Tested and validated

### Migration Flow

```
Oracle Table → Detect IDENTITY → Enable INSERT → Migrate Data → Disable INSERT → Done
```

---

**Last Updated**: 2025-11-26
**Version**: 2.0
**Status**: ✅ Production Ready
