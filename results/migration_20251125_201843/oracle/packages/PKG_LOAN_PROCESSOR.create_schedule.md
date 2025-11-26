# Oracle PACKAGE: PKG_LOAN_PROCESSOR.create_schedule

**Source**: Oracle Database  
**Captured**: 2025-11-25 20:22:12  

## Metadata

- **package**: PKG_LOAN_PROCESSOR
- **member**: create_schedule
- **member_type**: PROCEDURE

## Source Code

```sql
PROCEDURE create_schedule(
    p_loan_id     IN NUMBER,
    p_principal   IN NUMBER,
    p_annual_rate IN NUMBER,
    p_term        IN NUMBER,
    p_start_date  IN DATE
  ) IS
    TYPE t_sched_rec IS RECORD (
      schedule_id    NUMBER,
      loan_id        NUMBER,
      due_date       DATE,
      period_no      NUMBER,
      principal_amt  NUMBER,
      interest_amt   NUMBER,
      outstanding    NUMBER
    );

    TYPE t_sched_tab IS TABLE OF t_sched_rec INDEX BY PLS_INTEGER;

    v_tab          t_sched_tab;
    v_payment      NUMBER;
    v_outstanding  NUMBER := p_principal;
    v_interest     NUMBER;
    v_principal_pd NUMBER;
    idx            PLS_INTEGER := 0;
  BEGIN
    v_payment := calc_monthly_payment(p_principal, p_annual_rate, p_term);

    FOR i IN 1 .. p_term LOOP
      v_interest     := ROUND(v_outstanding * (p_annual_rate / 12 / 100), 2);
      v_principal_pd := LEAST(ROUND(v_payment - v_interest, 2), v_outstanding);
      v_outstanding  := ROUND(v_outstanding - v_principal_pd, 2);

      idx := idx + 1;

      v_tab(idx).schedule_id   := loan_seq.NEXTVAL;
      v_tab(idx).loan_id       := p_loan_id;
      v_tab(idx).due_date      := ADD_MONTHS(p_start_date, i);
      v_tab(idx).period_no     := i;
      v_tab(idx).principal_amt := v_principal_pd;
      v_tab(idx).interest_amt  := v_interest;
      v_tab(idx).outstanding   := v_outstanding;
    END LOOP;

    IF idx > 0 THEN
      FORALL j IN 1 .. idx
        INSERT INTO loan_schedule(
          schedule_id,
          loan_id,
          due_date,
          period_no,
          principal_amt,
          interest_amt,
          outstanding
        ) VALUES (
          v_tab(j).schedule_id,
          v_tab(j).loan_id,
          v_tab(j).due_date,
          v_tab(j).period_no,
          v_tab(j).principal_amt,
          v_tab(j).interest_amt,
          v_tab(j).outstanding
        );
    END IF;
  END create_schedule;
```
