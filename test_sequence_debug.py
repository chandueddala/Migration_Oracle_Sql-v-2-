"""
Test Script: Debug Sequence Detection

This script tests sequence detection directly to find why sequences show as 0
"""

import sys
sys.path.insert(0, 'c:/Users/Chandu Eddala/Desktop/oracle-sqlserver-migration-v2-FINAL')

from database.oracle_connector import OracleConnector
from agents.credential_agent import CredentialAgent
from utils.comprehensive_discovery import ComprehensiveDiscovery

def test_sequence_detection():
    """Test sequence detection step by step"""
    
    print("=" * 70)
    print("DEBUGGING: Sequence Detection")
    print("=" * 70)
    
    # Get credentials
    cred_agent = CredentialAgent()
    oracle_creds, _ = cred_agent.run()  # Fixed: use run() method
    
    if not oracle_creds:
        print("Failed to get Oracle credentials")
        return False
    
    # Connect to Oracle
    print("\n1. Connecting to Oracle database...")
    oracle_conn = OracleConnector(oracle_creds)
    if not oracle_conn.connect():
        print("❌ Failed to connect to Oracle")
        return False
    
    print("✅ Connected successfully")
    
    # Test 1: Direct query for all sequences (no filter)
    print("\n2. Test 1: Query ALL sequences (no filter)...")
    try:
        query1 = "SELECT sequence_name FROM user_sequences ORDER BY sequence_name"
        results1 = oracle_conn.execute_query(query1)
        print(f"   Found {len(results1)} sequences (total)")
        if results1:
            for row in results1:
                print(f"     - {row[0]}")
        else:
            print("   ⚠️  No sequences found in USER_SEQUENCES")
    except Exception as e:
        print(f"   ❌ Query failed: {e}")
    
    # Test 2: Check if sequences are in ALL_SEQUENCES instead
    print("\n3. Test 2: Query ALL_SEQUENCES (other schemas)...")
    try:
        query2 = """
        SELECT owner, sequence_name 
        FROM all_sequences 
        WHERE owner = USER
        ORDER BY sequence_name
        """
        results2 = oracle_conn.execute_query(query2)
        print(f"   Found {len(results2)} sequences in ALL_SEQUENCES")
        if results2:
            for row in results2:
                print(f"     - {row[0]}.{row[1]}")
    except Exception as e:
        print(f"   ❌ Query failed: {e}")
    
    # Test 3: Test list_sequences() method
    print("\n4. Test 3: Using list_sequences() method...")
    if hasattr(oracle_conn, 'list_sequences'):
        try:
            sequences = oracle_conn.list_sequences()
            print(f"   ✅ list_sequences() returned {len(sequences)} sequences")
            if sequences:
                for seq in sequences:
                    print(f"     - {seq}")
        except Exception as e:
            print(f"   ❌ list_sequences() failed: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("   ❌ list_sequences() method does NOT exist!")
    
    # Test 4: Test ComprehensiveDiscovery
    print("\n5. Test 4: Using ComprehensiveDiscovery...")
    try:
        discovery = ComprehensiveDiscovery(oracle_conn)
        sequences_objs = discovery._discover_sequences()
        print(f"   _discover_sequences() returned {len(sequences_objs)} sequences")
        if sequences_objs:
            for seq_obj in sequences_objs:
                print(f"     - {seq_obj.name} (current: {seq_obj.metadata.get('current_value')})")
    except Exception as e:
        print(f"   ❌ _discover_sequences() failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 5: Check for sequences used in procedures (indirect detection)
    print("\n6. Test 5: Search for sequence usage in code...")
    try:
        query3 = """
        SELECT DISTINCT name, type, text
        FROM user_source
        WHERE UPPER(text) LIKE '%NEXTVAL%' 
           OR UPPER(text) LIKE '%CURRVAL%'
        ORDER BY name
        """
        results3 = oracle_conn.execute_query(query3[:200])  # Limit for safety
        if results3:
            print(f"   Found {len(results3)} code objects using sequences")
            for row in results3[:5]:
                print(f"     - {row[0]} ({row[1]})")
        else:
            print("   No sequence usage found in code")
    except Exception as e:
        print(f"   Note: Could not search code: {e}")
    
    oracle_conn.disconnect()
    
    print("\n" + "=" * 70)
    print("DEBUGGING COMPLETE")
    print("=" * 70)
    
    return True


if __name__ == "__main__":
    try:
        test_sequence_detection()
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
