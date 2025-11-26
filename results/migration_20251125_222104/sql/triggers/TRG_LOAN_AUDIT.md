# SQL Server TRIGGER: TRG_LOAN_AUDIT

**Source**: SQL Server (Converted)  
**Captured**: 2025-11-25 22:29:40  

## Source Code

```sql
```sql
CREATE TRIGGER trg_loan_audit
ON loans
AFTER INSERT, UPDATE, DELETE
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @v_action NVARCHAR(10);
    DECLARE @v_message NVARCHAR(200);
    
    BEGIN TRY
        -- Handle INSERT
        IF EXISTS (SELECT 1 FROM inserted) AND NOT EXISTS (SELECT 1 FROM deleted)
        BEGIN
            INSERT INTO loan_audit(audit_id, stg_id, status, message, processed_on)
            SELECT 
                NEXT VALUE FOR audit_seq,
                NULL,
                'INSERT',
                'New loan created: ' + CAST(i.loan_id AS NVARCHAR(50)),
                SYSDATETIME()
            FROM inserted i;
        END
        
        -- Handle UPDATE
        ELSE IF EXISTS (SELECT 1 FROM inserted) AND EXISTS (SELECT 1 FROM deleted)
        BEGIN
            INSERT INTO loan_audit(audit_id, stg_id, status, message, processed_on)
            SELECT 
                NEXT VALUE FOR audit_seq,
                NULL,
                'UPDATE',
                'Loan updated: ' + CAST(i.loan_id AS NVARCHAR(50)),
                SYSDATETIME()
            FROM inserted i;
        END
        
        -- Handle DELETE
        ELSE IF NOT EXISTS (SELECT 1 FROM inserted) AND EXISTS (SELECT 1 FROM deleted)
        BEGIN
            INSERT INTO loan_audit(audit_id, stg_id, status, message, processed_on)
            SELECT 
                NEXT VALUE FOR audit_seq,
                NULL,
                'DELETE',
                'Loan deleted: ' + CAST(d.loan_id AS NVARCHAR(50)),
                SYSDATETIME()
            FROM deleted d;
        END
        
    END TRY
    BEGIN CATCH
        -- Handle errors if needed
        THROW;
    END CATCH
END;
```
```
