from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict


@dataclass
class ColumnInfo:
    name: str
    data_type: str
    data_length: Optional[int]
    nullable: bool
    default: Optional[str]


@dataclass
class ConstraintInfo:
    name: str
    constraint_type: str  # P, U, C, R
    table: str
    columns: List[str]
    referenced_table: Optional[str] = None
    referenced_columns: Optional[List[str]] = None


@dataclass
class IndexInfo:
    name: str
    columns: List[str]
    uniqueness: str


@dataclass
class TriggerInfo:
    name: str
    event: str
    body: str


@dataclass
class FunctionInfo:
    name: str
    arguments: List[Dict]
    return_type: str
    body: str


@dataclass
class ProcedureInfo:
    name: str
    arguments: List[Dict]
    body: str


@dataclass
class PackageInfo:
    name: str
    body: str
    spec: str


@dataclass
class ViewInfo:
    name: str
    query: str


@dataclass
class SequenceInfo:
    name: str
    min_value: Optional[int]
    max_value: Optional[int]
    increment_by: Optional[int]
    cycle_flag: Optional[str]


@dataclass
class TableInfo:
    owner: str
    name: str
    columns: List[ColumnInfo] = field(default_factory=list)
    constraints: List[ConstraintInfo] = field(default_factory=list)
    indexes: List[IndexInfo] = field(default_factory=list)
    triggers: List[TriggerInfo] = field(default_factory=list)
    to_migrate: bool = True


@dataclass
class SchemaInfo:
    name: str
    tables: List[TableInfo] = field(default_factory=list)
    views: List[ViewInfo] = field(default_factory=list)
    functions: List[FunctionInfo] = field(default_factory=list)
    procedures: List[ProcedureInfo] = field(default_factory=list)
    packages: List[PackageInfo] = field(default_factory=list)
    sequences: List[SequenceInfo] = field(default_factory=list)
    to_migrate: bool = True


@dataclass
class OracleDatabaseMemory:
    connection_name: str
    instance_name: Optional[str]
    schemas: List[SchemaInfo] = field(default_factory=list)

    def to_dict(self):
        return asdict(self)


# ============================================================================
# MIGRATION MEMORY - Shared memory for cross-agent learning
# ============================================================================

class MigrationMemory:
    """
    Centralized memory system for storing and retrieving migration patterns,
    error solutions, and object mappings across all agents.
    """
    
    def __init__(self):
        from collections import defaultdict
        from datetime import datetime
        
        # Identity columns tracking (for INSERT statement generation)
        self._identity_columns = defaultdict(list)
        
        # Table mappings (Oracle -> SQL Server)
        self._table_mappings = {}
        
        # Successful conversion patterns
        self._successful_patterns = []
        
        # Failed conversion patterns
        self._failed_patterns = []
        
        # Error solutions (error message -> solution)
        self._error_solutions = defaultdict(list)
        
        # Column mappings (Oracle type -> SQL Server type)
        self._column_type_mappings = {
            "NUMBER": "DECIMAL",
            "VARCHAR2": "NVARCHAR",
            "CLOB": "NVARCHAR(MAX)",
            "BLOB": "VARBINARY(MAX)",
            "DATE": "DATETIME2",
            "TIMESTAMP": "DATETIME2",
        }
    
    def register_identity_column(self, table_name, column_name):
        """Register a SQL Server IDENTITY column"""
        if column_name not in self._identity_columns[table_name.upper()]:
            self._identity_columns[table_name.upper()].append(column_name.upper())
    
    def get_identity_columns(self, table_name):
        """Get list of IDENTITY columns for a table"""
        return self._identity_columns.get(table_name.upper(), [])
    
    def has_identity_column(self, table_name):
        """Check if table has any IDENTITY columns"""
        return len(self._identity_columns.get(table_name.upper(), [])) > 0
    
    def store_table_mapping(self, oracle_table, sqlserver_table, schema="dbo"):
        """Store Oracle to SQL Server table mapping"""
        self._table_mappings[oracle_table.upper()] = {
            "sqlserver_table": sqlserver_table,
            "schema": schema
        }
    
    def get_table_mapping(self, oracle_table):
        """Get SQL Server table mapping for Oracle table"""
        return self._table_mappings.get(oracle_table.upper())
    
    def store_successful_pattern(self, pattern):
        """Store successful conversion pattern"""
        from datetime import datetime
        pattern['timestamp'] = datetime.now().isoformat()
        self._successful_patterns.append(pattern)
    
    def store_failed_pattern(self, pattern):
        """Store failed conversion pattern"""
        from datetime import datetime
        pattern['timestamp'] = datetime.now().isoformat()
        self._failed_patterns.append(pattern)
    
    def get_similar_patterns(self, object_type, limit=5):
        """Get similar successful patterns for an object type"""
        patterns = [p for p in self._successful_patterns if p.get('object_type') == object_type]
        return patterns[-limit:] if patterns else []
    
    def store_error_solution(self, error_message, solution):
        """Store solution for a specific error"""
        from datetime import datetime
        solution['timestamp'] = datetime.now().isoformat()
        # Use first 100 chars of error as key
        error_key = error_message[:100].strip()
        self._error_solutions[error_key].append(solution)
    
    def get_error_solutions(self, error_message, limit=3):
        """Get solutions for similar errors"""
        error_key = error_message[:100].strip()
        solutions = self._error_solutions.get(error_key, [])
        return solutions[-limit:] if solutions else []
    
    def get_column_type_mapping(self, oracle_type):
        """Get SQL Server type for Oracle type"""
        return self._column_type_mappings.get(oracle_type.upper(), oracle_type)
    
    def get_statistics(self):
        """Get memory statistics"""
        return {
            "identity_columns": len(self._identity_columns),
            "table_mappings": len(self._table_mappings),
            "successful_patterns": len(self._successful_patterns),
            "failed_patterns": len(self._failed_patterns),
            "error_solutions": sum(len(v) for v in self._error_solutions.values()),
        }
    
    def clear(self):
        """Clear all memory (useful for testing)"""
        self._identity_columns.clear()
        self._table_mappings.clear()
        self._successful_patterns.clear()
        self._failed_patterns.clear()
        self._error_solutions.clear()
