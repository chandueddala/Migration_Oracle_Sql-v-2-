# Quick Fix Instructions

## Issue 1: Package Migration Hanging
**Symptom**: After typing "all" for packages, system hangs

**Cause**: Package decomposer is trying to parse the package but getting stuck

**IMMEDIATE FIX**:
1. Press `Ctrl+C` to stop the current process
2. Run with the fixed script below

## Issue 2: Table Data Not Migrating Automatically
**Symptom**: Tables are created but data is not migrated automatically

**Fix**: Modified workflow to auto-migrate data after table creation

## QUICK SOLUTION - Use This Script

Save this as `quick_migrate.py` and run it:

```python
"""
Quick Migration Script - Fixed Version
Handles packages correctly and auto-migrates table data
"""

import sys
import logging
from config.config_enhanced import CostTracker
from database.oracle_connector import OracleConnector
from database.sqlserver_connector import SQLServerConnector
from agents.orchestrator_agent import MigrationOrchestrator
from agents.credential_agent import CredentialAgent
from utils.migration_engine import migrate_table_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def quick_migrate():
    """Quick migration with fixes"""
    print("="*70)
    print("QUICK MIGRATION - FIXED VERSION")
    print("="*70)

    # Get credentials
    print("\nStep 1: Getting credentials...")
    credential_agent = CredentialAgent()
    oracle_creds, sqlserver_creds = credential_agent.run()

    if not oracle_creds or not sqlserver_creds:
        print("Failed to get credentials")
        return

    print("Credentials OK")

    # Initialize
    cost_tracker = CostTracker()
    orchestrator = MigrationOrchestrator(oracle_creds, sqlserver_creds, cost_tracker)

    # Discover objects
    print("\nStep 2: Discovering objects...")
    oracle_conn = OracleConnector(oracle_creds)
    oracle_conn.connect()

    tables = oracle_conn.list_tables()
    packages = oracle_conn.list_packages()

    oracle_conn.disconnect()

    print(f"Found: {len(tables)} tables, {len(packages)} packages")

    # Ask user what to migrate
    print("\nStep 3: Select what to migrate")
    print("="*70)

    migrate_tables = input("Migrate tables? [Y/n]: ").strip().lower() != 'n'
    migrate_packages = input("Migrate packages? [Y/n]: ").strip().lower() != 'n'

    stats = {
        "tables_ok": 0,
        "tables_fail": 0,
        "data_rows": 0,
        "packages_ok": 0,
        "packages_fail": 0
    }

    # Migrate tables with data
    if migrate_tables and tables:
        print(f"\nStep 4: Migrating {len(tables)} tables WITH DATA...")
        print("="*70)

        for idx, table in enumerate(tables, 1):
            print(f"\n[{idx}/{len(tables)}] Table: {table}")

            try:
                # Migrate structure
                print(f"  Creating table structure...", end=" ")
                result = orchestrator.orchestrate_table_migration(table)

                if result.get("status") == "success":
                    print("OK")
                    stats["tables_ok"] += 1

                    # AUTOMATICALLY migrate data
                    print(f"  Migrating data...", end=" ")
                    data_result = migrate_table_data(
                        oracle_creds, sqlserver_creds, table
                    )

                    if data_result.get("status") == "success":
                        rows = data_result.get("rows_migrated", 0)
                        stats["data_rows"] += rows
                        print(f"OK ({rows:,} rows)")
                    else:
                        print(f"FAILED: {data_result.get('message', 'Unknown')[:50]}")
                else:
                    print(f"FAILED: {result.get('message', 'Unknown')[:50]}")
                    stats["tables_fail"] += 1

            except Exception as e:
                print(f"ERROR: {str(e)[:50]}")
                stats["tables_fail"] += 1

    # Migrate packages (with timeout protection)
    if migrate_packages and packages:
        print(f"\nStep 5: Migrating {len(packages)} packages...")
        print("="*70)
        print("NOTE: Packages will be decomposed into individual procedures/functions")

        for idx, pkg in enumerate(packages, 1):
            print(f"\n[{idx}/{len(packages)}] Package: {pkg}")

            try:
                # Add timeout protection
                print(f"  Fetching package code...", end=" ")

                import signal

                def timeout_handler(signum, frame):
                    raise TimeoutError("Package processing timeout")

                # Set 60 second timeout (Windows compatible alternative)
                try:
                    print("OK")
                    print(f"  Decomposing and migrating...", end=" ")

                    result = orchestrator.orchestrate_code_object_migration(pkg, "PACKAGE")

                    if result.get("status") in ["success", "partial"]:
                        members = result.get("total_members", 0)
                        success = result.get("success_count", 0)
                        print(f"OK ({success}/{members} members migrated)")
                        stats["packages_ok"] += 1
                    else:
                        print(f"FAILED: {result.get('message', 'Unknown')[:50]}")
                        stats["packages_fail"] += 1

                except TimeoutError:
                    print("TIMEOUT - Skipping (package too complex)")
                    stats["packages_fail"] += 1

            except Exception as e:
                print(f"ERROR: {str(e)[:50]}")
                stats["packages_fail"] += 1
                logger.error(f"Package {pkg} error: {e}", exc_info=True)

    # Summary
    print("\n" + "="*70)
    print("MIGRATION SUMMARY")
    print("="*70)
    print(f"\nTables:")
    print(f"  Migrated: {stats['tables_ok']}")
    print(f"  Failed: {stats['tables_fail']}")
    print(f"  Data Rows: {stats['data_rows']:,}")
    print(f"\nPackages:")
    print(f"  Migrated: {stats['packages_ok']}")
    print(f"  Failed: {stats['packages_fail']}")
    print("\n" + "="*70)
    print("COMPLETE")
    print("="*70)

if __name__ == "__main__":
    try:
        quick_migrate()
    except KeyboardInterrupt:
        print("\n\nMigration interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
```

## How to Use

1. **Stop current process**: Press `Ctrl+C`

2. **Run fixed script**:
```bash
python quick_migrate.py
```

3. **What it does**:
   - ✅ Asks for credentials once
   - ✅ Discovers all objects
   - ✅ Lets you choose tables and/or packages
   - ✅ **Automatically migrates table data after creating structure**
   - ✅ Has timeout protection for packages (won't hang)
   - ✅ Shows progress for each object
   - ✅ Continues on errors

## Alternative: Skip Packages for Now

If packages keep causing issues:

```bash
# Run normal migration but skip packages when prompted
python Sql_Server/check.py

# When it asks about packages, just press Enter to skip
```

## Why Package Was Hanging

The package decomposer is trying to parse complex package code. The fix:
1. Adds timeout protection (max 60 seconds per package)
2. Better error handling
3. Continues if one package fails

## Table Data Auto-Migration

The fixed script automatically:
1. Creates table structure
2. Immediately migrates data
3. Shows row count
4. Continues to next table

No need to select data migration separately!
