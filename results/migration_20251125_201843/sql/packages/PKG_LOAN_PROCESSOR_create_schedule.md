# SQL Server PACKAGE: PKG_LOAN_PROCESSOR_create_schedule

**Source**: SQL Server (Converted)  
**Captured**: 2025-11-25 20:22:20  

## Metadata

- **original_package**: PKG_LOAN_PROCESSOR
- **original_member**: create_schedule
- **member_type**: PROCEDURE

## Source Code

```sql
```sql
CREATE PROCEDURE create_schedule
    @p_loan_id     INT,
    @p_principal   DECIMAL(18,2),
    @p_annual_rate DECIMAL(8,4),
    @p_term        INT,
    @p_start_date  DATE
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @v_payment      DECIMAL(18,2);
    DECLARE @v_outstanding  DECIMAL(18,2) = @p_principal;
    DECLARE @v_interest     DECIMAL(18,2);
    DECLARE @v_principal_pd DECIMAL(18,2);
    DECLARE @i              INT = 1;
    
    DECLARE @schedule_table TABLE (
        schedule_id    INT,
        loan_id        INT,
        due_date       DATE,
        period_no      INT,
        principal_amt  DECIMAL(18,2),
        interest_amt   DECIMAL(18,2),
        outstanding    DECIMAL(18,2)
    );
    
    BEGIN TRY
        SET @v_payment = dbo.calc_monthly_payment(@p_principal, @p_annual_rate, @p_term);
        
        WHILE @i <= @p_term
        BEGIN
            SET @v_interest = ROUND(@v_outstanding * (@p_annual_rate / 12 / 100), 2);
            SET @v_principal_pd = CASE 
                WHEN ROUND(@v_payment - @v_interest, 2) < @v_outstanding 
                THEN ROUND(@v_payment - @v_interest, 2)
                ELSE @v_outstanding
            END;
            SET @v_outstanding = ROUND(@v_outstanding - @v_principal_pd, 2);
            
            INSERT INTO @schedule_table (
                schedule_id,
                loan_id,
                due_date,
                period_no,
                principal_amt,
                interest_amt,
                outstanding
            ) VALUES (
                NEXT VALUE FOR loan_seq,
                @p_loan_id,
                DATEADD(MONTH, @i, @p_start_date),
                @i,
                @v_principal_pd,
                @v_interest,
                @v_outstanding
            );
            
            SET @i = @i + 1;
        END;
        
        INSERT INTO loan_schedule (
            schedule_id,
            loan_id,
            due_date,
            period_no,
            principal_amt,
            interest_amt,
            outstanding
        )
        SELECT 
            schedule_id,
            loan_id,
            due_date,
            period_no,
            principal_amt,
            interest_amt,
            outstanding
        FROM @schedule_table;
        
    END TRY
    BEGIN CATCH
        THROW;
    END CATCH;
END;
```
```
