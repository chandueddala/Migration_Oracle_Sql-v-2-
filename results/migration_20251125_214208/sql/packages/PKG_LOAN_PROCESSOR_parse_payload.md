# SQL Server PACKAGE: PKG_LOAN_PROCESSOR_parse_payload

**Source**: SQL Server (Converted)  
**Captured**: 2025-11-25 21:47:20  

## Metadata

- **original_package**: PKG_LOAN_PROCESSOR
- **original_member**: parse_payload
- **member_type**: PROCEDURE

## Source Code

```sql
```sql
CREATE PROCEDURE parse_payload
    @p_payload NVARCHAR(MAX),
    @p_external_app_id VARCHAR(100) OUTPUT,
    @p_customer_id INT OUTPUT,
    @p_principal DECIMAL(18,2) OUTPUT,
    @p_rate DECIMAL(18,6) OUTPUT,
    @p_term INT OUTPUT,
    @p_start_date DATE OUTPUT
AS
BEGIN
    DECLARE @l_start VARCHAR(20);
    
    BEGIN TRY
        SELECT 
            @p_external_app_id = JSON_VALUE(@p_payload, '$.external_app_id'),
            @p_customer_id = JSON_VALUE(@p_payload, '$.customer_id'),
            @p_principal = JSON_VALUE(@p_payload, '$.principal'),
            @l_start = JSON_VALUE(@p_payload, '$.start_date'),
            @p_rate = JSON_VALUE(@p_payload, '$.annual_rate'),
            @p_term = JSON_VALUE(@p_payload, '$.term_months');

        SET @p_start_date = CONVERT(DATE, @l_start, 23);

        IF @p_customer_id IS NULL OR @p_principal IS NULL OR @p_term IS NULL
        BEGIN
            THROW 50010, 'Missing required JSON fields', 1;
        END;

        IF @p_external_app_id IS NULL AND @p_customer_id IS NULL AND @p_principal IS NULL
        BEGIN
            THROW 50011, 'Invalid JSON payload', 1;
        END;
    END TRY
    BEGIN CATCH
        IF ERROR_NUMBER() >= 50000
            THROW;
        ELSE
            THROW 50011, 'Invalid JSON payload', 1;
    END CATCH;
END;
```
```
