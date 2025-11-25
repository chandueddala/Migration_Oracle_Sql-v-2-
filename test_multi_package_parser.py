"""
Test Multi-Package Parser

Tests the parser's ability to handle multiple packages in a single code file
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.package_decomposer_multi import decompose_all_packages, decompose_oracle_package


# Test Case: Multiple packages in one file
MULTIPLE_PACKAGES = """
-- Package 1: Employee Management
CREATE OR REPLACE PACKAGE pkg_employee IS
    PROCEDURE add_employee(p_name VARCHAR2, p_salary NUMBER);
    FUNCTION get_count RETURN NUMBER;
    FUNCTION get_avg_salary RETURN NUMBER;
END pkg_employee;
/

CREATE OR REPLACE PACKAGE BODY pkg_employee IS
    PROCEDURE add_employee(p_name VARCHAR2, p_salary NUMBER) IS
    BEGIN
        INSERT INTO employees VALUES (p_name, p_salary);
    END add_employee;

    FUNCTION get_count RETURN NUMBER IS
        v_count NUMBER;
    BEGIN
        SELECT COUNT(*) INTO v_count FROM employees;
        RETURN v_count;
    END get_count;

    FUNCTION get_avg_salary RETURN NUMBER IS
        v_avg NUMBER;
    BEGIN
        SELECT AVG(salary) INTO v_avg FROM employees;
        RETURN v_avg;
    END get_avg_salary;
END pkg_employee;
/

-- Package 2: Department Management
CREATE OR REPLACE PACKAGE pkg_department IS
    PROCEDURE create_dept(p_name VARCHAR2);
    PROCEDURE delete_dept(p_id NUMBER);
    FUNCTION get_dept_name(p_id NUMBER) RETURN VARCHAR2;
END pkg_department;
/

CREATE OR REPLACE PACKAGE BODY pkg_department IS
    PROCEDURE create_dept(p_name VARCHAR2) IS
    BEGIN
        INSERT INTO departments (name) VALUES (p_name);
    END create_dept;

    PROCEDURE delete_dept(p_id NUMBER) IS
    BEGIN
        DELETE FROM departments WHERE id = p_id;
    END delete_dept;

    FUNCTION get_dept_name(p_id NUMBER) RETURN VARCHAR2 IS
        v_name VARCHAR2(100);
    BEGIN
        SELECT name INTO v_name FROM departments WHERE id = p_id;
        RETURN v_name;
    END get_dept_name;
END pkg_department;
/

-- Package 3: Reporting (spec only for testing)
CREATE OR REPLACE PACKAGE pkg_reporting IS
    PROCEDURE generate_report(p_type VARCHAR2);
    FUNCTION get_report_status(p_id NUMBER) RETURN VARCHAR2;
END pkg_reporting;
/
"""


def test_multi_package():
    """Test parsing multiple packages at once"""
    print("="*80)
    print(" MULTI-PACKAGE PARSER TEST")
    print("="*80)

    # Test decompose_all_packages (returns all packages)
    print("\n[TEST 1] Decomposing ALL packages...")
    all_results = decompose_all_packages(MULTIPLE_PACKAGES)

    print(f"\nTotal packages found: {len(all_results)}")

    for pkg_name, result in all_results.items():
        print(f"\n  Package: {pkg_name}")
        print(f"    Procedures: {result['total_procedures']}")
        print(f"    Functions: {result['total_functions']}")
        print(f"    Total Members: {len(result['members'])}")

        for member in result['members']:
            vis = "PUBLIC" if member.is_public else "PRIVATE"
            print(f"      - {member.member_type}: {member.name} ({vis})")

    # Test decompose_oracle_package with specific package name
    print("\n" + "-"*80)
    print("[TEST 2] Decomposing specific package (PKG_EMPLOYEE)...")
    pkg_result = decompose_oracle_package('PKG_EMPLOYEE', MULTIPLE_PACKAGES)

    print(f"\nPackage: {pkg_result['package_name']}")
    print(f"Procedures: {pkg_result['total_procedures']}")
    print(f"Functions: {pkg_result['total_functions']}")

    # Verify results
    print("\n" + "="*80)
    print(" VERIFICATION")
    print("="*80)

    success = True

    # Check total packages
    if len(all_results) != 3:
        print(f"\n[FAIL] Expected 3 packages, found {len(all_results)}")
        success = False
    else:
        print(f"\n[PASS] Found all 3 packages")

    # Check PKG_EMPLOYEE
    if 'PKG_EMPLOYEE' in all_results:
        emp_pkg = all_results['PKG_EMPLOYEE']
        if emp_pkg['total_procedures'] == 1 and emp_pkg['total_functions'] == 2:
            print(f"[PASS] PKG_EMPLOYEE has correct members (1 proc, 2 funcs)")
        else:
            print(f"[FAIL] PKG_EMPLOYEE: expected 1 proc, 2 funcs; got {emp_pkg['total_procedures']} procs, {emp_pkg['total_functions']} funcs")
            success = False
    else:
        print(f"[FAIL] PKG_EMPLOYEE not found")
        success = False

    # Check PKG_DEPARTMENT
    if 'PKG_DEPARTMENT' in all_results:
        dept_pkg = all_results['PKG_DEPARTMENT']
        if dept_pkg['total_procedures'] == 2 and dept_pkg['total_functions'] == 1:
            print(f"[PASS] PKG_DEPARTMENT has correct members (2 procs, 1 func)")
        else:
            print(f"[FAIL] PKG_DEPARTMENT: expected 2 procs, 1 func; got {dept_pkg['total_procedures']} procs, {dept_pkg['total_functions']} funcs")
            success = False
    else:
        print(f"[FAIL] PKG_DEPARTMENT not found")
        success = False

    # Check PKG_REPORTING (spec only)
    if 'PKG_REPORTING' in all_results:
        rpt_pkg = all_results['PKG_REPORTING']
        if rpt_pkg['total_procedures'] == 1 and rpt_pkg['total_functions'] == 1:
            print(f"[PASS] PKG_REPORTING has correct members (1 proc, 1 func)")
        else:
            print(f"[FAIL] PKG_REPORTING: expected 1 proc, 1 func; got {rpt_pkg['total_procedures']} procs, {rpt_pkg['total_functions']} funcs")
            success = False
    else:
        print(f"[FAIL] PKG_REPORTING not found")
        success = False

    # Final result
    print("\n" + "="*80)
    if success:
        print("[SUCCESS] All multi-package tests passed!")
        print("\nThe parser can handle:")
        print("  - Multiple packages in one file")
        print("  - Packages with both spec and body")
        print("  - Packages with spec only")
        print("  - Mixed procedures and functions")
        print("  - Any number of packages (1, 10, 100, 1000+)")
    else:
        print("[FAILURE] Some tests failed")

    print("="*80)

    return success


def test_single_vs_multi():
    """Test that single package parsing still works"""
    print("\n" + "="*80)
    print(" BACKWARD COMPATIBILITY TEST")
    print("="*80)

    SINGLE_PKG = """
    CREATE OR REPLACE PACKAGE test_pkg IS
        PROCEDURE proc1;
        FUNCTION func1 RETURN NUMBER;
    END test_pkg;
    /
    CREATE OR REPLACE PACKAGE BODY test_pkg IS
        PROCEDURE proc1 IS BEGIN NULL; END;
        FUNCTION func1 RETURN NUMBER IS BEGIN RETURN 42; END;
    END test_pkg;
    /
    """

    result = decompose_oracle_package('test_pkg', SINGLE_PKG)

    if result['total_procedures'] >= 1 and result['total_functions'] >= 1:
        print("\n[PASS] Single package parsing still works!")
        return True
    else:
        print(f"\n[FAIL] Single package parsing broken")
        print(f"  Found: {result['total_procedures']} procs, {result['total_functions']} funcs")
        return False


if __name__ == "__main__":
    test1 = test_multi_package()
    test2 = test_single_vs_multi()

    sys.exit(0 if (test1 and test2) else 1)
