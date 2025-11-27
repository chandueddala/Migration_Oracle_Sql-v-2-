# SQL Server PACKAGE: PKG_LOAN_PROCESSOR_audit_write

**Source**: SQL Server (Converted)  
**Captured**: 2025-11-27 02:12:23  

## Metadata

- **original_package**: PKG_LOAN_PROCESSOR
- **original_member**: audit_write
- **member_type**: PROCEDURE

## Source Code

```sql
```sql
CREATE PROCEDURE audit_write
    @p_stg_id INT,
    @p_status VARCHAR(255),
    @p_message VARCHAR(MAX)
AS
BEGIN
    SET NOCOUNT ON;
    
    BEGIN TRY
        INSERT INTO loan_audit(audit_id, stg_id, status, message, processed_on)
        VALUES (
            NEXT VALUE FOR audit_seq,
            @p_stg_id,
            @p_status,
            SUBSTRING(@p_message, 1, 4000),
            SYSDATETIME()
        );
        COMMIT;
    END TRY
    BEGIN CATCH
        -- Suppress all errors (equivalent to WHEN OTHERS THEN NULL)
    END CATCH
END
```
```
