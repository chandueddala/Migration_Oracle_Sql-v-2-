#!/usr/bin/env python3
"""
Oracle Loan Processing Database Loader
======================================

Standalone script to load Oracle database with:
- 5 Tables
- 2 Sequences  
- 1 Package (PKG_LOAN_PROCESSOR)
- Sample data

EDIT CREDENTIALS BELOW, then run:
    python oracle_data_load.py

Requirements:
    pip install oracledb
"""

import oracledb
import json
from datetime import datetime, timedelta
import random

# ============================================================================
# EDIT YOUR ORACLE CREDENTIALS HERE
# ============================================================================

USER = "app"
PASSWORD = "app"
DSN = "localhost:1521/FREEPDB1"

# Alternative formats:
# For Oracle Cloud:
# USER = "ADMIN"
# PASSWORD = "YourPassword123"
# DSN = "your_db_name_high"
#
# For TNS name:
# DSN = "ORCL"
#
# For thick mode (older Oracle client):
# oracledb.init_oracle_client(lib_dir="/path/to/instantclient")

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def drop_table_if_exists(cur, name: str):
    cur.execute(
        "SELECT 1 FROM user_tables WHERE table_name = :t",
        {"t": name.upper()},
    )
    if cur.fetchone():
        print(f"↻ Dropping table {name} …")
        cur.execute(f"DROP TABLE {name} CASCADE CONSTRAINTS PURGE")


def drop_sequence_if_exists(cur, name: str):
    cur.execute(
        "SELECT 1 FROM user_sequences WHERE sequence_name = :s",
        {"s": name.upper()},
    )
    if cur.fetchone():
        print(f"↻ Dropping sequence {name} …")
        cur.execute(f"DROP SEQUENCE {name}")


def drop_package_if_exists(cur, name: str):
    cur.execute(
        "SELECT 1 FROM user_objects WHERE object_type = 'PACKAGE' AND object_name = :n",
        {"n": name.upper()},
    )
    if cur.fetchone():
        print(f"↻ Dropping package {name} …")
        cur.execute(f"DROP PACKAGE {name}")


def exec_ddl(cur, sql: str):
    first_line = sql.strip().splitlines()[0]
    print(f"\n▶ Executing DDL: {first_line}")
    cur.execute(sql)


# ============================================================================
# DDL: TABLES & SEQUENCES
# ============================================================================

TABLE_DDLS = [
    # 1) STG_LOAN_APPS
    """
    CREATE TABLE stg_loan_apps (
      stg_id      NUMBER       PRIMARY KEY,
      payload     CLOB,
      created_on  TIMESTAMP
    )
    """,
    # 2) LOANS
    """
    CREATE TABLE loans (
      loan_id              NUMBER       PRIMARY KEY,
      external_app_id      VARCHAR2(100),
      customer_id          NUMBER,
      principal            NUMBER,
      annual_rate          NUMBER,
      term_months          NUMBER,
      start_date           DATE,
      status               VARCHAR2(30),
      outstanding_balance  NUMBER,
      created_on           TIMESTAMP
    )
    """,
    # 3) LOAN_SCHEDULE
    """
    CREATE TABLE loan_schedule (
      schedule_id    NUMBER       PRIMARY KEY,
      loan_id        NUMBER,
      due_date       DATE,
      period_no      NUMBER,
      principal_amt  NUMBER,
      interest_amt   NUMBER,
      outstanding    NUMBER
    )
    """,
    # 4) LOAN_PAYMENTS
    """
    CREATE TABLE loan_payments (
      payment_id           NUMBER       PRIMARY KEY,
      loan_id              NUMBER,
      paid_on              DATE,
      amount               NUMBER,
      applied_to_principal NUMBER,
      applied_to_interest  NUMBER
    )
    """,
    # 5) LOAN_AUDIT
    """
    CREATE TABLE loan_audit (
      audit_id     NUMBER       PRIMARY KEY,
      stg_id       NUMBER,
      status       VARCHAR2(30),
      message      VARCHAR2(4000),
      processed_on TIMESTAMP
    )
    """,
]

SEQUENCE_DDLS = [
    """
    CREATE SEQUENCE loan_seq
      START WITH 500000
      INCREMENT BY 1
      NOCACHE
      NOCYCLE
    """,
    """
    CREATE SEQUENCE app_seq
      START WITH 1
      INCREMENT BY 1
      NOCACHE
      NOCYCLE
    """,
]

# ============================================================================
# PL/SQL PACKAGE: PKG_LOAN_PROCESSOR (EXACT FROM YOUR TEXT FILE)
# ============================================================================

PACKAGE_SPEC = r"""
CREATE OR REPLACE PACKAGE pkg_loan_processor IS
  PROCEDURE process_batch(p_batch_size IN PLS_INTEGER := 50);
  PROCEDURE dry_run(p_batch_size IN PLS_INTEGER := 20);
END pkg_loan_processor;
"""

PACKAGE_BODY = r"""
CREATE OR REPLACE PACKAGE BODY pkg_loan_processor IS

  PRAGMA SERIALLY_REUSABLE;

  TYPE t_item IS RECORD (
    product VARCHAR2(100)
  );

  ---------------------------------------------------------------------------
  -- Autonomous audit writer
  ---------------------------------------------------------------------------
  PROCEDURE audit_write(
    p_stg_id  IN NUMBER,
    p_status  IN VARCHAR2,
    p_message IN VARCHAR2
  ) IS
    PRAGMA AUTONOMOUS_TRANSACTION;
  BEGIN
    INSERT INTO loan_audit(audit_id, stg_id, status, message, processed_on)
    VALUES (
      app_seq.NEXTVAL,
      p_stg_id,
      p_status,
      SUBSTR(p_message, 1, 4000),
      SYSTIMESTAMP
    );
    COMMIT;
  EXCEPTION
    WHEN OTHERS THEN
      NULL;
  END audit_write;

  ---------------------------------------------------------------------------
  -- Simulated credit check
  ---------------------------------------------------------------------------
  FUNCTION perform_credit_check(
    p_customer_id IN NUMBER,
    p_payload     IN CLOB
  ) RETURN VARCHAR2 IS
    l_score NUMBER;
  BEGIN
    l_score := MOD(NVL(p_customer_id, 0), 100);

    IF l_score > 30 THEN
      RETURN 'PASS';
    ELSIF l_score > 10 THEN
      RETURN 'REVIEW';
    ELSE
      RETURN 'FAIL';
    END IF;
  END perform_credit_check;

  ---------------------------------------------------------------------------
  -- Simple amortization: equal monthly payment (annuity)
  ---------------------------------------------------------------------------
  FUNCTION calc_monthly_payment(
    p_principal   IN NUMBER,
    p_annual_rate IN NUMBER,
    p_term_months IN NUMBER
  ) RETURN NUMBER IS
    l_r       NUMBER;
    l_n       NUMBER := p_term_months;
    l_payment NUMBER;
  BEGIN
    IF l_n IS NULL OR l_n <= 0 THEN
      RAISE_APPLICATION_ERROR(-20009, 'Invalid term_months');
    END IF;

    IF p_annual_rate IS NULL OR p_annual_rate = 0 THEN
      RETURN ROUND(p_principal / l_n, 2);
    END IF;

    l_r := p_annual_rate / 12 / 100;
    l_payment := p_principal * (l_r / (1 - POWER(1 + l_r, -l_n)));
    RETURN ROUND(l_payment, 2);
  END calc_monthly_payment;

  ---------------------------------------------------------------------------
  -- Build schedule and insert in bulk
  ---------------------------------------------------------------------------
  PROCEDURE create_schedule(
    p_loan_id     IN NUMBER,
    p_principal   IN NUMBER,
    p_annual_rate IN NUMBER,
    p_term        IN NUMBER,
    p_start_date  IN DATE
  ) IS
    TYPE t_sched_rec IS RECORD (
      schedule_id    NUMBER,
      loan_id        NUMBER,
      due_date       DATE,
      period_no      NUMBER,
      principal_amt  NUMBER,
      interest_amt   NUMBER,
      outstanding    NUMBER
    );
    TYPE t_sched_tab IS TABLE OF t_sched_rec INDEX BY PLS_INTEGER;

    v_tab          t_sched_tab;
    v_payment      NUMBER;
    v_outstanding  NUMBER := p_principal;
    v_interest     NUMBER;
    v_principal_pd NUMBER;
    idx            PLS_INTEGER := 0;
  BEGIN
    v_payment := calc_monthly_payment(p_principal, p_annual_rate, p_term);

    FOR i IN 1 .. p_term LOOP
      v_interest     := ROUND(v_outstanding * (p_annual_rate / 12 / 100), 2);
      v_principal_pd := LEAST(ROUND(v_payment - v_interest, 2), v_outstanding);
      v_outstanding  := ROUND(v_outstanding - v_principal_pd, 2);

      idx := idx + 1;
      v_tab(idx).schedule_id   := loan_seq.NEXTVAL;
      v_tab(idx).loan_id       := p_loan_id;
      v_tab(idx).due_date      := ADD_MONTHS(p_start_date, i);
      v_tab(idx).period_no     := i;
      v_tab(idx).principal_amt := v_principal_pd;
      v_tab(idx).interest_amt  := v_interest;
      v_tab(idx).outstanding   := v_outstanding;
    END LOOP;

    IF idx > 0 THEN
      FORALL j IN 1 .. idx
        INSERT INTO loan_schedule(
          schedule_id,
          loan_id,
          due_date,
          period_no,
          principal_amt,
          interest_amt,
          outstanding
        ) VALUES (
          v_tab(j).schedule_id,
          v_tab(j).loan_id,
          v_tab(j).due_date,
          v_tab(j).period_no,
          v_tab(j).principal_amt,
          v_tab(j).interest_amt,
          v_tab(j).outstanding
        );
    END IF;
  END create_schedule;

  ---------------------------------------------------------------------------
  -- Parse JSON payload from STG_LOAN_APPS
  ---------------------------------------------------------------------------
  PROCEDURE parse_payload(
    p_payload         IN  CLOB,
    p_external_app_id OUT VARCHAR2,
    p_customer_id     OUT NUMBER,
    p_principal       OUT NUMBER,
    p_rate            OUT NUMBER,
    p_term            OUT NUMBER,
    p_start_date      OUT DATE
  ) IS
    l_start_date_str VARCHAR2(20);
  BEGIN
    SELECT jt.external_app_id,
           jt.customer_id,
           jt.principal,
           jt.start_date,
           jt.annual_rate,
           jt.term_months
      INTO p_external_app_id,
           p_customer_id,
           p_principal,
           l_start_date_str,
           p_rate,
           p_term
      FROM JSON_TABLE(
             p_payload,
             '$'
             COLUMNS(
               external_app_id VARCHAR2(100) PATH '$.external_app_id',
               customer_id     NUMBER       PATH '$.customer_id',
               principal       NUMBER       PATH '$.principal',
               start_date      VARCHAR2(20) PATH '$.start_date',
               annual_rate     NUMBER       PATH '$.annual_rate',
               term_months     NUMBER       PATH '$.term_months'
             )
           ) jt;

    p_start_date := TO_DATE(l_start_date_str, 'YYYY-MM-DD');

    IF p_customer_id IS NULL
       OR p_principal  IS NULL
       OR p_term       IS NULL THEN
      RAISE_APPLICATION_ERROR(-20010, 'Missing required fields in payload');
    END IF;
  EXCEPTION
    WHEN NO_DATA_FOUND THEN
      RAISE_APPLICATION_ERROR(-20011, 'Invalid JSON payload structure');
  END parse_payload;

  ---------------------------------------------------------------------------
  -- Process one staging row
  ---------------------------------------------------------------------------
  PROCEDURE process_single(
    p_stg_id  IN NUMBER,
    p_payload IN CLOB
  ) IS
    l_external_app_id VARCHAR2(100);
    l_customer_id     NUMBER;
    l_principal       NUMBER;
    l_rate            NUMBER;
    l_term            NUMBER;
    l_start_date      DATE;
    l_credit_result   VARCHAR2(20);
    l_loan_id         NUMBER;
  BEGIN
    parse_payload(
      p_payload,
      l_external_app_id,
      l_customer_id,
      l_principal,
      l_rate,
      l_term,
      l_start_date
    );

    l_credit_result := perform_credit_check(l_customer_id, p_payload);

    IF l_credit_result = 'FAIL' THEN
      audit_write(p_stg_id, 'REJECTED', 'Credit check failed');
      RETURN;
    ELSIF l_credit_result = 'REVIEW' THEN
      audit_write(p_stg_id, 'MANUAL_REVIEW', 'Needs manual review');
      RETURN;
    END IF;

    IF l_external_app_id IS NOT NULL THEN
      BEGIN
        SELECT loan_id
          INTO l_loan_id
          FROM loans
         WHERE external_app_id = l_external_app_id;
      EXCEPTION
        WHEN NO_DATA_FOUND THEN
          l_loan_id := NULL;
      END;
    END IF;

    IF l_loan_id IS NULL THEN
      l_loan_id := loan_seq.NEXTVAL;
      INSERT INTO loans(
        loan_id,
        external_app_id,
        customer_id,
        principal,
        annual_rate,
        term_months,
        start_date,
        status,
        outstanding_balance,
        created_on
      ) VALUES (
        l_loan_id,
        l_external_app_id,
        l_customer_id,
        l_principal,
        l_rate,
        l_term,
        l_start_date,
        'ACTIVE',
        l_principal,
        SYSTIMESTAMP
      );
    ELSE
      UPDATE loans
         SET principal           = l_principal,
             annual_rate         = l_rate,
             term_months         = l_term,
             start_date          = l_start_date,
             status              = 'ACTIVE',
             outstanding_balance = l_principal
       WHERE loan_id = l_loan_id;
    END IF;

    create_schedule(
      l_loan_id,
      l_principal,
      l_rate,
      l_term,
      l_start_date
    );

    audit_write(p_stg_id, 'APPROVED', 'loan_id=' || l_loan_id);
  EXCEPTION
    WHEN OTHERS THEN
      audit_write(
        p_stg_id,
        'ERROR',
        SQLERRM || ' | ' || DBMS_UTILITY.FORMAT_ERROR_BACKTRACE
      );
      RAISE;
  END process_single;

  ---------------------------------------------------------------------------
  -- Batch processor
  ---------------------------------------------------------------------------
  PROCEDURE process_batch(
    p_batch_size IN PLS_INTEGER := 50
  ) IS
    CURSOR c_stg IS
      SELECT stg_id, payload
        FROM stg_loan_apps
       WHERE ROWNUM <= p_batch_size
       ORDER BY created_on
       FOR UPDATE SKIP LOCKED;

    l_count PLS_INTEGER := 0;
  BEGIN
    FOR r IN c_stg LOOP
      BEGIN
        SAVEPOINT sp_before_row;

        process_single(r.stg_id, r.payload);

        DELETE FROM stg_loan_apps
         WHERE stg_id = r.stg_id;

        l_count := l_count + 1;

        IF MOD(l_count, 20) = 0 THEN
          COMMIT;
        END IF;
      EXCEPTION
        WHEN OTHERS THEN
          ROLLBACK TO sp_before_row;
          audit_write(r.stg_id, 'ERR_PER_ROW', SQLERRM);

          INSERT INTO stg_loan_apps(stg_id, payload, created_on)
          VALUES (r.stg_id, r.payload, SYSTIMESTAMP);

          COMMIT;
      END;
    END LOOP;

    COMMIT;
  END process_batch;

  ---------------------------------------------------------------------------
  -- Dry-run: validate payloads only
  ---------------------------------------------------------------------------
  PROCEDURE dry_run(
    p_batch_size IN PLS_INTEGER := 20
  ) IS
  BEGIN
    FOR r IN (
      SELECT stg_id, payload
        FROM stg_loan_apps
       WHERE ROWNUM <= p_batch_size
       ORDER BY created_on
    ) LOOP
      BEGIN
        DECLARE
          l_external_app_id VARCHAR2(100);
          l_customer_id     NUMBER;
          l_principal       NUMBER;
          l_rate            NUMBER;
          l_term            NUMBER;
          l_start_date      DATE;
        BEGIN
          parse_payload(
            r.payload,
            l_external_app_id,
            l_customer_id,
            l_principal,
            l_rate,
            l_term,
            l_start_date
          );

          DBMS_OUTPUT.PUT_LINE(
            'DRY_RUN OK stg_id=' || r.stg_id ||
            ' cust=' || l_customer_id ||
            ' principal=' || l_principal ||
            ' term=' || l_term
          );
        END;
      EXCEPTION
        WHEN OTHERS THEN
          DBMS_OUTPUT.PUT_LINE(
            'DRY_RUN ERR stg_id=' || r.stg_id ||
            ' err=' || SQLERRM
          );
      END;
    END LOOP;
  END dry_run;

END pkg_loan_processor;
"""

# ============================================================================
# SAMPLE DATA GENERATION
# ============================================================================

def generate_sample_data():
    """Generate sample loan applications"""
    stg_rows = [
        (
            1,
            """{
               "external_app_id": "APP-1001",
               "customer_id": 12345,
               "principal": 25000,
               "annual_rate": 12.0,
               "term_months": 36,
               "start_date": "2025-01-01"
            }""",
        ),
        (
            2,
            """{
               "external_app_id": "APP-1002",
               "customer_id": 23015,
               "principal": 50000,
               "annual_rate": 9.5,
               "term_months": 60,
               "start_date": "2025-02-15"
            }""",
        ),
        (
            3,
            """{
               "external_app_id": "APP-1003",
               "customer_id": 7,
               "principal": 15000,
               "annual_rate": 15.0,
               "term_months": 24,
               "start_date": "2025-03-01"
            }""",
        ),
        (
            4,
            """{
               "external_app_id": "APP-1004",
               "customer_id": 45623,
               "principal": 30000,
               "annual_rate": 11.5,
               "term_months": 48,
               "start_date": "2025-01-15"
            }""",
        ),
        (
            5,
            """{
               "external_app_id": "APP-1005",
               "customer_id": 78901,
               "principal": 40000,
               "annual_rate": 10.0,
               "term_months": 60,
               "start_date": "2025-02-01"
            }""",
        ),
    ]
    return stg_rows


# ============================================================================
# MAIN SEEDING LOGIC
# ============================================================================

def main():
    print("="*70)
    print("  Oracle Loan Processing Database Loader")
    print("="*70)
    print(f"\nConnecting to Oracle: {DSN}")
    print(f"User: {USER}\n")
    
    try:
        conn = oracledb.connect(user=USER, password=PASSWORD, dsn=DSN)
        cur = conn.cursor()
        print("✅ Connected.\n")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("\nPlease check your credentials at the top of this file:")
        print("  USER, PASSWORD, DSN")
        return 1

    # 1) Drop existing loan objects
    print("🧹 Cleaning old loan objects …")
    for tbl in ["LOAN_SCHEDULE", "LOAN_PAYMENTS", "LOAN_AUDIT", "LOANS", "STG_LOAN_APPS"]:
        drop_table_if_exists(cur, tbl)

    for seq in ["LOAN_SEQ", "APP_SEQ"]:
        drop_sequence_if_exists(cur, seq)

    drop_package_if_exists(cur, "PKG_LOAN_PROCESSOR")

    # 2) Create tables
    print("\n🏗️ Creating tables …")
    for ddl in TABLE_DDLS:
        exec_ddl(cur, ddl)

    # 3) Create sequences
    print("\n🏗️ Creating sequences …")
    for ddl in SEQUENCE_DDLS:
        exec_ddl(cur, ddl)

    # 4) Create package
    print("\n📦 Creating package PKG_LOAN_PROCESSOR …")
    exec_ddl(cur, PACKAGE_SPEC)
    exec_ddl(cur, PACKAGE_BODY)

    conn.commit()
    print("\n✅ Tables, sequences, and package created.")

    # 5) Populate sample data
    print("\n💾 Inserting sample data into STG_LOAN_APPS …")

    stg_rows = generate_sample_data()
    for stg_id, payload in stg_rows:
        cur.execute(
            """
            INSERT INTO stg_loan_apps (stg_id, payload, created_on)
            VALUES (:1, :2, SYSTIMESTAMP)
            """,
            (stg_id, payload),
        )

    print(f"   → {len(stg_rows)} staging applications inserted.")

    # One manual loan
    print("\n💾 Inserting one manual LOANS row (MANUAL-0001) …")
    cur.execute(
        """
        INSERT INTO loans (
          loan_id,
          external_app_id,
          customer_id,
          principal,
          annual_rate,
          term_months,
          start_date,
          status,
          outstanding_balance,
          created_on
        ) VALUES (
          loan_seq.NEXTVAL,
          'MANUAL-0001',
          88888,
          10000,
          10.0,
          12,
          DATE '2025-01-10',
          'ACTIVE',
          10000,
          SYSTIMESTAMP
        )
        """
    )

    # One schedule row for that manual loan
    print("💾 Inserting one LOAN_SCHEDULE row for MANUAL-0001 …")
    cur.execute(
        """
        INSERT INTO loan_schedule (
          schedule_id,
          loan_id,
          due_date,
          period_no,
          principal_amt,
          interest_amt,
          outstanding
        )
        SELECT
          loan_seq.NEXTVAL,
          loan_id,
          ADD_MONTHS(start_date, 1),
          1,
          800,
          100,
          9200
        FROM loans
        WHERE external_app_id = 'MANUAL-0001'
        """
    )

    # One payment row
    print("💾 Inserting one LOAN_PAYMENTS row for MANUAL-0001 …")
    cur.execute(
        """
        INSERT INTO loan_payments (
          payment_id,
          loan_id,
          paid_on,
          amount,
          applied_to_principal,
          applied_to_interest
        )
        SELECT
          loan_seq.NEXTVAL,
          loan_id,
          DATE '2025-02-10',
          900,
          800,
          100
        FROM loans
        WHERE external_app_id = 'MANUAL-0001'
        """
    )

    # One audit row
    print("💾 Inserting one LOAN_AUDIT row …")
    cur.execute(
        """
        INSERT INTO loan_audit (
          audit_id,
          stg_id,
          status,
          message,
          processed_on
        ) VALUES (
          app_seq.NEXTVAL,
          9999,
          'INFO',
          'Initial demo audit row',
          SYSTIMESTAMP
        )
        """
    )

    conn.commit()
    print("\n✅ Sample data inserted.")

    # 6) Quick row-count check
    print("\n📊 Row counts:")
    for name in ["STG_LOAN_APPS", "LOANS", "LOAN_SCHEDULE", "LOAN_PAYMENTS", "LOAN_AUDIT"]:
        cur.execute(f"SELECT COUNT(*) FROM {name}")
        cnt = cur.fetchone()[0]
        print(f"  - {name:15s}: {cnt:3d}")

    cur.close()
    conn.close()
    
    print("\n" + "="*70)
    print("  🎉 SUCCESS!")
    print("="*70)
    print("\n✅ Loan tables + package created and populated in Oracle.")
    print("\nYou can now:")
    print("  1. Process batch: BEGIN pkg_loan_processor.process_batch(10); END;")
    print("  2. Dry run: BEGIN pkg_loan_processor.dry_run(5); END;")
    print("  3. Run migration to SQL Server")
    print("\n" + "="*70)
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
