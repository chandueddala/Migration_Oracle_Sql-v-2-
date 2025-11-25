"""
Orchestrator Agent - Manages Complete Migration Workflow
Coordinates all agents and handles the complete migration process
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
import json

from config.config_enhanced import (
    CostTracker,
    SSMA_ENABLED,
    MAX_REFLECTION_ITERATIONS
)
from database.migration_memory import MigrationMemory
from database.oracle_connector import OracleConnector
from database.sqlserver_connector import SQLServerConnector
from agents.converter_agent import ConverterAgent
from agents.reviewer_agent import ReviewerAgent
from agents.debugger_agent import DebuggerAgent
from agents.memory_agent import MemoryAgent

logger = logging.getLogger(__name__)

# Safe print function for Windows compatibility with emojis
import sys
def safe_print(message: str):
    """Print message, handling Unicode errors on Windows"""
    try:
        sys.stdout.write(message + '\n')
        sys.stdout.flush()
    except (UnicodeEncodeError, UnicodeDecodeError):
        # Remove emojis and special characters for Windows compatibility
        safe_msg = message.encode('ascii', 'ignore').decode('ascii')
        sys.stdout.write(safe_msg + '\n')
        sys.stdout.flush()

# Use LLM-POWERED decomposer - truly dynamic, works with ANY package structure
try:
    from utils.package_decomposer_llm import decompose_oracle_package
    logger.info("✅ Using LLM-POWERED decomposer (Claude analyzes package structure dynamically)")
except ImportError:
    try:
        from utils.package_decomposer_multi import decompose_oracle_package
        logger.info("⚠️ Using MULTI-PACKAGE UNIVERSAL decomposer (unlimited packages, any database)")
    except ImportError:
        try:
            from utils.package_decomposer_universal import decompose_oracle_package
            logger.info("⚠️ Using UNIVERSAL adaptive package decomposer (multi-database, fault-tolerant)")
        except ImportError:
            try:
                from utils.package_decomposer_dynamic import decompose_oracle_package
                logger.info("⚠️ Using DYNAMIC adaptive package decomposer (multi-database support)")
            except ImportError:
                try:
                    from utils.package_decomposer_fixed import decompose_oracle_package
                    logger.info("⚠️ Using FIXED robust package decomposer")
                except ImportError:
                    try:
                        from utils.package_decomposer_enhanced import decompose_oracle_package
                        logger.info("⚠️ Using enhanced dynamic package decomposer")
                    except ImportError:
                        from utils.package_decomposer import decompose_oracle_package
                        logger.info("⚠️ Using basic package decomposer")


class MigrationOrchestrator:
    """
    Central orchestrator for the entire migration process
    Manages workflow: Discovery → Conversion → Review → Deploy → Memory Update
    """
    
    def __init__(self, oracle_creds: Dict, sqlserver_creds: Dict, cost_tracker: CostTracker, migration_options: Dict = None):
        self.oracle_creds = oracle_creds
        self.sqlserver_creds = sqlserver_creds
        self.cost_tracker = cost_tracker
        self.migration_options = migration_options or {}
        
        # Initialize agents
        self.memory = MigrationMemory()
        self.converter = ConverterAgent(cost_tracker)
        self.reviewer = ReviewerAgent(cost_tracker)
        self.debugger = DebuggerAgent(cost_tracker, self.migration_options)
        self.memory_agent = MemoryAgent(self.memory, cost_tracker)
        
        # Initialize and connect to databases
        self.oracle_conn = OracleConnector(oracle_creds)
        self.sqlserver_conn = SQLServerConnector(sqlserver_creds)

        # Establish connections
        if not self.oracle_conn.connect():
            raise ConnectionError("Failed to establish Oracle connection")
        if not self.sqlserver_conn.connect():
            raise ConnectionError("Failed to establish SQL Server connection")
        
        # SSMA integration (if available)
        self.ssma_available = False
        if SSMA_ENABLED:
            try:
                from external_tools.ssma_integration import SSMAAgent
                self.ssma = SSMAAgent()
                self.ssma_available = self.ssma.available
                if self.ssma_available:
                    logger.info("✅ SSMA integration enabled and available")
                else:
                    logger.info("ℹ️  SSMA configured but not available - using LLM for all conversions")
            except Exception as e:
                logger.warning(f"SSMA not available: {e}")
        
        logger.info("✅ Orchestrator initialized with all agents")
    
    def orchestrate_table_migration(self, table_name: str) -> Dict[str, Any]:
        """
        Complete workflow for table migration
        
        Steps:
        1. Get Oracle DDL
        2. Convert to T-SQL (SSMA if available, else LLM)
        3. Review conversion (optional for tables)
        4. Deploy with repair loops
        5. Refresh SQL Server metadata
        6. Update shared memory
        7. Log unresolved errors if failed
        
        Args:
            table_name: Name of table to migrate
            
        Returns:
            Migration result dictionary
        """
        logger.info(f"🔄 Orchestrating table migration: {table_name}")
        safe_print(f"\n  🔄 Orchestrating: {table_name}")
        
        try:
            # Step 1: Get Oracle DDL
            safe_print("    📥 Step 1/5: Fetching Oracle DDL...")
            oracle_ddl = self.oracle_conn.get_table_ddl(table_name)
            
            if not oracle_ddl:
                return self._failure_result(
                    table_name, "TABLE",
                    "Failed to fetch DDL from Oracle"
                )
            
            logger.info(f"✅ Retrieved DDL for {table_name}: {len(oracle_ddl)} chars")
            
            # Step 2: Convert (SSMA or LLM)
            if self.ssma_available:
                safe_print("    🔄 Step 2/5: Converting to SQL Server (using SSMA)...")
                tsql = self._convert_with_ssma(oracle_ddl, table_name, "TABLE")
            else:
                safe_print("    🔄 Step 2/5: Converting to SQL Server (using LLM)...")
                tsql = self.converter.convert_table_ddl(
                    oracle_ddl=oracle_ddl,
                    table_name=table_name
                )

            if not tsql:
                return self._failure_result(
                    table_name, "TABLE",
                    "Conversion failed"
                )
            
            logger.info(f"✅ Converted {table_name}: {len(tsql)} chars")
            
            # Apply schema fixes
            tsql = self._fix_schema_references(tsql)
            
            # Step 3: Review (optional for tables)
            if MAX_REFLECTION_ITERATIONS > 0:
                safe_print("    👁️ Step 3/5: Reviewing conversion...")
                review = self.reviewer.review_code(
                    oracle_code=oracle_ddl,
                    tsql_code=tsql,
                    object_name=table_name,
                    object_type="TABLE",
                    cost_tracker=self.cost_tracker
                )
                logger.info(f"Review for {table_name}: {review.get('overall_quality', 'N/A')}")
            else:
                safe_print("    ⏭️  Step 3/5: Review skipped (disabled)")
            
            # Step 4: Deploy with repairs
            safe_print("    🚀 Step 4/5: Deploying to SQL Server...")
            deploy_result = self.debugger.deploy_with_repair(
                sql_code=tsql,
                object_name=table_name,
                object_type="TABLE",
                oracle_code=oracle_ddl,
                sqlserver_creds=self.sqlserver_creds
            )
            
            if deploy_result.get("status") == "success":
                # Step 5: Refresh metadata and update memory
                safe_print("    🔄 Step 5/5: Updating memory with SQL Server metadata...")
                self._refresh_and_update_memory(table_name, "TABLE")
                
                safe_print("    ✅ Table migration successful")
                return deploy_result
            else:
                # Step 6: Log unresolved error
                self._log_unresolved_error(
                    table_name, "TABLE",
                    deploy_result.get("error_history", []),
                    oracle_ddl,
                    deploy_result.get("final_attempt", "")
                )
                safe_print(f"    ❌ Migration failed: {deploy_result.get('message', 'Unknown')[:50]}...")
                return deploy_result
        
        except Exception as e:
            logger.error(f"❌ Orchestration failed for {table_name}: {e}", exc_info=True)
            return self._failure_result(table_name, "TABLE", str(e))
    
    def orchestrate_code_object_migration(self, obj_name: str, obj_type: str) -> Dict[str, Any]:
        """
        Complete workflow for procedure/function/package migration

        Args:
            obj_name: Object name
            obj_type: PROCEDURE, FUNCTION, PACKAGE, or TRIGGER

        Returns:
            Migration result dictionary
        """
        logger.info(f"🔄 Orchestrating {obj_type} migration: {obj_name}")
        safe_print(f"\n  🔄 Orchestrating: {obj_name} ({obj_type})")

        # SPECIAL HANDLING FOR PACKAGES
        if obj_type == "PACKAGE":
            return self._orchestrate_package_migration(obj_name)

        try:
            # Step 1: Get Oracle code
            safe_print("    📥 Step 1/5: Fetching Oracle code...")

            oracle_code = self.oracle_conn.get_code_object(obj_name, obj_type)

            if not oracle_code:
                return self._failure_result(
                    obj_name, obj_type,
                    f"Failed to fetch {obj_type} code from Oracle"
                )

            logger.info(f"✅ Retrieved {obj_type} code for {obj_name}: {len(oracle_code)} chars")

            # Step 2: Convert (SSMA or LLM)
            if self.ssma_available:
                safe_print("    🔄 Step 2/5: Converting to T-SQL (using SSMA)...")
                tsql = self._convert_with_ssma(oracle_code, obj_name, obj_type)
            else:
                safe_print("    🔄 Step 2/5: Converting to T-SQL (using LLM)...")
                tsql = self.converter.convert_code(
                    oracle_code=oracle_code,
                    object_name=obj_name,
                    object_type=obj_type
                )
            
            if not tsql:
                return self._failure_result(
                    obj_name, obj_type,
                    "Conversion failed"
                )
            
            logger.info(f"✅ Converted {obj_name}: {len(tsql)} chars")
            
            # Apply schema fixes
            tsql = self._fix_schema_references(tsql)
            
            # Step 3: Review
            safe_print("    👁️ Step 3/5: Reviewing conversion quality...")
            review = self.reviewer.review_code(
                oracle_code=oracle_code,
                tsql_code=tsql,
                object_name=obj_name,
                object_type=obj_type,
                cost_tracker=self.cost_tracker
            )
            logger.info(f"Review for {obj_name}: {review.get('overall_quality', 'N/A')}")
            
            # Step 4: Deploy with repairs
            safe_print("    🚀 Step 4/5: Deploying to SQL Server...")
            deploy_result = self.debugger.deploy_with_repair(
                sql_code=tsql,
                object_name=obj_name,
                object_type=obj_type,
                oracle_code=oracle_code,
                sqlserver_creds=self.sqlserver_creds
            )
            
            if deploy_result.get("status") == "success":
                # Step 5: Refresh metadata and update memory
                safe_print("    🔄 Step 5/5: Updating memory with SQL Server metadata...")
                self._refresh_and_update_memory(obj_name, obj_type)
                
                # Store success pattern
                self.memory_agent.store_successful_conversion(
                    object_name=obj_name,
                    object_type=obj_type,
                    oracle_code=oracle_code[:300],
                    tsql_code=tsql[:300],
                    review_quality=review.get('overall_quality')
                )
                
                safe_print(f"    ✅ {obj_type} migration successful")
                return deploy_result
            else:
                # Step 6: Log unresolved error
                self._log_unresolved_error(
                    obj_name, obj_type,
                    deploy_result.get("error_history", []),
                    oracle_code,
                    deploy_result.get("final_attempt", "")
                )
                safe_print(f"    ❌ Migration failed: {deploy_result.get('message', 'Unknown')[:50]}...")
                return deploy_result
        
        except Exception as e:
            logger.error(f"❌ Orchestration failed for {obj_name}: {e}", exc_info=True)
            return self._failure_result(obj_name, obj_type, str(e))
    
    def _convert_with_ssma(self, source_code: str, obj_name: str, obj_type: str) -> str:
        """
        Convert using SSMA
        
        Args:
            source_code: Oracle source code
            obj_name: Object name
            obj_type: Object type
            
        Returns:
            Converted T-SQL code
        """
        if not self.ssma_available:
            logger.warning(f"SSMA not available for {obj_name}, using LLM fallback")
            if obj_type == "TABLE":
                return self.converter.convert_table_ddl(source_code, obj_name)
            else:
                return self.converter.convert_code(source_code, obj_name, obj_type)
        
        try:
            logger.info(f"🔧 Using SSMA to convert {obj_name}")
            result = self.ssma.convert_object(source_code, obj_name, obj_type)

            # Check if LLM fallback is recommended
            if result.get("use_llm_fallback", False):
                logger.warning(f"⚠️ SSMA recommends LLM fallback for {obj_name}")
                if obj_type == "TABLE":
                    return self.converter.convert_table_ddl(source_code, obj_name)
                else:
                    return self.converter.convert_code(source_code, obj_name, obj_type)

            # SSMA conversion succeeded
            if result.get("status") in ["success", "warning"]:
                tsql = result.get("tsql", "")
                if result.get("status") == "warning":
                    logger.warning(f"⚠️ SSMA conversion has warnings for {obj_name}: {len(result.get('warnings', []))} warnings")
                else:
                    logger.info(f"✅ SSMA conversion successful for {obj_name}")
                return tsql
            else:
                # SSMA failed
                logger.warning(f"⚠️ SSMA conversion failed for {obj_name}, falling back to LLM")
                if obj_type == "TABLE":
                    return self.converter.convert_table_ddl(source_code, obj_name)
                else:
                    return self.converter.convert_code(source_code, obj_name, obj_type)
        
        except Exception as e:
            logger.error(f"❌ SSMA error for {obj_name}: {e}, falling back to LLM")
            if obj_type == "TABLE":
                return self.converter.convert_table_ddl(source_code, obj_name)
            else:
                return self.converter.convert_code(source_code, obj_name, obj_type)
    
    def _refresh_and_update_memory(self, obj_name: str, obj_type: str):
        """
        CRITICAL: Refresh SQL Server metadata after successful deployment
        Updates shared memory with actual database state
        """
        try:
            if obj_type == "TABLE":
                # Get table structure from SQL Server
                columns = self.sqlserver_conn.get_table_columns(obj_name)
                
                if columns:
                    # Register identity columns
                    for col in columns:
                        if col.get('is_identity'):
                            self.memory.register_identity_column(obj_name, col['name'])
                            logger.info(f"✅ Registered identity column: {obj_name}.{col['name']}")
                    
                    # Store table mapping
                    self.memory.store_table_mapping(
                        oracle_table=obj_name,
                        sqlserver_table=obj_name,
                        schema="dbo"
                    )
                    
                    logger.info(f"✅ Updated memory: {obj_name} with {len(columns)} columns")
            
            # NOTE: Metadata refresh for procedures/functions disabled
            # get_object_definition() method not implemented in SQLServerConnector
            # elif obj_type in ["PROCEDURE", "FUNCTION", "PACKAGE"]:
            #     # Get object definition from SQL Server
            #     definition = self.sqlserver_conn.get_object_definition(obj_name, obj_type)
            #     
            #     if definition:
            #         logger.info(f"✅ Retrieved SQL Server definition for {obj_name}: {len(definition)} chars")
        
        except Exception as e:
            logger.error(f"❌ Failed to refresh metadata for {obj_name}: {e}")
            # Don't fail the migration, just log
    def _log_unresolved_error(self, obj_name: str, obj_type: str,
                             error_history: List, oracle_code: str,
                             final_attempt: str):
        """
        Log unresolved errors for future analysis and retry (JSONL format)
        """
        logs_dir = Path("logs")
        logs_dir.mkdir(parents=True, exist_ok=True)
        log_file = logs_dir / "unresolved_migrations.jsonl"
        
        log_entry = {
            "object_name": obj_name,
            "object_type": obj_type,
            "timestamp": datetime.now().isoformat(),
            "oracle_code": oracle_code,
            "error_history": error_history,
            "final_attempt_sql": final_attempt,
            "status": "unresolved"
        }
        
        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry) + '\n')
            
            logger.error(f"⚠️ Unresolved error logged to {log_file}")
            safe_print(f"    📝 Unresolved error logged to: {log_file}")
            
            # Also store in shared memory
            self.memory.store_failed_pattern({
                "name": f"{obj_type}_{obj_name}_unresolved",
                "object_type": obj_type,
                "error": error_history[-1]['error'][:200] if error_history else "Unknown",
                "timestamp": datetime.now().isoformat(),
                "log_file": str(log_file)
            })
        except Exception as e:
            logger.error(f"Failed to log unresolved error: {e}")
    
    def _fix_schema_references(self, sql_code: str, target_schema: str = "dbo") -> str:
        """Fix schema references in SQL code - handles both quoted and unquoted identifiers"""
        import re

        # Pattern to match schema.object references with or without brackets
        # Matches: [SCHEMA].[OBJECT], SCHEMA.OBJECT, "SCHEMA"."OBJECT"
        pattern = r'\[?([A-Z_][A-Z0-9_]*)\]?\.\[?([A-Z_][A-Z0-9_]*)\]?'

        def replace_schema(match):
            schema = match.group(1)
            obj = match.group(2)

            # Common Oracle schemas to replace with dbo
            if schema.upper() in ['APP', 'HR', 'SCOTT', 'SYSTEM', 'SYS', 'PUBLIC', 'APEX', 'ORACLE']:
                return f"[{target_schema}].[{obj}]"

            # Keep other schemas as-is but ensure proper quoting
            return f"[{schema}].[{obj}]"

        result = re.sub(pattern, replace_schema, sql_code, flags=re.IGNORECASE)

        # Also ensure CREATE TABLE statements use dbo schema if no schema specified
        result = re.sub(
            r'CREATE\s+TABLE\s+(?!\[)([A-Z_][A-Z0-9_]*)\s*\(',
            f'CREATE TABLE [{target_schema}].[\\1] (',
            result,
            flags=re.IGNORECASE
        )

        return result
    
    def _orchestrate_package_migration(self, package_name: str) -> Dict[str, Any]:
        """
        Special handling for Oracle packages - DECOMPOSE into individual objects

        Oracle packages are NOT supported in SQL Server.
        We decompose them into individual procedures and functions.

        Args:
            package_name: Name of the Oracle package

        Returns:
            Migration result with details of all decomposed members
        """
        logger.info(f"📦 Decomposing Oracle package: {package_name}")
        safe_print(f"\n  📦 PACKAGE DECOMPOSITION: {package_name}")
        safe_print("  ⚠️  SQL Server does not support packages - decomposing into individual objects")

        try:
            # Step 1: Get package code from Oracle
            safe_print("    📥 Step 1/4: Fetching package code from Oracle...")
            oracle_code = self.oracle_conn.get_package_code(package_name)

            if not oracle_code:
                return self._failure_result(
                    package_name, "PACKAGE",
                    "Failed to fetch package code from Oracle"
                )

            logger.info(f"✅ Retrieved package code: {len(oracle_code)} chars")

            # Step 2: Decompose package into individual members
            safe_print("    🔧 Step 2/4: Decomposing package into procedures/functions...")
            decomposed = decompose_oracle_package(package_name, oracle_code)

            total_members = len(decomposed["members"])
            logger.info(
                f"✅ Decomposed into {total_members} members: "
                f"{decomposed['total_procedures']} procedures, "
                f"{decomposed['total_functions']} functions"
            )
            safe_print(f"       Found {total_members} members to migrate:")
            safe_print(f"       - {decomposed['total_procedures']} procedures")
            safe_print(f"       - {decomposed['total_functions']} functions")

            if decomposed["global_variables"]:
                safe_print(f"       ⚠️  {len(decomposed['global_variables'])} global variables detected")
                logger.warning(f"Package has {len(decomposed['global_variables'])} global variables")

            # Step 3: Migrate each member individually
            safe_print("    🚀 Step 3/4: Migrating individual members...")
            results = []
            success_count = 0
            failure_count = 0

            for i, member in enumerate(decomposed["members"], 1):
                # Generate SQL Server object name (PackageName_MemberName)
                sqlserver_name = f"{package_name}_{member.name}"
                safe_print(f"\n       [{i}/{total_members}] Migrating: {member.name} ({member.member_type})")
                safe_print(f"                          → SQL Server name: {sqlserver_name}")

                # Convert member code
                if self.ssma_available:
                    tsql = self._convert_with_ssma(member.body, sqlserver_name, member.member_type)
                else:
                    tsql = self.converter.convert_code(
                        oracle_code=member.body,
                        object_name=sqlserver_name,
                        object_type=member.member_type
                    )

                if not tsql:
                    logger.error(f"Failed to convert {member.name}")
                    failure_count += 1
                    results.append({
                        "member_name": member.name,
                        "sqlserver_name": sqlserver_name,
                        "status": "error",
                        "message": "Conversion failed"
                    })
                    continue

                # Apply schema fixes
                tsql = self._fix_schema_references(tsql)

                # Review (optional)
                if MAX_REFLECTION_ITERATIONS > 0:
                    review = self.reviewer.review_code(
                        oracle_code=member.body,
                        tsql_code=tsql,
                        object_name=sqlserver_name,
                        object_type=member.member_type,
                        cost_tracker=self.cost_tracker
                    )
                    logger.info(f"Review for {sqlserver_name}: {review.get('overall_quality', 'N/A')}")

                # Deploy
                deploy_result = self.debugger.deploy_with_repair(
                    sql_code=tsql,
                    object_name=sqlserver_name,
                    object_type=member.member_type,
                    oracle_code=member.body,
                    sqlserver_creds=self.sqlserver_creds
                )

                if deploy_result.get("status") == "success":
                    success_count += 1
                    safe_print(f"                          ✅ Success")
                    logger.info(f"✅ Successfully migrated {sqlserver_name}")

                    # Update memory
                    self._refresh_and_update_memory(sqlserver_name, member.member_type)
                else:
                    failure_count += 1
                    safe_print(f"                          ❌ Failed: {deploy_result.get('message', 'Unknown')[:50]}")
                    logger.error(f"❌ Failed to migrate {sqlserver_name}")

                    # Log unresolved error
                    self._log_unresolved_error(
                        sqlserver_name, member.member_type,
                        deploy_result.get("error_history", []),
                        member.body,
                        deploy_result.get("final_attempt", "")
                    )

                results.append({
                    "member_name": member.name,
                    "sqlserver_name": sqlserver_name,
                    "type": member.member_type,
                    "status": deploy_result.get("status"),
                    "message": deploy_result.get("message", "")
                })

            # Step 4: Summary
            safe_print(f"\n    📊 Step 4/4: Package decomposition summary")
            safe_print(f"       ✅ Successfully migrated: {success_count}/{total_members}")
            safe_print(f"       ❌ Failed: {failure_count}/{total_members}")

            if decomposed["initialization"]:
                safe_print(f"       ⚠️  Package initialization code detected - requires manual migration")
                logger.warning("Package has initialization code that requires manual handling")

            # Return comprehensive result
            return {
                "status": "success" if failure_count == 0 else "partial",
                "object_name": package_name,
                "object_type": "PACKAGE",
                "strategy": "DECOMPOSED",
                "total_members": total_members,
                "success_count": success_count,
                "failure_count": failure_count,
                "members": results,
                "has_global_variables": len(decomposed["global_variables"]) > 0,
                "has_initialization": bool(decomposed["initialization"]),
                "notes": decomposed["migration_plan"]["notes"],
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"❌ Package decomposition failed for {package_name}: {e}", exc_info=True)
            return self._failure_result(package_name, "PACKAGE", str(e))

    def _failure_result(self, obj_name: str, obj_type: str, message: str) -> Dict:
        """Create standardized failure result"""
        return {
            "status": "error",
            "object_name": obj_name,
            "object_type": obj_type,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
    
    def get_migration_status(self) -> Dict[str, Any]:
        """Get current migration status and statistics"""
        return {
            "memory_stats": {
                "successful_patterns": len(self.memory.get_similar_patterns("ALL", limit=1000)),
                "failed_patterns": len(self.memory.get_similar_patterns("FAILED", limit=1000)),
                "error_solutions": len(self.memory.get_error_solutions("", limit=1000)),
            },
            "ssma_available": self.ssma_available,
            "cost_tracker": {
                "total_cost": self.cost_tracker.total_cost,
                "total_tokens": self.cost_tracker.total_tokens_used,
            },
            "timestamp": datetime.now().isoformat()
        }
