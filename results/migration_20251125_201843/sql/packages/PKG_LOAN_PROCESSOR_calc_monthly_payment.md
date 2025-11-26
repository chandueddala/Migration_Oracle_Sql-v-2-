# SQL Server PACKAGE: PKG_LOAN_PROCESSOR_calc_monthly_payment

**Source**: SQL Server (Converted)  
**Captured**: 2025-11-25 20:25:52  

## Metadata

- **original_package**: PKG_LOAN_PROCESSOR
- **original_member**: calc_monthly_payment
- **member_type**: FUNCTION

## Source Code

```sql
```sql
CREATE FUNCTION calc_monthly_payment(
    @p_principal   DECIMAL(18,2),
    @p_annual_rate DECIMAL(10,6),
    @p_term_months INT
) RETURNS DECIMAL(18,2)
AS
BEGIN
    DECLARE @l_r       DECIMAL(18,10);
    DECLARE @l_n       INT = @p_term_months;
    DECLARE @l_payment DECIMAL(18,10);

    IF @p_principal IS NULL OR @p_principal <= 0
    BEGIN
        THROW 50009, 'Principal must be positive', 1;
    END

    IF @l_n IS NULL OR @l_n <= 0
    BEGIN
        THROW 50009, 'Term must be positive', 1;
    END

    IF @p_annual_rate IS NULL OR @p_annual_rate = 0
    BEGIN
        RETURN ROUND(@p_principal / @l_n, 2);
    END

    SET @l_r = @p_annual_rate / 12.0 / 100.0;
    SET @l_payment = @p_principal * (@l_r / (1 - POWER(1 + @l_r, -@l_n)));
    
    RETURN ROUND(@l_payment, 2);
END
```
```
