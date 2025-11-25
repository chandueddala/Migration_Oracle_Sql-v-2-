"""
Upfront Migration - Ask Everything First

This version:
1. Discovers ALL database objects upfront
2. Asks user to select EVERYTHING before migration starts
3. Then migrates all selected objects
4. Perfect for frontend integration

NO interruptions during migration!
"""

import sys
import logging
import json
from pathlib import Path

from config.config_enhanced import CostTracker
from agents.credential_agent import CredentialAgent
from database.oracle_connector import OracleConnector
from agents.orchestrator_agent import MigrationOrchestrator
from utils.comprehensive_discovery import ComprehensiveDiscovery
from utils.interactive_selection import InteractiveSelector
from utils.migration_engine import migrate_table_data

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/migration.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def main():
    """Main migration flow with upfront selection"""
    print("\n" + "="*80)
    print(" ORACLE TO SQL SERVER MIGRATION - UPFRONT SELECTION MODE")
    print("="*80)
    print("\n  This mode:")
    print("    1. Discovers ALL database objects")
    print("    2. Asks you to select EVERYTHING upfront")
    print("    3. Migrates all selected objects without interruption")
    print("    4. Perfect for automation and frontend integration\n")

    # Step 1: Get credentials
    print("="*80)
    print(" STEP 1: CREDENTIALS")
    print("="*80)

    credential_agent = CredentialAgent()
    oracle_creds, sqlserver_creds = credential_agent.run()

    # Step 2: Comprehensive Discovery
    print("\n" + "="*80)
    print(" STEP 2: COMPREHENSIVE DISCOVERY")
    print("="*80)
    print("\n  Discovering ALL database objects...\n")

    oracle_conn = OracleConnector(oracle_creds)
    if not oracle_conn.connect():
        print("  [ERROR] Failed to connect to Oracle")
        return 1

    discovery = ComprehensiveDiscovery(oracle_conn)
    result = discovery.discover_all()

    # Show discovery results
    print("\n  Discovery complete!")
    print(f"    Time: {result.discovery_time_seconds:.2f}s")
    print(f"    Total objects: {result.total_objects}")
    print(f"\n    Breakdown:")
    print(f"      Tables: {len(result.tables)}")
    print(f"      Packages: {len(result.packages)}")
    print(f"      Procedures: {len(result.procedures)}")
    print(f"      Functions: {len(result.functions)}")
    print(f"      Triggers: {len(result.triggers)}")
    print(f"      Views: {len(result.views)}")
    print(f"      Sequences: {len(result.sequences)}")
    print(f"      Types: {len(result.types)}")
    print(f"      Synonyms: {len(result.synonyms)}")

    # Save discovery to JSON (for frontend)
    discovery_json = discovery.to_json(result)
    output_file = Path("output/discovery_result.json")
    output_file.parent.mkdir(exist_ok=True)
    with open(output_file, 'w') as f:
        json.dump(discovery_json, f, indent=2)
    print(f"\n    Discovery data saved: {output_file}")

    oracle_conn.disconnect()

    # Step 3: Interactive Selection (EVERYTHING UPFRONT)
    print("\n" + "="*80)
    print(" STEP 3: SELECT OBJECTS TO MIGRATE")
    print("="*80)
    print("\n  Select EVERYTHING you want to migrate now!")
    print("  No more questions after this...\n")

    selector = InteractiveSelector()
    selection = selector.select_all_upfront(result)

    # Save selection to JSON (for frontend)
    selection_json = selection.to_json()
    selection_file = Path("output/migration_selection.json")
    with open(selection_file, 'w') as f:
        json.dump(selection_json, f, indent=2)
    print(f"\n    Selection saved: {selection_file}")

    # Step 4: Migration Execution
    print("\n" + "="*80)
    print(" STEP 4: MIGRATION EXECUTION")
    print("="*80)
    print(f"\n  Migrating {selection.total_objects()} objects...")
    print("  This will run without interruption!\n")

    cost_tracker = CostTracker()
    orchestrator = MigrationOrchestrator(oracle_creds, sqlserver_creds, cost_tracker)

    results = {
        "tables": [],
        "packages": [],
        "procedures": [],
        "functions": [],
        "triggers": [],
        "views": [],
        "sequences": []
    }

    success_count = 0
    failure_count = 0

    # Migrate tables
    if selection.selected_tables:
        print(f"\n  [TABLES] Migrating {len(selection.selected_tables)} tables...")

        for i, table_name in enumerate(selection.selected_tables, 1):
            print(f"\n    [{i}/{len(selection.selected_tables)}] {table_name}")

            # Migrate schema
            result = orchestrator.orchestrate(table_name, "TABLE")
            results["tables"].append(result)

            if result.get("status") == "success":
                success_count += 1
                print(f"      [OK] Schema migrated")

                # Migrate data if selected
                if table_name in selection.tables_with_data:
                    print(f"      [DATA] Migrating data...")
                    data_result = migrate_table_data(oracle_creds, sqlserver_creds, table_name)

                    if data_result.get("status") == "success":
                        rows = data_result.get("rows_migrated", 0)
                        print(f"      [OK] Data migrated: {rows:,} rows")
                    elif data_result.get("status") == "partial":
                        rows = data_result.get("rows_migrated", 0)
                        expected = data_result.get("rows_expected", 0)
                        print(f"      [WARN] Partial data migration: {rows:,}/{expected:,} rows")
                    else:
                        print(f"      [FAIL] Data migration failed: {data_result.get('message', 'Unknown error')}")
                else:
                    print(f"      [SKIP] Data migration (schema only)")
            else:
                failure_count += 1
                print(f"      [FAIL] {result.get('message', 'Unknown error')}")

    # Migrate packages
    if selection.selected_packages:
        print(f"\n  [PACKAGES] Migrating {len(selection.selected_packages)} packages...")

        for i, pkg_name in enumerate(selection.selected_packages, 1):
            print(f"\n    [{i}/{len(selection.selected_packages)}] {pkg_name}")
            result = orchestrator.orchestrate(pkg_name, "PACKAGE")
            results["packages"].append(result)

            if result.get("status") in ["success", "partial"]:
                success_count += 1
                print(f"      [OK] Package migrated")
            else:
                failure_count += 1
                print(f"      [FAIL] {result.get('message', 'Unknown error')}")

    # Migrate procedures
    if selection.selected_procedures:
        print(f"\n  [PROCEDURES] Migrating {len(selection.selected_procedures)} procedures...")

        for i, proc_name in enumerate(selection.selected_procedures, 1):
            print(f"\n    [{i}/{len(selection.selected_procedures)}] {proc_name}")
            result = orchestrator.orchestrate(proc_name, "PROCEDURE")
            results["procedures"].append(result)

            if result.get("status") == "success":
                success_count += 1
                print(f"      [OK] Migrated")
            else:
                failure_count += 1
                print(f"      [FAIL]")

    # Migrate functions
    if selection.selected_functions:
        print(f"\n  [FUNCTIONS] Migrating {len(selection.selected_functions)} functions...")

        for i, func_name in enumerate(selection.selected_functions, 1):
            print(f"\n    [{i}/{len(selection.selected_functions)}] {func_name}")
            result = orchestrator.orchestrate(func_name, "FUNCTION")
            results["functions"].append(result)

            if result.get("status") == "success":
                success_count += 1
                print(f"      [OK] Migrated")
            else:
                failure_count += 1
                print(f"      [FAIL]")

    # Migrate triggers
    if selection.selected_triggers:
        print(f"\n  [TRIGGERS] Migrating {len(selection.selected_triggers)} triggers...")

        for i, trigger_name in enumerate(selection.selected_triggers, 1):
            print(f"\n    [{i}/{len(selection.selected_triggers)}] {trigger_name}")
            result = orchestrator.orchestrate(trigger_name, "TRIGGER")
            results["triggers"].append(result)

            if result.get("status") == "success":
                success_count += 1
                print(f"      [OK] Migrated")
            else:
                failure_count += 1
                print(f"      [FAIL]")

    # Final summary
    print("\n" + "="*80)
    print(" MIGRATION COMPLETE")
    print("="*80)

    print(f"\n  Total objects: {selection.total_objects()}")
    print(f"  Successful: {success_count}")
    print(f"  Failed: {failure_count}")

    print(f"\n  {cost_tracker}")

    # Save final results
    final_results = {
        "selection": selection_json,
        "results": results,
        "summary": {
            "total": selection.total_objects(),
            "success": success_count,
            "failed": failure_count
        },
        "cost": str(cost_tracker)
    }

    results_file = Path("output/migration_results.json")
    with open(results_file, 'w') as f:
        json.dump(final_results, f, indent=2)

    print(f"\n  Results saved: {results_file}")

    print("\n" + "="*80)

    return 0 if failure_count == 0 else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n[CANCELLED] Migration cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        print(f"\n[ERROR] {e}")
        sys.exit(1)
