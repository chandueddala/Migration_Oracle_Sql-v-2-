# Oracle SEQUENCE Migration Guide

## Overview

This guide explains the intelligent Oracle SEQUENCE migration system that automatically determines the optimal migration strategy for each sequence based on its usage patterns.

## Migration Strategies

The system supports three migration strategies:

### 1. IDENTITY Column Conversion

**When Used:**
- Sequence is used ONLY in a simple BEFORE INSERT trigger for primary key generation
- Trigger has no complex logic (no SELECT, UPDATE, DELETE, loops, or conditions)
- Sequence is associated with a single table

**Benefits:**
- Native SQL Server IDENTITY columns are more performant
- No trigger needed - SQL Server auto-generates values
- Simpler architecture

**Example:**
```sql
-- Oracle
CREATE SEQUENCE emp_seq START WITH 1;

CREATE TRIGGER trg_emp_pk
BEFORE INSERT ON employees
FOR EACH ROW
BEGIN
  :NEW.employee_id := emp_seq.NEXTVAL;
END;

-- Migrated to SQL Server
CREATE TABLE employees (
    employee_id INT IDENTITY(1,1) PRIMARY KEY,
    -- other columns...
);
-- Trigger is dropped (not needed)
```

### 2. SQL Server SEQUENCE Object

**When Used:**
- Sequence is used in procedures, functions, or views
- Sequence has complex usage patterns
- Single sequence used for non-PK purposes

**Benefits:**
- Maintains Oracle-like behavior
- Can be used across multiple contexts
- Supports NEXT VALUE FOR syntax

**Example:**
```sql
-- Oracle
CREATE SEQUENCE order_num_seq START WITH 1000;

CREATE PROCEDURE generate_order_number AS
BEGIN
  SELECT order_num_seq.NEXTVAL INTO v_order_num FROM DUAL;
  -- ...
END;

-- Migrated to SQL Server
CREATE SEQUENCE dbo.order_num_seq
  START WITH 1001
  INCREMENT BY 1;

CREATE PROCEDURE generate_order_number AS
BEGIN
  DECLARE @order_num INT = NEXT VALUE FOR dbo.order_num_seq;
  -- ...
END;
```

### 3. Shared SEQUENCE

**When Used:**
- Single sequence is shared across multiple tables
- Used for generating business-wide unique IDs

**Benefits:**
- Maintains cross-table uniqueness
- Preserves Oracle semantics

**Example:**
```sql
-- Oracle
CREATE SEQUENCE shared_seq START WITH 1;

-- Used in multiple triggers
CREATE TRIGGER trg_orders_pk
BEFORE INSERT ON orders
FOR EACH ROW
BEGIN
  :NEW.order_id := shared_seq.NEXTVAL;
END;

CREATE TRIGGER trg_invoices_pk
BEFORE INSERT ON invoices
FOR EACH ROW
BEGIN
  :NEW.invoice_id := shared_seq.NEXTVAL;
END;

-- Migrated to SQL Server
CREATE SEQUENCE dbo.shared_seq START WITH 1;

-- Convert to default constraints or computed columns
ALTER TABLE orders ADD CONSTRAINT DF_orders_id
  DEFAULT (NEXT VALUE FOR dbo.shared_seq) FOR order_id;
```

## Decision Tree

```
Is sequence used only in a simple BEFORE INSERT trigger for PK?
├─ YES
│  └─ Is it for a single table?
│     ├─ YES → IDENTITY Column
│     └─ NO  → Shared SEQUENCE
└─ NO
   └─ Is sequence used in procedures/functions/queries?
      ├─ YES → SQL Server SEQUENCE
      └─ NO  → Manual Review
```

## Implementation Components

### 1. Sequence Analyzer (`utils/sequence_analyzer.py`)

The core analysis engine that:
- Scans all PL/SQL code for `.NEXTVAL` and `.CURRVAL` references
- Tracks sequence usage across triggers, procedures, functions, views
- Determines if triggers are "simple PK triggers" vs complex
- Generates migration plans for each sequence

**Key Methods:**
```python
analyzer = SequenceAnalyzer(default_schema="dbo")

# Register sequences
analyzer.register_sequence("emp_seq", "hr", current_value=100)

# Analyze trigger
analyzer.analyze_trigger("trg_emp_pk", trigger_code, "employees", "hr")

# Generate migration plan
plan = analyzer.generate_migration_plan()
```

### 2. Identity Converter (`utils/identity_converter.py`)

Handles IDENTITY column conversions:
- Modifies DDL to add `IDENTITY(start, increment)` to columns
- Generates `SET IDENTITY_INSERT ON/OFF` statements for data migration
- Calculates reseed values based on MAX(id) after data load
- Tracks which tables have IDENTITY columns

**Key Methods:**
```python
converter = IdentityConverter()

# Convert column to IDENTITY
modified_ddl = converter.convert_column_to_identity(
    ddl, "employees", "employee_id", start_value=1, increment=1
)

# Generate data migration script
script = converter.generate_data_migration_script(
    "employees", "employee_id", schema="hr"
)
```

### 3. Orchestrator Integration

The orchestrator now includes:

```python
# In __init__
self.sequence_analyzer = SequenceAnalyzer(default_schema="dbo")
self.identity_converter = IdentityConverter()

# New method
result = orchestrator.analyze_sequences_and_triggers()
```

## Migration Workflow

### Phase 1: Analysis (Before Migration)

1. **Discover Sequences**
   ```python
   sequences = oracle_conn.list_sequences()
   ```

2. **Scan All Code**
   - Triggers: Look for BEFORE INSERT patterns
   - Procedures: Detect NEXTVAL/CURRVAL usage
   - Functions: Detect NEXTVAL/CURRVAL usage
   - Views: Detect NEXTVAL/CURRVAL usage

3. **Generate Migration Plan**
   ```python
   plan = analyzer.generate_migration_plan()
   report = analyzer.generate_migration_report()
   ```

### Phase 2: Table Migration (With Modifications)

For sequences designated as IDENTITY:

1. **Modify Table DDL**
   ```python
   if sequence_plan['strategy'] == 'identity_column':
       table_ddl = identity_converter.convert_column_to_identity(
           table_ddl, table_name, column_name, start_value
       )
   ```

2. **Skip Trigger Migration**
   - Simple PK triggers are NOT migrated
   - They're documented as "dropped (replaced by IDENTITY)"

### Phase 3: Data Migration

For IDENTITY tables:

```sql
-- Enable IDENTITY_INSERT
SET IDENTITY_INSERT [schema.table] ON;

-- Load data
INSERT INTO [schema.table] (id, col1, col2)
SELECT id, col1, col2 FROM oracle_source;

-- Disable IDENTITY_INSERT
SET IDENTITY_INSERT [schema.table] OFF;

-- Reseed IDENTITY
DECLARE @MaxID INT = (SELECT MAX(id) FROM [schema.table]);
DBCC CHECKIDENT ('[schema.table]', RESEED, @MaxID + 1);
```

### Phase 4: Sequence Object Creation

For sequences designated as SQL Server SEQUENCE:

```sql
CREATE SEQUENCE [schema.sequence_name]
  START WITH <current_value + 1>
  INCREMENT BY 1
  MINVALUE 1
  NO MAXVALUE
  CACHE 50;
```

### Phase 5: Code Object Migration

1. **Procedures/Functions**
   - Convert `SEQ.NEXTVAL` to `NEXT VALUE FOR schema.SEQ`
   - Convert `SEQ.CURRVAL` to use variables (requires state management)

2. **Complex Triggers**
   - Migrate as stored procedures
   - Convert sequence references

## Testing

Comprehensive test suite: `test_sequence_migration.py`

**Test Coverage:**
- ✅ Simple PK trigger detection
- ✅ Shared sequence handling
- ✅ Procedure/function sequence usage
- ✅ IDENTITY column conversion
- ✅ IDENTITY_INSERT statement generation
- ✅ Reseed calculation
- ✅ Data migration script generation
- ✅ Trigger complexity analysis
- ✅ Cross-schema sequences
- ✅ Migration report generation

**Running Tests:**
```bash
python test_sequence_migration.py
```

## Usage Example

```python
from agents.orchestrator_agent import MigrationOrchestrator

# Initialize orchestrator
orchestrator = MigrationOrchestrator(
    oracle_creds, sqlserver_creds, cost_tracker
)

# Analyze sequences BEFORE migrating tables
result = orchestrator.analyze_sequences_and_triggers()

# Review the plan
print(result['report'])

# Migrate tables (DDL will be modified for IDENTITY columns)
orchestrator.migrate_tables()

# Migrate data (with IDENTITY_INSERT handling)
orchestrator.migrate_data()

# Create SQL Server SEQUENCE objects
orchestrator.create_sequences()

# Migrate code objects (with sequence reference conversion)
orchestrator.migrate_code_objects()
```

## Migration Report

The system generates a comprehensive report:

```
================================================================================
ORACLE SEQUENCE MIGRATION PLAN
================================================================================

SUMMARY BY STRATEGY:
  IDENTITY_COLUMN: 5 sequence(s)
  SQL_SERVER_SEQUENCE: 3 sequence(s)
  SHARED_SEQUENCE: 1 sequence(s)
  MANUAL_REVIEW: 1 sequence(s)

================================================================================
STRATEGY: IDENTITY_COLUMN
================================================================================

Sequence: hr.emp_seq
  Current Value: 100
  Usage:
    Total Usages: 1
    NEXTVAL: 1, CURRVAL: 0
    Associated Tables: 1
  Tables: hr.employees
  PK Columns:
    hr.employees.employee_id
  Migration SQL:
    -- Convert employee_id to IDENTITY column
    ALTER TABLE [hr.employees]
      ALTER COLUMN [employee_id] INT IDENTITY(1,1) NOT NULL;

    -- Drop Oracle-style trigger (no longer needed with IDENTITY)
    DROP TRIGGER IF EXISTS [hr.trg_emp_pk];

... (more sequences)
```

## Edge Cases Handled

1. **CURRVAL References**
   - Detected but require manual review
   - Cannot be directly converted (needs state tracking)

2. **Sequences with No Usage**
   - Flagged for manual review
   - May be referenced in ad-hoc queries

3. **Complex Triggers**
   - Triggers with business logic are migrated as SQL Server SEQUENCE
   - Not converted to IDENTITY

4. **Cross-Schema References**
   - Properly qualified: `schema.sequence_name`
   - Handles both `[schema].[sequence]` and `schema.sequence` syntax

5. **Schema-Qualified Sequence Names**
   - Handles `hr.emp_seq.NEXTVAL`
   - Handles `emp_seq.NEXTVAL` (uses default schema)

## Performance Considerations

### IDENTITY Columns (Best Performance)
- Fastest option
- Native SQL Server optimization
- Auto-generates values without overhead

### SQL Server SEQUENCE Objects
- Slight overhead compared to IDENTITY
- More flexible for complex scenarios
- Supports caching for better performance

### Recommendation
- Prefer IDENTITY whenever possible
- Use SEQUENCE only when necessary (procedures, shared usage)

## Troubleshooting

### Issue: Sequence not detected in trigger

**Solution:** Check that:
- Trigger uses `.NEXTVAL` syntax
- Sequence name matches exactly
- Schema qualification is correct

### Issue: Wrong strategy chosen

**Solution:** Review the trigger complexity:
- Are there SELECT/UPDATE/DELETE statements?
- Is there conditional logic?
- Is it used by multiple tables?

### Issue: IDENTITY_INSERT fails

**Solution:**
- Ensure table has no data before migration
- Check that IDENTITY column is correctly defined
- Verify connection has appropriate permissions

## Best Practices

1. **Run Analysis First**
   - Always run `analyze_sequences_and_triggers()` before migration
   - Review the generated report

2. **Review Manual Cases**
   - Sequences marked for manual review need human inspection
   - CURRVAL usage requires special handling

3. **Test with Sample Data**
   - Verify IDENTITY reseeding works correctly
   - Test NEXT VALUE FOR syntax in procedures

4. **Document Decisions**
   - Save the sequence migration plan
   - Include it in migration documentation

## Summary

The intelligent sequence migration system:

✅ **Automatically determines optimal strategy** for each sequence
✅ **Converts to IDENTITY** when appropriate for best performance
✅ **Creates SQL Server SEQUENCE** when needed for compatibility
✅ **Handles shared sequences** across multiple tables
✅ **Manages IDENTITY_INSERT** for data migration
✅ **Calculates reseed values** automatically
✅ **Generates comprehensive reports** for review
✅ **Fully tested** with 10 comprehensive test cases
✅ **Production-ready** and integrated with orchestrator

This ensures Oracle sequences are migrated intelligently, preserving functionality while optimizing for SQL Server's native capabilities.
