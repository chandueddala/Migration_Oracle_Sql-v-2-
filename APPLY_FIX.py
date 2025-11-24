"""
Automatic fix for migration_engine.py
This script fixes the fetch_table_data -> get_table_data issue
"""
import os
import sys
import time

def fix_migration_engine():
    """Fix the method name in migration_engine.py"""
    file_path = os.path.join("utils", "migration_engine.py")

    if not os.path.exists(file_path):
        print(f"ERROR: File not found: {file_path}")
        return False

    print(f"Reading {file_path}...")

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"ERROR reading file: {e}")
        print("\nTIP: Close any editors that have migration_engine.py open")
        return False

    # Check if fix is needed
    if 'oracle_conn.fetch_table_data(table_name)' not in content:
        print("Fix already applied! File contains get_table_data")
        return True

    print("Applying fix: fetch_table_data -> get_table_data")

    # Apply fix
    content = content.replace(
        'oracle_conn.fetch_table_data(table_name)',
        'oracle_conn.get_table_data(table_name)'
    )

    # Write back
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print("SUCCESS! File fixed successfully")
        return True
    except PermissionError:
        print("\nERROR: Permission denied - file is locked")
        print("\nPLEASE:")
        print("1. Close VSCode or any editor with migration_engine.py open")
        print("2. Close any running Python migration processes")
        print("3. Run this script again")
        return False
    except Exception as e:
        print(f"ERROR writing file: {e}")
        return False

def verify_fix():
    """Verify the fix was applied correctly"""
    file_path = os.path.join("utils", "migration_engine.py")

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        if 'oracle_conn.get_table_data(table_name)' in content:
            print("\nVERIFIED: Fix is correctly applied")
            return True
        else:
            print("\nWARNING: Fix may not be applied correctly")
            return False
    except Exception as e:
        print(f"ERROR verifying: {e}")
        return False

if __name__ == "__main__":
    print("=" * 70)
    print("MIGRATION ENGINE FIX")
    print("=" * 70)
    print("\nThis will fix: fetch_table_data -> get_table_data")
    print()

    success = fix_migration_engine()

    if success:
        print()
        verify_fix()
        print("\n" + "=" * 70)
        print("You can now run: python main.py")
        print("=" * 70)
    else:
        print("\n" + "=" * 70)
        print("FIX FAILED - See instructions above")
        print("=" * 70)
        sys.exit(1)
