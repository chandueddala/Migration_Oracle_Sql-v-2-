"""
Migrate ALL - Fully Automatic Migration Entry Point

This script automatically migrates ALL database objects without user selection:
- All Tables (structure + data)
- All Procedures
- All Functions
- All Triggers
- All Packages (automatically decomposed)

Usage:
    python migrate_all.py                    # Migrate everything
    python migrate_all.py --no-data          # Migrate structures only, no data
    python migrate_all.py --tables-only      # Migrate only tables
    python migrate_all.py --code-only        # Migrate only code objects (no tables)
"""

import sys
import argparse
from utils.automatic_migration import run_automatic_migration


def main():
    """Main entry point for automatic migration"""
    parser = argparse.ArgumentParser(
        description="Automatic Migration - Process ALL Oracle database objects",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python migrate_all.py                    # Migrate everything (tables + data + code)
  python migrate_all.py --no-data          # Migrate structures only (no table data)
  python migrate_all.py --tables-only      # Only migrate tables
  python migrate_all.py --code-only        # Only migrate code objects (procedures, functions, etc.)
  python migrate_all.py --no-packages      # Exclude packages
  python migrate_all.py --no-triggers      # Exclude triggers

The system will:
  1. Automatically discover ALL objects in Oracle
  2. Migrate each object type automatically
  3. Packages are automatically decomposed into individual procedures/functions
  4. Generate comprehensive migration report
        """
    )

    # Migration options
    parser.add_argument(
        "--no-data",
        action="store_true",
        help="Migrate table structures only, skip data migration"
    )

    parser.add_argument(
        "--tables-only",
        action="store_true",
        help="Migrate only tables (skip code objects)"
    )

    parser.add_argument(
        "--code-only",
        action="store_true",
        help="Migrate only code objects (skip tables)"
    )

    parser.add_argument(
        "--no-procedures",
        action="store_true",
        help="Skip procedures"
    )

    parser.add_argument(
        "--no-functions",
        action="store_true",
        help="Skip functions"
    )

    parser.add_argument(
        "--no-triggers",
        action="store_true",
        help="Skip triggers"
    )

    parser.add_argument(
        "--no-packages",
        action="store_true",
        help="Skip packages"
    )

    parser.add_argument(
        "--include-views",
        action="store_true",
        help="Include views (may need manual review)"
    )

    parser.add_argument(
        "--include-sequences",
        action="store_true",
        help="Include sequences (may need manual review)"
    )

    args = parser.parse_args()

    # Determine what to migrate based on arguments
    if args.tables_only:
        migrate_tables = True
        migrate_procedures = False
        migrate_functions = False
        migrate_triggers = False
        migrate_packages = False
    elif args.code_only:
        migrate_tables = False
        migrate_procedures = True
        migrate_functions = True
        migrate_triggers = True
        migrate_packages = True
    else:
        # Default: Migrate everything
        migrate_tables = True
        migrate_procedures = not args.no_procedures
        migrate_functions = not args.no_functions
        migrate_triggers = not args.no_triggers
        migrate_packages = not args.no_packages

    migrate_data = migrate_tables and not args.no_data
    migrate_views = args.include_views
    migrate_sequences = args.include_sequences

    # Run automatic migration
    print("\n" + "="*70)
    print("🤖 AUTOMATIC MIGRATION - ALL OBJECTS")
    print("="*70)
    print("\nStarting fully automatic migration...")
    print("All database objects will be processed without manual selection.\n")

    try:
        stats = run_automatic_migration(
            migrate_tables=migrate_tables,
            migrate_data=migrate_data,
            migrate_procedures=migrate_procedures,
            migrate_functions=migrate_functions,
            migrate_triggers=migrate_triggers,
            migrate_packages=migrate_packages,
            migrate_views=migrate_views,
            migrate_sequences=migrate_sequences
        )

        # Check if migration was successful
        total_failed = sum([
            stats.get("tables", {}).get("failed", 0),
            stats.get("procedures", {}).get("failed", 0),
            stats.get("functions", {}).get("failed", 0),
            stats.get("triggers", {}).get("failed", 0),
            stats.get("packages", {}).get("failed", 0)
        ])

        if total_failed == 0:
            print("\n✅ All objects migrated successfully!")
            return 0
        else:
            print(f"\n⚠️  Migration completed with {total_failed} failed objects")
            return 1

    except KeyboardInterrupt:
        print("\n\n⚠️  Migration interrupted by user")
        return 130
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
