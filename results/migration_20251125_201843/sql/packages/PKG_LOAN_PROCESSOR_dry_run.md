# SQL Server PACKAGE: PKG_LOAN_PROCESSOR_dry_run

**Source**: SQL Server (Converted)  
**Captured**: 2025-11-25 20:25:16  

## Metadata

- **original_package**: PKG_LOAN_PROCESSOR
- **original_member**: dry_run
- **member_type**: PROCEDURE

## Source Code

```sql
```sql
CREATE PROCEDURE dry_run(
    @p_batch_size INT = 20
)
AS
BEGIN
    DECLARE @stg_id INT;
    DECLARE @payload NVARCHAR(MAX);
    
    DECLARE loan_cursor CURSOR FOR
    SELECT TOP (@p_batch_size) stg_id, payload
    FROM stg_loan_apps
    ORDER BY created_on;
    
    OPEN loan_cursor;
    
    FETCH NEXT FROM loan_cursor INTO @stg_id, @payload;
    
    WHILE @@FETCH_STATUS = 0
    BEGIN
        BEGIN TRY
            DECLARE @a VARCHAR(100);
            DECLARE @b NUMERIC;
            DECLARE @c NUMERIC;
            DECLARE @d NUMERIC;
            DECLARE @e NUMERIC;
            DECLARE @f DATETIME;
            
            EXEC parse_payload @payload, @a OUTPUT, @b OUTPUT, @c OUTPUT, @d OUTPUT, @e OUTPUT, @f OUTPUT;
            PRINT 'DRY_RUN OK stg_id=' + CAST(@stg_id AS VARCHAR(10));
        END TRY
        BEGIN CATCH
            PRINT 'DRY_RUN ERR stg_id=' + CAST(@stg_id AS VARCHAR(10)) + ' ' + ERROR_MESSAGE();
        END CATCH
        
        FETCH NEXT FROM loan_cursor INTO @stg_id, @payload;
    END
    
    CLOSE loan_cursor;
    DEALLOCATE loan_cursor;
END
```
```
