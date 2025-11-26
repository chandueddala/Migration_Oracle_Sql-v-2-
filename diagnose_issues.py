"""
Diagnostic script to test Web Access and Memory Share functionality
"""

import sys
import traceback
from pathlib import Path

print("=" * 60)
print("DIAGNOSTIC TEST: Web Access & Memory Share")
print("=" * 60)

# TEST 1: Check Streamlit availability
print("\n[TEST 1] Checking Streamlit (Web Access)...")
try:
    import streamlit as st
    print(f"✅ Streamlit is installed: version {st.__version__}")
    streamlit_ok = True
except ImportError as e:
    print(f"❌ Streamlit not available: {e}")
    streamlit_ok = False
except Exception as e:
    print(f"❌ Error checking Streamlit: {e}")
    streamlit_ok = False

# TEST 2: Check if web app file exists and is readable
print("\n[TEST 2] Checking web application file...")
try:
    app_file = Path("app.py")
    if app_file.exists():
        print(f"✅ Web app file found: {app_file.absolute()}")
        print(f"   Size: {app_file.stat().st_size} bytes")
        # Try to read first few lines
        with open(app_file, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()
            print(f"   First line: {first_line[:50]}...")
        app_file_ok = True
    else:
        print(f"❌ Web app file not found: {app_file.absolute()}")
        app_file_ok = False
except Exception as e:
    print(f"❌ Error checking web app file: {e}")
    traceback.print_exc()
    app_file_ok = False

# TEST 3: Check shared memory module
print("\n[TEST 3] Checking Shared Memory module...")
try:
    from agents.memory_agent import SharedMemory, get_shared_memory
    print("✅ SharedMemory module imported successfully")
    memory_module_ok = True
except ImportError as e:
    print(f"❌ Cannot import SharedMemory: {e}")
    traceback.print_exc()
    memory_module_ok = False
except Exception as e:
    print(f"❌ Error importing SharedMemory: {e}")
    traceback.print_exc()
    memory_module_ok = False

# TEST 4: Try to create a shared memory instance
print("\n[TEST 4] Creating Shared Memory instance...")
if memory_module_ok:
    try:
        memory = get_shared_memory()
        print(f"✅ Shared memory instance created")
        
        # Get statistics
        stats = memory.get_statistics()
        print(f"   Schemas tracked: {stats['schemas_tracked']}")
        print(f"   Tables with identity: {stats['tables_with_identity']}")
        print(f"   Error solutions: {stats['error_solutions']}")
        print(f"   Successful patterns: {stats['successful_patterns']}")
        
        # Check persistence file
        persist_file = memory.persistence_file
        print(f"   Persistence file: {persist_file}")
        if persist_file.exists():
            print(f"   File size: {persist_file.stat().st_size} bytes")
        else:
            print(f"   ⚠️ Persistence file doesn't exist yet (will be created on save)")
        
        memory_instance_ok = True
    except Exception as e:
        print(f"❌ Error creating shared memory instance: {e}")
        traceback.print_exc()
        memory_instance_ok = False
else:
    memory_instance_ok = False
    print("⏭️ Skipped (module not available)")

# TEST 5: Test memory operations
print("\n[TEST 5] Testing memory operations...")
if memory_instance_ok:
    try:
        # Test storing a schema
        memory.store_schema("test_db", "test_schema", exists=True)
        print("✅ Successfully stored test schema")
        
        # Test retrieving a schema
        schema_info = memory.get_schema("test_db", "test_schema")
        if schema_info:
            print(f"✅ Successfully retrieved schema: {schema_info['schema']}")
        else:
            print("❌ Failed to retrieve stored schema")
        
        # Test saving to disk
        memory.save()
        
        # Verify file was created/updated
        if memory.persistence_file.exists():
            print(f"✅ Memory persisted to disk: {memory.persistence_file}")
            memory_ops_ok = True
        else:
            print(f"❌ Persistence file not created")
            memory_ops_ok = False
            
    except Exception as e:
        print(f"❌ Error during memory operations: {e}")
        traceback.print_exc()
        memory_ops_ok = False
else:
    memory_ops_ok = False
    print("⏭️ Skipped (instance not available)")

# TEST 6: Check database connectors
print("\n[TEST 6] Checking database connectors...")
try:
    from database.oracle_connector import OracleConnector
    from database.sqlserver_connector import SQLServerConnector
    print("✅ Database connector modules available")
    connectors_ok = True
except ImportError as e:
    print(f"❌ Database connectors not available: {e}")
    connectors_ok = False
except Exception as e:
    print(f"❌ Error checking connectors: {e}")
    connectors_ok = False

# SUMMARY
print("\n" + "=" * 60)
print("DIAGNOSTIC SUMMARY")
print("=" * 60)

results = {
    "Streamlit (Web Access)": streamlit_ok,
    "Web App File": app_file_ok,
    "Shared Memory Module": memory_module_ok,
    "Shared Memory Instance": memory_instance_ok,
    "Memory Operations": memory_ops_ok,
    "Database Connectors": connectors_ok
}

for test_name, result in results.items():
    status = "✅ PASS" if result else "❌ FAIL"
    print(f"{status:10} - {test_name}")

all_passed = all(results.values())
print("\n" + "=" * 60)
if all_passed:
    print("✅ ALL TESTS PASSED - System is functional")
else:
    print("❌ SOME TESTS FAILED - See details above")
print("=" * 60)

sys.exit(0 if all_passed else 1)
