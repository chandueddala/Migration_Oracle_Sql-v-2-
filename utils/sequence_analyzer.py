"""
Oracle SEQUENCE Analyzer - Intelligent Sequence Migration Strategy
===================================================================

Analyzes Oracle SEQUENCES and determines the best SQL Server migration path:

1. IDENTITY COLUMN: For sequences used only in BEFORE INSERT triggers for PKs
2. SQL SERVER SEQUENCE: For sequences used in procedures/functions/queries
3. SHARED SEQUENCE: For sequences used across multiple tables

This is a FULLY DYNAMIC, schema-agnostic implementation.
"""

import re
import logging
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class SequenceMigrationStrategy(Enum):
    """Strategy for migrating an Oracle sequence"""
    IDENTITY_COLUMN = "identity_column"  # Convert to IDENTITY column
    SQL_SERVER_SEQUENCE = "sql_server_sequence"  # Create SQL Server SEQUENCE
    SHARED_SEQUENCE = "shared_sequence"  # Shared across tables - must be SEQUENCE
    MANUAL_REVIEW = "manual_review"  # Complex usage - needs review


@dataclass
class SequenceUsage:
    """Tracks where and how a sequence is used"""
    sequence_name: str
    schema: Optional[str]

    # Where it's used
    used_in_triggers: Set[str] = field(default_factory=set)
    used_in_procedures: Set[str] = field(default_factory=set)
    used_in_functions: Set[str] = field(default_factory=set)
    used_in_views: Set[str] = field(default_factory=set)
    used_in_packages: Set[str] = field(default_factory=set)

    # How it's used
    nextval_count: int = 0  # .NEXTVAL usages
    currval_count: int = 0  # .CURRVAL usages

    # Tables using this sequence
    associated_tables: Set[str] = field(default_factory=set)
    associated_pk_columns: Set[Tuple[str, str]] = field(default_factory=set)  # (table, column)

    # Trigger analysis
    is_simple_pk_trigger: bool = False  # True if only used in BEFORE INSERT for PK
    trigger_details: List[Dict] = field(default_factory=list)

    # Current value (for reseeding)
    current_value: Optional[int] = None

    def get_full_name(self) -> str:
        """Get fully qualified sequence name"""
        if self.schema:
            return f"{self.schema}.{self.sequence_name}"
        return self.sequence_name

    def get_usage_summary(self) -> Dict:
        """Get summary of usage"""
        return {
            "total_usages": (
                len(self.used_in_triggers) +
                len(self.used_in_procedures) +
                len(self.used_in_functions) +
                len(self.used_in_views) +
                len(self.used_in_packages)
            ),
            "nextval_count": self.nextval_count,
            "currval_count": self.currval_count,
            "tables": len(self.associated_tables),
            "is_simple_pk": self.is_simple_pk_trigger
        }

    def determine_strategy(self) -> SequenceMigrationStrategy:
        """
        Determine the best migration strategy based on usage patterns

        Returns:
            Recommended migration strategy
        """
        # Rule 1: If used ONLY in a single table's BEFORE INSERT trigger for PK
        if (self.is_simple_pk_trigger and
            len(self.associated_tables) == 1 and
            len(self.used_in_procedures) == 0 and
            len(self.used_in_functions) == 0 and
            len(self.used_in_views) == 0 and
            len(self.used_in_packages) == 0):
            return SequenceMigrationStrategy.IDENTITY_COLUMN

        # Rule 2: If used across multiple tables (shared sequence)
        if len(self.associated_tables) > 1:
            return SequenceMigrationStrategy.SHARED_SEQUENCE

        # Rule 3: If used in procedures/functions/queries
        if (len(self.used_in_procedures) > 0 or
            len(self.used_in_functions) > 0 or
            len(self.used_in_views) > 0 or
            len(self.used_in_packages) > 0):
            return SequenceMigrationStrategy.SQL_SERVER_SEQUENCE

        # Rule 4: If used in triggers but complex pattern
        if len(self.used_in_triggers) > 0 and not self.is_simple_pk_trigger:
            return SequenceMigrationStrategy.SQL_SERVER_SEQUENCE

        # Default: Needs manual review
        return SequenceMigrationStrategy.MANUAL_REVIEW


class SequenceAnalyzer:
    """
    Analyzes Oracle sequences and determines migration strategy

    FULLY DYNAMIC - No hardcoded schemas or assumptions
    """

    # Regex patterns for detecting sequence usage (schema-agnostic)
    NEXTVAL_PATTERN = re.compile(
        r'(?:(?:\[([^\]]+)\]|(\w+))\.)?'  # Optional schema
        r'(?:\[([^\]]+)\]|(\w+))'  # Sequence name
        r'\.NEXTVAL',
        re.IGNORECASE
    )

    CURRVAL_PATTERN = re.compile(
        r'(?:(?:\[([^\]]+)\]|(\w+))\.)?'  # Optional schema
        r'(?:\[([^\]]+)\]|(\w+))'  # Sequence name
        r'\.CURRVAL',
        re.IGNORECASE
    )

    def __init__(self, default_schema: str = "dbo"):
        """
        Initialize sequence analyzer

        Args:
            default_schema: Default schema for unqualified references
        """
        self.default_schema = default_schema
        self.sequences: Dict[str, SequenceUsage] = {}  # Key: fully qualified name
        self.migration_plan: Dict[str, Dict] = {}

    def register_sequence(
        self,
        sequence_name: str,
        schema: Optional[str] = None,
        current_value: Optional[int] = None
    ):
        """
        Register a sequence from Oracle

        Args:
            sequence_name: Name of the sequence
            schema: Schema name (optional)
            current_value: Current sequence value (optional)
        """
        schema = schema or self.default_schema
        full_name = f"{schema}.{sequence_name}"

        if full_name not in self.sequences:
            self.sequences[full_name] = SequenceUsage(
                sequence_name=sequence_name,
                schema=schema,
                current_value=current_value
            )
            logger.info(f"Registered sequence: {full_name}")

    def analyze_trigger(
        self,
        trigger_name: str,
        trigger_code: str,
        table_name: str,
        schema: Optional[str] = None
    ):
        """
        Analyze trigger for sequence usage

        Args:
            trigger_name: Name of the trigger
            trigger_code: PL/SQL trigger code
            table_name: Table the trigger is on
            schema: Schema name (optional)
        """
        schema = schema or self.default_schema

        # Find NEXTVAL usages
        nextval_matches = list(self.NEXTVAL_PATTERN.finditer(trigger_code))
        currval_matches = list(self.CURRVAL_PATTERN.finditer(trigger_code))

        for match in nextval_matches:
            seq_schema = (match.group(1) or match.group(2) or schema).strip()
            seq_name = (match.group(3) or match.group(4)).strip()
            full_seq_name = f"{seq_schema}.{seq_name}"

            # Register if not exists
            if full_seq_name not in self.sequences:
                self.register_sequence(seq_name, seq_schema)

            seq_usage = self.sequences[full_seq_name]
            seq_usage.used_in_triggers.add(f"{schema}.{trigger_name}")
            seq_usage.nextval_count += 1
            seq_usage.associated_tables.add(f"{schema}.{table_name}")

            # Check if it's a simple PK trigger
            if self._is_simple_pk_trigger(trigger_code, seq_name, table_name):
                seq_usage.is_simple_pk_trigger = True

                # Extract PK column name
                pk_col = self._extract_pk_column_from_trigger(trigger_code)
                if pk_col:
                    seq_usage.associated_pk_columns.add((f"{schema}.{table_name}", pk_col))

            seq_usage.trigger_details.append({
                "trigger": trigger_name,
                "table": table_name,
                "schema": schema,
                "type": "BEFORE INSERT" if "BEFORE INSERT" in trigger_code.upper() else "OTHER"
            })

        for match in currval_matches:
            seq_schema = (match.group(1) or match.group(2) or schema).strip()
            seq_name = (match.group(3) or match.group(4)).strip()
            full_seq_name = f"{seq_schema}.{seq_name}"

            if full_seq_name not in self.sequences:
                self.register_sequence(seq_name, seq_schema)

            seq_usage = self.sequences[full_seq_name]
            seq_usage.used_in_triggers.add(f"{schema}.{trigger_name}")
            seq_usage.currval_count += 1

    def analyze_procedure(
        self,
        procedure_name: str,
        procedure_code: str,
        schema: Optional[str] = None
    ):
        """Analyze procedure for sequence usage"""
        schema = schema or self.default_schema
        self._analyze_code_object(
            procedure_code,
            "procedure",
            f"{schema}.{procedure_name}",
            schema
        )

    def analyze_function(
        self,
        function_name: str,
        function_code: str,
        schema: Optional[str] = None
    ):
        """Analyze function for sequence usage"""
        schema = schema or self.default_schema
        self._analyze_code_object(
            function_code,
            "function",
            f"{schema}.{function_name}",
            schema
        )

    def analyze_view(
        self,
        view_name: str,
        view_code: str,
        schema: Optional[str] = None
    ):
        """Analyze view for sequence usage"""
        schema = schema or self.default_schema
        self._analyze_code_object(
            view_code,
            "view",
            f"{schema}.{view_name}",
            schema
        )

    def analyze_package(
        self,
        package_name: str,
        package_code: str,
        schema: Optional[str] = None
    ):
        """Analyze package for sequence usage"""
        schema = schema or self.default_schema
        self._analyze_code_object(
            package_code,
            "package",
            f"{schema}.{package_name}",
            schema
        )

    def _analyze_code_object(
        self,
        code: str,
        object_type: str,
        full_object_name: str,
        schema: str
    ):
        """Generic code analysis for sequence usage"""
        nextval_matches = list(self.NEXTVAL_PATTERN.finditer(code))
        currval_matches = list(self.CURRVAL_PATTERN.finditer(code))

        for match in nextval_matches:
            seq_schema = (match.group(1) or match.group(2) or schema).strip()
            seq_name = (match.group(3) or match.group(4)).strip()
            full_seq_name = f"{seq_schema}.{seq_name}"

            if full_seq_name not in self.sequences:
                self.register_sequence(seq_name, seq_schema)

            seq_usage = self.sequences[full_seq_name]
            seq_usage.nextval_count += 1

            if object_type == "procedure":
                seq_usage.used_in_procedures.add(full_object_name)
            elif object_type == "function":
                seq_usage.used_in_functions.add(full_object_name)
            elif object_type == "view":
                seq_usage.used_in_views.add(full_object_name)
            elif object_type == "package":
                seq_usage.used_in_packages.add(full_object_name)

        for match in currval_matches:
            seq_schema = (match.group(1) or match.group(2) or schema).strip()
            seq_name = (match.group(3) or match.group(4)).strip()
            full_seq_name = f"{seq_schema}.{seq_name}"

            if full_seq_name not in self.sequences:
                self.register_sequence(seq_name, seq_schema)

            seq_usage = self.sequences[full_seq_name]
            seq_usage.currval_count += 1

            if object_type == "procedure":
                seq_usage.used_in_procedures.add(full_object_name)
            elif object_type == "function":
                seq_usage.used_in_functions.add(full_object_name)
            elif object_type == "view":
                seq_usage.used_in_views.add(full_object_name)
            elif object_type == "package":
                seq_usage.used_in_packages.add(full_object_name)

    def _is_simple_pk_trigger(
        self,
        trigger_code: str,
        sequence_name: str,
        table_name: str
    ) -> bool:
        """
        Check if trigger is a simple BEFORE INSERT for PK generation

        Pattern:
        BEFORE INSERT ON table
        FOR EACH ROW
        BEGIN
          :NEW.id := sequence.NEXTVAL;
        END;
        """
        code_upper = trigger_code.upper()

        # Must be BEFORE INSERT
        if "BEFORE INSERT" not in code_upper:
            return False

        # Must be FOR EACH ROW
        if "FOR EACH ROW" not in code_upper:
            return False

        # Must have :NEW.column := [schema.]sequence.NEXTVAL pattern
        # Handle both schema.sequence.NEXTVAL and sequence.NEXTVAL
        seq_name_upper = sequence_name.upper()
        new_pattern = r':NEW\.(\w+)\s*:=\s*(?:\w+\.)?' + re.escape(seq_name_upper) + r'\.NEXTVAL'
        if not re.search(new_pattern, code_upper):
            return False

        # Should not have complex logic (heuristic: check code length and complexity)
        lines = trigger_code.strip().split('\n')

        # Simple trigger should be < 15 lines typically
        if len(lines) > 15:
            return False

        # Should not have SELECT, UPDATE, DELETE, LOOP, IF (beyond simple assignment)
        # Use word boundaries to avoid false matches
        complexity_keywords = [r'\bSELECT\b', r'\bUPDATE\b', r'\bDELETE\b', r'\bLOOP\b', r'\bWHILE\b']

        for keyword_pattern in complexity_keywords:
            if re.search(keyword_pattern, code_upper):
                return False

        # Check for FOR loops (but not FOR EACH ROW which is the trigger declaration)
        # Use word boundary to avoid matching "FOR" in "BEFORE"
        for_count = len(re.findall(r'\bFOR\b', code_upper))
        if for_count > 1:  # More than one FOR (beyond FOR EACH ROW)
            return False

        # Check for IFs (more than simple validation)
        # Use word boundary to avoid matching "IF" in other words
        if_count = len(re.findall(r'\bIF\b', code_upper))
        if if_count > 1:
            return False

        return True

    def _extract_pk_column_from_trigger(self, trigger_code: str) -> Optional[str]:
        """Extract PK column name from trigger"""
        # Pattern: :NEW.column_name :=
        match = re.search(r':NEW\.(\w+)\s*:=', trigger_code, re.IGNORECASE)
        if match:
            return match.group(1)
        return None

    def generate_migration_plan(self) -> Dict[str, Dict]:
        """
        Generate comprehensive migration plan for all sequences

        Returns:
            Dict mapping sequence names to migration details
        """
        self.migration_plan = {}

        for seq_full_name, seq_usage in self.sequences.items():
            strategy = seq_usage.determine_strategy()

            self.migration_plan[seq_full_name] = {
                "sequence_name": seq_usage.sequence_name,
                "schema": seq_usage.schema,
                "strategy": strategy.value,
                "usage_summary": seq_usage.get_usage_summary(),
                "current_value": seq_usage.current_value,
                "associated_tables": list(seq_usage.associated_tables),
                "associated_pk_columns": [
                    {"table": tbl, "column": col}
                    for tbl, col in seq_usage.associated_pk_columns
                ],
                "used_in": {
                    "triggers": list(seq_usage.used_in_triggers),
                    "procedures": list(seq_usage.used_in_procedures),
                    "functions": list(seq_usage.used_in_functions),
                    "views": list(seq_usage.used_in_views),
                    "packages": list(seq_usage.used_in_packages)
                },
                "migration_sql": self._generate_migration_sql(seq_usage, strategy)
            }

        logger.info(f"Generated migration plan for {len(self.migration_plan)} sequences")
        return self.migration_plan

    def _generate_migration_sql(
        self,
        seq_usage: SequenceUsage,
        strategy: SequenceMigrationStrategy
    ) -> Dict[str, str]:
        """Generate SQL statements for migration"""
        sql = {}

        if strategy == SequenceMigrationStrategy.IDENTITY_COLUMN:
            # Generate ALTER TABLE to add IDENTITY
            for table, column in seq_usage.associated_pk_columns:
                sql[f"alter_table_{table}"] = (
                    f"-- Convert {column} to IDENTITY column\n"
                    f"-- Note: Requires table recreation or ALTER COLUMN\n"
                    f"ALTER TABLE [{table}] ALTER COLUMN [{column}] INT IDENTITY(1,1) NOT NULL;"
                )

            # Generate trigger DROP statements
            for trigger in seq_usage.used_in_triggers:
                sql[f"drop_trigger_{trigger}"] = (
                    f"-- Drop Oracle-style trigger (no longer needed with IDENTITY)\n"
                    f"DROP TRIGGER IF EXISTS [{trigger}];"
                )

        elif strategy in [SequenceMigrationStrategy.SQL_SERVER_SEQUENCE,
                          SequenceMigrationStrategy.SHARED_SEQUENCE]:
            # Generate CREATE SEQUENCE
            start_value = (seq_usage.current_value or 0) + 1
            sql["create_sequence"] = (
                f"-- Create SQL Server SEQUENCE\n"
                f"CREATE SEQUENCE [{seq_usage.get_full_name()}]\n"
                f"  START WITH {start_value}\n"
                f"  INCREMENT BY 1\n"
                f"  MINVALUE 1\n"
                f"  NO MAXVALUE\n"
                f"  CACHE 50;"  # SQL Server default
            )

            # Generate example of converting .NEXTVAL to NEXT VALUE FOR
            sql["usage_example"] = (
                f"-- Convert Oracle: {seq_usage.sequence_name}.NEXTVAL\n"
                f"-- To SQL Server: NEXT VALUE FOR {seq_usage.get_full_name()}"
            )

        return sql

    def save_migration_plan(self, output_path: str):
        """Save migration plan to JSON file"""
        import json
        from datetime import datetime

        plan_with_metadata = {
            "generated_at": datetime.now().isoformat(),
            "total_sequences": len(self.migration_plan),
            "strategies": {
                "identity_column": sum(
                    1 for p in self.migration_plan.values()
                    if p["strategy"] == SequenceMigrationStrategy.IDENTITY_COLUMN.value
                ),
                "sql_server_sequence": sum(
                    1 for p in self.migration_plan.values()
                    if p["strategy"] == SequenceMigrationStrategy.SQL_SERVER_SEQUENCE.value
                ),
                "shared_sequence": sum(
                    1 for p in self.migration_plan.values()
                    if p["strategy"] == SequenceMigrationStrategy.SHARED_SEQUENCE.value
                ),
                "manual_review": sum(
                    1 for p in self.migration_plan.values()
                    if p["strategy"] == SequenceMigrationStrategy.MANUAL_REVIEW.value
                )
            },
            "sequences": self.migration_plan
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(plan_with_metadata, f, indent=2)

        logger.info(f"Migration plan saved to: {output_path}")

    def generate_migration_report(self) -> str:
        """Generate human-readable migration report"""
        if not self.migration_plan:
            self.generate_migration_plan()

        lines = []
        lines.append("=" * 80)
        lines.append("ORACLE SEQUENCE MIGRATION PLAN")
        lines.append("=" * 80)
        lines.append("")

        # Summary by strategy
        strategies = {}
        for seq_name, plan in self.migration_plan.items():
            strategy = plan["strategy"]
            if strategy not in strategies:
                strategies[strategy] = []
            strategies[strategy].append(seq_name)

        lines.append("SUMMARY BY STRATEGY:")
        for strategy, sequences in sorted(strategies.items()):
            lines.append(f"  {strategy.upper()}: {len(sequences)} sequence(s)")
        lines.append("")

        # Details for each strategy
        for strategy in sorted(strategies.keys()):
            lines.append("=" * 80)
            lines.append(f"STRATEGY: {strategy.upper()}")
            lines.append("=" * 80)

            for seq_name in sorted(strategies[strategy]):
                plan = self.migration_plan[seq_name]
                lines.append(f"\nSequence: {seq_name}")
                lines.append(f"  Current Value: {plan['current_value']}")
                lines.append(f"  Usage:")
                usage = plan["usage_summary"]
                lines.append(f"    Total Usages: {usage['total_usages']}")
                lines.append(f"    NEXTVAL: {usage['nextval_count']}, CURRVAL: {usage['currval_count']}")
                lines.append(f"    Associated Tables: {usage['tables']}")

                if plan["associated_tables"]:
                    lines.append(f"  Tables: {', '.join(plan['associated_tables'])}")

                if plan["associated_pk_columns"]:
                    lines.append(f"  PK Columns:")
                    for pk_info in plan["associated_pk_columns"]:
                        lines.append(f"    {pk_info['table']}.{pk_info['column']}")

                # Show migration SQL
                if plan["migration_sql"]:
                    lines.append(f"  Migration SQL:")
                    for sql_key, sql_stmt in plan["migration_sql"].items():
                        lines.append(f"    {sql_stmt}")

                lines.append("")

        lines.append("=" * 80)

        return "\n".join(lines)
