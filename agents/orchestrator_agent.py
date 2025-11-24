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


class MigrationOrchestrator:
    """
    Central orchestrator for the entire migration process
    Manages workflow: Discovery → Conversion → Review → Deploy → Memory Update
    """
    
    def __init__(self, oracle_creds: Dict, sqlserver_creds: Dict, cost_tracker: CostTracker):
        self.oracle_creds = oracle_creds
        self.sqlserver_creds = sqlserver_creds
        self.cost_tracker = cost_tracker
        
        # Initialize agents
        self.memory = MigrationMemory()
        self.converter = ConverterAgent(cost_tracker)
        self.reviewer = ReviewerAgent(cost_tracker)
        self.debugger = DebuggerAgent(cost_tracker)
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
        print(f"\n  🔄 Orchestrating: {table_name}")
        
        try:
            # Step 1: Get Oracle DDL
            print("    📥 Step 1/5: Fetching Oracle DDL...")
            oracle_ddl = self.oracle_conn.get_table_ddl(table_name)
            
            if not oracle_ddl:
                return self._failure_result(
                    table_name, "TABLE",
                    "Failed to fetch DDL from Oracle"
                )
            
            logger.info(f"✅ Retrieved DDL for {table_name}: {len(oracle_ddl)} chars")
            
            # Step 2: Convert (SSMA or LLM)
            print("    🔄 Step 2/5: Converting to SQL Server...")
            if self.ssma_available:
                tsql = self._convert_with_ssma(oracle_ddl, table_name, "TABLE")
            else:
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
                print("    👁️ Step 3/5: Reviewing conversion...")
                review = self.reviewer.review_code(
                    oracle_code=oracle_ddl,
                    tsql_code=tsql,
                    object_name=table_name,
                    object_type="TABLE",
                    cost_tracker=self.cost_tracker
                )
                logger.info(f"Review for {table_name}: {review.get('overall_quality', 'N/A')}")
            else:
                print("    ⏭️  Step 3/5: Review skipped (disabled)")
            
            # Step 4: Deploy with repairs
            print("    🚀 Step 4/5: Deploying to SQL Server...")
            deploy_result = self.debugger.deploy_with_repair(
                sql_code=tsql,
                object_name=table_name,
                object_type="TABLE",
                oracle_code=oracle_ddl,
                sqlserver_creds=self.sqlserver_creds
            )
            
            if deploy_result.get("status") == "success":
                # Step 5: Refresh metadata and update memory
                print("    🔄 Step 5/5: Updating memory with SQL Server metadata...")
                self._refresh_and_update_memory(table_name, "TABLE")
                
                print("    ✅ Table migration successful")
                return deploy_result
            else:
                # Step 6: Log unresolved error
                self._log_unresolved_error(
                    table_name, "TABLE",
                    deploy_result.get("error_history", []),
                    oracle_ddl,
                    deploy_result.get("final_attempt", "")
                )
                print(f"    ❌ Migration failed: {deploy_result.get('message', 'Unknown')[:50]}...")
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
        print(f"\n  🔄 Orchestrating: {obj_name} ({obj_type})")
        
        try:
            # Step 1: Get Oracle code
            print("    📥 Step 1/5: Fetching Oracle code...")
            
            if obj_type == "PACKAGE":
                oracle_code = self.oracle_conn.get_package_code(obj_name)
            else:
                oracle_code = self.oracle_conn.get_code_object(obj_name, obj_type)
            
            if not oracle_code:
                return self._failure_result(
                    obj_name, obj_type,
                    f"Failed to fetch {obj_type} code from Oracle"
                )
            
            logger.info(f"✅ Retrieved {obj_type} code for {obj_name}: {len(oracle_code)} chars")
            
            # Step 2: Convert (SSMA or LLM)
            print("    🔄 Step 2/5: Converting to T-SQL...")
            if self.ssma_available:
                tsql = self._convert_with_ssma(oracle_code, obj_name, obj_type)
            else:
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
            print("    👁️ Step 3/5: Reviewing conversion quality...")
            review = self.reviewer.review_code(
                oracle_code=oracle_code,
                tsql_code=tsql,
                object_name=obj_name,
                object_type=obj_type,
                cost_tracker=self.cost_tracker
            )
            logger.info(f"Review for {obj_name}: {review.get('overall_quality', 'N/A')}")
            
            # Step 4: Deploy with repairs
            print("    🚀 Step 4/5: Deploying to SQL Server...")
            deploy_result = self.debugger.deploy_with_repair(
                sql_code=tsql,
                object_name=obj_name,
                object_type=obj_type,
                oracle_code=oracle_code,
                sqlserver_creds=self.sqlserver_creds
            )
            
            if deploy_result.get("status") == "success":
                # Step 5: Refresh metadata and update memory
                print("    🔄 Step 5/5: Updating memory with SQL Server metadata...")
                self._refresh_and_update_memory(obj_name, obj_type)
                
                # Store success pattern
                self.memory_agent.store_successful_conversion(
                    object_name=obj_name,
                    object_type=obj_type,
                    oracle_code=oracle_code[:300],
                    tsql_code=tsql[:300],
                    review_quality=review.get('overall_quality')
                )
                
                print(f"    ✅ {obj_type} migration successful")
                return deploy_result
            else:
                # Step 6: Log unresolved error
                self._log_unresolved_error(
                    obj_name, obj_type,
                    deploy_result.get("error_history", []),
                    oracle_code,
                    deploy_result.get("final_attempt", "")
                )
                print(f"    ❌ Migration failed: {deploy_result.get('message', 'Unknown')[:50]}...")
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
            result = self.ssma.convert_code(source_code, obj_name, obj_type)
            
            if result.get("status") == "success":
                logger.info(f"✅ SSMA conversion successful for {obj_name}")
                return result.get("tsql_code", "")
            else:
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
            
            elif obj_type in ["PROCEDURE", "FUNCTION", "PACKAGE"]:
                # Get object definition from SQL Server
                definition = self.sqlserver_conn.get_object_definition(obj_name, obj_type)
                
                if definition:
                    logger.info(f"✅ Retrieved SQL Server definition for {obj_name}: {len(definition)} chars")
        
        except Exception as e:
            logger.error(f"❌ Failed to refresh metadata for {obj_name}: {e}")
            # Don't fail the migration, just log
    
    def _log_unresolved_error(self, obj_name: str, obj_type: str,
                             error_history: List, oracle_code: str,
                             final_attempt: str):
        """
        Log unresolved errors for future analysis and retry
        """
        logs_dir = Path("logs/unresolved")
        logs_dir.mkdir(parents=True, exist_ok=True)
        
        log_entry = {
            "object_name": obj_name,
            "object_type": obj_type,
            "timestamp": datetime.now().isoformat(),
            "oracle_code": oracle_code[:2000],  # Truncate for readability
            "error_history": error_history,
            "final_sql_attempt": final_attempt[:2000],
            "total_repair_attempts": len(error_history),
            "unresolved_reason": "Max repair attempts exceeded without success",
            "memory_context": {
                "identity_columns": self.memory.get_identity_columns(obj_name),
                "similar_patterns": [
                    p.get('name', 'unnamed') 
                    for p in self.memory.get_similar_patterns(obj_type, limit=3)
                ],
                "error_solutions_available": len(
                    self.memory.get_error_solutions(
                        error_history[-1]['error'] if error_history else "", 
                        limit=3
                    )
                )
            },
            "recommendations": [
                "Review error history for patterns",
                "Check if manual T-SQL adjustment is needed",
                "Consider schema or constraint issues",
                "Verify Oracle code compatibility with SQL Server"
            ]
        }
        
        timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = logs_dir / f"{obj_name}_{timestamp_str}.json"
        
        with open(log_file, 'w') as f:
            json.dump(log_entry, f, indent=2)
        
        logger.error(f"⚠️ Unresolved error logged: {log_file}")
        print(f"    📝 Unresolved error logged to: {log_file}")
        
        # Also store in shared memory
        self.memory.store_failed_pattern({
            "name": f"{obj_type}_{obj_name}_unresolved",
            "object_type": obj_type,
            "error": error_history[-1]['error'][:200] if error_history else "Unknown",
            "timestamp": datetime.now().isoformat(),
            "log_file": str(log_file)
        })
    
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
