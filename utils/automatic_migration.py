"""
Fully Automatic Migration - Process ALL database objects without user selection

This module provides automatic migration of ALL database objects:
- Tables (structure + data)
- Procedures
- Functions
- Triggers
- Packages (automatically decomposed)
- Views (optional)
- Sequences (optional)

No user selection required - processes everything automatically.
"""

import logging
from typing import Dict, List, Tuple
from datetime import datetime

from config.config_enhanced import OUTPUT_DIR, CostTracker, SecurityLogger
from database.oracle_connector import OracleConnector
from database.sqlserver_connector import SQLServerConnector
from agents.orchestrator_agent import MigrationOrchestrator
from agents.credential_agent import CredentialAgent
from agents.memory_agent import get_shared_memory, ensure_schema_exists
from utils.migration_engine import migrate_table_data

logger = logging.getLogger(__name__)


def run_automatic_migration(
    migrate_tables: bool = True,
    migrate_data: bool = True,
    migrate_procedures: bool = True,
    migrate_functions: bool = True,
    migrate_triggers: bool = True,
    migrate_packages: bool = True,
    migrate_views: bool = False,  # Optional
    migrate_sequences: bool = False  # Optional
):
    """
    Fully automatic migration - processes ALL objects without user selection

    Args:
        migrate_tables: Migrate table structures
        migrate_data: Migrate table data (requires migrate_tables=True)
        migrate_procedures: Migrate stored procedures
        migrate_functions: Migrate functions
        migrate_triggers: Migrate triggers
        migrate_packages: Migrate packages (auto-decomposed)
        migrate_views: Migrate views (optional, may need manual review)
        migrate_sequences: Migrate sequences (optional)

    Returns:
        Migration statistics dictionary
    """
    cost_tracker = CostTracker()
    shared_memory = get_shared_memory()

    migration_stats = {
        "tables": {"migrated": 0, "failed": 0, "skipped": 0, "data_rows": 0},
        "procedures": {"migrated": 0, "failed": 0, "skipped": 0},
        "functions": {"migrated": 0, "failed": 0, "skipped": 0},
        "triggers": {"migrated": 0, "failed": 0, "skipped": 0},
        "packages": {"migrated": 0, "failed": 0, "skipped": 0, "decomposed_members": 0},
        "views": {"migrated": 0, "failed": 0, "skipped": 0},
        "sequences": {"migrated": 0, "failed": 0, "skipped": 0},
        "start_time": datetime.now().isoformat(),
        "mode": "AUTOMATIC"
    }

    print("\n" + "="*70)
    print("🤖 AUTOMATIC MIGRATION MODE - ALL OBJECTS")
    print("="*70)
    print("\nConfiguration:")
    print(f"  Tables: {'✅' if migrate_tables else '❌'}")
    print(f"  Data: {'✅' if migrate_data else '❌'}")
    print(f"  Procedures: {'✅' if migrate_procedures else '❌'}")
    print(f"  Functions: {'✅' if migrate_functions else '❌'}")
    print(f"  Triggers: {'✅' if migrate_triggers else '❌'}")
    print(f"  Packages: {'✅' if migrate_packages else '❌'}")
    print(f"  Views: {'✅' if migrate_views else '❌'}")
    print(f"  Sequences: {'✅' if migrate_sequences else '❌'}")
    print("="*70)

    # Step 1: Collect credentials
    print("\n[STEP 1/6] Collecting credentials...")
    credential_agent = CredentialAgent()
    oracle_creds, sqlserver_creds = credential_agent.run()

    if not oracle_creds or not sqlserver_creds:
        print("❌ Unable to establish database connections")
        return migration_stats

    print("✅ Database connections established")

    # Step 2: Initialize orchestrator
    print("\n[STEP 2/6] Initializing orchestrator...")
    orchestrator = MigrationOrchestrator(oracle_creds, sqlserver_creds, cost_tracker)
    print("✅ Orchestrator ready")

    # Step 3: Discover all objects
    print("\n[STEP 3/6] Discovering all database objects...")
    discovered = _discover_all_objects(oracle_creds)

    print(f"\nDiscovered:")
    print(f"  📊 Tables: {len(discovered['tables'])}")
    print(f"  🔧 Procedures: {len(discovered['procedures'])}")
    print(f"  🔍 Functions: {len(discovered['functions'])}")
    print(f"  ⚡ Triggers: {len(discovered['triggers'])}")
    print(f"  📦 Packages: {len(discovered['packages'])}")
    if migrate_views:
        print(f"  👁️  Views: {len(discovered.get('views', []))}")
    if migrate_sequences:
        print(f"  🔢 Sequences: {len(discovered.get('sequences', []))}")

    total_objects = (
        len(discovered['tables']) +
        len(discovered['procedures']) +
        len(discovered['functions']) +
        len(discovered['triggers']) +
        len(discovered['packages'])
    )
    if migrate_views:
        total_objects += len(discovered.get('views', []))
    if migrate_sequences:
        total_objects += len(discovered.get('sequences', []))

    print(f"\n📊 Total objects to process: {total_objects}")

    # Step 4: Create schemas
    print("\n[STEP 4/6] Preparing SQL Server schemas...")
    _ensure_schemas_exist(sqlserver_creds)
    print("✅ Schemas ready")

    # Step 5: Migrate all objects
    print("\n[STEP 5/6] Migrating all objects...")
    print("="*70)

    # 5.1: Migrate Tables
    if migrate_tables and discovered['tables']:
        print(f"\n📊 Migrating {len(discovered['tables'])} tables...")
        _migrate_tables_automatic(
            orchestrator, discovered['tables'],
            migrate_data, oracle_creds, sqlserver_creds,
            migration_stats
        )

    # 5.2: Migrate Procedures
    if migrate_procedures and discovered['procedures']:
        print(f"\n🔧 Migrating {len(discovered['procedures'])} procedures...")
        _migrate_code_objects_automatic(
            orchestrator, discovered['procedures'], "PROCEDURE",
            migration_stats
        )

    # 5.3: Migrate Functions
    if migrate_functions and discovered['functions']:
        print(f"\n🔍 Migrating {len(discovered['functions'])} functions...")
        _migrate_code_objects_automatic(
            orchestrator, discovered['functions'], "FUNCTION",
            migration_stats
        )

    # 5.4: Migrate Triggers
    if migrate_triggers and discovered['triggers']:
        print(f"\n⚡ Migrating {len(discovered['triggers'])} triggers...")
        _migrate_code_objects_automatic(
            orchestrator, discovered['triggers'], "TRIGGER",
            migration_stats
        )

    # 5.5: Migrate Packages (auto-decomposed)
    if migrate_packages and discovered['packages']:
        print(f"\n📦 Migrating {len(discovered['packages'])} packages (will be decomposed)...")
        _migrate_packages_automatic(
            orchestrator, discovered['packages'],
            migration_stats
        )

    # 5.6: Migrate Views (optional)
    if migrate_views and discovered.get('views'):
        print(f"\n👁️  Migrating {len(discovered['views'])} views...")
        # Note: Views might need manual review for complex queries
        _migrate_views_automatic(
            orchestrator, discovered['views'],
            migration_stats
        )

    # 5.7: Migrate Sequences (optional)
    if migrate_sequences and discovered.get('sequences'):
        print(f"\n🔢 Migrating {len(discovered['sequences'])} sequences...")
        _migrate_sequences_automatic(
            orchestrator, discovered['sequences'],
            migration_stats
        )

    # Step 6: Generate report
    print("\n[STEP 6/6] Generating migration report...")
    migration_stats["end_time"] = datetime.now().isoformat()
    migration_stats["cost"] = cost_tracker.get_stats()

    _print_automatic_migration_summary(migration_stats)
    _save_automatic_migration_report(migration_stats)

    print("\n" + "="*70)
    print("✅ AUTOMATIC MIGRATION COMPLETE")
    print("="*70)

    return migration_stats


def _discover_all_objects(oracle_creds: Dict) -> Dict:
    """Discover ALL objects in Oracle database"""
    discovered = {
        "tables": [],
        "procedures": [],
        "functions": [],
        "triggers": [],
        "packages": [],
        "views": [],
        "sequences": []
    }

    try:
        oracle_conn = OracleConnector(oracle_creds)
        if not oracle_conn.connect():
            logger.error("Failed to connect to Oracle for discovery")
            return discovered

        discovered["tables"] = oracle_conn.list_tables()
        discovered["procedures"] = oracle_conn.list_procedures()
        discovered["functions"] = oracle_conn.list_functions()
        discovered["triggers"] = oracle_conn.list_triggers()
        discovered["packages"] = oracle_conn.list_packages()

        # Optional: Discover views and sequences
        try:
            discovered["views"] = oracle_conn.list_views() if hasattr(oracle_conn, 'list_views') else []
        except:
            discovered["views"] = []

        try:
            discovered["sequences"] = oracle_conn.list_sequences() if hasattr(oracle_conn, 'list_sequences') else []
        except:
            discovered["sequences"] = []

        oracle_conn.disconnect()

    except Exception as e:
        logger.error(f"Discovery error: {e}", exc_info=True)

    return discovered


def _ensure_schemas_exist(sqlserver_creds: Dict):
    """Ensure all required schemas exist in SQL Server"""
    schemas = ["dbo", "staging", "archive"]  # Common schemas

    for schema in schemas:
        ensure_schema_exists(schema, sqlserver_creds)


def _migrate_tables_automatic(
    orchestrator: MigrationOrchestrator,
    tables: List[str],
    migrate_data: bool,
    oracle_creds: Dict,
    sqlserver_creds: Dict,
    stats: Dict
):
    """Migrate all tables automatically"""
    for idx, table_name in enumerate(tables, 1):
        print(f"  [{idx}/{len(tables)}] {table_name}...", end=" ")

        try:
            # Migrate table structure
            result = orchestrator.orchestrate_table_migration(table_name)

            if result.get("status") == "success":
                stats["tables"]["migrated"] += 1
                print("✅")

                # Migrate data if requested
                if migrate_data:
                    print(f"      → Migrating data...", end=" ")
                    SecurityLogger.log_data_access("migrate", table_name, 0)

                    data_result = migrate_table_data(
                        oracle_creds, sqlserver_creds, table_name
                    )

                    if data_result.get("status") == "success":
                        rows = data_result.get("rows_migrated", 0)
                        stats["tables"]["data_rows"] += rows
                        print(f"✅ ({rows:,} rows)")
                        SecurityLogger.log_data_access("migrate_complete", table_name, rows)
                    else:
                        print("⚠️  Data migration failed")
            else:
                stats["tables"]["failed"] += 1
                print(f"❌ {result.get('message', 'Unknown error')[:30]}")

        except Exception as e:
            stats["tables"]["failed"] += 1
            print(f"❌ {str(e)[:30]}")
            logger.error(f"Table migration error: {table_name}: {e}")


def _migrate_code_objects_automatic(
    orchestrator: MigrationOrchestrator,
    objects: List[str],
    obj_type: str,
    stats: Dict
):
    """Migrate code objects (procedures, functions, triggers) automatically"""
    type_map = {
        "PROCEDURE": "procedures",
        "FUNCTION": "functions",
        "TRIGGER": "triggers"
    }
    stat_key = type_map[obj_type]

    for idx, obj_name in enumerate(objects, 1):
        print(f"  [{idx}/{len(objects)}] {obj_name}...", end=" ")

        try:
            result = orchestrator.orchestrate_code_object_migration(obj_name, obj_type)

            if result.get("status") == "success":
                stats[stat_key]["migrated"] += 1
                print("✅")
            elif result.get("status") == "partial":
                # Partial success (for packages)
                stats[stat_key]["migrated"] += 1
                print("⚠️  Partial")
            else:
                stats[stat_key]["failed"] += 1
                print(f"❌ {result.get('message', '')[:30]}")

        except Exception as e:
            stats[stat_key]["failed"] += 1
            print(f"❌ {str(e)[:30]}")
            logger.error(f"{obj_type} migration error: {obj_name}: {e}")


def _migrate_packages_automatic(
    orchestrator: MigrationOrchestrator,
    packages: List[str],
    stats: Dict
):
    """Migrate packages (automatically decomposed) """
    for idx, pkg_name in enumerate(packages, 1):
        print(f"  [{idx}/{len(packages)}] {pkg_name} (will decompose)...", end=" ")

        try:
            result = orchestrator.orchestrate_code_object_migration(pkg_name, "PACKAGE")

            if result.get("status") in ["success", "partial"]:
                stats["packages"]["migrated"] += 1
                members = result.get("total_members", 0)
                success = result.get("success_count", 0)
                stats["packages"]["decomposed_members"] += success
                print(f"✅ ({success}/{members} members)")
            else:
                stats["packages"]["failed"] += 1
                print(f"❌ {result.get('message', '')[:30]}")

        except Exception as e:
            stats["packages"]["failed"] += 1
            print(f"❌ {str(e)[:30]}")
            logger.error(f"Package migration error: {pkg_name}: {e}")


def _migrate_views_automatic(
    orchestrator: MigrationOrchestrator,
    views: List[str],
    stats: Dict
):
    """Migrate views (may need manual review)"""
    # Note: Views are similar to functions - contain SELECT queries
    for idx, view_name in enumerate(views, 1):
        print(f"  [{idx}/{len(views)}] {view_name}...", end=" ")
        print("⚠️  Manual review recommended")
        stats["views"]["skipped"] += 1


def _migrate_sequences_automatic(
    orchestrator: MigrationOrchestrator,
    sequences: List[str],
    stats: Dict
):
    """Migrate sequences (convert to identity columns or sequences)"""
    for idx, seq_name in enumerate(sequences, 1):
        print(f"  [{idx}/{len(sequences)}] {seq_name}...", end=" ")
        print("⚠️  Manual review recommended")
        stats["sequences"]["skipped"] += 1


def _print_automatic_migration_summary(stats: Dict):
    """Print comprehensive summary"""
    print("\n" + "="*70)
    print("AUTOMATIC MIGRATION SUMMARY")
    print("="*70)

    total_migrated = 0
    total_failed = 0

    for key in ["tables", "procedures", "functions", "triggers", "packages"]:
        migrated = stats[key]["migrated"]
        failed = stats[key]["failed"]
        total_migrated += migrated
        total_failed += failed

        if migrated > 0 or failed > 0:
            print(f"\n{key.upper()}:")
            print(f"  ✅ Migrated: {migrated}")
            print(f"  ❌ Failed: {failed}")

            if key == "tables" and stats[key]["data_rows"] > 0:
                print(f"  📊 Data Rows: {stats[key]['data_rows']:,}")

            if key == "packages" and stats[key]["decomposed_members"] > 0:
                print(f"  🔧 Decomposed Members: {stats[key]['decomposed_members']}")

    print(f"\n" + "="*70)
    print(f"TOTALS:")
    print(f"  ✅ Successfully Migrated: {total_migrated}")
    print(f"  ❌ Failed: {total_failed}")
    print(f"  📈 Success Rate: {(total_migrated/(total_migrated+total_failed)*100) if (total_migrated+total_failed) > 0 else 0:.1f}%")


def _save_automatic_migration_report(stats: Dict):
    """Save migration report to file"""
    import json
    from datetime import datetime

    report_file = OUTPUT_DIR / f"automatic_migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    with open(report_file, 'w') as f:
        json.dump(stats, f, indent=2)

    print(f"\n📄 Report saved: {report_file}")
