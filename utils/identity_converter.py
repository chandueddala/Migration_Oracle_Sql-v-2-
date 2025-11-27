"""
IDENTITY Column Converter - Handles IDENTITY conversion and data migration
============================================================================

Converts Oracle sequences to SQL Server IDENTITY columns and manages
IDENTITY_INSERT for data migration.
"""

import re
import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class IdentityConverter:
    """
    Converts tables to use IDENTITY columns and manages IDENTITY_INSERT
    """

    def __init__(self):
        """Initialize IDENTITY converter"""
        self.identity_columns: Dict[str, List[Dict]] = {}  # table -> [column info]

    def convert_column_to_identity(
        self,
        ddl: str,
        table_name: str,
        column_name: str,
        start_value: int = 1,
        increment: int = 1
    ) -> str:
        """
        Convert a column in CREATE TABLE DDL to IDENTITY

        Args:
            ddl: Original CREATE TABLE statement
            table_name: Table name
            column_name: Column to convert to IDENTITY
            start_value: IDENTITY start value
            increment: IDENTITY increment value

        Returns:
            Modified DDL with IDENTITY column
        """
        logger.info(f"Converting {table_name}.{column_name} to IDENTITY({start_value},{increment})")

        # Pattern to find the column definition
        # Matches: column_name data_type [constraints]
        col_pattern = re.compile(
            rf'\b{re.escape(column_name)}\b'  # Column name
            r'\s+'  # Whitespace
            r'(INT|INTEGER|BIGINT|SMALLINT|TINYINT|NUMERIC|DECIMAL)'  # Numeric type
            r'(\s*\(\s*\d+\s*(?:,\s*\d+\s*)?\))?'  # Optional precision (numeric types)
            r'([^,)]*)',  # Rest of the definition until comma or close paren
            re.IGNORECASE
        )

        def replace_with_identity(match):
            data_type = match.group(1).upper()
            constraints = match.group(3) or ''

            # Remove NOT NULL if present (IDENTITY implies NOT NULL)
            constraints = re.sub(r'\bNOT\s+NULL\b', '', constraints, flags=re.IGNORECASE)

            # Build IDENTITY column definition
            identity_def = f"{column_name} {data_type} IDENTITY({start_value},{increment}){constraints}"
            return identity_def

        # Replace the column definition
        modified_ddl = col_pattern.sub(replace_with_identity, ddl, count=1)

        # Track the IDENTITY column
        if table_name not in self.identity_columns:
            self.identity_columns[table_name] = []

        self.identity_columns[table_name].append({
            "column": column_name,
            "start_value": start_value,
            "increment": increment
        })

        return modified_ddl

    def remove_sequence_trigger(
        self,
        trigger_code: str,
        sequence_name: str
    ) -> Optional[str]:
        """
        Analyze trigger to see if it should be removed (simple PK trigger)

        Args:
            trigger_code: Trigger DDL/code
            sequence_name: Sequence name used in trigger

        Returns:
            None if trigger should be removed (simple PK assignment)
            Modified trigger code if it has other logic
        """
        code_upper = trigger_code.upper()

        # If it's a simple PK trigger, return None (remove it)
        if self._is_simple_pk_trigger_pattern(trigger_code, sequence_name):
            logger.info(f"Trigger uses {sequence_name} only for PK - will be removed (IDENTITY replaces it)")
            return None

        # If trigger has other logic, remove just the sequence assignment
        # and return the modified trigger
        pattern = rf':NEW\.(\w+)\s*:=\s*{re.escape(sequence_name)}\.NEXTVAL\s*;'
        modified = re.sub(pattern, '', trigger_code, flags=re.IGNORECASE)

        if modified != trigger_code:
            logger.info(f"Removed sequence assignment from trigger (other logic preserved)")
            return modified

        return trigger_code

    def _is_simple_pk_trigger_pattern(self, trigger_code: str, sequence_name: str) -> bool:
        """Check if trigger is just for PK generation"""
        code_upper = trigger_code.upper()

        # Must have sequence assignment
        has_sequence = f"{sequence_name}.NEXTVAL".upper() in code_upper

        # Should not have complex logic
        complexity_indicators = [
            'SELECT', 'UPDATE', 'DELETE', 'INSERT',
            'LOOP', 'WHILE', 'FOR',
            'EXCEPTION', 'RAISE'
        ]

        # Count significant keywords
        complexity_count = sum(1 for keyword in complexity_indicators if keyword in code_upper)

        # Simple trigger: has sequence and minimal complexity
        return has_sequence and complexity_count <= 1

    def generate_identity_insert_statements(
        self,
        table_name: str,
        schema: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Generate IDENTITY_INSERT ON/OFF statements

        Args:
            table_name: Table name
            schema: Schema name (optional)

        Returns:
            Tuple of (SET IDENTITY_INSERT ON statement, SET IDENTITY_INSERT OFF statement)
        """
        full_table = f"{schema}.{table_name}" if schema else table_name

        on_stmt = f"SET IDENTITY_INSERT [{full_table}] ON;"
        off_stmt = f"SET IDENTITY_INSERT [{full_table}] OFF;"

        return on_stmt, off_stmt

    def calculate_reseed_value(
        self,
        max_id: Optional[int],
        increment: int = 1
    ) -> int:
        """
        Calculate the value to reseed IDENTITY

        Args:
            max_id: Maximum ID currently in table (or None if empty)
            increment: IDENTITY increment value

        Returns:
            Value to reseed to
        """
        if max_id is None:
            return 0  # Empty table, start from beginning

        return max_id + increment

    def generate_reseed_statement(
        self,
        table_name: str,
        reseed_value: int,
        schema: Optional[str] = None
    ) -> str:
        """
        Generate DBCC CHECKIDENT statement to reseed IDENTITY

        Args:
            table_name: Table name
            reseed_value: Value to reseed to
            schema: Schema name (optional)

        Returns:
            DBCC CHECKIDENT statement
        """
        full_table = f"{schema}.{table_name}" if schema else table_name

        stmt = f"DBCC CHECKIDENT ('[{full_table}]', RESEED, {reseed_value});"

        return stmt

    def get_max_id_query(
        self,
        table_name: str,
        column_name: str,
        schema: Optional[str] = None
    ) -> str:
        """
        Generate query to get MAX(id) from table

        Args:
            table_name: Table name
            column_name: ID column name
            schema: Schema name (optional)

        Returns:
            SELECT MAX query
        """
        full_table = f"{schema}.{table_name}" if schema else table_name

        query = f"SELECT ISNULL(MAX([{column_name}]), 0) FROM [{full_table}];"

        return query

    def generate_data_migration_script(
        self,
        table_name: str,
        column_name: str,
        schema: Optional[str] = None
    ) -> str:
        """
        Generate complete data migration script for IDENTITY table

        Args:
            table_name: Table name
            column_name: IDENTITY column name
            schema: Schema name (optional)

        Returns:
            Complete migration script
        """
        lines = []

        lines.append(f"-- ============================================")
        lines.append(f"-- Data Migration for {table_name} (IDENTITY)")
        lines.append(f"-- ============================================")
        lines.append("")

        # Step 1: Enable IDENTITY_INSERT
        on_stmt, off_stmt = self.generate_identity_insert_statements(table_name, schema)
        lines.append("-- Step 1: Enable IDENTITY_INSERT")
        lines.append(on_stmt)
        lines.append("")

        # Step 2: Insert data (placeholder - actual data comes from Oracle)
        lines.append("-- Step 2: Insert data from Oracle")
        lines.append("-- INSERT INTO [...] VALUES (...);")
        lines.append("-- (Bulk insert data here)")
        lines.append("")

        # Step 3: Disable IDENTITY_INSERT
        lines.append("-- Step 3: Disable IDENTITY_INSERT")
        lines.append(off_stmt)
        lines.append("")

        # Step 4: Get max ID and reseed
        lines.append("-- Step 4: Reseed IDENTITY to MAX(id) + 1")
        max_query = self.get_max_id_query(table_name, column_name, schema)
        lines.append(f"DECLARE @MaxID INT = ({max_query.rstrip(';')});")
        lines.append(f"DECLARE @ReseedValue INT = @MaxID + 1;")
        lines.append("")

        reseed_stmt = self.generate_reseed_statement(
            table_name,
            reseed_value=0,  # Will be replaced by @ReseedValue
            schema=schema
        )

        # Replace literal value with variable
        reseed_stmt = reseed_stmt.replace(", 0)", ", @ReseedValue)")

        lines.append(reseed_stmt)
        lines.append("")

        lines.append("-- ============================================")

        return "\n".join(lines)

    def get_identity_columns(self, table_name: str) -> List[Dict]:
        """
        Get IDENTITY columns for a table

        Args:
            table_name: Table name

        Returns:
            List of IDENTITY column info dicts
        """
        return self.identity_columns.get(table_name, [])

    def has_identity_column(self, table_name: str) -> bool:
        """Check if table has IDENTITY column"""
        return table_name in self.identity_columns and len(self.identity_columns[table_name]) > 0

    def get_statistics(self) -> Dict:
        """Get statistics on IDENTITY conversions"""
        total_tables = len(self.identity_columns)
        total_columns = sum(len(cols) for cols in self.identity_columns.values())

        return {
            "total_tables_with_identity": total_tables,
            "total_identity_columns": total_columns,
            "tables": list(self.identity_columns.keys())
        }

    def clear(self):
        """Clear all tracked IDENTITY columns"""
        self.identity_columns.clear()
        logger.info("IDENTITY converter cleared")
