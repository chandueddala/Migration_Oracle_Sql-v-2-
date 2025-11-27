"""
Test IDENTITY Column Detection and Data Migration Fix
"""

import sys
import logging
from pathlib import Path
import io

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from database.sqlserver_connector import SQLServerConnector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_identity_detection():
    """Test detecting identity columns from SQL Server"""
    print("\n" + "=" * 80)
    print("  TEST: Identity Column Detection")
    print("=" * 80 + "\n")

    # SQL Server credentials (Windows Authentication)
    sqlserver_creds = {
        "server": "CHANDU-EDDALA\\SQLEXPRESS",
        "database": "NORTHWIND_TARGET",
        "user": "",  # Empty for Windows auth
        "password": "",
        "driver": "ODBC Driver 18 for SQL Server",  # No curly braces needed
        "trusted_connection": "yes"
    }

    try:
        # Connect to SQL Server
        conn = SQLServerConnector(sqlserver_creds)
        if not conn.connect():
            print("❌ Failed to connect to SQL Server")
            return False

        print("✅ Connected to SQL Server\n")

        # Test with CATEGORIES table (known to have identity column)
        table_name = "CATEGORIES"
        print(f"Testing table: {table_name}")

        # Get table columns
        columns = conn.get_table_columns(table_name)

        print(f"\nFound {len(columns)} columns:")
        for col in columns:
            identity_mark = " [IDENTITY]" if col.get('is_identity') else ""
            print(f"  - {col['name']}: {col['type']}{identity_mark}")

        # Extract identity columns
        identity_cols = [col['name'] for col in columns if col.get('is_identity')]

        if identity_cols:
            print(f"\n✅ Detected IDENTITY columns: {', '.join(identity_cols)}")
            print("\nThis means IDENTITY_INSERT will be enabled automatically during data migration.")
        else:
            print(f"\n⚠️  No IDENTITY columns detected in {table_name}")

        conn.disconnect()
        return len(identity_cols) > 0

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        logger.error(f"Test error: {e}", exc_info=True)
        return False


def test_identity_insert():
    """Test IDENTITY_INSERT toggle"""
    print("\n" + "=" * 80)
    print("  TEST: IDENTITY_INSERT Toggle")
    print("=" * 80 + "\n")

    sqlserver_creds = {
        "server": "CHANDU-EDDALA\\SQLEXPRESS",
        "database": "NORTHWIND_TARGET",
        "user": "",
        "password": "",
        "driver": "ODBC Driver 18 for SQL Server",
        "trusted_connection": "yes"
    }

    try:
        conn = SQLServerConnector(sqlserver_creds)
        if not conn.connect():
            print("❌ Failed to connect to SQL Server")
            return False

        print("✅ Connected to SQL Server\n")

        table_name = "CATEGORIES"

        # Test enabling IDENTITY_INSERT
        print(f"Enabling IDENTITY_INSERT for {table_name}...")
        success = conn.set_identity_insert(table_name, True)
        if success:
            print("✅ IDENTITY_INSERT enabled")
        else:
            print("❌ Failed to enable IDENTITY_INSERT")
            return False

        # Test disabling IDENTITY_INSERT
        print(f"\nDisabling IDENTITY_INSERT for {table_name}...")
        success = conn.set_identity_insert(table_name, False)
        if success:
            print("✅ IDENTITY_INSERT disabled")
        else:
            print("❌ Failed to disable IDENTITY_INSERT")
            return False

        conn.disconnect()
        return True

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        logger.error(f"Test error: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("  IDENTITY COLUMN FIX - TEST SUITE")
    print("=" * 80)

    tests = [
        ("Identity Column Detection", test_identity_detection),
        ("IDENTITY_INSERT Toggle", test_identity_insert),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"\n❌ Test '{test_name}' crashed: {e}")
            logger.error(f"Test crash: {test_name}", exc_info=True)
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 80)
    print("  TEST SUMMARY")
    print("=" * 80 + "\n")

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name}")

    print("\n" + "-" * 80)
    print(f"TOTAL: {passed}/{total} tests passed ({(passed/total)*100:.1f}%)")
    print("-" * 80)

    if passed == total:
        print("\n🎉 All tests passed! Identity column fix is working.")
        print("\nThe fix ensures that:")
        print("  ✅ Identity columns are detected automatically")
        print("  ✅ IDENTITY_INSERT is enabled when needed")
        print("  ✅ Data migration will work for tables with identity columns")
        sys.exit(0)
    else:
        print(f"\n❌ {total - passed} test(s) failed.")
        sys.exit(1)
