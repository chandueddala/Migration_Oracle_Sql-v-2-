# Oracle VIEW: VW_ACTIVE_LOANS

**Source**: Oracle Database  
**Captured**: 2025-11-25 22:30:00  

## Source Code

```sql
CREATE OR REPLACE FORCE EDITIONABLE VIEW "APP"."VW_ACTIVE_LOANS" ("LOAN_ID", "EXTERNAL_APP_ID", "CUSTOMER_ID", "PRINCIPAL", "ANNUAL_RATE", "TERM_MONTHS", "OUTSTANDING_BALANCE", "START_DATE", "TOTAL_PERIODS", "PAYMENT_COUNT", "TOTAL_PAID") AS 
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
      NVL(s.total_periods, 0) AS total_periods,
      NVL(p.payment_count, 0) AS payment_count,
      NVL(p.total_paid, 0)    AS total_paid
    FROM loans l
    LEFT JOIN sched s ON l.loan_id = s.loan_id
    LEFT JOIN pay   p ON l.loan_id = p.loan_id
    WHERE l.status = 'ACTIVE'
```
