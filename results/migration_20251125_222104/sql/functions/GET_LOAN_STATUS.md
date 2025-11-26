# SQL Server FUNCTION: GET_LOAN_STATUS

**Source**: SQL Server (Converted)  
**Captured**: 2025-11-25 22:28:55  

## Source Code

```sql
```sql
CREATE FUNCTION get_loan_status(
    @p_loan_id INT
) 
RETURNS VARCHAR(30)
AS
BEGIN
    DECLARE @v_status VARCHAR(30);
    
    BEGIN TRY
        SELECT @v_status = status
        FROM loans
        WHERE loan_id = @p_loan_id;
        
        IF @v_status IS NULL
            SET @v_status = 'NOT_FOUND';
            
        RETURN @v_status;
    END TRY
    BEGIN CATCH
        RETURN 'ERROR';
    END CATCH
    
    RETURN @v_status;
END
```
```
