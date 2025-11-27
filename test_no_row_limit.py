"""
Test Script: Verify No Row Limit in Data Migration

This script tests that data migration processes ALL rows, not just 100.
"""

import sys
sys.path.insert(0, 'c:/Users/Chandu Eddala/Desktop/oracle-sqlserver-migration-v2-FINAL')

from database.oracle_connector import OracleConnector
from database.sqlserver_connector import SQLServerConnector
from agents.credential_agent import CredentialAgent
from utils.migration_engine import migrate_table_data

def test_no_row_limit():
    """Test that migration handles tables with > 100 rows correctly"""
    
    print("=" * 70)
    print("TESTING: No Row Limit in Data Migration")
    print("=" * 70)
    
    # Get credentials
    cred_agent = CredentialAgent()
    oracle_creds = cred_agent.get_oracle_credentials()
    sqlserver_creds = cred_agent.get_sqlserver_credentials()
    
    # Connect to Oracle to find a table with > 100 rows
    print("\n1. Finding a table with > 100 rows...")
    oracle_conn = OracleConnector(oracle_creds)
    if not oracle_conn.connect():
        print("❌ Failed to connect to Oracle")
        return False
    
    # Get list of tables
    tables = oracle_conn.list_tables()
    test_table = None
    test_table_count = 0
    
    for table in tables:
        try:
            count = oracle_conn.get_table_row_count(table)
            print(f"   - {table}: {count:,} rows")
            
            if count > 100 and test_table is None:
                test_table = table
                test_table_count = count
                print(f"   ✅ Selected {table} ({count:,} rows) for testing")
        except:
            pass
    
    oracle_conn.disconnect()
    
    if not test_table:
        print("\n⚠️  No tables with > 100 rows found. Test cannot proceed.")
        print("   Recommendation: Seed more data into Oracle database")
        return False
    
    print(f"\n2. Testing migration of {test_table} ({test_table_count:,} rows)...")
    print(f"   Expected: All {test_table_count:,} rows should migrate")
    print(f"   Previous Bug: Only 100 rows would migrate")
    
    # Perform migration
    result = migrate_table_data(oracle_creds, sqlserver_creds, test_table)
    
    print(f"\n3. Migration Result:")
    print(f"   Status: {result['status']}")
    print(f"   Rows Migrated: {result.get('rows_migrated', 0):,}")
    
    # Verify results
    if result['status'] == 'success':
        if result['rows_migrated'] == test_table_count:
            print(f"\n✅ TEST PASSED!")
            print(f"   All {test_table_count:,} rows were migrated successfully")
            print(f"   No row limit detected - migration handles ANY number of rows")
            return True
        elif result['rows_migrated'] == 100:
            print(f"\n❌ TEST FAILED!")
            print(f"   Only 100 rows migrated (old bug still present)")
            print(f"   Expected: {test_table_count:,} rows")
            return False
        else:
            print(f"\n⚠️  PARTIAL SUCCESS")
            print(f"   Migrated {result['rows_migrated']:,} of {test_table_count:,} rows")
            print(f"   Not necessarily a row limit, but unexpected count")
            return False
    else:
        print(f"\n❌ TEST FAILED!")
        print(f"   Migration failed: {result.get('message', 'Unknown error')}")
        return False


if __name__ == "__main__":
    try:
        success = test_no_row_limit()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
