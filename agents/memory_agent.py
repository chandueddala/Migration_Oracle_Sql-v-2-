"""
Shared Memory System for Agents
Stores schemas, patterns, errors, and solutions across all agents
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
from collections import defaultdict

logger = logging.getLogger(__name__)


class SharedMemory:
    """
    Centralized memory system shared across all agents
    Stores learned patterns, schemas, errors, and solutions
    """
    
    def __init__(self, persistence_file: Optional[Path] = None):
        self.persistence_file = persistence_file or Path("output/shared_memory.json")
        
        # Core memory stores
        self.schemas: Dict[str, Any] = {}  # Database schemas
        self.identity_columns: Dict[str, List[str]] = {}  # Tables with identity columns
        self.error_solutions: Dict[str, List[Dict]] = defaultdict(list)  # Error â†’ Solutions
        self.successful_patterns: List[Dict] = []  # Successful conversion patterns
        self.failed_patterns: List[Dict] = []  # Failed patterns to avoid
        self.table_mappings: Dict[str, str] = {}  # Oracle table â†’ SQL Server table
        
        # Load existing memory if available
        self.load()
    
    # ==================== SCHEMA MANAGEMENT ====================
    
    def store_schema(self, database: str, schema_name: str, exists: bool = True):
        """Store information about database schema"""
        key = f"{database}.{schema_name}"
        self.schemas[key] = {
            "database": database,
            "schema": schema_name,
            "exists": exists,
            "created_at": datetime.now().isoformat(),
            "last_verified": datetime.now().isoformat()
        }
        logger.info(f"Stored schema info: {key} (exists={exists})")
        self.save()
    
    def get_schema(self, database: str, schema_name: str) -> Optional[Dict]:
        """Get schema information"""
        key = f"{database}.{schema_name}"
        return self.schemas.get(key)
    
    def schema_exists(self, database: str, schema_name: str) -> bool:
        """Check if schema exists in memory"""
        schema_info = self.get_schema(database, schema_name)
        return schema_info is not None and schema_info.get("exists", False)
    
    def create_schema_if_needed(self, database: str, schema_name: str, 
                               sqlserver_creds: Dict) -> bool:
        """
        Create schema in SQL Server if it doesn't exist
        Returns True if schema exists or was created successfully
        """
        # Check memory first
        if self.schema_exists(database, schema_name):
            logger.info(f"Schema {schema_name} already exists in memory")
            return True
        
        # Try to create schema
        try:
            from database.sqlserver_connector import SQLServerConnector

            sqlserver_conn = SQLServerConnector(sqlserver_creds)
            if not sqlserver_conn.connect():
                logger.error(f"Failed to connect to SQL Server for schema creation")
                return False

            conn = sqlserver_conn.connection
            cursor = conn.cursor()

            # Check if schema exists
            cursor.execute("""
                SELECT SCHEMA_NAME
                FROM INFORMATION_SCHEMA.SCHEMATA
                WHERE SCHEMA_NAME = ?
            """, schema_name)

            if cursor.fetchone():
                logger.info(f"Schema {schema_name} already exists in database")
                self.store_schema(database, schema_name, exists=True)
                cursor.close()
                sqlserver_conn.disconnect()
                return True

            # Create schema
            create_schema_sql = f"CREATE SCHEMA [{schema_name}]"
            cursor.execute(create_schema_sql)
            conn.commit()
            cursor.close()
            sqlserver_conn.disconnect()

            logger.info(f"Created schema: {schema_name}")
            self.store_schema(database, schema_name, exists=True)
            return True
                
        except Exception as e:
            logger.error(f"Failed to create schema {schema_name}: {e}")
            self.store_schema(database, schema_name, exists=False)
            return False
    
    # ==================== IDENTITY COLUMN TRACKING ====================
    
    def register_identity_column(self, table_name: str, column_name: str):
        """Register a table column as identity/auto-increment"""
        if table_name not in self.identity_columns:
            self.identity_columns[table_name] = []
        
        if column_name not in self.identity_columns[table_name]:
            self.identity_columns[table_name].append(column_name)
            logger.info(f"Registered identity column: {table_name}.{column_name}")
            self.save()
    
    def get_identity_columns(self, table_name: str) -> List[str]:
        """Get list of identity columns for a table"""
        return self.identity_columns.get(table_name, [])
    
    def has_identity_columns(self, table_name: str) -> bool:
        """Check if table has identity columns"""
        return table_name in self.identity_columns and len(self.identity_columns[table_name]) > 0
    
    def get_identity_insert_wrapper(self, table_name: str, insert_sql: str) -> str:
        """
        Wrap INSERT statement with IDENTITY_INSERT if table has identity columns
        """
        if self.has_identity_columns(table_name):
            return f"""
SET IDENTITY_INSERT [{table_name}] ON;
{insert_sql}
SET IDENTITY_INSERT [{table_name}] OFF;
"""
        return insert_sql
    
    # ==================== ERROR SOLUTION TRACKING ====================
    
    def store_error_solution(self, error_message: str, solution: Dict):
        """Store a successful solution for an error"""
        error_key = self._normalize_error(error_message)
        
        solution_entry = {
            "solution": solution.get("fix", ""),
            "object_type": solution.get("object_type", ""),
            "success_count": 1,
            "timestamp": datetime.now().isoformat(),
            "context": solution.get("context", {})
        }
        
        # Check if similar solution already exists
        existing = self.error_solutions[error_key]
        found = False
        
        for entry in existing:
            if entry["solution"] == solution_entry["solution"]:
                entry["success_count"] += 1
                entry["timestamp"] = datetime.now().isoformat()
                found = True
                break
        
        if not found:
            self.error_solutions[error_key].append(solution_entry)
        
        logger.info(f"Stored solution for error: {error_key[:50]}...")
        self.save()
    
    def get_error_solutions(self, error_message: str, limit: int = 5) -> List[Dict]:
        """Get known solutions for an error"""
        error_key = self._normalize_error(error_message)
        solutions = self.error_solutions.get(error_key, [])
        
        # Sort by success count
        sorted_solutions = sorted(solutions, key=lambda x: x["success_count"], reverse=True)
        return sorted_solutions[:limit]
    
    def _normalize_error(self, error_message: str) -> str:
        """Normalize error message for matching"""
        # Remove specific details like line numbers, table names in some cases
        normalized = error_message.lower()
        
        # Extract key error patterns
        if "schema name" in normalized and "does not exist" in normalized:
            return "schema_does_not_exist"
        elif "identity_insert" in normalized:
            return "identity_insert_off"
        elif "incorrect syntax near" in normalized:
            return "syntax_error"
        elif "cannot insert explicit value for identity" in normalized:
            return "identity_column_insert"
        
        # Return first 100 chars as key
        return normalized[:100]
    
    # ==================== PATTERN TRACKING ====================
    
    def store_successful_pattern(self, pattern: Dict):
        """Store a successful conversion/migration pattern"""
        pattern_entry = {
            **pattern,
            "timestamp": datetime.now().isoformat(),
            "success": True
        }
        
        self.successful_patterns.append(pattern_entry)
        logger.info(f"Stored successful pattern: {pattern.get('name', 'unnamed')}")
        self.save()
    
    def store_failed_pattern(self, pattern: Dict):
        """Store a failed pattern to avoid"""
        pattern_entry = {
            **pattern,
            "timestamp": datetime.now().isoformat(),
            "success": False
        }
        
        self.failed_patterns.append(pattern_entry)
        logger.info(f"Stored failed pattern: {pattern.get('name', 'unnamed')}")
        self.save()
    
    def get_similar_patterns(self, object_type: str, limit: int = 5) -> List[Dict]:
        """Get similar successful patterns"""
        relevant = [p for p in self.successful_patterns 
                   if p.get("object_type") == object_type]
        return relevant[-limit:]  # Return most recent
    
    # ==================== TABLE MAPPING ====================
    
    def store_table_mapping(self, oracle_table: str, sqlserver_table: str, 
                           schema: str = "dbo"):
        """Store Oracle â†’ SQL Server table mapping"""
        self.table_mappings[oracle_table] = {
            "sqlserver_table": sqlserver_table,
            "schema": schema,
            "mapped_at": datetime.now().isoformat()
        }
        logger.info(f"Stored table mapping: {oracle_table} â†’ {schema}.{sqlserver_table}")
        self.save()
    
    def get_table_mapping(self, oracle_table: str) -> Optional[Dict]:
        """Get SQL Server table mapping for Oracle table"""
        return self.table_mappings.get(oracle_table)
    
    # ==================== PERSISTENCE ====================
    
    def save(self):
        """Save shared memory to disk"""
        try:
            self.persistence_file.parent.mkdir(exist_ok=True)
            
            data = {
                "schemas": self.schemas,
                "identity_columns": self.identity_columns,
                "error_solutions": dict(self.error_solutions),
                "successful_patterns": self.successful_patterns,
                "failed_patterns": self.failed_patterns,
                "table_mappings": self.table_mappings,
                "last_updated": datetime.now().isoformat()
            }
            
            with open(self.persistence_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.debug(f"Saved shared memory to {self.persistence_file}")
            
        except Exception as e:
            logger.error(f"Failed to save shared memory: {e}")
    
    def load(self):
        """Load shared memory from disk"""
        try:
            if self.persistence_file.exists():
                with open(self.persistence_file, 'r') as f:
                    data = json.load(f)
                
                self.schemas = data.get("schemas", {})
                self.identity_columns = data.get("identity_columns", {})
                self.error_solutions = defaultdict(list, data.get("error_solutions", {}))
                self.successful_patterns = data.get("successful_patterns", [])
                self.failed_patterns = data.get("failed_patterns", [])
                self.table_mappings = data.get("table_mappings", {})
                
                logger.info(f"Loaded shared memory from {self.persistence_file}")
                logger.info(f"  - Schemas: {len(self.schemas)}")
                logger.info(f"  - Identity columns: {len(self.identity_columns)}")
                logger.info(f"  - Error solutions: {len(self.error_solutions)}")
                logger.info(f"  - Successful patterns: {len(self.successful_patterns)}")
            else:
                logger.info("No existing shared memory found, starting fresh")
                
        except Exception as e:
            logger.error(f"Failed to load shared memory: {e}")
    
    def clear(self):
        """Clear all shared memory (use with caution)"""
        self.schemas = {}
        self.identity_columns = {}
        self.error_solutions = defaultdict(list)
        self.successful_patterns = []
        self.failed_patterns = []
        self.table_mappings = {}
        self.save()
        logger.warning("Shared memory cleared")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about shared memory"""
        return {
            "schemas_tracked": len(self.schemas),
            "tables_with_identity": len(self.identity_columns),
            "error_solutions": len(self.error_solutions),
            "successful_patterns": len(self.successful_patterns),
            "failed_patterns": len(self.failed_patterns),
            "table_mappings": len(self.table_mappings),
            "total_identity_columns": sum(len(cols) for cols in self.identity_columns.values())
        }
    
    def get_summary(self) -> str:
        """Get human-readable summary"""
        stats = self.get_statistics()
        
        lines = [
            "\nðŸ§  SHARED MEMORY SUMMARY",
            "="*50,
            f"ðŸ“Š Schemas tracked: {stats['schemas_tracked']}",
            f"ðŸ”‘ Tables with identity columns: {stats['tables_with_identity']}",
            f"ðŸ’¡ Error solutions stored: {stats['error_solutions']}",
            f"âœ… Successful patterns: {stats['successful_patterns']}",
            f"âŒ Failed patterns: {stats['failed_patterns']}",
            f"ðŸ—ºï¸  Table mappings: {stats['table_mappings']}",
            "="*50
        ]
        
        return "\n".join(lines)


# Global shared memory instance
_shared_memory = None


def get_shared_memory() -> SharedMemory:
    """Get or create the global shared memory instance"""
    global _shared_memory
    if _shared_memory is None:
        _shared_memory = SharedMemory()
    return _shared_memory


# ==================== HELPER FUNCTIONS ====================

def ensure_schema_exists(schema_name: str, sqlserver_creds: Dict) -> bool:
    """
    Ensure schema exists in SQL Server
    Uses shared memory to avoid repeated checks
    """
    memory = get_shared_memory()
    return memory.create_schema_if_needed("sqlserver", schema_name, sqlserver_creds)


def fix_schema_references(sql_code: str, target_schema: str = "dbo") -> str:
    """
    Fix schema references in SQL code
    Replace APP.table_name with dbo.table_name or [schema].table_name
    """
    import re
    
    # Pattern to match schema.table references
    pattern = r'\b([A-Z_]+)\.([A-Z_]+)\b'
    
    def replace_schema(match):
        schema = match.group(1)
        table = match.group(2)
        
        # If it's a known Oracle schema, replace with target schema
        if schema in ['APP', 'HR', 'SCOTT', 'SYSTEM']:
            return f"[{target_schema}].[{table}]"
        
        return match.group(0)
    
    fixed_code = re.sub(pattern, replace_schema, sql_code, flags=re.IGNORECASE)
    return fixed_code


def handle_identity_columns(table_name: str, columns: List[str],
                           insert_sql: str) -> str:
    """
    Automatically handle identity column inserts
    Wraps INSERT with IDENTITY_INSERT ON/OFF
    """
    memory = get_shared_memory()

    # Register identity columns if not already done
    for col in columns:
        if 'ID' in col.upper() or col.upper().endswith('_ID'):
            memory.register_identity_column(table_name, col)

    # Wrap INSERT if needed
    return memory.get_identity_insert_wrapper(table_name, insert_sql)


# ==================== MEMORY AGENT WRAPPER ====================

class MemoryAgent:
    """Agent wrapper for SharedMemory to provide agent-like interface"""
    def store_failed_pattern(self, pattern: Dict):
        """Store a failed pattern to avoid"""
        pattern_entry = {
            **pattern,
            "timestamp": datetime.now().isoformat(),
            "success": False
        }
        
        self.failed_patterns.append(pattern_entry)
        logger.info(f"Stored failed pattern: {pattern.get('name', 'unnamed')}")
        self.save()
    
    def get_similar_patterns(self, object_type: str, limit: int = 5) -> List[Dict]:
        """Get similar successful patterns"""
        relevant = [p for p in self.successful_patterns 
                   if p.get("object_type") == object_type]
        return relevant[-limit:]  # Return most recent
    
    # ==================== TABLE MAPPING ====================
    
    def store_table_mapping(self, oracle_table: str, sqlserver_table: str, 
                           schema: str = "dbo"):
        """Store Oracle â†’ SQL Server table mapping"""
        self.table_mappings[oracle_table] = {
            "sqlserver_table": sqlserver_table,
            "schema": schema,
            "mapped_at": datetime.now().isoformat()
        }
        logger.info(f"Stored table mapping: {oracle_table} â†’ {schema}.{sqlserver_table}")
        self.save()
    
    def get_table_mapping(self, oracle_table: str) -> Optional[Dict]:
        """Get SQL Server table mapping for Oracle table"""
        return self.table_mappings.get(oracle_table)
    
    # ==================== PERSISTENCE ====================
    
    def save(self):
        """Save shared memory to disk"""
        try:
            self.persistence_file.parent.mkdir(exist_ok=True)
            
            data = {
                "schemas": self.schemas,
                "identity_columns": self.identity_columns,
                "error_solutions": dict(self.error_solutions),
                "successful_patterns": self.successful_patterns,
                "failed_patterns": self.failed_patterns,
                "table_mappings": self.table_mappings,
                "last_updated": datetime.now().isoformat()
            }
            
            with open(self.persistence_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.debug(f"Saved shared memory to {self.persistence_file}")
            
        except Exception as e:
            logger.error(f"Failed to save shared memory: {e}")
    
    def load(self):
        """Load shared memory from disk"""
        try:
            if self.persistence_file.exists():
                with open(self.persistence_file, 'r') as f:
                    data = json.load(f)
                
                self.schemas = data.get("schemas", {})
                self.identity_columns = data.get("identity_columns", {})
                self.error_solutions = defaultdict(list, data.get("error_solutions", {}))
                self.successful_patterns = data.get("successful_patterns", [])
                self.failed_patterns = data.get("failed_patterns", [])
                self.table_mappings = data.get("table_mappings", {})
                
                logger.info(f"Loaded shared memory from {self.persistence_file}")
                logger.info(f"  - Schemas: {len(self.schemas)}")
                logger.info(f"  - Identity columns: {len(self.identity_columns)}")
                logger.info(f"  - Error solutions: {len(self.error_solutions)}")
                logger.info(f"  - Successful patterns: {len(self.successful_patterns)}")
            else:
                logger.info("No existing shared memory found, starting fresh")
                
        except Exception as e:
            logger.error(f"Failed to load shared memory: {e}")
    
    def clear(self):
        """Clear all shared memory (use with caution)"""
        self.schemas = {}
        self.identity_columns = {}
        self.error_solutions = defaultdict(list)
        self.successful_patterns = []
        self.failed_patterns = []
        self.table_mappings = {}
        self.save()
        logger.warning("Shared memory cleared")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about shared memory"""
        return {
            "schemas_tracked": len(self.schemas),
            "tables_with_identity": len(self.identity_columns),
            "error_solutions": len(self.error_solutions),
            "successful_patterns": len(self.successful_patterns),
            "failed_patterns": len(self.failed_patterns),
            "table_mappings": len(self.table_mappings),
            "total_identity_columns": sum(len(cols) for cols in self.identity_columns.values())
        }
    
    def get_summary(self) -> str:
        """Get human-readable summary"""
        stats = self.get_statistics()
        
        lines = [
            "\nðŸ§  SHARED MEMORY SUMMARY",
            "="*50,
            f"ðŸ“Š Schemas tracked: {stats['schemas_tracked']}",
            f"ðŸ”‘ Tables with identity columns: {stats['tables_with_identity']}",
            f"ðŸ’¡ Error solutions stored: {stats['error_solutions']}",
            f"âœ… Successful patterns: {stats['successful_patterns']}",
            f"âŒ Failed patterns: {stats['failed_patterns']}",
            f"ðŸ—ºï¸  Table mappings: {stats['table_mappings']}",
            "="*50
        ]
        
        return "\n".join(lines)


# Global shared memory instance
_shared_memory = None


def get_shared_memory() -> SharedMemory:
    """Get or create the global shared memory instance"""
    global _shared_memory
    if _shared_memory is None:
        _shared_memory = SharedMemory()
    return _shared_memory


# ==================== HELPER FUNCTIONS ====================

def ensure_schema_exists(schema_name: str, sqlserver_creds: Dict) -> bool:
    """
    Ensure schema exists in SQL Server
    Uses shared memory to avoid repeated checks
    """
    memory = get_shared_memory()
    return memory.create_schema_if_needed("sqlserver", schema_name, sqlserver_creds)


def fix_schema_references(sql_code: str, target_schema: str = "dbo") -> str:
    """
    Fix schema references in SQL code
    Replace APP.table_name with dbo.table_name or [schema].table_name
    """
    import re
    
    # Pattern to match schema.table references
    pattern = r'\b([A-Z_]+)\.([A-Z_]+)\b'
    
    def replace_schema(match):
        schema = match.group(1)
        table = match.group(2)
        
        # If it's a known Oracle schema, replace with target schema
        if schema in ['APP', 'HR', 'SCOTT', 'SYSTEM']:
            return f"[{target_schema}].[{table}]"
        
        return match.group(0)
    
    fixed_code = re.sub(pattern, replace_schema, sql_code, flags=re.IGNORECASE)
    return fixed_code


def handle_identity_columns(table_name: str, columns: List[str],
                           insert_sql: str) -> str:
    """
    Automatically handle identity column inserts
    Wraps INSERT with IDENTITY_INSERT ON/OFF
    """
    memory = get_shared_memory()

    # Register identity columns if not already done
    for col in columns:
        if 'ID' in col.upper() or col.upper().endswith('_ID'):
            memory.register_identity_column(table_name, col)

    # Wrap INSERT if needed
    return memory.get_identity_insert_wrapper(table_name, insert_sql)


# ==================== MEMORY AGENT WRAPPER ====================

class MemoryAgent:
    """Agent wrapper for SharedMemory to provide agent-like interface"""

    def __init__(self, memory, cost_tracker):
        self.memory = memory
        self.cost_tracker = cost_tracker

    def store_successful_conversion(self, object_name: str, object_type: str,
                                    oracle_code: str, tsql_code: str,
                                    review_quality: str = None):
        """Store successful conversion pattern"""
        pattern = {
            "name": object_name,
            "object_type": object_type,
            "oracle_snippet": oracle_code[:300],
            "tsql_snippet": tsql_code[:300],
            "review_quality": review_quality  # Store quality if provided
        }
        self.memory.store_successful_pattern(pattern)