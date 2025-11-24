"""
Quick Migration V2 - FIXED Data Migration
This version ENSURES table data is migrated properly
"""

import sys
import logging
from config.config_enhanced import CostTracker
from database.oracle_connector import OracleConnector
from agents.orchestrator_agent import MigrationOrchestrator
from agents.credential_agent import CredentialAgent

# Use the FIXED data migration function
from hotfix_data_migration import migrate_table_data_fixed

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def quick_migrate_v2():
    """Quick migration V2 with fixed data migration"""
    print("\n" + "="*70)
    print("QUICK MIGRATION V2 - DATA MIGRATION FIXED")
    print("="*70)

    # Step 1: Get credentials
    print("\n[STEP 1] Getting credentials...")
    credential_agent = CredentialAgent()
    oracle_creds, sqlserver_creds = credential_agent.run()

    if not oracle_creds or not sqlserver_creds:
        print("FAILED - Cannot get credentials")
        return 1

    print("OK")

    # Step 2: Initialize
    print("\n[STEP 2] Initializing...")
    cost_tracker = CostTracker()
    orchestrator = MigrationOrchestrator(oracle_creds, sqlserver_creds, cost_tracker)
    print("OK")

    # Step 3: Discover
    print("\n[STEP 3] Discovering objects...")
    oracle_conn = OracleConnector(oracle_creds)

    if not oracle_conn.connect():
        print("FAILED - Cannot connect to Oracle")
        return 1

    tables = oracle_conn.list_tables()
    packages = oracle_conn.list_packages()

    oracle_conn.disconnect()

    print(f"\nFound:")
    print(f"  Tables: {len(tables)}")
    print(f"  Packages: {len(packages)}")

    # Step 4: Select
    print("\n[STEP 4] Selection")
    print("="*70)

    do_tables = input("Migrate tables WITH DATA? [Y/n]: ").strip().lower() != 'n'
    do_packages = input("Migrate packages? [y/N]: ").strip().lower() == 'y'

    stats = {
        "tables_ok": 0,
        "tables_fail": 0,
        "data_rows": 0,
        "packages_ok": 0,
        "packages_fail": 0,
        "package_members": 0
    }

    # Step 5: Migrate Tables WITH DATA
    if do_tables and tables:
        print(f"\n[STEP 5] Migrating {len(tables)} tables WITH DATA")
        print("="*70)

        for idx, table in enumerate(tables, 1):
            print(f"\n[{idx}/{len(tables)}] {table}")

            try:
                # Create table
                print(f"  [1/2] Creating structure...", end=" ", flush=True)
                result = orchestrator.orchestrate_table_migration(table)

                if result.get("status") != "success":
                    print(f"FAILED: {result.get('message', '')[:50]}")
                    stats["tables_fail"] += 1
                    continue

                print("OK")
                stats["tables_ok"] += 1

                # Migrate data using FIXED function
                print(f"  [2/2] Migrating data...", end=" ", flush=True)

                # CRITICAL: Use the FIXED data migration function
                data_result = migrate_table_data_fixed(
                    oracle_creds,
                    sqlserver_creds,
                    table
                )

                if data_result.get("status") == "success":
                    rows = data_result.get("rows_migrated", 0)
                    stats["data_rows"] += rows
                    print(f"OK ({rows:,} rows)")
                else:
                    error = data_result.get('message', 'Unknown error')
                    print(f"FAILED: {error[:50]}")
                    logger.error(f"Data migration failed for {table}: {error}")

            except Exception as e:
                print(f"ERROR: {str(e)[:50]}")
                stats["tables_fail"] += 1
                logger.error(f"Table {table} error: {e}", exc_info=True)

    # Step 6: Migrate Packages
    if do_packages and packages:
        print(f"\n[STEP 6] Migrating {len(packages)} packages")
        print("="*70)
        print("(Packages will be decomposed)\n")

        for idx, pkg in enumerate(packages, 1):
            print(f"[{idx}/{len(packages)}] {pkg}...", end=" ", flush=True)

            try:
                result = orchestrator.orchestrate_code_object_migration(pkg, "PACKAGE")

                if result.get("status") in ["success", "partial"]:
                    members = result.get("total_members", 0)
                    success = result.get("success_count", 0)
                    stats["package_members"] += success
                    print(f"OK ({success}/{members} members)")
                    stats["packages_ok"] += 1
                else:
                    error = result.get('message', '')
                    print(f"FAILED: {error[:40]}")
                    stats["packages_fail"] += 1

            except Exception as e:
                print(f"ERROR: {str(e)[:40]}")
                stats["packages_fail"] += 1

    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"\nTables:")
    print(f"  OK: {stats['tables_ok']}")
    print(f"  Failed: {stats['tables_fail']}")
    print(f"  Data Rows Migrated: {stats['data_rows']:,}")

    if do_packages:
        print(f"\nPackages:")
        print(f"  OK: {stats['packages_ok']}")
        print(f"  Failed: {stats['packages_fail']}")
        print(f"  Members Migrated: {stats['package_members']}")

    print("\n" + "="*70)

    total_fail = stats["tables_fail"] + stats["packages_fail"]
    return 0 if total_fail == 0 else 1


if __name__ == "__main__":
    try:
        exit_code = quick_migrate_v2()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\nFATAL: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
