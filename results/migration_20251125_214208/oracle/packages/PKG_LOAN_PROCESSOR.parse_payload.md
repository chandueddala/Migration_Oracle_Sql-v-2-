# Oracle PACKAGE: PKG_LOAN_PROCESSOR.parse_payload

**Source**: Oracle Database  
**Captured**: 2025-11-25 21:47:13  

## Metadata

- **package**: PKG_LOAN_PROCESSOR
- **member**: parse_payload
- **member_type**: PROCEDURE

## Source Code

```sql
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
```
