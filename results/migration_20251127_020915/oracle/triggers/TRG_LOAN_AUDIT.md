# Oracle TRIGGER: TRG_LOAN_AUDIT

**Source**: Oracle Database  
**Captured**: 2025-11-27 02:18:01  

## Source Code

```sql
TRIGGER trg_loan_audit
      AFTER INSERT OR UPDATE OR DELETE ON loans
      FOR EACH ROW
    DECLARE
      v_action  VARCHAR2(10);
      v_message VARCHAR2(200);
    BEGIN
      IF INSERTING THEN
        v_action := 'INSERT';
        v_message := 'New loan created: ' || :NEW.loan_id;
      ELSIF UPDATING THEN
        v_action := 'UPDATE';
        v_message := 'Loan updated: ' || :NEW.loan_id;
      ELSIF DELETING THEN
        v_action := 'DELETE';
        v_message := 'Loan deleted: ' || :OLD.loan_id;
      END IF;

      INSERT INTO loan_audit(audit_id, stg_id, status, message, processed_on)
      VALUES (audit_seq.NEXTVAL, NULL, v_action, v_message, SYSTIMESTAMP);
    END;
```
