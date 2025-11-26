# SQL Server PACKAGE: PKG_LOAN_PROCESSOR_process_batch

**Source**: SQL Server (Converted)  
**Captured**: 2025-11-25 21:49:53  

## Metadata

- **original_package**: PKG_LOAN_PROCESSOR
- **original_member**: process_batch
- **member_type**: PROCEDURE

## Source Code

```sql
```sql
CREATE PROCEDURE process_batch
    @p_batch_size INT = 50
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @stg_id INT;
    DECLARE @payload NVARCHAR(MAX);
    DECLARE @l_count INT = 0;
    DECLARE @error_message NVARCHAR(4000);
    
    DECLARE c_stg CURSOR FOR
        SELECT TOP (@p_batch_size) stg_id, payload
        FROM stg_loan_apps WITH (UPDLOCK, READPAST)
        ORDER BY created_on;
    
    OPEN c_stg;
    
    FETCH NEXT FROM c_stg INTO @stg_id, @payload;
    
    WHILE @@FETCH_STATUS = 0
    BEGIN
        BEGIN TRY
            BEGIN TRANSACTION sp1;
            
            EXEC process_single @stg_id, @payload;
            
            DELETE FROM stg_loan_apps WHERE stg_id = @stg_id;
            
            SET @l_count = @l_count + 1;
            
            IF @l_count % 20 = 0
            BEGIN
                COMMIT TRANSACTION sp1;
            END
            ELSE
            BEGIN
                COMMIT TRANSACTION sp1;
            END
            
        END TRY
        BEGIN CATCH
            IF @@TRANCOUNT > 0
                ROLLBACK TRANSACTION sp1;
            
            SET @error_message = ERROR_MESSAGE();
            EXEC audit_write @stg_id, 'ERR_PER_ROW', @error_message;
        END CATCH
        
        FETCH NEXT FROM c_stg INTO @stg_id, @payload;
    END
    
    CLOSE c_stg;
    DEALLOCATE c_stg;
END
```
```
