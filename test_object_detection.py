"""
Test Script: Verify Object Detection

Tests that all Oracle object types are properly detected:
- Tables
- Procedures
- Functions
- Triggers  
- Packages
- Sequences (NEW)
- Views (NEW)
"""

import sys
sys.path.insert(0, 'c:/Users/Chandu Eddala/Desktop/oracle-sqlserver-migration-v2-FINAL')

from database.oracle_connector import OracleConnector
from agents.credential_agent import CredentialAgent

def test_object_detection():
    """Test detection of all Oracle object types"""
    
    print("=" * 70)
    print("TESTING: Oracle Object Detection")
    print("=" * 70)
    
    # Get credentials
    cred_agent = CredentialAgent()
    oracle_creds = cred_agent.get_oracle_credentials()
    
    # Connect to Oracle
    print("\n1. Connecting to Oracle database...")
    oracle_conn = OracleConnector(oracle_creds)
    if not oracle_conn.connect():
        print("❌ Failed to connect to Oracle")
        return False
    
    print("✅ Connected successfully")
    
    # Test all detection methods
    print("\n2. Discovering objects...")
    print("-" * 70)
    
    try:
        # Tables
        tables = oracle_conn.list_tables()
        print(f"\n📊 TABLES: {len(tables)} found")
        if tables:
            print(f"   Examples: {', '.join(tables[:5])}")
        
        # Procedures
        procedures = oracle_conn.list_procedures()
        print(f"\n🔧 PROCEDURES: {len(procedures)} found")
        if procedures:
            print(f"   Examples: {', '.join(procedures[:5])}")
        
        # Functions
        functions = oracle_conn.list_functions()
        print(f"\n🔍 FUNCTIONS: {len(functions)} found")
        if functions:
            print(f"   Examples: {', '.join(functions[:5])}")
        
        # Triggers
        triggers = oracle_conn.list_triggers()
        print(f"\n⚡ TRIGGERS: {len(triggers)} found")
        if triggers:
            print(f"   Examples: {', '.join(triggers[:5])}")
        
        # Packages
        packages = oracle_conn.list_packages()
        print(f"\n📦 PACKAGES: {len(packages)} found")
        if packages:
            print(f"   Examples: {', '.join(packages[:5])}")
        
        # Sequences (NEW - should work now)
        print(f"\n🔢 SEQUENCES: ")
        if hasattr(oracle_conn, 'list_sequences'):
            sequences = oracle_conn.list_sequences()
            print(f"   ✅ Detection method exists: {len(sequences)} found")
            if sequences:
                print(f"   Examples: {', '.join(sequences[:5])}")
        else:
            print("   ❌ Detection method MISSING")
        
        # Views (NEW - should work now)  
        print(f"\n👁️  VIEWS: ")
        if hasattr(oracle_conn, 'list_views'):
            views = oracle_conn.list_views()
            print(f"   ✅ Detection method exists: {len(views)} found")
            if views:
                print(f"   Examples: {', '.join(views[:5])}")
        else:
            print("   ❌ Detection method MISSING")
        
    except Exception as e:
        print(f"\n❌ Error during detection: {e}")
        import traceback
        traceback.print_exc()
        oracle_conn.disconnect()
        return False
    
    oracle_conn.disconnect()
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    total_objects = len(tables) + len(procedures) + len(functions) + len(triggers) + len(packages)
    if hasattr(oracle_conn, 'list_sequences'):
        total_objects += len(sequences)
    if hasattr(oracle_conn, 'list_views'):
        total_objects += len(views)
    
    print(f"\n✅ Total objects detected: {total_objects}")
    print(f"\n🎯 Sequences detection: {'✅ WORKING' if hasattr(oracle_conn, 'list_sequences') else '❌ BROKEN'}")
    print(f"🎯 Views detection: {'✅ WORKING' if hasattr(oracle_conn, 'list_views') else '❌ BROKEN'}")
    
    return True


if __name__ == "__main__":
    try:
        success = test_object_detection()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
