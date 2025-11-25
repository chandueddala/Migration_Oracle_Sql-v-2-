"""
Interactive Selection System

Asks user for ALL selections upfront:
- Which tables to migrate
- Whether to migrate data for each table
- Which packages to migrate
- Which procedures/functions/triggers to migrate

Perfect for frontend integration - returns structured selection data.
"""

import logging
from typing import Dict, List, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class MigrationSelection:
    """User's migration selections"""
    # Tables
    selected_tables: List[str] = field(default_factory=list)
    tables_with_data: List[str] = field(default_factory=list)  # Tables to migrate data
    tables_schema_only: List[str] = field(default_factory=list)  # Tables without data

    # Code objects
    selected_packages: List[str] = field(default_factory=list)
    selected_procedures: List[str] = field(default_factory=list)
    selected_functions: List[str] = field(default_factory=list)
    selected_triggers: List[str] = field(default_factory=list)
    selected_views: List[str] = field(default_factory=list)
    selected_sequences: List[str] = field(default_factory=list)

    # Options
    migrate_all_tables: bool = False
    migrate_all_data: bool = True
    migrate_all_packages: bool = False
    migrate_all_code: bool = False

    def total_objects(self) -> int:
        """Total number of objects selected"""
        return (
            len(self.selected_tables) +
            len(self.selected_packages) +
            len(self.selected_procedures) +
            len(self.selected_functions) +
            len(self.selected_triggers) +
            len(self.selected_views) +
            len(self.selected_sequences)
        )

    def to_json(self) -> Dict[str, Any]:
        """Convert to JSON for frontend"""
        return {
            "tables": {
                "selected": self.selected_tables,
                "with_data": self.tables_with_data,
                "schema_only": self.tables_schema_only,
                "count": len(self.selected_tables)
            },
            "packages": {
                "selected": self.selected_packages,
                "count": len(self.selected_packages)
            },
            "procedures": {
                "selected": self.selected_procedures,
                "count": len(self.selected_procedures)
            },
            "functions": {
                "selected": self.selected_functions,
                "count": len(self.selected_functions)
            },
            "triggers": {
                "selected": self.selected_triggers,
                "count": len(self.selected_triggers)
            },
            "views": {
                "selected": self.selected_views,
                "count": len(self.selected_views)
            },
            "sequences": {
                "selected": self.selected_sequences,
                "count": len(self.selected_sequences)
            },
            "totals": {
                "objects": self.total_objects(),
                "tables_with_data": len(self.tables_with_data),
                "tables_schema_only": len(self.tables_schema_only)
            },
            "options": {
                "migrate_all_tables": self.migrate_all_tables,
                "migrate_all_data": self.migrate_all_data,
                "migrate_all_packages": self.migrate_all_packages,
                "migrate_all_code": self.migrate_all_code
            }
        }


class InteractiveSelector:
    """
    Interactive selection system
    Asks for ALL selections upfront
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def select_all_upfront(self, discovery_result) -> MigrationSelection:
        """
        Interactive selection - asks everything upfront

        Args:
            discovery_result: Result from ComprehensiveDiscovery

        Returns:
            MigrationSelection with all user choices
        """
        selection = MigrationSelection()

        print("\n" + "="*80)
        print(" MIGRATION SELECTION - SELECT EVERYTHING UPFRONT")
        print("="*80)

        # Step 1: Select tables
        if discovery_result.tables:
            selection.selected_tables, selection.migrate_all_tables = self._select_tables(discovery_result.tables)

            # Step 2: For each table, ask if migrate data
            if selection.selected_tables:
                selection.tables_with_data, selection.tables_schema_only = self._select_table_data(
                    selection.selected_tables,
                    discovery_result.tables
                )

        # Step 3: Select packages
        if discovery_result.packages:
            selection.selected_packages, selection.migrate_all_packages = self._select_packages(discovery_result.packages)

        # Step 4: Select other code objects
        selection.selected_procedures = self._select_objects(discovery_result.procedures, "PROCEDURES")
        selection.selected_functions = self._select_objects(discovery_result.functions, "FUNCTIONS")
        selection.selected_triggers = self._select_objects(discovery_result.triggers, "TRIGGERS")

        # Step 5: Optional: Select views and sequences
        if discovery_result.views:
            selection.selected_views = self._select_objects(discovery_result.views, "VIEWS (optional)")
        if discovery_result.sequences:
            selection.selected_sequences = self._select_objects(discovery_result.sequences, "SEQUENCES (optional)")

        # Step 6: Summary
        self._show_selection_summary(selection)

        return selection

    def _select_tables(self, tables: List) -> tuple[List[str], bool]:
        """Select which tables to migrate"""
        print("\n" + "="*80)
        print(" STEP 1: SELECT TABLES TO MIGRATE")
        print("="*80)

        print(f"\n  Found {len(tables)} tables:\n")

        for i, table in enumerate(tables, 1):
            print(f"     {i:2d}. {table.name:30s} ({table.row_count:,} rows, {table.size_mb:.2f} MB)")

        print("\n  Options:")
        print("    - Enter numbers (e.g., 1,3,5)")
        print("    - Enter range (e.g., 1-5)")
        print("    - Enter 'all' for all tables")
        print("    - Press Enter to skip tables")

        choice = input("\n  Select tables to migrate: ").strip()

        if not choice:
            return [], False

        if choice.lower() == 'all':
            return [t.name for t in tables], True

        selected = self._parse_selection(choice, len(tables))
        return [tables[i-1].name for i in selected if i <= len(tables)], False

    def _select_table_data(self, selected_tables: List[str], all_tables: List) -> tuple[List[str], List[str]]:
        """For each table, ask if migrate data"""
        print("\n" + "="*80)
        print(" STEP 2: SELECT WHICH TABLES TO MIGRATE DATA")
        print("="*80)

        print("\n  For each table, choose:")
        print("    - Schema + Data")
        print("    - Schema Only (no data)")

        print("\n  Quick options:")
        print("    - Enter 'all' to migrate data for ALL tables")
        print("    - Enter 'none' for schema only (no data)")
        print("    - Enter specific numbers for tables to include data")

        choice = input("\n  Migrate data for which tables? [all/none/numbers]: ").strip()

        if choice.lower() == 'all':
            return selected_tables, []

        if choice.lower() == 'none':
            return [], selected_tables

        # Show table list with numbers
        print("\n  Tables:")
        for i, table_name in enumerate(selected_tables, 1):
            # Find row count
            table_obj = next((t for t in all_tables if t.name == table_name), None)
            row_count = table_obj.row_count if table_obj else 0
            print(f"     {i}. {table_name} ({row_count:,} rows)")

        choice = input("\n  Enter numbers for tables to include data: ").strip()

        if not choice:
            return [], selected_tables

        selected_indices = self._parse_selection(choice, len(selected_tables))
        with_data = [selected_tables[i-1] for i in selected_indices if i <= len(selected_tables)]
        schema_only = [t for t in selected_tables if t not in with_data]

        return with_data, schema_only

    def _select_packages(self, packages: List) -> tuple[List[str], bool]:
        """Select packages to migrate"""
        print("\n" + "="*80)
        print(" STEP 3: SELECT PACKAGES TO MIGRATE")
        print("="*80)

        if not packages:
            print("\n  No packages found to migrate")
            return [], False

        print(f"\n  Found {len(packages)} packages:\n")

        for i, pkg in enumerate(packages, 1):
            member_count = pkg.metadata.get('member_count', 0)
            status_icon = "[OK]" if pkg.status == 'VALID' else "[!]"
            print(f"     {i:2d}. {pkg.name:30s} ({member_count} members) {status_icon}")

        print("\n  Options:")
        print("    - Enter numbers (e.g., 1,3,5)")
        print("    - Enter range (e.g., 1-5)")
        print("    - Enter 'all' for all packages")
        print("    - Press Enter to skip")

        choice = input("\n  Select packages to migrate: ").strip()

        if not choice:
            return [], False

        if choice.lower() == 'all':
            return [p.name for p in packages], True

        selected = self._parse_selection(choice, len(packages))
        return [packages[i-1].name for i in selected if i <= len(packages)], False

    def _select_objects(self, objects: List, object_type: str) -> List[str]:
        """Generic object selection"""
        print("\n" + "="*80)
        print(f" STEP: SELECT {object_type}")
        print("="*80)

        if not objects:
            print(f"\n  No {object_type.lower()} found")
            return []

        print(f"\n  Found {len(objects)} {object_type.lower()}:\n")

        for i, obj in enumerate(objects, 1):
            status_icon = "[OK]" if obj.status == 'VALID' else "[!]"
            print(f"     {i:2d}. {obj.name:40s} {status_icon}")

        print("\n  Options:")
        print("    - Enter 'all' for all")
        print("    - Enter numbers (e.g., 1,3,5)")
        print("    - Press Enter to skip")

        choice = input(f"\n  Select {object_type.lower()}: ").strip()

        if not choice:
            return []

        if choice.lower() == 'all':
            return [o.name for o in objects]

        selected = self._parse_selection(choice, len(objects))
        return [objects[i-1].name for i in selected if i <= len(objects)]

    def _parse_selection(self, choice: str, max_num: int) -> List[int]:
        """Parse user selection (numbers, ranges, etc.)"""
        if not choice:
            return []

        selected = set()

        for part in choice.split(','):
            part = part.strip()

            if '-' in part:
                # Range like "1-5"
                try:
                    start, end = part.split('-')
                    start = int(start.strip())
                    end = int(end.strip())
                    selected.update(range(start, end + 1))
                except:
                    pass
            else:
                # Single number
                try:
                    num = int(part)
                    if 1 <= num <= max_num:
                        selected.add(num)
                except:
                    pass

        return sorted(list(selected))

    def _show_selection_summary(self, selection: MigrationSelection):
        """Show summary of selections"""
        print("\n" + "="*80)
        print(" SELECTION SUMMARY")
        print("="*80)

        print(f"\n  Tables:")
        print(f"    Total selected: {len(selection.selected_tables)}")
        print(f"    With data: {len(selection.tables_with_data)}")
        print(f"    Schema only: {len(selection.tables_schema_only)}")

        print(f"\n  Code Objects:")
        print(f"    Packages: {len(selection.selected_packages)}")
        print(f"    Procedures: {len(selection.selected_procedures)}")
        print(f"    Functions: {len(selection.selected_functions)}")
        print(f"    Triggers: {len(selection.selected_triggers)}")

        if selection.selected_views:
            print(f"    Views: {len(selection.selected_views)}")
        if selection.selected_sequences:
            print(f"    Sequences: {len(selection.selected_sequences)}")

        print(f"\n  TOTAL OBJECTS TO MIGRATE: {selection.total_objects()}")

        print("\n" + "="*80)

        # Confirm
        confirm = input("\n  Proceed with migration? [Y/n]: ").strip().lower()

        if confirm and confirm != 'y':
            print("\n  Migration cancelled by user")
            exit(0)

        print("\n  Starting migration...")
