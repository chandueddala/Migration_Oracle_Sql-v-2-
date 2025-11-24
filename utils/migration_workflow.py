"""
Enhanced Migration Engine with Orchestrator Integration
Implements System Prompt v1.0 requirements
"""

import json
import logging
from datetime import datetime
from typing import Dict, List

from config.config_enhanced import OUTPUT_DIR, CostTracker, SecurityLogger
from database.oracle_connector import OracleConnector
from database.sqlserver_connector import SQLServerConnector
from agents.orchestrator_agent import MigrationOrchestrator
from agents.credential_agent import CredentialAgent
from agents.memory_agent import get_shared_memory, ensure_schema_exists
from utils.migration_engine import migrate_table_data, get_user_selection

logger = logging.getLogger(__name__)


# ==================== CREDENTIAL COLLECTION ====================
# NOTE: Credential collection is now handled by CredentialAgent
# These functions are kept for backward compatibility

def collect_credentials() -> tuple:
    """
    DEPRECATED: Use CredentialAgent instead.
    Collect Oracle and SQL Server credentials from user input
    """
    logger.warning("collect_credentials() is deprecated. Use CredentialAgent instead.")
    print("\nOracle Database Credentials:")
    oracle_creds = {
        "host": input("  Host (default: localhost): ").strip() or "localhost",
        "port": input("  Port (default: 1521): ").strip() or "1521",
        "service_name": input("  Service Name: ").strip(),
        "username": input("  Username: ").strip(),
        "password": input("  Password: ").strip()
    }

    print("\nSQL Server Database Credentials:")
    sqlserver_creds = {
        "server": input("  Server (default: localhost): ").strip() or "localhost",
        "database": input("  Database: ").strip(),
        "username": input("  Username: ").strip(),
        "password": input("  Password: ").strip()
    }

    return oracle_creds, sqlserver_creds


def validate_credentials(oracle_creds: Dict, sqlserver_creds: Dict) -> bool:
    """
    DEPRECATED: Use CredentialAgent instead.
    Validate database credentials by attempting connections
    """
    logger.warning("validate_credentials() is deprecated. Use CredentialAgent instead.")
    print("\nValidating connections...")

    # Test Oracle connection
    try:
        print("  Testing Oracle connection...")
        oracle_conn = OracleConnector(oracle_creds)
        if oracle_conn.connect():
            print("  ✅ Oracle connection successful")
            oracle_conn.disconnect()
        else:
            print("  ❌ Oracle connection failed")
            return False
    except Exception as e:
        print(f"  ❌ Oracle connection error: {e}")
        return False

    # Test SQL Server connection
    try:
        print("  Testing SQL Server connection...")
        sqlserver_conn = SQLServerConnector(sqlserver_creds)
        if sqlserver_conn.connect():
            print("  ✅ SQL Server connection successful")
            sqlserver_conn.disconnect()
        else:
            print("  ❌ SQL Server connection failed")
            return False
    except Exception as e:
        print(f"  ❌ SQL Server connection error: {e}")
        return False

    return True


def discover_oracle_tables(oracle_creds: Dict) -> Dict:
    """Discover all tables in Oracle database"""
    try:
        oracle_conn = OracleConnector(oracle_creds)
        if not oracle_conn.connect():
            return {"status": "error", "message": "Failed to connect to Oracle"}

        tables = oracle_conn.list_tables()
        oracle_conn.disconnect()

        return {
            "status": "success",
            "tables": tables,
            "count": len(tables)
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


def discover_oracle_schema(oracle_creds: Dict) -> Dict:
    """Discover all schema objects in Oracle database"""
    try:
        oracle_conn = OracleConnector(oracle_creds)
        if not oracle_conn.connect():
            return {"status": "error", "message": "Failed to connect to Oracle"}

        procedures = oracle_conn.list_procedures()
        functions = oracle_conn.list_functions()
        triggers = oracle_conn.list_triggers()
        packages = oracle_conn.list_packages()
        oracle_conn.disconnect()

        return {
            "status": "success",
            "procedures": procedures,
            "functions": functions,
            "triggers": triggers,
            "packages": packages
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


def run_migration_orchestrated():
    """
    Main migration with Orchestrator Agent
    Implements complete System Prompt v1.0 workflow
    """
    cost_tracker = CostTracker()
    shared_memory = get_shared_memory()
    
    migration_stats = {
        "tables": {"migrated": 0, "failed": 0, "data_rows": 0},
        "procedures": {"migrated": 0, "failed": 0},
        "functions": {"migrated": 0, "failed": 0},
        "triggers": {"migrated": 0, "failed": 0},
        "packages": {"migrated": 0, "failed": 0},
        "ssma_used": 0,
        "llm_fallback_used": 0
    }
    
    print("\n" + "="*70)
    print("ðŸš€ ORACLE TO SQL SERVER MIGRATION SYSTEM v2.0")
    print("   WITH ORCHESTRATOR AGENT")
    print("="*70)
    print(shared_memory.get_summary())
    print()
    
    # Step 1: Collect and validate credentials
    print("\n" + "="*70)
    print("STEP 1: DATABASE CONNECTION")
    print("="*70)
    # Use the intelligent credential agent with retry logic
    credential_agent = CredentialAgent()
    oracle_creds, sqlserver_creds = credential_agent.run()

    # Check if credential validation succeeded
    if not oracle_creds or not sqlserver_creds:
        print("\n❌ Unable to establish database connections")
        print("Please verify your credentials and try again.")
        logger.error("Migration aborted: credential validation failed")
        return
    
    # Step 2: Initialize orchestrator
    print("\n" + "="*70)
    print("STEP 2: INITIALIZING ORCHESTRATOR")
    print("="*70)
    orchestrator = MigrationOrchestrator(oracle_creds, sqlserver_creds, cost_tracker)
    print("âœ… Orchestrator initialized")
    
    # Check SSMA availability
    try:
        from external_tools.ssma_integration import is_ssma_available
        if is_ssma_available():
            print("âœ… SSMA available - will be used as primary converter")
            orchestrator.ssma_available = True
            migration_stats["ssma_available"] = True
        else:
            print("â„¹ï¸  SSMA not available - using LLM for all conversions")
            migration_stats["ssma_available"] = False
    except ImportError:
        print("â„¹ï¸  SSMA agent not installed - using LLM for all conversions")
        migration_stats["ssma_available"] = False
    
    # Step 3: Discover and create schemas
    print("\n" + "="*70)
    print("STEP 3: SCHEMA DISCOVERY & PREPARATION")
    print("="*70)
    created_schemas = _discover_and_create_schemas(sqlserver_creds)
    print(f"âœ… Schemas ready: {', '.join(created_schemas)}")
    
    # Step 4: Discover and migrate tables
    tables_to_migrate = []
    migrate_data = False
    
    print("\n" + "="*70)
    print("STEP 4: TABLE DISCOVERY & SELECTION")
    print("="*70)
    
    try:
        tinfo = discover_oracle_tables(oracle_creds)

        if tinfo.get("status") == "success" and tinfo.get("tables"):
            tables_to_migrate = get_user_selection("Tables", tinfo["tables"])
            
            if tables_to_migrate:
                data_choice = input("\n  Migrate TABLE DATA as well? [y/N]: ").strip().lower()
                migrate_data = (data_choice == 'y')
                
                if migrate_data:
                    print("  âœ… Will migrate: Structure + Data")
                    logger.info("SECURITY: Table data migration will be performed WITHOUT LLM involvement")
                else:
                    print("  â„¹ï¸  Will migrate: Structure only")
    except Exception as e:
        print(f"  âš ï¸  Error discovering tables: {e}")
        logger.error(f"Table discovery error: {e}", exc_info=True)
    
    # Step 5: Migrate tables using orchestrator
    if tables_to_migrate:
        print(f"\n" + "="*70)
        print(f"STEP 5: MIGRATING {len(tables_to_migrate)} TABLES")
        print("="*70)
        
        for idx, tname in enumerate(tables_to_migrate, 1):
            print(f"\n[{idx}/{len(tables_to_migrate)}] Table: {tname}")
            
            try:
                # Use orchestrator for table migration
                result = orchestrator.orchestrate_table_migration(tname)
                
                if result.get("status") == "success":
                    migration_stats["tables"]["migrated"] += 1
                    
                    # Migrate data if requested
                    if migrate_data:
                        print(f"    Migrating data...")
                        SecurityLogger.log_data_access("migrate", tname, 0)
                        
                        data_result = migrate_table_data(
                            oracle_creds, sqlserver_creds, tname
                        )
                        
                        if data_result.get("status") == "success":
                            rows = data_result.get("rows_migrated", 0)
                            migration_stats["tables"]["data_rows"] += rows
                            SecurityLogger.log_data_access("migrate_complete", tname, rows)
                else:
                    migration_stats["tables"]["failed"] += 1
            
            except Exception as e:
                print(f"    âŒ Error: {e}")
                logger.error(f"Error migrating table {tname}: {e}", exc_info=True)
                migration_stats["tables"]["failed"] += 1
    
    # Step 6: Discover schema objects
    print("\n" + "="*70)
    print("STEP 6: SCHEMA OBJECT DISCOVERY")
    print("="*70)
    
    try:
        schema = discover_oracle_schema(oracle_creds)

        if schema.get("status") != "success":
            print(f"\nâŒ Schema discovery failed: {schema.get('message')}")
            return
    except Exception as e:
        print(f"\nâŒ Error: {e}")
        logger.error(f"Schema discovery error: {e}", exc_info=True)
        return
    
    # Step 7: User selection for code objects
    print("\n" + "="*70)
    print("STEP 7: CODE OBJECT SELECTION")
    print("="*70)
    
    procs = get_user_selection("Procedures", schema.get('procedures', []))
    funcs = get_user_selection("Functions", schema.get('functions', []))
    trigs = get_user_selection("Triggers", schema.get('triggers', []))
    pkgs = get_user_selection("Packages", schema.get('packages', []))

    total_objects = len(procs) + len(funcs) + len(trigs) + len(pkgs)

    if total_objects == 0:
        print("\n⚠️  No code objects selected")
    else:
        print(f"\n✅ Total: {total_objects} code objects")

        # Step 8: Migrate code objects using orchestrator
        print("\n" + "="*70)
        print(f"STEP 8: MIGRATING {total_objects} CODE OBJECTS")
        print("="*70)

        all_objects = (
            [(p, "PROCEDURE") for p in procs] +
            [(f, "FUNCTION") for f in funcs] +
            [(t, "TRIGGER") for t in trigs] +
            [(pkg, "PACKAGE") for pkg in pkgs]
        )
        
        for idx, (obj_name, obj_type) in enumerate(all_objects, 1):
            print(f"\n[{idx}/{total_objects}] {obj_type}: {obj_name}")
            
            try:
                # Use orchestrator for code object migration
                result = orchestrator.orchestrate_code_object_migration(
                    obj_name, obj_type
                )
                
                if result.get("status") == "success":
                    _update_stats(migration_stats, obj_type, True)
                else:
                    _update_stats(migration_stats, obj_type, False)
            
            except Exception as e:
                print(f"    âŒ Error: {e}")
                logger.error(f"Error processing {obj_name}: {e}", exc_info=True)
                _update_stats(migration_stats, obj_type, False)
    
    # Step 9: Generate final report
    print("\n" + "="*70)
    print("STEP 9: GENERATING MIGRATION REPORT")
    print("="*70)
    
    _print_migration_summary(migration_stats, cost_tracker, shared_memory)
    _save_migration_report(migration_stats, cost_tracker, shared_memory)
    
    print("\n" + "="*70)
    print("âœ… MIGRATION COMPLETE")
    print("="*70 + "\n")


def _discover_and_create_schemas(sqlserver_creds: Dict) -> List[str]:
    """Discover and create schemas in SQL Server"""
    shared_memory = get_shared_memory()
    schemas_needed = {"dbo"}  # Always ensure dbo exists

    print("\nAnalyzing schema requirements...")

    # Check shared memory for previously used schemas
    for schema_key in shared_memory.schemas.keys():
        if "." in schema_key:
            _, schema_name = schema_key.split(".", 1)
            if schema_name not in ["sys", "guest", "INFORMATION_SCHEMA"]:
                schemas_needed.add(schema_name)

    # Create/verify all needed schemas
    created_schemas = []
    for schema in schemas_needed:
        print(f"  Checking schema [{schema}]...")
        if ensure_schema_exists(schema, sqlserver_creds):
            print(f"    Schema [{schema}] ready")
            created_schemas.append(schema)
        else:
            print(f"    Schema [{schema}] verification failed")

    return created_schemas


def _update_stats(stats: dict, obj_type: str, success: bool):
    """Update migration statistics"""
    type_map = {
        "PROCEDURE": "procedures",
        "FUNCTION": "functions",
        "TRIGGER": "triggers",
        "PACKAGE": "packages"
    }
    key = type_map.get(obj_type)
    if key:
        stats[key]["migrated" if success else "failed"] += 1


def _print_migration_summary(stats: dict, cost_tracker: CostTracker,
                             shared_memory):
    """Print comprehensive migration summary"""
    print("\n" + "="*70)
    print("MIGRATION SUMMARY")
    print("="*70)

    # Tables
    print(f"\nTABLES:")
    print(f"  Migrated: {stats['tables']['migrated']}")
    print(f"  Failed: {stats['tables']['failed']}")
    if stats['tables']['data_rows'] > 0:
        print(f"  Data Rows: {stats['tables']['data_rows']:,}")

    # Procedures
    if stats['procedures']['migrated'] > 0 or stats['procedures']['failed'] > 0:
        print(f"\nPROCEDURES:")
        print(f"  Migrated: {stats['procedures']['migrated']}")
        print(f"  Failed: {stats['procedures']['failed']}")

    # Functions
    if stats['functions']['migrated'] > 0 or stats['functions']['failed'] > 0:
        print(f"\nFUNCTIONS:")
        print(f"  Migrated: {stats['functions']['migrated']}")
        print(f"  Failed: {stats['functions']['failed']}")

    # Triggers
    if stats['triggers']['migrated'] > 0 or stats['triggers']['failed'] > 0:
        print(f"\nTRIGGERS:")
        print(f"  Migrated: {stats['triggers']['migrated']}")
        print(f"  Failed: {stats['triggers']['failed']}")

    # Packages
    if stats['packages']['migrated'] > 0 or stats['packages']['failed'] > 0:
        print(f"\nPACKAGES:")
        print(f"  Migrated: {stats['packages']['migrated']}")
        print(f"  Failed: {stats['packages']['failed']}")

    # SSMA vs LLM usage
    if stats.get('ssma_available'):
        print(f"\nCONVERSION METHODS:")
        print(f"  SSMA Used: {stats.get('ssma_used', 0)}")
        print(f"  LLM Fallback: {stats.get('llm_fallback_used', 0)}")

    # Cost summary
    print(cost_tracker.summary())

    # Memory summary
    print(shared_memory.get_summary())

    # Links
    print(f"\nRESOURCES:")
    print(f"  LangSmith: https://smith.langchain.com/")
    print(f"  Logs: {OUTPUT_DIR}")


def _save_migration_report(stats: dict, cost_tracker: CostTracker, 
                           shared_memory):
    """Save detailed migration report to file"""
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = OUTPUT_DIR / f"migration_report_{timestamp}.json"
        
        report = {
            "migration_info": {
                "timestamp": datetime.now().isoformat(),
                "version": "2.0",
                "orchestrator_used": True
            },
            "statistics": stats,
            "shared_memory": shared_memory.get_statistics(),
            "cost": {
                "total_usd": cost_tracker.total,
                "details": cost_tracker.get_stats()
            },
            "summary": {
                "total_objects": sum([
                    stats['tables']['migrated'] + stats['tables']['failed'],
                    stats['procedures']['migrated'] + stats['procedures']['failed'],
                    stats['functions']['migrated'] + stats['functions']['failed'],
                    stats['triggers']['migrated'] + stats['triggers']['failed']
                ]),
                "success_rate": _calculate_success_rate(stats)
            }
        }
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"\nMigration report saved: {report_file}")
        logger.info(f"Migration report saved: {report_file}")

    except Exception as e:
        print(f"Failed to save report: {e}")
        logger.error(f"Failed to save report: {e}")


def _calculate_success_rate(stats: dict) -> float:
    """Calculate overall migration success rate"""
    total = sum([
        stats['tables']['migrated'] + stats['tables']['failed'],
        stats['procedures']['migrated'] + stats['procedures']['failed'],
        stats['functions']['migrated'] + stats['functions']['failed'],
        stats['triggers']['migrated'] + stats['triggers']['failed'],
        stats['packages']['migrated'] + stats['packages']['failed']
    ])

    if total == 0:
        return 0.0

    successful = sum([
        stats['tables']['migrated'],
        stats['procedures']['migrated'],
        stats['functions']['migrated'],
        stats['triggers']['migrated'],
        stats['packages']['migrated']
    ])
    
    return round((successful / total) * 100, 2)
