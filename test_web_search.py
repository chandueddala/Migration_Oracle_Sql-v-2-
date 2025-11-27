"""
Test Web Search Functionality
Tests the Tavily web search integration for finding SQL Server error solutions
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

from external_tools.web_search import (
    WebSearchHelper,
    get_web_search_helper,
    search_for_error_solution,
    format_search_results_for_llm
)
from config.config_enhanced import TAVILY_API_KEY, ENABLE_WEB_SEARCH

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


def test_configuration():
    """Test 1: Verify web search configuration"""
    print_section("TEST 1: Configuration Verification")

    print(f"ENABLE_WEB_SEARCH: {ENABLE_WEB_SEARCH}")
    print(f"TAVILY_API_KEY set: {'Yes' if TAVILY_API_KEY else 'No'}")

    if TAVILY_API_KEY:
        # Mask the key for security
        masked_key = TAVILY_API_KEY[:10] + "..." + TAVILY_API_KEY[-5:]
        print(f"API Key (masked): {masked_key}")

    print("\n✅ Configuration check complete")
    return TAVILY_API_KEY is not None


def test_web_search_helper_initialization():
    """Test 2: Initialize WebSearchHelper"""
    print_section("TEST 2: WebSearchHelper Initialization")

    try:
        helper = WebSearchHelper()
        print(f"Helper enabled: {helper.enabled}")
        print(f"Tavily client initialized: {helper.tavily_client is not None}")

        if helper.enabled:
            print("\n✅ WebSearchHelper initialized successfully")
            return True
        else:
            print("\n❌ WebSearchHelper is disabled")
            if not TAVILY_API_KEY:
                print("   Reason: TAVILY_API_KEY not set")
            elif not ENABLE_WEB_SEARCH:
                print("   Reason: ENABLE_WEB_SEARCH is False")
            return False

    except Exception as e:
        print(f"\n❌ Failed to initialize WebSearchHelper: {e}")
        return False


def test_simple_search():
    """Test 3: Perform a simple search"""
    print_section("TEST 3: Simple Web Search")

    error_message = "Incorrect syntax near the keyword 'DECLARE'"
    object_type = "PROCEDURE"

    print(f"Searching for solution to error:")
    print(f"  Error: {error_message}")
    print(f"  Object Type: {object_type}")
    print()

    try:
        results = search_for_error_solution(error_message, object_type)

        if results:
            print(f"\n✅ Search successful!")
            print(f"   Total results: {results.get('total_results', 0)}")
            print(f"   Sources found: {len(results.get('sources', []))}")

            # Display top 3 sources
            if results.get('sources'):
                print("\n   Top 3 sources:")
                for idx, source in enumerate(results['sources'][:3], 1):
                    print(f"\n   {idx}. {source.get('title', 'Untitled')}")
                    print(f"      URL: {source.get('url', 'N/A')}")
                    print(f"      Score: {source.get('score', 0):.2f}")
                    content = source.get('content', '')[:150]
                    print(f"      Preview: {content}...")

            return True
        else:
            print("\n❌ Search returned no results")
            return False

    except Exception as e:
        print(f"\n❌ Search failed: {e}")
        logger.error(f"Search error: {e}", exc_info=True)
        return False


def test_complex_search():
    """Test 4: Test with complex SQL Server error"""
    print_section("TEST 4: Complex Error Search")

    error_message = """
    Msg 156, Level 15, State 1, Procedure usp_ProcessData, Line 45
    Incorrect syntax near the keyword 'END'.
    Cannot use the ROLLBACK statement within an INSERT-EXEC statement.
    """
    object_type = "PROCEDURE"
    context = "stored procedure with transaction handling"

    print(f"Searching for solution to complex error:")
    print(f"  Error: {error_message.strip()}")
    print(f"  Object Type: {object_type}")
    print(f"  Context: {context}")
    print()

    try:
        results = search_for_error_solution(error_message, object_type, context)

        if results:
            print(f"\n✅ Complex search successful!")
            print(f"   Total results: {results.get('total_results', 0)}")

            # Display formatted results for LLM
            formatted = format_search_results_for_llm(results)
            if formatted:
                print("\n   Sample of formatted output for LLM:")
                print(formatted[:500] + "..." if len(formatted) > 500 else formatted)

            return True
        else:
            print("\n❌ Complex search returned no results")
            return False

    except Exception as e:
        print(f"\n❌ Complex search failed: {e}")
        logger.error(f"Complex search error: {e}", exc_info=True)
        return False


def test_different_object_types():
    """Test 5: Test searches for different object types"""
    print_section("TEST 5: Different Object Types")

    test_cases = [
        ("Invalid column name 'dept_id'", "TABLE"),
        ("Cannot create trigger on view", "TRIGGER"),
        ("Scalar UDF cannot return table", "FUNCTION"),
        ("Subquery returned more than 1 value", "VIEW"),
    ]

    results_summary = []

    for error, obj_type in test_cases:
        print(f"\nTesting {obj_type}: {error[:50]}...")
        try:
            result = search_for_error_solution(error, obj_type)
            if result and result.get('sources'):
                print(f"  ✅ Found {len(result['sources'])} sources")
                results_summary.append((obj_type, True, len(result['sources'])))
            else:
                print(f"  ⚠️ No results found")
                results_summary.append((obj_type, False, 0))
        except Exception as e:
            print(f"  ❌ Error: {e}")
            results_summary.append((obj_type, False, 0))

    # Summary
    print("\n" + "-" * 60)
    print("Summary:")
    success_count = sum(1 for _, success, _ in results_summary if success)
    print(f"  Successful searches: {success_count}/{len(test_cases)}")

    for obj_type, success, count in results_summary:
        status = "✅" if success else "❌"
        print(f"  {status} {obj_type}: {count} sources")

    return success_count > 0


def test_global_instance():
    """Test 6: Test global helper instance"""
    print_section("TEST 6: Global Instance Management")

    print("Getting first helper instance...")
    helper1 = get_web_search_helper()

    print("Getting second helper instance...")
    helper2 = get_web_search_helper()

    if helper1 is helper2:
        print("\n✅ Global instance working correctly (same object)")
        print(f"   Instance ID: {id(helper1)}")
        return True
    else:
        print("\n❌ Global instance not working (different objects)")
        return False


def test_search_query_building():
    """Test 7: Test search query optimization"""
    print_section("TEST 7: Search Query Building")

    helper = get_web_search_helper()

    test_cases = [
        {
            "error": "Incorrect syntax near 'DECLARE'",
            "obj_type": "PROCEDURE",
            "context": "Oracle to SQL Server migration"
        },
        {
            "error": "Cannot find either column 'dbo' or the user-defined function",
            "obj_type": "FUNCTION",
            "context": ""
        },
        {
            "error": "Subquery returned more than 1 value. This is not permitted when the subquery follows =, !=, <, <= , >, >=",
            "obj_type": "VIEW",
            "context": "complex subquery"
        }
    ]

    print("Testing query building for different scenarios:\n")

    for idx, case in enumerate(test_cases, 1):
        query = helper._build_search_query(
            case["error"],
            case["obj_type"],
            case.get("context", "")
        )

        print(f"{idx}. Object Type: {case['obj_type']}")
        print(f"   Error: {case['error'][:60]}...")
        print(f"   Generated Query: {query}")
        print()

    print("✅ Query building test complete")
    return True


def run_all_tests():
    """Run all web search tests"""
    print("\n" + "=" * 80)
    print("  ORACLE TO SQL SERVER MIGRATION - WEB SEARCH TEST SUITE")
    print("=" * 80)

    tests = [
        ("Configuration", test_configuration),
        ("Helper Initialization", test_web_search_helper_initialization),
        ("Simple Search", test_simple_search),
        ("Complex Search", test_complex_search),
        ("Different Object Types", test_different_object_types),
        ("Global Instance", test_global_instance),
        ("Query Building", test_search_query_building),
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
        print("\n🎉 All tests passed! Web search is working correctly.")
        return 0
    elif passed > 0:
        print(f"\n⚠️ {total - passed} test(s) failed. Web search is partially working.")
        return 1
    else:
        print("\n❌ All tests failed. Web search is not working.")
        print("\nTroubleshooting steps:")
        print("1. Check if TAVILY_API_KEY is set in .env file")
        print("2. Verify Tavily API key is valid at https://tavily.com/")
        print("3. Check internet connection")
        print("4. Review logs above for specific errors")
        return 2


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
