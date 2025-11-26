# SQL Server PACKAGE: PKG_LOAN_PROCESSOR_process_single

**Source**: SQL Server (Converted)  
**Captured**: 2025-11-25 21:48:19  

## Metadata

- **original_package**: PKG_LOAN_PROCESSOR
- **original_member**: process_single
- **member_type**: PROCEDURE

## Source Code

```sql
```sql
CREATE PROCEDURE process_single(
    @p_stg_id  INT,
    @p_payload NVARCHAR(MAX)
)
AS
BEGIN
    DECLARE @l_app_id   VARCHAR(100);
    DECLARE @l_cust     INT;
    DECLARE @l_prin     DECIMAL(18,2);
    DECLARE @l_rate     DECIMAL(18,6);
    DECLARE @l_term     INT;
    DECLARE @l_start    DATE;
    DECLARE @l_result   VARCHAR(20);
    DECLARE @l_loan_id  INT;

    BEGIN TRY
        EXEC parse_payload @p_payload, @l_app_id OUTPUT, @l_cust OUTPUT, @l_prin OUTPUT, @l_rate OUTPUT, @l_term OUTPUT, @l_start OUTPUT;

        SET @l_result = dbo.perform_credit_check(@l_cust, @p_payload);

        IF @l_result = 'FAIL'
        BEGIN
            EXEC audit_write @p_stg_id, 'REJECTED', 'Credit failure';
            RETURN;
        END
        ELSE IF @l_result = 'REVIEW'
        BEGIN
            EXEC audit_write @p_stg_id, 'MANUAL_REVIEW', 'Requires manual review';
            RETURN;
        END

        SELECT @l_loan_id = loan_id FROM loans WHERE external_app_id = @l_app_id;

        IF @l_loan_id IS NULL
        BEGIN
            SELECT @l_loan_id = NEXT VALUE FOR loan_seq;
            INSERT INTO loans(
                loan_id, external_app_id, customer_id, principal,
                annual_rate, term_months, start_date,
                status, outstanding_balance, created_on
            ) VALUES (
                @l_loan_id, @l_app_id, @l_cust, @l_prin,
                @l_rate, @l_term, @l_start,
                'ACTIVE', @l_prin, SYSDATETIME()
            );
        END
        ELSE
        BEGIN
            UPDATE loans
               SET principal           = @l_prin,
                   annual_rate         = @l_rate,
                   term_months         = @l_term,
                   start_date          = @l_start,
                   outstanding_balance = @l_prin,
                   status              = 'ACTIVE'
             WHERE loan_id = @l_loan_id;
        END

        DELETE FROM loan_schedule WHERE loan_id = @l_loan_id;

        EXEC create_schedule @l_loan_id, @l_prin, @l_rate, @l_term, @l_start;

        EXEC audit_write @p_stg_id, 'APPROVED', 'loan_id=' + CAST(@l_loan_id AS VARCHAR(20));
    END TRY
    BEGIN CATCH
        EXEC audit_write @p_stg_id, 'ERROR', ERROR_MESSAGE();
        THROW;
    END CATCH
END
```
```
