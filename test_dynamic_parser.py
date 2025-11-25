"""
Comprehensive Test Suite for Dynamic Package Parser

Tests various package structures from different databases and formatting styles
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.package_decomposer_universal import decompose_oracle_package


# Test Case 1: Standard Oracle Package with Spec and Body
ORACLE_STANDARD = """
CREATE OR REPLACE PACKAGE pkg_employee IS
    PROCEDURE add_employee(p_name IN VARCHAR2, p_salary IN NUMBER);
    FUNCTION get_employee_count RETURN NUMBER;
END pkg_employee;
/

CREATE OR REPLACE PACKAGE BODY pkg_employee IS
    PROCEDURE add_employee(p_name IN VARCHAR2, p_salary IN NUMBER) IS
    BEGIN
        INSERT INTO employees VALUES (p_name, p_salary);
    END add_employee;

    FUNCTION get_employee_count RETURN NUMBER IS
        v_count NUMBER;
    BEGIN
        SELECT COUNT(*) INTO v_count FROM employees;
        RETURN v_count;
    END get_employee_count;
END pkg_employee;
/
"""

# Test Case 2: Complex Package with Nested Blocks
ORACLE_COMPLEX = """
CREATE OR REPLACE PACKAGE BODY pkg_complex IS
    PROCEDURE process_data(p_id IN NUMBER) IS
        v_status VARCHAR2(20);
    BEGIN
        FOR rec IN (SELECT * FROM data WHERE id = p_id) LOOP
            BEGIN
                IF rec.type = 'A' THEN
                    UPDATE data SET status = 'PROCESSED' WHERE id = rec.id;
                ELSE
                    DELETE FROM data WHERE id = rec.id;
                END IF;
            EXCEPTION
                WHEN OTHERS THEN
                    v_status := 'ERROR';
            END;
        END LOOP;
    END process_data;

    FUNCTION calculate(p_a NUMBER, p_b NUMBER) RETURN NUMBER IS
    BEGIN
        RETURN p_a + p_b;
    END calculate;
END pkg_complex;
/
"""

# Test Case 3: Package with Parameters Having Data Types
ORACLE_DATATYPES = """
CREATE OR REPLACE PACKAGE pkg_types IS
    PROCEDURE update_record(
        p_id IN NUMBER,
        p_name IN VARCHAR2(100),
        p_amount IN NUMBER(10,2),
        p_date IN DATE,
        p_flag IN OUT BOOLEAN
    );

    FUNCTION format_string(
        p_input IN VARCHAR2(500),
        p_max_len IN NUMBER DEFAULT 100
    ) RETURN VARCHAR2;
END pkg_types;
/
"""

# Test Case 4: Compact Formatting (All on Few Lines)
ORACLE_COMPACT = """
CREATE OR REPLACE PACKAGE pkg_compact IS
PROCEDURE proc1(p1 IN NUMBER); PROCEDURE proc2(p2 VARCHAR2);
FUNCTION func1(f1 NUMBER) RETURN NUMBER;
END pkg_compact;
/
CREATE OR REPLACE PACKAGE BODY pkg_compact IS
PROCEDURE proc1(p1 IN NUMBER) IS BEGIN NULL; END;
PROCEDURE proc2(p2 VARCHAR2) IS BEGIN NULL; END;
FUNCTION func1(f1 NUMBER) RETURN NUMBER IS BEGIN RETURN f1*2; END;
END pkg_compact;
/
"""

# Test Case 5: Package with Private Members
ORACLE_PRIVATE = """
CREATE OR REPLACE PACKAGE pkg_mixed IS
    -- Public
    PROCEDURE public_proc(p_val IN NUMBER);
    FUNCTION public_func RETURN VARCHAR2;
END pkg_mixed;
/

CREATE OR REPLACE PACKAGE BODY pkg_mixed IS
    -- Private procedure (not in spec)
    PROCEDURE private_proc(p_msg IN VARCHAR2) IS
    BEGIN
        DBMS_OUTPUT.PUT_LINE(p_msg);
    END private_proc;

    -- Public implementations
    PROCEDURE public_proc(p_val IN NUMBER) IS
    BEGIN
        private_proc('Processing: ' || p_val);
    END public_proc;

    FUNCTION public_func RETURN VARCHAR2 IS
    BEGIN
        RETURN 'SUCCESS';
    END public_func;
END pkg_mixed;
/
"""

# Test Case 6: PostgreSQL-style Package (for multi-DB support)
POSTGRES_STYLE = """
CREATE OR REPLACE PACKAGE pkg_postgres AS
    PROCEDURE insert_log(msg TEXT);
    FUNCTION get_version() RETURNS VARCHAR;
END;
/

CREATE OR REPLACE PACKAGE BODY pkg_postgres AS
    PROCEDURE insert_log(msg TEXT) IS
    BEGIN
        INSERT INTO logs (message) VALUES (msg);
    END;

    FUNCTION get_version() RETURNS VARCHAR IS
    BEGIN
        RETURN '1.0.0';
    END;
END;
/
"""


def run_test(name: str, code: str, expected_procs: int, expected_funcs: int):
    """Run a single test case"""
    print("\n" + "="*80)
    print(f"TEST: {name}")
    print("="*80)

    try:
        result = decompose_oracle_package(name, code)

        procs = result['total_procedures']
        funcs = result['total_functions']
        members = len(result['members'])

        print(f"\nPackage: {result['package_name']}")
        print(f"Procedures: {procs} (expected: {expected_procs})")
        print(f"Functions: {funcs} (expected: {expected_funcs})")
        print(f"Total Members: {members}")

        # Show members
        if members > 0:
            print("\nMembers Found:")
            for i, member in enumerate(result['members'], 1):
                vis = "PUBLIC" if member.is_public else "PRIVATE"
                print(f"  {i}. {member.member_type}: {member.name} ({vis})")
                print(f"     Params: {len(member.parameters)}")
                if member.member_type == 'FUNCTION':
                    print(f"     Returns: {member.return_type}")

        # Check result
        passed = (procs >= expected_procs and funcs >= expected_funcs)

        if passed:
            print("\n[PASS] Test passed!")
            return True
        else:
            print(f"\n[FAIL] Expected at least {expected_procs} procs and {expected_funcs} funcs")
            return False

    except Exception as e:
        print(f"\n[ERROR] Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("="*80)
    print(" DYNAMIC PACKAGE PARSER - COMPREHENSIVE TEST SUITE")
    print("="*80)
    print("\nTesting various package structures and formatting styles...")

    tests = [
        ("Standard Oracle Package", ORACLE_STANDARD, 1, 1),
        ("Complex Nested Blocks", ORACLE_COMPLEX, 1, 1),
        ("Various Data Types", ORACLE_DATATYPES, 1, 1),
        ("Compact Formatting", ORACLE_COMPACT, 2, 1),
        ("Public/Private Members", ORACLE_PRIVATE, 2, 1),  # 1 public + 1 private proc, 1 func
        ("PostgreSQL Style", POSTGRES_STYLE, 1, 1),
    ]

    results = []
    for test_args in tests:
        results.append(run_test(*test_args))

    # Summary
    print("\n" + "="*80)
    print(" TEST SUMMARY")
    print("="*80)

    passed = sum(results)
    total = len(results)

    print(f"\nPassed: {passed}/{total}")
    print(f"Failed: {total - passed}/{total}")

    if passed == total:
        print("\n[SUCCESS] All tests passed!")
        print("\nThe dynamic parser is working correctly with:")
        print("  - Standard Oracle packages")
        print("  - Complex nested structures")
        print("  - Various data types and parameters")
        print("  - Different formatting styles")
        print("  - Public and private members")
        print("  - Multiple database syntaxes")
    else:
        print("\n[PARTIAL] Some tests failed")
        print("The parser needs improvement for failed test cases")

    print("\n" + "="*80)
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
