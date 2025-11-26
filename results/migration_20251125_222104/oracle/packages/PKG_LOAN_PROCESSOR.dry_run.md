# Oracle PACKAGE: PKG_LOAN_PROCESSOR.dry_run

**Source**: Oracle Database  
**Captured**: 2025-11-25 22:27:19  

## Metadata

- **package**: PKG_LOAN_PROCESSOR
- **member**: dry_run
- **member_type**: PROCEDURE

## Source Code

```sql
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
```
