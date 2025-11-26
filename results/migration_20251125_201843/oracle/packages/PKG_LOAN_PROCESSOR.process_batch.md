# Oracle PACKAGE: PKG_LOAN_PROCESSOR.process_batch

**Source**: Oracle Database  
**Captured**: 2025-11-25 20:24:43  

## Metadata

- **package**: PKG_LOAN_PROCESSOR
- **member**: process_batch
- **member_type**: PROCEDURE

## Source Code

```sql
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
```
