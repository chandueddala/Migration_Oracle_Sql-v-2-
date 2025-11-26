# Oracle FUNCTION: GET_LOAN_STATUS

**Source**: Oracle Database  
**Captured**: 2025-11-25 22:28:51  

## Source Code

```sql
FUNCTION get_loan_status(
      p_loan_id IN NUMBER
    ) RETURN VARCHAR2 IS
      v_status VARCHAR2(30);
    BEGIN
      SELECT status INTO v_status
        FROM loans
       WHERE loan_id = p_loan_id;

      RETURN v_status;
    EXCEPTION
      WHEN NO_DATA_FOUND THEN
        RETURN 'NOT_FOUND';
      WHEN OTHERS THEN
        RETURN 'ERROR';
    END get_loan_status;
```
