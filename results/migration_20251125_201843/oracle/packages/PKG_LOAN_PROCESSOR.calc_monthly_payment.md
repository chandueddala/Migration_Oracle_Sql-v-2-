# Oracle PACKAGE: PKG_LOAN_PROCESSOR.calc_monthly_payment

**Source**: Oracle Database  
**Captured**: 2025-11-25 20:25:47  

## Metadata

- **package**: PKG_LOAN_PROCESSOR
- **member**: calc_monthly_payment
- **member_type**: FUNCTION

## Source Code

```sql
FUNCTION calc_monthly_payment(
    p_principal   IN NUMBER,
    p_annual_rate IN NUMBER,
    p_term_months IN NUMBER
  ) RETURN NUMBER IS
    l_r       NUMBER;
    l_n       NUMBER := p_term_months;
    l_payment NUMBER;
  BEGIN
    IF p_principal IS NULL OR p_principal <= 0 THEN
      RAISE_APPLICATION_ERROR(-20009, 'Principal must be positive');
    END IF;

    IF l_n IS NULL OR l_n <= 0 THEN
      RAISE_APPLICATION_ERROR(-20009, 'Term must be positive');
    END IF;

    IF p_annual_rate IS NULL OR p_annual_rate = 0 THEN
      RETURN ROUND(p_principal / l_n, 2);
    END IF;

    l_r := p_annual_rate / 12 / 100;
    l_payment := p_principal * (l_r / (1 - POWER(1 + l_r, -l_n)));
    RETURN ROUND(l_payment, 2);
  END calc_monthly_payment;
```
