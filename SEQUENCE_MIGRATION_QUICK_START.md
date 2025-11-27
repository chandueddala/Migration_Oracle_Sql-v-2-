# Oracle SEQUENCE Migration - Quick Start

## TL;DR

The system **automatically** converts Oracle SEQUENCEs to either:
- **IDENTITY columns** (faster, simpler) - for simple PK triggers
- **SQL Server SEQUENCE objects** - for complex usage

## Three Migration Strategies

| Strategy | When Used | Result |
|----------|-----------|--------|
| **IDENTITY Column** | Simple PK trigger, single table | Convert to `INT IDENTITY(1,1)`, drop trigger |
| **SQL Server SEQUENCE** | Used in procedures/functions | Create `CREATE SEQUENCE`, convert `.NEXTVAL` |
| **Shared SEQUENCE** | Multiple tables use same sequence | Create `CREATE SEQUENCE`, shared across tables |

## Quick Example

### Oracle Code

```sql
-- Sequence
CREATE SEQUENCE emp_seq START WITH 1;

-- Simple trigger
CREATE TRIGGER trg_emp_pk
BEFORE INSERT ON employees
FOR EACH ROW
BEGIN
  :NEW.employee_id := emp_seq.NEXTVAL;
END;
```

### SQL Server Result

```sql
-- Table with IDENTITY
CREATE TABLE employees (
    employee_id INT IDENTITY(1,1) PRIMARY KEY,
    -- other columns...
);
-- Trigger is dropped (not needed)
```

## How to Use

### 1. Analyze Sequences (Before Migration)

```python
from agents.orchestrator_agent import MigrationOrchestrator

orchestrator = MigrationOrchestrator(oracle_creds, sqlserver_creds, cost_tracker)

# Run analysis
result = orchestrator.analyze_sequences_and_triggers()

# View report
print(result['report'])
```

### 2. Review the Plan

The system generates a detailed report showing:
- Which sequences become IDENTITY columns
- Which sequences become SQL Server SEQUENCEs
- Which sequences need manual review

Example output:
```
📊 Migration Strategy Summary:
   • 5 sequence(s) → IDENTITY column
   • 3 sequence(s) → SQL Server SEQUENCE
   • 1 sequence(s) → Manual review needed
```

### 3. Migrate Tables

The orchestrator automatically:
- Modifies DDL for IDENTITY columns
- Skips simple PK triggers (no longer needed)
- Creates SQL Server SEQUENCEs

```python
# Tables are migrated with IDENTITY columns automatically
orchestrator.migrate_tables()
```

### 4. Migrate Data

For IDENTITY tables, the system:
- Enables `SET IDENTITY_INSERT ON`
- Loads data
- Disables `SET IDENTITY_INSERT OFF`
- Reseeds IDENTITY to `MAX(id) + 1`

```python
orchestrator.migrate_data()
```

## Decision Logic

```
Sequence used only in simple BEFORE INSERT trigger?
├─ YES → IDENTITY Column ✅ (fastest)
└─ NO  → SQL Server SEQUENCE

Sequence shared across multiple tables?
└─ Always SQL Server SEQUENCE
```

## What is a "Simple PK Trigger"?

A trigger is considered "simple" if:
- ✅ Is `BEFORE INSERT`
- ✅ Is `FOR EACH ROW`
- ✅ Only assigns `:NEW.column := sequence.NEXTVAL`
- ✅ No SELECT, UPDATE, DELETE, IF, LOOP statements
- ✅ Less than 15 lines

Example:
```sql
-- SIMPLE (becomes IDENTITY)
CREATE TRIGGER trg_simple
BEFORE INSERT ON table1
FOR EACH ROW
BEGIN
  :NEW.id := seq.NEXTVAL;
END;

-- COMPLEX (becomes SQL Server SEQUENCE)
CREATE TRIGGER trg_complex
BEFORE INSERT ON table1
FOR EACH ROW
BEGIN
  :NEW.id := seq.NEXTVAL;
  :NEW.created_date := SYSDATE;

  IF :NEW.status IS NULL THEN
    :NEW.status := 'ACTIVE';
  END IF;
END;
```

## Files Created

After analysis, the system creates:
- `sequence_migration_plan.txt` - Detailed migration plan
- Modified DDL scripts with IDENTITY columns
- SQL Server SEQUENCE creation scripts

## Testing

Run comprehensive tests:
```bash
python test_sequence_migration.py
```

All 10 tests should pass:
- ✅ Simple PK sequence detection
- ✅ Shared sequence handling
- ✅ Procedure/function usage
- ✅ IDENTITY conversion
- ✅ IDENTITY_INSERT handling
- ✅ Reseed calculation
- ✅ And more...

## Key Benefits

1. **Automatic Detection** - No manual configuration needed
2. **Optimal Performance** - Uses IDENTITY when possible (fastest)
3. **Preserves Semantics** - Uses SEQUENCE when needed (compatible)
4. **Handles Edge Cases** - Shared sequences, complex triggers, cross-schema
5. **Data Migration** - Automatic IDENTITY_INSERT and reseed handling
6. **Comprehensive Reporting** - Know exactly what's happening

## Common Scenarios

### Scenario 1: Simple Auto-Increment

**Oracle:**
```sql
CREATE SEQUENCE id_seq;
CREATE TRIGGER trg BEFORE INSERT ON t FOR EACH ROW
BEGIN :NEW.id := id_seq.NEXTVAL; END;
```

**Result:** IDENTITY column, trigger dropped ✅

### Scenario 2: Sequence in Procedure

**Oracle:**
```sql
CREATE SEQUENCE order_seq;
CREATE PROCEDURE new_order AS
  v_id NUMBER;
BEGIN
  SELECT order_seq.NEXTVAL INTO v_id FROM DUAL;
END;
```

**Result:** SQL Server SEQUENCE created, procedure updated ✅

### Scenario 3: Shared Sequence

**Oracle:**
```sql
CREATE SEQUENCE global_id;
-- Used in triggers for orders AND invoices
```

**Result:** SQL Server SEQUENCE created, shared across tables ✅

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Sequence not detected | Check `.NEXTVAL` syntax in code |
| Wrong strategy chosen | Review trigger complexity |
| IDENTITY_INSERT fails | Check permissions and table state |

## Next Steps

1. Run `analyze_sequences_and_triggers()`
2. Review the generated report
3. Check sequences marked for "manual review"
4. Proceed with migration

For detailed documentation, see [SEQUENCE_MIGRATION_GUIDE.md](SEQUENCE_MIGRATION_GUIDE.md)
