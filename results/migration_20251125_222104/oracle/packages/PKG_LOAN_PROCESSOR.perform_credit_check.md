# Oracle PACKAGE: PKG_LOAN_PROCESSOR.perform_credit_check

**Source**: Oracle Database  
**Captured**: 2025-11-25 22:27:43  

## Metadata

- **package**: PKG_LOAN_PROCESSOR
- **member**: perform_credit_check
- **member_type**: FUNCTION

## Source Code

```sql
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
```
