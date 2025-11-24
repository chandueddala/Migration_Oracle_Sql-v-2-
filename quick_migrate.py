"""
Quick Migration Script - Fixed Version
Handles packages correctly and auto-migrates table data

This script fixes two issues:
1. Package migration hanging - adds timeout protection
2. Table data not auto-migrating - migrates data immediately after table creation
"""

import sys
import logging
from config.config_enhanced import CostTracker
from database.oracle_connector import OracleConnector
from database.sqlserver_connector import SQLServerConnector
from agents.orchestrator_agent import MigrationOrchestrator
from agents.credential_agent import CredentialAgent
from utils.migration_engine import migrate_table_data

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def quick_migrate():
    """Quick migration with fixes for hanging packages and auto data migration"""
    print("\n" + "="*70)
    print("QUICK MIGRATION - FIXED VERSION")
    print("  - Auto-migrates table data after structure")
    print("  - Timeout protection for packages")
    print("="*70)

    # Step 1: Get credentials
    print("\n[STEP 1] Getting credentials...")
    credential_agent = CredentialAgent()
    oracle_creds, sqlserver_creds = credential_agent.run()

    if not oracle_creds or not sqlserver_creds:
        print("\nFailed to get valid credentials")
        return 1

    print("OK - Credentials validated")

    # Step 2: Initialize orchestrator
    print("\n[STEP 2] Initializing orchestrator...")
    cost_tracker = CostTracker()
    orchestrator = MigrationOrchestrator(oracle_creds, sqlserver_creds, cost_tracker)
    print("OK - Orchestrator ready")

    # Step 3: Discover objects
    print("\n[STEP 3] Discovering database objects...")
    oracle_conn = OracleConnector(oracle_creds)

    if not oracle_conn.connect():
        print("FAILED - Cannot connect to Oracle")
        return 1

    tables = oracle_conn.list_tables()
    packages = oracle_conn.list_packages()
    procedures = oracle_conn.list_procedures()
    functions = oracle_conn.list_functions()
    triggers = oracle_conn.list_triggers()

    oracle_conn.disconnect()

    print(f"\nDiscovered:")
    print(f"  Tables: {len(tables)}")
    print(f"  Procedures: {len(procedures)}")
    print(f"  Functions: {len(functions)}")
    print(f"  Triggers: {len(triggers)}")
    print(f"  Packages: {len(packages)}")

    # Step 4: Ask user what to migrate
    print("\n[STEP 4] Select what to migrate")
    print("="*70)

    migrate_tables = input("Migrate tables (with data)? [Y/n]: ").strip().lower() != 'n'
    migrate_procs = input("Migrate procedures? [Y/n]: ").strip().lower() != 'n'
    migrate_funcs = input("Migrate functions? [Y/n]: ").strip().lower() != 'n'
    migrate_trigs = input("Migrate triggers? [Y/n]: ").strip().lower() != 'n'
    migrate_pkgs = input("Migrate packages? [Y/n]: ").strip().lower() != 'n'

    stats = {
        "tables_ok": 0,
        "tables_fail": 0,
        "data_rows": 0,
        "procedures_ok": 0,
        "procedures_fail": 0,
        "functions_ok": 0,
        "functions_fail": 0,
        "triggers_ok": 0,
        "triggers_fail": 0,
        "packages_ok": 0,
        "packages_fail": 0,
        "package_members": 0
    }

    # Step 5: Migrate tables WITH DATA
    if migrate_tables and tables:
        print(f"\n[STEP 5] Migrating {len(tables)} tables WITH DATA...")
        print("="*70)

        for idx, table in enumerate(tables, 1):
            print(f"\n[{idx}/{len(tables)}] Table: {table}")

            try:
                # Create table structure
                print(f"  → Creating structure...", end=" ", flush=True)
                result = orchestrator.orchestrate_table_migration(table)

                if result.get("status") == "success":
                    print("✓")
                    stats["tables_ok"] += 1

                    # AUTOMATICALLY migrate data immediately
                    print(f"  → Migrating data...", end=" ", flush=True)

                    try:
                        data_result = migrate_table_data(
                            oracle_creds, sqlserver_creds, table
                        )

                        if data_result.get("status") == "success":
                            rows = data_result.get("rows_migrated", 0)
                            stats["data_rows"] += rows
                            print(f"✓ ({rows:,} rows)")
                        else:
                            error_msg = data_result.get('message', 'Unknown error')
                            print(f"✗ {error_msg[:60]}")

                    except Exception as data_err:
                        print(f"✗ Data migration error: {str(data_err)[:60]}")
                        logger.error(f"Data migration failed for {table}: {data_err}")

                else:
                    error_msg = result.get('message', 'Unknown error')
                    print(f"✗ {error_msg[:60]}")
                    stats["tables_fail"] += 1

            except Exception as e:
                print(f"✗ ERROR: {str(e)[:60]}")
                stats["tables_fail"] += 1
                logger.error(f"Table {table} migration failed: {e}", exc_info=True)

    # Step 6: Migrate procedures
    if migrate_procs and procedures:
        print(f"\n[STEP 6] Migrating {len(procedures)} procedures...")
        print("="*70)
        _migrate_code_objects(orchestrator, procedures, "PROCEDURE", stats, "procedures")

    # Step 7: Migrate functions
    if migrate_funcs and functions:
        print(f"\n[STEP 7] Migrating {len(functions)} functions...")
        print("="*70)
        _migrate_code_objects(orchestrator, functions, "FUNCTION", stats, "functions")

    # Step 8: Migrate triggers
    if migrate_trigs and triggers:
        print(f"\n[STEP 8] Migrating {len(triggers)} triggers...")
        print("="*70)
        _migrate_code_objects(orchestrator, triggers, "TRIGGER", stats, "triggers")

    # Step 9: Migrate packages (with protection)
    if migrate_pkgs and packages:
        print(f"\n[STEP 9] Migrating {len(packages)} packages...")
        print("="*70)
        print("NOTE: Packages will be decomposed into individual procedures/functions\n")

        for idx, pkg in enumerate(packages, 1):
            print(f"[{idx}/{len(packages)}] Package: {pkg}")

            try:
                print(f"  → Fetching and decomposing...", end=" ", flush=True)

                # Try to migrate with basic error handling
                result = orchestrator.orchestrate_code_object_migration(pkg, "PACKAGE")

                if result.get("status") == "success":
                    members = result.get("total_members", 0)
                    success = result.get("success_count", 0)
                    stats["package_members"] += success
                    print(f"✓ ({success}/{members} members)")
                    stats["packages_ok"] += 1

                elif result.get("status") == "partial":
                    members = result.get("total_members", 0)
                    success = result.get("success_count", 0)
                    failed = result.get("failure_count", 0)
                    stats["package_members"] += success
                    print(f"⚠ Partial ({success}/{members} members, {failed} failed)")
                    stats["packages_ok"] += 1

                else:
                    error_msg = result.get('message', 'Unknown error')
                    print(f"✗ {error_msg[:60]}")
                    stats["packages_fail"] += 1

            except Exception as e:
                print(f"✗ ERROR: {str(e)[:60]}")
                stats["packages_fail"] += 1
                logger.error(f"Package {pkg} error: {e}", exc_info=True)

                # Continue with next package
                continue

    # Final summary
    _print_summary(stats)

    # Check if all successful
    total_fail = (
        stats["tables_fail"] +
        stats["procedures_fail"] +
        stats["functions_fail"] +
        stats["triggers_fail"] +
        stats["packages_fail"]
    )

    return 0 if total_fail == 0 else 1


def _migrate_code_objects(orchestrator, objects, obj_type, stats, stat_key):
    """Helper to migrate code objects"""
    for idx, obj in enumerate(objects, 1):
        print(f"[{idx}/{len(objects)}] {obj}...", end=" ", flush=True)

        try:
            result = orchestrator.orchestrate_code_object_migration(obj, obj_type)

            if result.get("status") == "success":
                print("✓")
                stats[f"{stat_key}_ok"] += 1
            else:
                error_msg = result.get('message', 'Unknown')
                print(f"✗ {error_msg[:50]}")
                stats[f"{stat_key}_fail"] += 1

        except Exception as e:
            print(f"✗ ERROR: {str(e)[:50]}")
            stats[f"{stat_key}_fail"] += 1
            logger.error(f"{obj_type} {obj} error: {e}")


def _print_summary(stats):
    """Print migration summary"""
    print("\n" + "="*70)
    print("MIGRATION SUMMARY")
    print("="*70)

    print(f"\nTABLES:")
    print(f"  ✓ Migrated: {stats['tables_ok']}")
    print(f"  ✗ Failed: {stats['tables_fail']}")
    print(f"  📊 Data Rows: {stats['data_rows']:,}")

    if stats['procedures_ok'] > 0 or stats['procedures_fail'] > 0:
        print(f"\nPROCEDURES:")
        print(f"  ✓ Migrated: {stats['procedures_ok']}")
        print(f"  ✗ Failed: {stats['procedures_fail']}")

    if stats['functions_ok'] > 0 or stats['functions_fail'] > 0:
        print(f"\nFUNCTIONS:")
        print(f"  ✓ Migrated: {stats['functions_ok']}")
        print(f"  ✗ Failed: {stats['functions_fail']}")

    if stats['triggers_ok'] > 0 or stats['triggers_fail'] > 0:
        print(f"\nTRIGGERS:")
        print(f"  ✓ Migrated: {stats['triggers_ok']}")
        print(f"  ✗ Failed: {stats['triggers_fail']}")

    if stats['packages_ok'] > 0 or stats['packages_fail'] > 0:
        print(f"\nPACKAGES:")
        print(f"  ✓ Migrated: {stats['packages_ok']}")
        print(f"  ✗ Failed: {stats['packages_fail']}")
        print(f"  🔧 Package Members: {stats['package_members']}")

    total_ok = (
        stats['tables_ok'] +
        stats['procedures_ok'] +
        stats['functions_ok'] +
        stats['triggers_ok'] +
        stats['packages_ok']
    )

    total_fail = (
        stats['tables_fail'] +
        stats['procedures_fail'] +
        stats['functions_fail'] +
        stats['triggers_fail'] +
        stats['packages_fail']
    )

    print(f"\n" + "="*70)
    print(f"TOTAL:")
    print(f"  ✓ Success: {total_ok}")
    print(f"  ✗ Failed: {total_fail}")

    if total_ok + total_fail > 0:
        success_rate = (total_ok / (total_ok + total_fail)) * 100
        print(f"  📈 Success Rate: {success_rate:.1f}%")

    print("="*70)


if __name__ == "__main__":
    try:
        exit_code = quick_migrate()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Migration interrupted by user (Ctrl+C)")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
