"""
Direct fix for migration_engine.py
Replaces fetch_table_data with get_table_data
"""

import os
import sys

def fix_migration_engine():
    """Fix the migration_engine.py file directly"""

    file_path = os.path.join("utils", "migration_engine.py")

    if not os.path.exists(file_path):
        print("ERROR: File not found: " + file_path)
        return False

    print("Fixing migration_engine.py...")

    try:
        # Read the file
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check if already fixed
        if 'oracle_conn.get_table_data(table_name)' in content:
            print("ALREADY FIXED! File uses get_table_data")
            return True

        # Check if needs fixing
        if 'oracle_conn.fetch_table_data(table_name)' not in content:
            print("WARNING: Could not find fetch_table_data in file")
            print("File might be in different format")
            return False

        # Apply fix
        content = content.replace(
            'oracle_conn.fetch_table_data(table_name)',
            'oracle_conn.get_table_data(table_name)'
        )

        # Write back
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        print("FIXED! Changed fetch_table_data to get_table_data")
        print("File: " + file_path)

        # Verify
        with open(file_path, 'r', encoding='utf-8') as f:
            verify_content = f.read()

        if 'oracle_conn.get_table_data(table_name)' in verify_content:
            print("VERIFIED! Fix applied successfully")
            return True
        else:
            print("ERROR: Verification failed!")
            return False

    except Exception as e:
        print("ERROR: " + str(e))
        return False


if __name__ == "__main__":
    print("\n" + "="*70)
    print("MIGRATION ENGINE FIX")
    print("="*70)
    print("\nThis will fix the 'fetch_table_data' error")
    print("Changing: fetch_table_data -> get_table_data")
    print("")

    success = fix_migration_engine()

    if success:
        print("\n" + "="*70)
        print("FIX COMPLETE!")
        print("="*70)
        print("\nYou can now run: python main.py")
        print("Data migration will work correctly!")
        sys.exit(0)
    else:
        print("\n" + "="*70)
        print("FIX FAILED")
        print("="*70)
        print("\nPlease manually edit utils/migration_engine.py")
        print("Line 123: Change fetch_table_data to get_table_data")
        sys.exit(1)
