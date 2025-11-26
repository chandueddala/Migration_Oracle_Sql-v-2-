# SQL Server PACKAGE: PKG_LOAN_PROCESSOR_perform_credit_check

**Source**: SQL Server (Converted)  
**Captured**: 2025-11-25 20:25:34  

## Metadata

- **original_package**: PKG_LOAN_PROCESSOR
- **original_member**: perform_credit_check
- **member_type**: FUNCTION

## Source Code

```sql
```sql
CREATE FUNCTION perform_credit_check(
    @p_customer_id INT,
    @p_payload NVARCHAR(MAX)
) RETURNS VARCHAR(10)
AS
BEGIN
    DECLARE @l_score INT;
    
    SET @l_score = ISNULL(@p_customer_id, 0) % 100;

    IF @l_score > 30
        RETURN 'PASS';
    ELSE IF @l_score > 10
        RETURN 'REVIEW';
    ELSE
        RETURN 'FAIL';

    RETURN NULL;
END
```
```
