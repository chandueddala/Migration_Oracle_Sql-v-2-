# SQL Server VIEW: VW_ACTIVE_LOANS

**Source**: SQL Server (Converted)  
**Captured**: 2025-11-25 22:30:05  

## Source Code

```sql
```sql
CREATE VIEW VW_ACTIVE_LOANS AS
WITH sched AS (
    SELECT
        loan_id,
        COUNT(*) AS total_periods
    FROM loan_schedule
    GROUP BY loan_id
),
pay AS (
    SELECT
        loan_id,
        COUNT(*) AS payment_count,
        SUM(amount) AS total_paid
    FROM loan_payments
    GROUP BY loan_id
)
SELECT
    l.loan_id,
    l.external_app_id,
    l.customer_id,
    l.principal,
    l.annual_rate,
    l.term_months,
    l.outstanding_balance,
    l.start_date,
    ISNULL(s.total_periods, 0) AS total_periods,
    ISNULL(p.payment_count, 0) AS payment_count,
    ISNULL(p.total_paid, 0) AS total_paid
FROM loans l
LEFT JOIN sched s ON l.loan_id = s.loan_id
LEFT JOIN pay p ON l.loan_id = p.loan_id
WHERE l.status = 'ACTIVE';
```
```
