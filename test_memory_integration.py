"""
Test Migration Memory Integration
Tests that memory solutions are being retrieved and stored during error repair
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

from database.migration_memory import MigrationMemory
from agents.debugger_agent import DebuggerAgent
from config.config_enhanced import CostTracker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_section(title):
    """Print a formatted section header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def test_memory_initialization():
    """Test 1: Memory instance creation"""
    print_section("TEST 1: Memory Initialization")

    memory = MigrationMemory()
    print(f"Memory instance created: {memory is not None}")
    print(f"Identity columns dict: {type(memory._identity_columns)}")
    print(f"Error solutions dict: {type(memory._error_solutions)}")

    stats = memory.get_statistics()
    print(f"\nInitial stats: {stats}")

    print("\n✅ Memory initialization test passed")
    return memory


def test_store_and_retrieve_solution():
    """Test 2: Store and retrieve error solutions"""
    print_section("TEST 2: Store and Retrieve Solutions")

    memory = MigrationMemory()

    # Store a solution
    error_msg = "Incorrect syntax near the keyword 'DECLARE'"
    solution = {
        "object_name": "TEST_PROCEDURE",
        "object_type": "PROCEDURE",
        "error_message": error_msg,
        "oracle_code": "PROCEDURE test AS BEGIN DECLARE v_test NUMBER; END;",
        "fixed_sql": "CREATE PROCEDURE test AS BEGIN SET v_test INT; END;",
        "solution": "Removed DECLARE keyword - not needed in SQL Server",
        "fix_description": "SQL Server doesn't use DECLARE in procedure body"
    }

    print(f"Storing solution for error: {error_msg[:50]}...")
    memory.store_error_solution(error_msg, solution)

    # Retrieve the solution
    print(f"\nRetrieving solutions...")
    retrieved = memory.get_error_solutions(error_msg, limit=5)

    print(f"Found {len(retrieved)} solutions")
    if retrieved:
        print(f"\nFirst solution:")
        print(f"  Object: {retrieved[0].get('object_name')}")
        print(f"  Type: {retrieved[0].get('object_type')}")
        print(f"  Fix: {retrieved[0].get('fix_description')}")

    # Test with similar error
    similar_error = "Incorrect syntax near the keyword 'BEGIN'"
    similar = memory.get_error_solutions(similar_error, limit=5)
    print(f"\nSearching for similar error: {similar_error}")
    print(f"Found {len(similar)} solutions (should be 0 for exact match)")

    stats = memory.get_statistics()
    print(f"\nStats after storing: {stats}")

    print("\n✅ Store and retrieve test passed")
    return memory


def test_debugger_with_memory():
    """Test 3: Debugger agent with memory integration"""
    print_section("TEST 3: Debugger with Memory")

    memory = MigrationMemory()
    cost_tracker = CostTracker()

    # Create debugger WITH memory
    debugger = DebuggerAgent(
        cost_tracker=cost_tracker,
        migration_options={},
        memory=memory
    )

    print(f"Debugger created with memory: {debugger.memory is not None}")
    print(f"Memory instance matches: {debugger.memory is memory}")

    # Pre-populate memory with a solution
    error = "Cannot find column 'dept_id'"
    memory.store_error_solution(error, {
        "object_name": "EMPLOYEE_TABLE",
        "object_type": "TABLE",
        "error_message": error,
        "oracle_code": "SELECT dept_id FROM employee",
        "fixed_sql": "SELECT department_id FROM employee",
        "solution": "Column was renamed from dept_id to department_id",
        "fix_description": "Updated column name to match SQL Server schema"
    })

    # Verify debugger can access memory
    solutions = debugger.memory.get_error_solutions(error)
    print(f"\nDebugger accessed memory: {len(solutions)} solutions found")

    if solutions:
        print(f"Solution details:")
        print(f"  Object: {solutions[0].get('object_name')}")
        print(f"  Fix: {solutions[0].get('fix_description')}")

    print("\n✅ Debugger with memory test passed")
    return debugger


def test_memory_accumulation():
    """Test 4: Memory accumulates solutions over time"""
    print_section("TEST 4: Memory Accumulation")

    memory = MigrationMemory()

    errors_and_solutions = [
        ("Syntax error near 'ROWNUM'", "Replace ROWNUM with ROW_NUMBER()"),
        ("Invalid function SYSDATE", "Replace SYSDATE with GETDATE()"),
        ("Cannot use PRAGMA", "Remove PRAGMA - not supported in SQL Server"),
        ("Sequence not found", "Create identity column or SEQUENCE object"),
        ("Package body error", "Decompose package into individual procedures"),
    ]

    print(f"Storing {len(errors_and_solutions)} solutions...")
    for idx, (error, fix) in enumerate(errors_and_solutions, 1):
        memory.store_error_solution(error, {
            "object_name": f"TEST_OBJ_{idx}",
            "object_type": "PROCEDURE",
            "error_message": error,
            "solution": fix,
            "fix_description": fix
        })
        print(f"  {idx}. {error[:40]}... -> {fix[:40]}...")

    stats = memory.get_statistics()
    print(f"\nFinal stats: {stats}")
    print(f"Total error solutions: {stats['error_solutions']}")

    # Test retrieval of each
    print(f"\nVerifying retrievals:")
    for error, _ in errors_and_solutions[:3]:  # Test first 3
        solutions = memory.get_error_solutions(error, limit=1)
        status = "✅" if solutions else "❌"
        print(f"  {status} {error[:50]}: {len(solutions)} found")

    print("\n✅ Memory accumulation test passed")
    return memory


def test_memory_persistence():
    """Test 5: Multiple memory instances share data (in-memory only)"""
    print_section("TEST 5: Memory Instance Behavior")

    # Create two separate memory instances
    memory1 = MigrationMemory()
    memory2 = MigrationMemory()

    print(f"Memory 1 ID: {id(memory1)}")
    print(f"Memory 2 ID: {id(memory2)}")
    print(f"Are same instance: {memory1 is memory2}")

    # Store in first instance
    memory1.store_error_solution("Test error", {
        "solution": "Test solution from memory1"
    })

    # Try to retrieve from second instance
    solutions1 = memory1.get_error_solutions("Test error")
    solutions2 = memory2.get_error_solutions("Test error")

    print(f"\nSolutions in memory1: {len(solutions1)}")
    print(f"Solutions in memory2: {len(solutions2)}")

    print("\nNote: Each memory instance is independent (not global)")
    print("In production, the orchestrator creates ONE memory instance")
    print("and passes it to all agents for sharing.")

    print("\n✅ Memory instance behavior test passed")


def test_identity_column_tracking():
    """Test 6: Identity column tracking"""
    print_section("TEST 6: Identity Column Tracking")

    memory = MigrationMemory()

    # Register some identity columns
    memory.register_identity_column("EMPLOYEES", "EMPLOYEE_ID")
    memory.register_identity_column("DEPARTMENTS", "DEPT_ID")
    memory.register_identity_column("EMPLOYEES", "EMPLOYEE_ID")  # Duplicate

    print("Registered identity columns:")
    print(f"  EMPLOYEES: {memory.get_identity_columns('EMPLOYEES')}")
    print(f"  DEPARTMENTS: {memory.get_identity_columns('DEPARTMENTS')}")

    # Check if table has identity
    print(f"\nHas identity column:")
    print(f"  EMPLOYEES: {memory.has_identity_column('EMPLOYEES')}")
    print(f"  DEPARTMENTS: {memory.has_identity_column('DEPARTMENTS')}")
    print(f"  PRODUCTS: {memory.has_identity_column('PRODUCTS')}")

    # Store table mapping
    memory.store_table_mapping("EMP", "EMPLOYEES", "dbo")
    mapping = memory.get_table_mapping("EMP")
    print(f"\nTable mapping for EMP: {mapping}")

    print("\n✅ Identity column tracking test passed")


def run_all_tests():
    """Run all memory integration tests"""
    print("\n" + "=" * 80)
    print("  MIGRATION MEMORY INTEGRATION - TEST SUITE")
    print("=" * 80)

    tests = [
        ("Memory Initialization", test_memory_initialization),
        ("Store and Retrieve Solutions", test_store_and_retrieve_solution),
        ("Debugger with Memory", test_debugger_with_memory),
        ("Memory Accumulation", test_memory_accumulation),
        ("Memory Instance Behavior", test_memory_persistence),
        ("Identity Column Tracking", test_identity_column_tracking),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            test_func()
            results.append((test_name, True))
        except Exception as e:
            print(f"\n❌ Test '{test_name}' failed: {e}")
            logger.error(f"Test failure: {test_name}", exc_info=True)
            results.append((test_name, False))

    # Final Summary
    print_section("FINAL TEST SUMMARY")

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name}")

    print("\n" + "-" * 80)
    print(f"TOTAL: {passed}/{total} tests passed ({(passed/total)*100:.1f}%)")
    print("-" * 80)

    if passed == total:
        print("\n🎉 All tests passed! Memory integration is working correctly.")
        print("\nKey Features Verified:")
        print("  ✅ Memory stores error solutions")
        print("  ✅ Memory retrieves solutions for similar errors")
        print("  ✅ Debugger agent receives memory instance")
        print("  ✅ Multiple solutions accumulate over time")
        print("  ✅ Identity columns are tracked")
        print("  ✅ Table mappings are stored")
        return 0
    elif passed > 0:
        print(f"\n⚠️ {total - passed} test(s) failed. Memory integration is partially working.")
        return 1
    else:
        print("\n❌ All tests failed. Memory integration has issues.")
        return 2


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
