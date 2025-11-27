"""
Foreign Key Manager - Strips and manages foreign keys during table migration
============================================================================

This module implements a two-phase foreign key strategy:
1. Strip all foreign keys from CREATE TABLE statements during initial creation
2. Store foreign key definitions in memory
3. After all tables are created, replay foreign keys as ALTER TABLE statements

This prevents dependency order issues and circular reference errors.
"""

import re
import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ForeignKeyDefinition:
    """Represents a foreign key constraint"""
    constraint_name: str
    source_table: str
    source_columns: List[str]
    referenced_table: str
    referenced_columns: List[str]
    on_delete: Optional[str] = None
    on_update: Optional[str] = None
    raw_definition: str = ""

    def to_alter_table_statement(self) -> str:
        """
        Generate ALTER TABLE statement to add this foreign key

        Returns:
            ALTER TABLE ADD CONSTRAINT statement
        """
        cols = ', '.join(self.source_columns)
        ref_cols = ', '.join(self.referenced_columns)

        stmt = f"ALTER TABLE {self.source_table} ADD CONSTRAINT {self.constraint_name}\n"
        stmt += f"  FOREIGN KEY ({cols})\n"
        stmt += f"  REFERENCES {self.referenced_table} ({ref_cols})"

        if self.on_delete:
            stmt += f"\n  ON DELETE {self.on_delete}"
        if self.on_update:
            stmt += f"\n  ON UPDATE {self.on_update}"

        stmt += ";"

        return stmt


class ForeignKeyManager:
    """
    Manages foreign key extraction, storage, and re-application
    """

    def __init__(self):
        """Initialize the foreign key manager"""
        self.foreign_keys: Dict[str, List[ForeignKeyDefinition]] = {}
        self.stripped_count = 0
        self.applied_count = 0

    def strip_foreign_keys_from_ddl(self, ddl: str, table_name: str) -> str:
        """
        Remove all FOREIGN KEY constraints from CREATE TABLE DDL and store them

        Args:
            ddl: CREATE TABLE DDL statement
            table_name: Name of the table

        Returns:
            DDL with foreign keys removed
        """
        logger.info(f"Stripping foreign keys from {table_name}")

        # Initialize storage for this table if needed
        if table_name not in self.foreign_keys:
            self.foreign_keys[table_name] = []

        # Pattern to match CONSTRAINT ... FOREIGN KEY
        # Matches both inline and out-of-line foreign key constraints
        # Supports schema-qualified table names: [schema].[table] or schema.table
        fk_pattern = re.compile(
            r',?\s*CONSTRAINT\s+(\[?[\w_]+\]?)\s+'
            r'FOREIGN\s+KEY\s*\(([^)]+)\)\s+'
            r'REFERENCES\s+(\[?[\w_.]+\]?\.?\[?[\w_]+\]?)\s*\(([^)]+)\)'
            r'(\s+ON\s+DELETE\s+(CASCADE|SET\s+NULL|NO\s+ACTION|SET\s+DEFAULT))?'
            r'(\s+ON\s+UPDATE\s+(CASCADE|SET\s+NULL|NO\s+ACTION|SET\s+DEFAULT))?',
            re.IGNORECASE | re.MULTILINE
        )

        # Find all foreign keys
        matches = list(fk_pattern.finditer(ddl))

        if not matches:
            logger.info(f"No foreign keys found in {table_name}")
            return ddl

        # Extract foreign key definitions before removing
        for match in matches:
            constraint_name = match.group(1).strip('[]')
            source_cols_str = match.group(2).strip()
            ref_table_raw = match.group(3)  # Keep the full schema.table format
            ref_cols_str = match.group(4).strip()
            on_delete = match.group(6) if match.group(6) else None
            on_update = match.group(8) if match.group(8) else None

            # Properly format schema.table or just table
            # Input might be: [APP].[SALES_ORDERS], APP].[SALES_ORDERS, [SALES_ORDERS], etc.
            ref_table = ref_table_raw.strip()
            # Normalize: if it has dots, ensure both parts are bracketed
            if '.' in ref_table:
                parts = ref_table.split('.')
                schema_part = parts[0].strip().strip('[]')
                table_part = parts[1].strip().strip('[]')
                ref_table = f"[{schema_part}].[{table_part}]"
            else:
                # Single table name, just bracket it
                ref_table = f"[{ref_table.strip('[]')}]"

            # Parse column lists
            source_cols = [c.strip().strip('[]') for c in source_cols_str.split(',')]
            ref_cols = [c.strip().strip('[]') for c in ref_cols_str.split(',')]

            fk_def = ForeignKeyDefinition(
                constraint_name=constraint_name,
                source_table=table_name,
                source_columns=source_cols,
                referenced_table=ref_table,
                referenced_columns=ref_cols,
                on_delete=on_delete,
                on_update=on_update,
                raw_definition=match.group(0)
            )

            self.foreign_keys[table_name].append(fk_def)
            self.stripped_count += 1
            logger.info(f"  Stripped FK: {constraint_name} -> {ref_table}")

        # Remove foreign keys from DDL (replace with empty string)
        cleaned_ddl = fk_pattern.sub('', ddl)

        # Clean up extra commas and whitespace left behind
        cleaned_ddl = self._cleanup_ddl(cleaned_ddl)

        logger.info(f"Stripped {len(matches)} foreign key(s) from {table_name}")
        return cleaned_ddl

    def _cleanup_ddl(self, ddl: str) -> str:
        """
        Clean up DDL after removing foreign keys

        Removes:
        - Double commas (,,)
        - Trailing commas before closing parenthesis
        - Extra whitespace

        Args:
            ddl: DDL to clean

        Returns:
            Cleaned DDL
        """
        # Remove double commas
        ddl = re.sub(r',\s*,', ',', ddl)

        # Remove trailing comma before closing parenthesis
        ddl = re.sub(r',(\s*)\)', r'\1)', ddl)

        # Remove comma at the end of constraint list
        ddl = re.sub(r',(\s*)(?=\);?\s*$)', r'\1', ddl, flags=re.MULTILINE)

        # Clean up multiple blank lines
        ddl = re.sub(r'\n\s*\n\s*\n', '\n\n', ddl)

        return ddl

    def get_foreign_keys_for_table(self, table_name: str) -> List[ForeignKeyDefinition]:
        """
        Get all foreign keys for a specific table

        Args:
            table_name: Name of the table

        Returns:
            List of foreign key definitions
        """
        return self.foreign_keys.get(table_name, [])

    def get_all_foreign_keys(self) -> List[ForeignKeyDefinition]:
        """
        Get all foreign keys from all tables

        Returns:
            List of all foreign key definitions
        """
        all_fks = []
        for fks in self.foreign_keys.values():
            all_fks.extend(fks)
        return all_fks

    def generate_alter_table_statements(self) -> List[str]:
        """
        Generate ALTER TABLE statements for all stored foreign keys

        Returns:
            List of ALTER TABLE statements
        """
        statements = []

        # Sort tables to try to apply in dependency order
        # (tables without dependencies first)
        sorted_fks = self._sort_foreign_keys_by_dependency()

        for fk in sorted_fks:
            statements.append(fk.to_alter_table_statement())

        return statements

    def _sort_foreign_keys_by_dependency(self) -> List[ForeignKeyDefinition]:
        """
        Sort foreign keys to minimize dependency issues

        Strategy:
        1. Self-referencing FKs last
        2. FKs referencing tables without FKs first
        3. Others in between

        Returns:
            Sorted list of foreign key definitions
        """
        all_fks = self.get_all_foreign_keys()

        # Get tables that are referenced but have no outgoing FKs
        referenced_tables = {fk.referenced_table for fk in all_fks}
        source_tables = set(self.foreign_keys.keys())
        leaf_tables = referenced_tables - source_tables

        # Categorize FKs
        self_referencing = []
        to_leaf_tables = []
        others = []

        for fk in all_fks:
            if fk.source_table == fk.referenced_table:
                self_referencing.append(fk)
            elif fk.referenced_table in leaf_tables:
                to_leaf_tables.append(fk)
            else:
                others.append(fk)

        # Combine: leaf tables first, then others, then self-referencing last
        return to_leaf_tables + others + self_referencing

    def get_summary(self) -> Dict[str, any]:
        """
        Get summary statistics

        Returns:
            Dictionary with statistics
        """
        total_fks = sum(len(fks) for fks in self.foreign_keys.values())

        # Count only tables that actually have FKs
        tables_with_fks = sum(1 for fks in self.foreign_keys.values() if len(fks) > 0)

        return {
            "total_tables_with_fks": tables_with_fks,
            "total_foreign_keys": total_fks,
            "foreign_keys_stripped": self.stripped_count,
            "foreign_keys_applied": self.applied_count,
            "pending_application": self.stripped_count - self.applied_count
        }

    def apply_foreign_keys(self, sqlserver_conn, batch_size: int = 10) -> Dict[str, any]:
        """
        Apply all stored foreign keys to SQL Server

        Args:
            sqlserver_conn: SQLServerConnector instance
            batch_size: Number of FKs to apply in each batch

        Returns:
            Result dictionary with success/failure counts
        """
        logger.info("=" * 70)
        logger.info("APPLYING FOREIGN KEY CONSTRAINTS")
        logger.info("=" * 70)

        statements = self.generate_alter_table_statements()

        if not statements:
            logger.info("No foreign keys to apply")
            return {
                "status": "success",
                "total": 0,
                "applied": 0,
                "failed": 0,
                "errors": []
            }

        logger.info(f"Generated {len(statements)} ALTER TABLE statements")

        applied = 0
        failed = 0
        errors = []

        for i, stmt in enumerate(statements, 1):
            try:
                logger.info(f"[{i}/{len(statements)}] Applying FK constraint...")

                # Execute the ALTER TABLE statement
                sqlserver_conn.execute_ddl(stmt)

                applied += 1
                self.applied_count += 1
                logger.info(f"  ✅ Success")

            except Exception as e:
                failed += 1
                error_msg = str(e)
                errors.append({
                    "statement": stmt,
                    "error": error_msg
                })
                logger.error(f"  ❌ Failed: {error_msg}")

        logger.info("=" * 70)
        logger.info(f"Foreign Key Application Complete:")
        logger.info(f"  Total:   {len(statements)}")
        logger.info(f"  Applied: {applied}")
        logger.info(f"  Failed:  {failed}")
        logger.info("=" * 70)

        return {
            "status": "success" if failed == 0 else "partial",
            "total": len(statements),
            "applied": applied,
            "failed": failed,
            "errors": errors
        }

    def save_foreign_key_scripts(self, output_dir: str) -> str:
        """
        Save foreign key ALTER TABLE scripts to a file

        Args:
            output_dir: Directory to save the script

        Returns:
            Path to the saved script file
        """
        import os
        from pathlib import Path

        # Create output directory if needed
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        script_path = os.path.join(output_dir, "apply_foreign_keys.sql")

        statements = self.generate_alter_table_statements()

        with open(script_path, 'w') as f:
            f.write("-- ======================================================================\n")
            f.write("-- FOREIGN KEY CONSTRAINTS - Apply After All Tables Are Created\n")
            f.write("-- ======================================================================\n")
            f.write(f"-- Generated: {__import__('datetime').datetime.now()}\n")
            f.write(f"-- Total Foreign Keys: {len(statements)}\n")
            f.write("-- ======================================================================\n\n")

            for i, stmt in enumerate(statements, 1):
                f.write(f"-- [{i}/{len(statements)}]\n")
                f.write(stmt)
                f.write("\n\nGO\n\n")

        logger.info(f"Saved foreign key script to: {script_path}")
        return script_path

    def clear(self):
        """Clear all stored foreign keys"""
        self.foreign_keys.clear()
        self.stripped_count = 0
        self.applied_count = 0
        logger.info("Foreign key manager cleared")
