"""Test Universal Parser"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.package_decomposer_universal import decompose_oracle_package

# Simple test
SIMPLE_PKG = """
CREATE OR REPLACE PACKAGE pkg_test IS
    PROCEDURE test_proc(p_id IN NUMBER);
    FUNCTION test_func RETURN VARCHAR2;
END pkg_test;
/

CREATE OR REPLACE PACKAGE BODY pkg_test IS
    PROCEDURE test_proc(p_id IN NUMBER) IS
    BEGIN
        NULL;
    END test_proc;

    FUNCTION test_func RETURN VARCHAR2 IS
    BEGIN
        RETURN 'OK';
    END test_func;
END pkg_test;
/
"""

result = decompose_oracle_package('pkg_test', SIMPLE_PKG)

print("Package:", result['package_name'])
print("Procedures:", result['total_procedures'])
print("Functions:", result['total_functions'])
print("Total Members:", len(result['members']))

for m in result['members']:
    print(f"  - {m.member_type}: {m.name} ({'PUBLIC' if m.is_public else 'PRIVATE'})")

if result['total_procedures'] >= 1 and result['total_functions'] >= 1:
    print("\n[PASS] Universal parser works!")
else:
    print("\n[FAIL] Parser didn't find all members")
