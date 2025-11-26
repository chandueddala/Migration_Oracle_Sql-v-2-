# Oracle PACKAGE: PKG_LOAN_PROCESSOR

**Source**: Oracle Database  
**Captured**: 2025-11-25 20:21:18  

## Source Code

```sql
PACKAGE BODY pkg_loan_processor IS

  ---------------------------------------------------------------------------
  -- Autonomous audit log writer
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
  EXCEPTION WHEN OTHERS THEN
    NULL;
  END audit_write;

  ---------------------------------------------------------------------------
  -- Fake credit logic
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
  -- EMI formula
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
    IF p_principal IS NULL OR p_principal <= 0 THEN
      RAISE_APPLICATION_ERROR(-20009, 'Principal must be positive');
    END IF;

    IF l_n IS NULL OR l_n <= 0 THEN
      RAISE_APPLICATION_ERROR(-20009, 'Term must be positive');
    END IF;

    IF p_annual_rate IS NULL OR p_annual_rate = 0 THEN
      RETURN ROUND(p_principal / l_n, 2);
    END IF;

    l_r := p_annual_rate / 12 / 100;
    l_payment := p_principal * (l_r / (1 - POWER(1 + l_r, -l_n)));
    RETURN ROUND(l_payment, 2);
  END calc_monthly_payment;

  ---------------------------------------------------------------------------
  -- Build amortization schedule
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
  -- Parse JSON payload
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
    l_start VARCHAR2(20);
  BEGIN
    SELECT external_app_id,
           customer_id,
           principal,
           start_date,
           annual_rate,
           term_months
      INTO p_external_app_id,
           p_customer_id,
           p_principal,
           l_start,
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
           );

    p_start_date := TO_DATE(l_start, 'YYYY-MM-DD');

    IF p_customer_id IS NULL OR p_principal IS NULL OR p_term IS NULL THEN
      RAISE_APPLICATION_ERROR(-20010, 'Missing required JSON fields');
    END IF;
  EXCEPTION
    WHEN NO_DATA_FOUND THEN
      RAISE_APPLICATION_ERROR(-20011, 'Invalid JSON payload');
  END parse_payload;

  ---------------------------------------------------------------------------
  -- Process a single staging row
  ---------------------------------------------------------------------------
  PROCEDURE process_single(
    p_stg_id  IN NUMBER,
    p_payload IN CLOB
  ) IS
    l_app_id   VARCHAR2(100);
    l_cust     NUMBER;
    l_prin     NUMBER;
    l_rate     NUMBER;
    l_term     NUMBER;
    l_start    DATE;
    l_result   VARCHAR2(20);
    l_loan_id  NUMBER;
  BEGIN
    parse_payload(p_payload, l_app_id, l_cust, l_prin, l_rate, l_term, l_start);

    l_result := perform_credit_check(l_cust, p_payload);

    IF l_result = 'FAIL' THEN
      audit_write(p_stg_id, 'REJECTED', 'Credit failure');
      RETURN;
    ELSIF l_result = 'REVIEW' THEN
      audit_write(p_stg_id, 'MANUAL_REVIEW', 'Requires manual review');
      RETURN;
    END IF;

    BEGIN
      SELECT loan_id INTO l_loan_id FROM loans WHERE external_app_id = l_app_id;
    EXCEPTION WHEN NO_DATA_FOUND THEN
      l_loan_id := NULL;
    END;

    IF l_loan_id IS NULL THEN
      l_loan_id := loan_seq.NEXTVAL;
      INSERT INTO loans(
        loan_id, external_app_id, customer_id, principal,
        annual_rate, term_months, start_date,
        status, outstanding_balance, created_on
      ) VALUES (
        l_loan_id, l_app_id, l_cust, l_prin,
        l_rate, l_term, l_start,
        'ACTIVE', l_prin, SYSTIMESTAMP
      );
    ELSE
      UPDATE loans
         SET principal           = l_prin,
             annual_rate         = l_rate,
             term_months         = l_term,
             start_date          = l_start,
             outstanding_balance = l_prin,
             status              = 'ACTIVE'
       WHERE loan_id = l_loan_id;
    END IF;

    DELETE FROM loan_schedule WHERE loan_id = l_loan_id;

    create_schedule(l_loan_id, l_prin, l_rate, l_term, l_start);

    audit_write(p_stg_id, 'APPROVED', 'loan_id=' || l_loan_id);
  EXCEPTION WHEN OTHERS THEN
    audit_write(p_stg_id, 'ERROR', SQLERRM);
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

    l_count NUMBER := 0;
  BEGIN
    FOR r IN c_stg LOOP
      BEGIN
        SAVEPOINT sp1;

        process_single(r.stg_id, r.payload);

        DELETE FROM stg_loan_apps WHERE stg_id = r.stg_id;

        l_count := l_count + 1;

        IF MOD(l_count, 20) = 0 THEN
          COMMIT;
        END IF;

      EXCEPTION WHEN OTHERS THEN
        ROLLBACK TO sp1;
        audit_write(r.stg_id, 'ERR_PER_ROW', SQLERRM);
      END;
    END LOOP;

    COMMIT;
  END process_batch;

  ---------------------------------------------------------------------------
  -- Dry run
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
          a VARCHAR2(100);
          b NUMBER;
          c NUMBER;
          d NUMBER;
          e NUMBER;
          f DATE;
        BEGIN
          parse_payload(r.payload, a, b, c, d, e, f);
          DBMS_OUTPUT.PUT_LINE('DRY_RUN OK stg_id=' || r.stg_id);
        END;
      EXCEPTION
        WHEN OTHERS THEN
          DBMS_OUTPUT.PUT_LINE('DRY_RUN ERR stg_id=' || r.stg_id || ' ' || SQLERRM);
      END;
    END LOOP;
  END dry_run;

END pkg_loan_processor;PACKAGE pkg_loan_processor IS
  PROCEDURE process_batch(p_batch_size IN PLS_INTEGER := 50);
  PROCEDURE dry_run(p_batch_size IN PLS_INTEGER := 20);
END pkg_loan_processor;
```
