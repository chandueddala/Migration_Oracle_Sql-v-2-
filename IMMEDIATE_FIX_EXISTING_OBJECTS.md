# IMMEDIATE FIX: Handle Existing Objects

## Quick Solution for Current Error

Your migration is failing because tables already exist. Here's the immediate fix:

### Option 1: Manual SQL Server Cleanup (FASTEST)

Run this in SQL Server Management Studio or Azure Data Studio:

```sql
-- Drop all existing tables
USE master;
GO

DROP TABLE IF EXISTS [LOANS];
DROP TABLE IF EXISTS [LOAN_AUDIT];
DROP TABLE IF EXISTS [LOAN_PAYMENTS];
DROP TABLE IF EXISTS [LOAN_SCHEDULE];
DROP TABLE IF EXISTS [STG_LOAN_APPS];
GO

-- Drop procedures if they exist
DROP PROCEDURE IF EXISTS [dbo].[sp_calculate_monthly_payment];
DROP PROCEDURE IF EXISTS [dbo].[sp_create_loan];
DROP PROCEDURE IF EXISTS [dbo].[sp_calculate_payment];
DROP PROCEDURE IF EXISTS [dbo].[sp_early_payoff_savings];
DROP PROCEDURE IF EXISTS [dbo].[sp_create_loan_from_json];
DROP PROCEDURE IF EXISTS [dbo].[sp_update_loan_from_json];
DROP PROCEDURE IF EXISTS [dbo].[sp_process_staging_batch];
GO
```

Then run your migration again: `python main.py`

---

### Option 2: Add Automated Cleanup (BETTER)

Create a new file to handle this automatically.

**File:** `utils/cleanup_existing.py`

```python
"""
Cleanup existing objects before migration
"""
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


def cleanup_existing_objects(sqlserver_creds: Dict, tables: List[str] = None, procedures: List[str] = None):
    """
    Drop existing tables and procedures before migration

    Args:
        sqlserver_creds: SQL Server credentials
        tables: List of table names to drop
        procedures: List of procedure names to drop
    """
    from database.sqlserver_connector import SQLServerConnector

    print("\n" + "="*70)
    print("CLEANUP: Removing Existing Objects")
    print("="*70)

    if not tables and not procedures:
        print("  ℹ️  No objects specified for cleanup")
        return

    conn = SQLServerConnector(sqlserver_creds)
    if not conn.connect():
        print("  ❌ Failed to connect to SQL Server")
        return

    # Drop tables
    if tables:
        print(f"\n  Dropping {len(tables)} tables...")
        for table in tables:
            try:
                sql = f"DROP TABLE IF EXISTS [{table}]"
                conn.connection.cursor().execute(sql)
                conn.connection.commit()
                print(f"    ✅ Dropped table: {table}")
            except Exception as e:
                print(f"    ⚠️  Could not drop {table}: {e}")

    # Drop procedures
    if procedures:
        print(f"\n  Dropping {len(procedures)} procedures...")
        for proc in procedures:
            try:
                sql = f"DROP PROCEDURE IF EXISTS [dbo].[{proc}]"
                conn.connection.cursor().execute(sql)
                conn.connection.commit()
                print(f"    ✅ Dropped procedure: {proc}")
            except Exception as e:
                print(f"    ⚠️  Could not drop {proc}: {e}")

    conn.disconnect()
    print("\n  ✅ Cleanup complete")


def ask_user_to_cleanup(tables: List[str], procedures: List[str] = None) -> bool:
    """
    Ask user if they want to drop existing objects

    Returns:
        True if user wants to cleanup, False otherwise
    """
    print("\n" + "="*70)
    print("⚠️  EXISTING OBJECTS DETECTED")
    print("="*70)

    if tables:
        print(f"\n  📋 Tables that will be dropped:")
        for table in tables:
            print(f"     - {table}")

    if procedures:
        print(f"\n  📋 Procedures that will be dropped:")
        for proc in procedures:
            print(f"     - {proc}")

    print(f"\n  ⚠️  Warning: This action cannot be undone!")
    print(f"     All data in these tables will be lost.")

    while True:
        choice = input(f"\n  Drop existing objects and continue? (yes/no): ").strip().lower()
        if choice in ['yes', 'y']:
            return True
        elif choice in ['no', 'n']:
            return False
        print("  Please enter 'yes' or 'no'")
```

**Usage in `utils/migration_workflow.py`:**

Add this before Step 5 (table migration):

```python
# Before migrating tables, check for existing objects
if tables_to_migrate:
    from utils.cleanup_existing import ask_user_to_cleanup, cleanup_existing_objects

    # Ask user if they want to cleanup
    if ask_user_to_cleanup(tables=tables_to_migrate):
        cleanup_existing_objects(
            sqlserver_creds=sqlserver_creds,
            tables=tables_to_migrate
        )
    else:
        print("\n  ⚠️  User chose not to cleanup. Migration may fail for existing objects.")
        print("     You can:")
        print("       1. Manually drop objects in SQL Server")
        print("       2. Select different tables")
        print("       3. Exit and cleanup later")

        proceed = input("\n  Continue anyway? (y/n): ").strip().lower()
        if proceed != 'y':
            print("\n  Migration cancelled by user")
            return
```

---

### Option 3: Add DROP IF EXISTS to Generated SQL (BEST)

Modify the converter agent to always include DROP statements.

**File:** `agents/converter_agent.py`

Find the `convert_table_ddl` method and update it:

```python
def convert_table_ddl(self, oracle_ddl: str, table_name: str) -> str:
    """Convert Oracle table DDL to SQL Server with DROP IF EXISTS"""

    # ... existing conversion code ...

    # Add DROP IF EXISTS at the beginning
    if 'CREATE TABLE' in tsql_code:
        drop_statement = f"-- Drop table if it exists\nDROP TABLE IF EXISTS [{table_name}];\nGO\n\n"
        tsql_code = drop_statement + tsql_code

    return tsql_code
```

---

## Recommended Approach

**Use Option 1 NOW, then implement Option 3 for future runs.**

### Step-by-Step:

1. **Right now:**
   ```sql
   -- Run this in SQL Server
   DROP TABLE IF EXISTS [LOANS];
   DROP TABLE IF EXISTS [LOAN_AUDIT];
   DROP TABLE IF EXISTS [LOAN_PAYMENTS];
   DROP TABLE IF EXISTS [LOAN_SCHEDULE];
   DROP TABLE IF EXISTS [STG_LOAN_APPS];
   GO
   ```

2. **Then run migration:**
   ```bash
   python main.py
   ```

3. **For future-proofing:**
   - Implement Option 2 (cleanup utility)
   - Implement Option 3 (auto DROP IF EXISTS)

---

## Complete Fix Script

Create: `cleanup_and_migrate.ps1`

```powershell
# Cleanup and Migration Script
Write-Host "=" * 70
Write-Host "CLEANUP AND MIGRATION"
Write-Host "=" * 70

# Step 1: Apply migration_engine fix if needed
Write-Host "`n1. Applying migration_engine fix..."
if (Test-Path ".\fix_migration_engine.ps1") {
    .\fix_migration_engine.ps1
} else {
    Write-Host "   ⚠️  fix_migration_engine.ps1 not found"
}

# Step 2: Cleanup SQL Server
Write-Host "`n2. Cleaning up existing objects..."
$cleanup = @"
DROP TABLE IF EXISTS [LOANS];
DROP TABLE IF EXISTS [LOAN_AUDIT];
DROP TABLE IF EXISTS [LOAN_PAYMENTS];
DROP TABLE IF EXISTS [LOAN_SCHEDULE];
DROP TABLE IF EXISTS [STG_LOAN_APPS];
GO
"@

Write-Host "   SQL Cleanup script:"
Write-Host $cleanup

$proceed = Read-Host "`n   Run cleanup on SQL Server? (y/n)"
if ($proceed -eq 'y') {
    # Save to temp file
    $cleanup | Out-File -FilePath "temp_cleanup.sql" -Encoding UTF8
    Write-Host "   ✅ Cleanup script saved to temp_cleanup.sql"
    Write-Host "   📋 Run this script in SQL Server Management Studio"
    Write-Host ""
    Write-Host "   Then press Enter to continue with migration..."
    Read-Host
}

# Step 3: Run migration
Write-Host "`n3. Starting migration..."
python main.py

Write-Host "`n✅ Process complete!"
```

---

## Usage

```powershell
# Quick fix NOW:
1. Open SQL Server Management Studio
2. Connect to your SQL Server
3. Run the DROP statements above
4. Run: python main.py

# OR use the script:
.\cleanup_and_migrate.ps1
```

---

## Why This Happens

1. **Previous migration ran successfully** for table structure
2. **Data migration failed** (the fetch_table_data error)
3. **Tables remain in SQL Server** from previous run
4. **New migration attempts** fail because tables exist

---

## Preventing Future Issues

After implementing the fixes:

1. ✅ DROP IF EXISTS will be automatic
2. ✅ User will be asked before dropping
3. ✅ Clear error messages
4. ✅ Option to skip or alter existing objects

---

**Run the SQL cleanup NOW, then your migration will work!** 🚀
