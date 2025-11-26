# Oracle PACKAGE: PKG_LOAN_PROCESSOR.process_single

**Source**: Oracle Database  
**Captured**: 2025-11-25 21:48:10  

## Metadata

- **package**: PKG_LOAN_PROCESSOR
- **member**: process_single
- **member_type**: PROCEDURE

## Source Code

```sql
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
```
