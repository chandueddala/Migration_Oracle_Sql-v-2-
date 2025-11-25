"""
Test parser with RAW package code (from USER_SOURCE)
This is how Oracle returns package code - without CREATE statement
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.package_decomposer_multi import decompose_oracle_package

# Simulates what Oracle returns from USER_SOURCE
RAW_PACKAGE_CODE = """
PACKAGE PKG_LOAN_PROCESSOR IS
    PROCEDURE PROCESS_LOAN(p_loan_id IN NUMBER);
    PROCEDURE VALIDATE_APPLICATION(p_app_id IN NUMBER, p_status OUT VARCHAR2);
    FUNCTION GET_LOAN_STATUS(p_loan_id IN NUMBER) RETURN VARCHAR2;
    FUNCTION CALCULATE_INTEREST(p_amount IN NUMBER, p_rate IN NUMBER) RETURN NUMBER;
END PKG_LOAN_PROCESSOR;

PACKAGE BODY PKG_LOAN_PROCESSOR IS
    PROCEDURE LOG_ERROR(p_message IN VARCHAR2) IS
    BEGIN
        INSERT INTO ERROR_LOG (message, log_date) VALUES (p_message, SYSDATE);
    END LOG_ERROR;

    PROCEDURE PROCESS_LOAN(p_loan_id IN NUMBER) IS
        v_status VARCHAR2(20);
    BEGIN
        UPDATE LOANS
        SET status = 'PROCESSING',
            process_date = SYSDATE
        WHERE loan_id = p_loan_id;
        COMMIT;
    EXCEPTION
        WHEN OTHERS THEN
            LOG_ERROR('Error processing loan: ' || SQLERRM);
            RAISE;
    END PROCESS_LOAN;

    PROCEDURE VALIDATE_APPLICATION(p_app_id IN NUMBER, p_status OUT VARCHAR2) IS
        v_count NUMBER;
    BEGIN
        SELECT COUNT(*) INTO v_count
        FROM APPLICATIONS
        WHERE app_id = p_app_id;

        IF v_count = 0 THEN
            p_status := 'NOT_FOUND';
        ELSE
            p_status := 'VALID';
        END IF;
    END VALIDATE_APPLICATION;

    FUNCTION GET_LOAN_STATUS(p_loan_id IN NUMBER) RETURN VARCHAR2 IS
        v_status VARCHAR2(20);
    BEGIN
        SELECT status INTO v_status
        FROM LOANS
        WHERE loan_id = p_loan_id;
        RETURN v_status;
    EXCEPTION
        WHEN NO_DATA_FOUND THEN
            RETURN 'NOT_FOUND';
    END GET_LOAN_STATUS;

    FUNCTION CALCULATE_INTEREST(p_amount IN NUMBER, p_rate IN NUMBER) RETURN NUMBER IS
    BEGIN
        RETURN p_amount * (p_rate / 100);
    END CALCULATE_INTEREST;
END PKG_LOAN_PROCESSOR;
"""

print("="*80)
print(" TEST: RAW PACKAGE CODE (from USER_SOURCE)")
print("="*80)

result = decompose_oracle_package('PKG_LOAN_PROCESSOR', RAW_PACKAGE_CODE)

print(f"\nPackage: {result['package_name']}")
print(f"Procedures: {result['total_procedures']}")
print(f"Functions: {result['total_functions']}")
print(f"Total Members: {len(result['members'])}")

print("\nMembers Found:")
for i, member in enumerate(result['members'], 1):
    vis = "PUBLIC" if member.is_public else "PRIVATE"
    print(f"  {i}. {member.member_type}: {member.name} ({vis})")

print("\n" + "="*80)
if result['total_procedures'] >= 2 and result['total_functions'] >= 2:
    print("[PASS] Raw package code parsed successfully!")
    print(f"  Found {result['total_procedures']} procedures")
    print(f"  Found {result['total_functions']} functions")
else:
    print("[FAIL] Expected at least 2 procedures and 2 functions")
    print(f"  Got {result['total_procedures']} procedures")
    print(f"  Got {result['total_functions']} functions")

print("="*80)
