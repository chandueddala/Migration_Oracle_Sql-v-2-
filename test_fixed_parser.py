"""
Test the fixed package decomposer

This will test with a sample Oracle package structure
"""

# Sample Oracle package for testing
SAMPLE_PACKAGE = """
CREATE OR REPLACE PACKAGE PKG_LOAN_PROCESSOR IS
    -- Public procedures
    PROCEDURE PROCESS_LOAN(p_loan_id IN NUMBER);
    PROCEDURE VALIDATE_APPLICATION(p_app_id IN NUMBER, p_status OUT VARCHAR2);

    -- Public functions
    FUNCTION GET_LOAN_STATUS(p_loan_id IN NUMBER) RETURN VARCHAR2;
    FUNCTION CALCULATE_INTEREST(p_amount IN NUMBER, p_rate IN NUMBER) RETURN NUMBER;
END PKG_LOAN_PROCESSOR;
/

CREATE OR REPLACE PACKAGE BODY PKG_LOAN_PROCESSOR IS

    -- Private procedure
    PROCEDURE LOG_ERROR(p_message IN VARCHAR2) IS
    BEGIN
        INSERT INTO ERROR_LOG (message, log_date) VALUES (p_message, SYSDATE);
    END LOG_ERROR;

    -- Public procedure implementation
    PROCEDURE PROCESS_LOAN(p_loan_id IN NUMBER) IS
        v_status VARCHAR2(20);
    BEGIN
        -- Process the loan
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

    -- Public procedure implementation
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

    -- Public function implementation
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

    -- Public function implementation
    FUNCTION CALCULATE_INTEREST(p_amount IN NUMBER, p_rate IN NUMBER) RETURN NUMBER IS
    BEGIN
        RETURN p_amount * (p_rate / 100);
    END CALCULATE_INTEREST;

END PKG_LOAN_PROCESSOR;
/
"""


def test_fixed_parser():
    """Test the fixed parser"""
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    from utils.package_decomposer_fixed import decompose_oracle_package

    print("=" * 80)
    print("TESTING FIXED PACKAGE DECOMPOSER")
    print("=" * 80)

    print(f"\nInput package code: {len(SAMPLE_PACKAGE)} characters")

    # Parse the package
    result = decompose_oracle_package('PKG_LOAN_PROCESSOR', SAMPLE_PACKAGE)

    print(f"\nPackage Name: {result['package_name']}")
    print(f"Total Procedures: {result['total_procedures']}")
    print(f"Total Functions: {result['total_functions']}")
    print(f"Total Members: {len(result['members'])}")

    print("\n" + "-" * 80)
    print("MEMBERS FOUND:")
    print("-" * 80)

    for i, member in enumerate(result['members'], 1):
        visibility = "PUBLIC" if member.is_public else "PRIVATE"
        print(f"\n{i}. {member.member_type}: {member.name} ({visibility})")
        print(f"   SQL Server name: {member.get_sql_server_name('PKG_LOAN_PROCESSOR')}")
        print(f"   Specification: {member.specification[:80]}...")
        if member.body:
            print(f"   Body length: {len(member.body)} chars")
        else:
            print(f"   Body: (declaration only)")

    print("\n" + "=" * 80)
    print("MIGRATION PLAN:")
    print("=" * 80)

    plan = result['migration_plan']
    print(f"\nStrategy: {plan['strategy']}")
    print(f"Components to migrate: {len(plan['components'])}")

    for comp in plan['components']:
        print(f"\n- {comp['type']}: {comp['original_name']} -> {comp['name']}")
        print(f"  Visibility: {comp['visibility']}")
        print(f"  Action: {comp['migration_action']}")

    # Test result
    print("\n" + "=" * 80)
    if result['total_procedures'] >= 2 and result['total_functions'] >= 2:
        print("✅ TEST PASSED!")
        print(f"   Found {result['total_procedures']} procedures and {result['total_functions']} functions")
        print("   Parser is working correctly!")
    else:
        print("❌ TEST FAILED!")
        print(f"   Expected at least 2 procedures and 2 functions")
        print(f"   Got {result['total_procedures']} procedures and {result['total_functions']} functions")
    print("=" * 80)


if __name__ == "__main__":
    test_fixed_parser()
