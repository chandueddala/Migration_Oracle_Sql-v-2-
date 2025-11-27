# Oracle PACKAGE: PKG_LOAN_PROCESSOR.audit_write

**Source**: Oracle Database  
**Captured**: 2025-11-27 02:12:18  

## Metadata

- **package**: PKG_LOAN_PROCESSOR
- **member**: audit_write
- **member_type**: PROCEDURE

## Source Code

```sql
PROCEDURE audit_write(
    p_stg_id  IN NUMBER,
    p_status  IN VARCHAR2,
    p_message IN VARCHAR2
  ) IS
    PRAGMA AUTONOMOUS_TRANSACTION;
  BEGIN
    INSERT INTO loan_audit(audit_id, stg_id, status, message, processed_on)
    VALUES (
      audit_seq.NEXTVAL,
      p_stg_id,
      p_status,
      SUBSTR(p_message, 1, 4000),
      SYSTIMESTAMP
    );
    COMMIT;
  EXCEPTION WHEN OTHERS THEN
    NULL;
  END audit_write;
```
