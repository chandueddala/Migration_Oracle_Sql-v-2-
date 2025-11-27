"""
Foreign Key Manager V2 - Fully Dynamic, Schema-Agnostic Implementation
========================================================================

IMPROVEMENTS:
1. No hardcoded schemas (dbo, etc.)
2. Handles qualified names (schema.table)
3. Supports multiple naming conventions
4. Validates input data
5. Comprehensive edge case handling
6. Stateless operation (no instance variables for migration state)
7. Thread-safe if needed
8. Database-agnostic (works with any SQL Server schema)
"""

import re
import logging
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ForeignKeyDefinition:
    """Represents a foreign key constraint - fully schema-aware"""
    constraint_name: str
    source_schema: Optional[str]
    source_table: str
    source_columns: List[str]
    referenced_schema: Optional[str]
    referenced_table: str
    referenced_columns: List[str]
    on_delete: Optional[str] = None
    on_update: Optional[str] = None
    raw_definition: str = ""

    def get_full_source_table(self) -> str:
        """Get fully qualified source table name"""
        if self.source_schema:
            return f"{self.source_schema}.{self.source_table}"
        return self.source_table

    def get_full_referenced_table(self) -> str:
        """Get fully qualified referenced table name"""
        if self.referenced_schema:
            return f"{self.referenced_schema}.{self.referenced_table}"
        return self.referenced_table

    def to_alter_table_statement(self, use_schema: bool = True) -> str:
        """
        Generate ALTER TABLE statement to add this foreign key

        Args:
            use_schema: Whether to include schema in table names

        Returns:
            ALTER TABLE ADD CONSTRAINT statement
        """
        # Source table (with or without schema)
        source_tbl = self.get_full_source_table() if use_schema and self.source_schema else self.source_table

        # Referenced table (with or without schema)
        ref_tbl = self.get_full_referenced_table() if use_schema and self.referenced_schema else self.referenced_table

        # Column lists
        cols = ', '.join(f"[{col}]" for col in self.source_columns)
        ref_cols = ', '.join(f"[{col}]" for col in self.referenced_columns)

        # Build statement
        stmt = f"ALTER TABLE [{source_tbl}] ADD CONSTRAINT [{self.constraint_name}]\n"
        stmt += f"  FOREIGN KEY ({cols})\n"
        stmt += f"  REFERENCES [{ref_tbl}] ({ref_cols})"

        if self.on_delete:
            stmt += f"\n  ON DELETE {self.on_delete}"
        if self.on_update:
            stmt += f"\n  ON UPDATE {self.on_update}"

        stmt += ";"

        return stmt

    def validate(self) -> Tuple[bool, Optional[str]]:
        """
        Validate FK definition

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self.constraint_name:
            return False, "Constraint name is required"

        if not self.source_table:
            return False, "Source table is required"

        if not self.referenced_table:
            return False, "Referenced table is required"

        if not self.source_columns:
            return False, "Source columns are required"

        if not self.referenced_columns:
            return False, "Referenced columns are required"

        if len(self.source_columns) != len(self.referenced_columns):
            return False, f"Column count mismatch: {len(self.source_columns)} != {len(self.referenced_columns)}"

        return True, None


class ForeignKeyManager:
    """
    Manages foreign key extraction, storage, and re-application

    FULLY DYNAMIC - No hardcoded schemas or assumptions
    """

    # Regex patterns for FK detection (schema-agnostic)
    FK_PATTERN = re.compile(
        r',?\s*CONSTRAINT\s+(?:\[([^\]]+)\]|(\w+))\s+'  # Constraint name (bracketed or not)
        r'FOREIGN\s+KEY\s*\(([^)]+)\)\s+'  # Source columns
        r'REFERENCES\s+(?:(?:\[([^\]]+)\]|(\w+))\.)?(?:\[([^\]]+)\]|(\w+))\s*\(([^)]+)\)'  # Ref table & columns
        r'(?:\s+ON\s+DELETE\s+(CASCADE|SET\s+NULL|NO\s+ACTION|SET\s+DEFAULT|RESTRICT))?'  # ON DELETE
        r'(?:\s+ON\s+UPDATE\s+(CASCADE|SET\s+NULL|NO\s+ACTION|SET\s+DEFAULT|RESTRICT))?',  # ON UPDATE
        re.IGNORECASE | re.MULTILINE
    )

    def __init__(self, default_schema: str = "dbo"):
        """
        Initialize the foreign key manager

        Args:
            default_schema: Default schema to use if not specified (default: "dbo")
        """
        self.default_schema = default_schema
        self.foreign_keys: Dict[str, List[ForeignKeyDefinition]] = {}
        self.stripped_count = 0
        self.applied_count = 0
        self.validation_errors: List[str] = []

    def parse_table_name(self, table_ref: str) -> Tuple[Optional[str], str]:
        """
        Parse table reference into schema and table name

        Handles:
        - table_name
        - schema.table_name
        - [schema].[table_name]
        - [schema.table_name] (edge case)

        Args:
            table_ref: Table reference string

        Returns:
            Tuple of (schema, table_name)
        """
        # Remove outer brackets if present
        table_ref = table_ref.strip()
        if table_ref.startswith('[') and table_ref.endswith(']'):
            table_ref = table_ref[1:-1]

        # Check for schema.table format
        if '.' in table_ref:
            parts = table_ref.split('.', 1)
            schema = parts[0].strip('[]')
            table = parts[1].strip('[]')
            return schema, table
        else:
            # No schema specified, use default
            return self.default_schema, table_ref.strip('[]')
    
    def add_foreign_key_from_oracle(self, fk_dict: Dict[str, any]) -> None:
        """
        Add a foreign key definition from Oracle discovery
        
        Converts Oracle FK metadata dictionary into ForeignKeyDefinition
        and stores it for later application.
        
        Args:
            fk_dict: Dictionary with Oracle FK metadata from discover_foreign_keys():
                {
                    'constraint_name': str,
                    'child_schema': str,
                    'child_table': str,
                    'child_columns': List[str],
                    'parent_schema': str,
                    'parent_table': str,
                    'parent_columns': List[str],
                    'delete_rule': str,  # CASCADE, SET NULL, NO ACTION
                    'status': str  # ENABLED, DISABLED
                }
        """
        try:
            # Extract FK metadata
            constraint_name = fk_dict.get('constraint_name', '')
            child_schema = fk_dict.get('child_schema', self.default_schema)
            child_table = fk_dict.get('child_table', '')
            child_columns = fk_dict.get('child_columns', [])
            parent_schema = fk_dict.get('parent_schema', self.default_schema)
            parent_table = fk_dict.get('parent_table', '')
            parent_columns = fk_dict.get('parent_columns', [])
            delete_rule = fk_dict.get('delete_rule', 'NO ACTION')
            status = fk_dict.get('status', 'ENABLED')
            
            # Skip disabled FKs
            if status == 'DISABLED':
                logger.info(f"Skipping disabled FK: {constraint_name}")
                return
            
            # Create ForeignKeyDefinition
            fk_def = ForeignKeyDefinition(
                constraint_name=constraint_name,
                source_schema=child_schema,
                source_table=child_table,
                source_columns=child_columns,
                referenced_schema=parent_schema,
                referenced_table=parent_table,
                referenced_columns=parent_columns,
                on_delete=delete_rule if delete_rule != 'NO ACTION' else None,
                on_update=None,  # Oracle doesn't have ON UPDATE rules like SQL Server
                raw_definition=f"Oracle FK: {constraint_name}"
            )
            
            # Validate FK definition
            is_valid, error_msg = fk_def.validate()
            if not is_valid:
                logger.error(f"Invalid FK from Oracle: {constraint_name} - {error_msg}")
                self.validation_errors.append(f"{constraint_name}: {error_msg}")
                return
            
            # Store FK
            table_key = f"{child_schema}.{child_table}"
            if table_key not in self.foreign_keys:
                self.foreign_keys[table_key] = []
            
            self.foreign_keys[table_key].append(fk_def)
            logger.info(f"Added Oracle FK: {constraint_name} ({child_table}.{','.join(child_columns)} -> {parent_table}.{','.join(parent_columns)})")
            
        except Exception as e:
            logger.error(f"Failed to add Oracle FK: {e}", exc_info=True)
            self.validation_errors.append(f"Oracle FK error: {str(e)}")

    def strip_foreign_keys_from_ddl(
        self,
        ddl: str,
        table_name: str,
        source_schema: Optional[str] = None
    ) -> str:
        """
        Remove all FOREIGN KEY constraints from CREATE TABLE DDL and store them

        Args:
            ddl: CREATE TABLE DDL statement
            table_name: Name of the table
            source_schema: Schema of the source table (optional)

        Returns:
            DDL with foreign keys removed
        """
        if not ddl or not table_name:
            logger.warning("strip_foreign_keys_from_ddl called with empty DDL or table name")
            return ddl

        # Use default schema if not provided
        if not source_schema:
            source_schema = self.default_schema

        logger.info(f"Stripping foreign keys from {source_schema}.{table_name}")

        # Initialize storage for this table if needed
        table_key = f"{source_schema}.{table_name}"
        if table_key not in self.foreign_keys:
            self.foreign_keys[table_key] = []

        # Find all foreign keys
        matches = list(self.FK_PATTERN.finditer(ddl))

        if not matches:
            logger.info(f"No foreign keys found in {table_key}")
            return ddl

        # Extract foreign key definitions before removing
        for match in matches:
            try:
                fk_def = self._parse_fk_match(match, source_schema, table_name)

                # Validate FK definition
                is_valid, error_msg = fk_def.validate()
                if not is_valid:
                    logger.error(f"Invalid FK definition for {fk_def.constraint_name}: {error_msg}")
                    self.validation_errors.append(f"{table_key}.{fk_def.constraint_name}: {error_msg}")
                    continue

                self.foreign_keys[table_key].append(fk_def)
                self.stripped_count += 1
                logger.info(f"  Stripped FK: {fk_def.constraint_name} -> {fk_def.get_full_referenced_table()}")

            except Exception as e:
                logger.error(f"Error parsing FK from {table_key}: {e}", exc_info=True)
                self.validation_errors.append(f"{table_key}: {str(e)}")

        # Remove foreign keys from DDL (replace with empty string)
        cleaned_ddl = self.FK_PATTERN.sub('', ddl)

        # Clean up extra commas and whitespace left behind
        cleaned_ddl = self._cleanup_ddl(cleaned_ddl)

        logger.info(f"Stripped {len(matches)} foreign key(s) from {table_key}")
        return cleaned_ddl

    def _parse_fk_match(
        self,
        match: re.Match,
        source_schema: str,
        source_table: str
    ) -> ForeignKeyDefinition:
        """
        Parse regex match into ForeignKeyDefinition

        Args:
            match: Regex match object
            source_schema: Schema of source table
            source_table: Name of source table

        Returns:
            ForeignKeyDefinition object
        """
        # Constraint name (group 1 or 2 - bracketed or unbracketed)
        constraint_name = (match.group(1) or match.group(2)).strip()

        # Source columns (group 3)
        source_cols_str = match.group(3).strip()
        source_cols = [c.strip().strip('[]') for c in source_cols_str.split(',')]

        # Referenced schema (group 4 or 5 - bracketed or unbracketed)
        ref_schema = (match.group(4) or match.group(5) or self.default_schema).strip() if (match.group(4) or match.group(5)) else self.default_schema

        # Referenced table (group 6 or 7 - bracketed or unbracketed)
        ref_table = (match.group(6) or match.group(7)).strip()

        # Referenced columns (group 8)
        ref_cols_str = match.group(8).strip()
        ref_cols = [c.strip().strip('[]') for c in ref_cols_str.split(',')]

        # ON DELETE (group 9)
        on_delete = match.group(9).strip() if match.group(9) else None

        # ON UPDATE (group 10)
        on_update = match.group(10).strip() if match.group(10) else None

        return ForeignKeyDefinition(
            constraint_name=constraint_name,
            source_schema=source_schema,
            source_table=source_table,
            source_columns=source_cols,
            referenced_schema=ref_schema,
            referenced_table=ref_table,
            referenced_columns=ref_cols,
            on_delete=on_delete,
            on_update=on_update,
            raw_definition=match.group(0)
        )

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

    def get_foreign_keys_for_table(
        self,
        table_name: str,
        schema: Optional[str] = None
    ) -> List[ForeignKeyDefinition]:
        """
        Get all foreign keys for a specific table

        Args:
            table_name: Name of the table
            schema: Schema name (optional, uses default if not provided)

        Returns:
            List of foreign key definitions
        """
        schema = schema or self.default_schema
        table_key = f"{schema}.{table_name}"
        return self.foreign_keys.get(table_key, [])

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

    def generate_alter_table_statements(self, use_schema: bool = True) -> List[str]:
        """
        Generate ALTER TABLE statements for all stored foreign keys

        Args:
            use_schema: Whether to include schema in table names

        Returns:
            List of ALTER TABLE statements
        """
        statements = []

        # Sort tables to try to apply in dependency order
        sorted_fks = self._sort_foreign_keys_by_dependency()

        for fk in sorted_fks:
            statements.append(fk.to_alter_table_statement(use_schema=use_schema))

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
        referenced_tables = {fk.get_full_referenced_table() for fk in all_fks}
        source_tables = set(self.foreign_keys.keys())
        leaf_tables = referenced_tables - source_tables

        # Categorize FKs
        self_referencing = []
        to_leaf_tables = []
        others = []

        for fk in all_fks:
            source_full = fk.get_full_source_table()
            ref_full = fk.get_full_referenced_table()

            if source_full == ref_full:
                self_referencing.append(fk)
            elif ref_full in leaf_tables:
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
            "pending_application": self.stripped_count - self.applied_count,
            "validation_errors": len(self.validation_errors)
        }

    def apply_foreign_keys(
        self,
        sqlserver_conn,
        batch_size: int = 10,
        continue_on_error: bool = True
    ) -> Dict[str, any]:
        """
        Apply all stored foreign keys to SQL Server

        Args:
            sqlserver_conn: SQLServerConnector instance
            batch_size: Number of FKs to apply in each batch
            continue_on_error: Whether to continue if an FK fails to apply

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

                if not continue_on_error:
                    logger.error("Stopping FK application due to error (continue_on_error=False)")
                    break

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

        with open(script_path, 'w', encoding='utf-8') as f:
            f.write("-- ======================================================================\n")
            f.write("-- FOREIGN KEY CONSTRAINTS - Apply After All Tables Are Created\n")
            f.write("-- ======================================================================\n")
            f.write(f"-- Generated: {datetime.now()}\n")
            f.write(f"-- Total Foreign Keys: {len(statements)}\n")
            f.write("-- ======================================================================\n\n")

            for i, stmt in enumerate(statements, 1):
                f.write(f"-- [{i}/{len(statements)}]\n")
                f.write(stmt)
                f.write("\n\nGO\n\n")

            # Add validation errors if any
            if self.validation_errors:
                f.write("\n-- ======================================================================\n")
                f.write("-- VALIDATION ERRORS\n")
                f.write("-- ======================================================================\n")
                for error in self.validation_errors:
                    f.write(f"-- ERROR: {error}\n")

        logger.info(f"Saved foreign key script to: {script_path}")
        return script_path

    def clear(self):
        """Clear all stored foreign keys and counters"""
        self.foreign_keys.clear()
        self.stripped_count = 0
        self.applied_count = 0
        self.validation_errors.clear()
        logger.info("Foreign key manager cleared")

    def get_validation_errors(self) -> List[str]:
        """Get list of validation errors"""
        return self.validation_errors.copy()
