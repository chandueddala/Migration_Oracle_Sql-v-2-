# Foreign Key Migration Strategy Guide

## Overview

This migration system implements a **two-phase foreign key strategy** to prevent dependency order issues and circular reference errors during table migration.

## The Problem

When migrating tables with foreign keys in a single pass, you often encounter:

1. **Dependency Order Issues**: Table A references Table B, but B is created after A
2. **Circular References**: Table A references B, and B references A
3. **Self-References**: Table references itself (e.g., EMPLOYEES.MANAGER_ID → EMPLOYEES.EMPLOYEE_ID)
4. **Migration Failures**: Foreign key constraints fail because referenced tables don't exist yet

## The Solution: Two-Phase Migration

### Phase 1: Table Creation (WITHOUT Foreign Keys)

1. **Strip Foreign Keys**: All FOREIGN KEY constraints are removed from CREATE TABLE statements
2. **Store Definitions**: Foreign key definitions are saved in memory
3. **Create Tables**: Tables are created without foreign key constraints
4. **Migrate Data**: Data is migrated into the tables

### Phase 2: Foreign Key Application (AFTER All Tables Exist)

1. **Generate ALTER TABLE Statements**: Stored foreign keys are converted to ALTER TABLE statements
2. **Dependency Sorting**: Foreign keys are sorted to minimize dependency issues:
   - FKs to tables without outgoing FKs first (leaf tables)
   - Other FKs in the middle
   - Self-referencing FKs last
3. **Apply Constraints**: Each ALTER TABLE statement is executed
4. **Save Script**: All FK statements are saved to `apply_foreign_keys.sql` for manual review/replay

## Implementation Details

### Foreign Key Manager

Located in: `utils/foreign_key_manager.py`

**Key Features:**
- Strips FOREIGN KEY constraints from DDL using regex
- Stores constraint definitions with full metadata
- Generates ALTER TABLE statements
- Sorts FKs by dependency to reduce failures
- Tracks statistics (stripped, applied, failed)

**Example Usage:**

```python
from utils.foreign_key_manager import ForeignKeyManager

# Initialize
fk_manager = ForeignKeyManager()

# Phase 1: Strip FKs during table creation
cleaned_ddl = fk_manager.strip_foreign_keys_from_ddl(ddl, "EMPLOYEES")

# Phase 2: Apply FKs after all tables exist
result = fk_manager.apply_foreign_keys(sqlserver_conn)
```

### Integration with Converter Agent

The `ConverterAgent` automatically strips foreign keys during table DDL conversion:

```python
# In agents/converter_agent.py
class ConverterAgent:
    def __init__(self, cost_tracker: CostTracker, fk_manager=None):
        self.fk_manager = fk_manager

    def convert_table_ddl(self, oracle_ddl: str, table_name: str) -> str:
        ddl = convert_table_ddl(oracle_ddl, table_name, self.cost_tracker)

        # Strip foreign keys if FK manager is available
        if self.fk_manager:
            ddl = self.fk_manager.strip_foreign_keys_from_ddl(ddl, table_name)

        return ddl
```

### Integration with Orchestrator

The `MigrationOrchestrator` manages the two-phase process:

```python
# In agents/orchestrator_agent.py
class MigrationOrchestrator:
    def __init__(self, oracle_creds, sqlserver_creds, cost_tracker, migration_options):
        # Initialize FK manager
        self.fk_manager = ForeignKeyManager()

        # Pass to converter
        self.converter = ConverterAgent(cost_tracker, fk_manager=self.fk_manager)

    def apply_all_foreign_keys(self) -> Dict[str, Any]:
        """Apply all stored FKs after table migration"""
        return self.fk_manager.apply_foreign_keys(self.sqlserver_conn)
```

### Integration with Main Migration Workflow

In `app.py`, foreign keys are applied after all tables are created:

```python
# Migrate tables (Phase 1)
for table_name in selected['tables']:
    result = orchestrator.orchestrate_table_migration(table_name)
    # Tables are created WITHOUT foreign keys
    # FKs are stored in fk_manager

# Apply foreign keys (Phase 2)
fk_result = orchestrator.apply_all_foreign_keys()
```

## What Gets Stripped

The FK manager removes all `CONSTRAINT ... FOREIGN KEY` clauses including:

- Inline foreign keys
- Out-of-line foreign keys
- Multi-column (composite) foreign keys
- Foreign keys with `ON DELETE` clauses (CASCADE, SET NULL, NO ACTION, SET DEFAULT)
- Foreign keys with `ON UPDATE` clauses
- Self-referencing foreign keys

## What Gets Preserved

The FK manager preserves:

- Constraint name
- Source table and columns
- Referenced table and columns
- ON DELETE action
- ON UPDATE action

## Generated ALTER TABLE Statements

Example input:

```sql
CREATE TABLE EMPLOYEES (
    EMPLOYEE_ID INT PRIMARY KEY,
    DEPARTMENT_ID INT,
    CONSTRAINT FK_EMP_DEPT FOREIGN KEY (DEPARTMENT_ID)
        REFERENCES DEPARTMENTS (DEPARTMENT_ID) ON DELETE CASCADE
);
```

Gets cleaned to:

```sql
CREATE TABLE EMPLOYEES (
    EMPLOYEE_ID INT PRIMARY KEY,
    DEPARTMENT_ID INT
);
```

And generates:

```sql
ALTER TABLE EMPLOYEES ADD CONSTRAINT FK_EMP_DEPT
  FOREIGN KEY (DEPARTMENT_ID)
  REFERENCES DEPARTMENTS (DEPARTMENT_ID)
  ON DELETE CASCADE;
```

## Output Files

After migration, you'll find:

**`results/migration_YYYYMMDD_HHMMSS/apply_foreign_keys.sql`**

This file contains all ALTER TABLE statements for manual review or replay if needed.

```sql
-- ======================================================================
-- FOREIGN KEY CONSTRAINTS - Apply After All Tables Are Created
-- ======================================================================
-- Generated: 2025-11-26 14:30:00
-- Total Foreign Keys: 15
-- ======================================================================

-- [1/15]
ALTER TABLE EMPLOYEES ADD CONSTRAINT FK_EMP_DEPT
  FOREIGN KEY (DEPARTMENT_ID)
  REFERENCES DEPARTMENTS (DEPARTMENT_ID);

GO

-- [2/15]
ALTER TABLE SALES_ORDERS ADD CONSTRAINT FK_ORDER_CUST
  FOREIGN KEY (CUSTOMER_ID)
  REFERENCES CUSTOMERS (CUSTOMER_ID)
  ON DELETE CASCADE;

GO

...
```

## Dependency Sorting

The FK manager sorts foreign keys to minimize failures:

1. **Leaf Table FKs First**: Foreign keys pointing to tables that have no outgoing FKs
2. **Regular FKs**: Other foreign keys
3. **Self-Referencing FKs Last**: Foreign keys where source = target table

This reduces (but doesn't eliminate) the chance of FK application failures.

## Error Handling

If a foreign key fails to apply:

- The error is logged
- The migration continues with remaining FKs
- Failed FKs are reported in the result summary
- The SQL script is saved for manual review

**Common FK Application Failures:**

1. **Missing Referenced Table**: Referenced table wasn't migrated
2. **Data Integrity Violation**: Existing data violates the FK constraint
3. **Missing Referenced Columns**: Referenced column doesn't exist or has wrong type
4. **Circular Dependencies**: Even with sorting, some circular refs may fail

**Resolution:**

1. Review the saved `apply_foreign_keys.sql` script
2. Fix data integrity issues in SQL Server
3. Manually apply failed FKs using the ALTER TABLE statements

## Statistics and Monitoring

The FK manager tracks:

```python
{
    "total_tables_with_fks": 8,      # Tables that had FKs
    "total_foreign_keys": 15,        # Total FK constraints
    "foreign_keys_stripped": 15,     # FKs removed from DDL
    "foreign_keys_applied": 13,      # FKs successfully applied
    "pending_application": 2         # FKs not yet applied
}
```

## Testing

Run the test suite to verify FK manager functionality:

```bash
python test_foreign_key_manager.py
```

**Tests Include:**

1. Basic FK stripping
2. Multiple tables with FKs
3. FKs with CASCADE options
4. Tables without FKs
5. Composite (multi-column) FKs

## Benefits

✅ **Eliminates Dependency Order Issues**: Tables can be created in any order

✅ **Handles Circular References**: Circular FKs are no problem since tables exist first

✅ **Simplifies Migration Logic**: No need to topologically sort tables

✅ **Provides Audit Trail**: All FK statements saved to SQL file

✅ **Enables Manual Review**: DBAs can review/modify FK statements before applying

✅ **Reduces Migration Failures**: Tables create successfully even with complex FK relationships

## Migration Workflow Example

```
┌─────────────────────────────────────────────────────────────┐
│ PHASE 1: TABLE CREATION                                     │
├─────────────────────────────────────────────────────────────┤
│ 1. Fetch Oracle DDL                                         │
│ 2. Convert to SQL Server (with FKs)                         │
│ 3. Strip FKs → Store in FK Manager                          │
│ 4. Create table (without FKs)                               │
│ 5. Migrate data                                             │
│ 6. Repeat for all tables                                    │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ PHASE 2: FOREIGN KEY APPLICATION                            │
├─────────────────────────────────────────────────────────────┤
│ 1. Retrieve all stored FKs                                  │
│ 2. Sort by dependency (leaf → regular → self-ref)           │
│ 3. Generate ALTER TABLE statements                          │
│ 4. Save to apply_foreign_keys.sql                           │
│ 5. Execute each ALTER TABLE                                 │
│ 6. Report success/failures                                  │
└─────────────────────────────────────────────────────────────┘
```

## Limitations

- **Doesn't Guarantee 100% Success**: Complex circular dependencies may still fail
- **Data Integrity Required**: FKs will fail if data violates referential integrity
- **Manual Intervention May Be Needed**: Some FKs may need to be applied manually
- **Regex-Based Parsing**: May miss non-standard FK syntax (rare)

## Best Practices

1. **Always Review the SQL Script**: Check `apply_foreign_keys.sql` after migration
2. **Fix Data Issues First**: Resolve data integrity violations before applying FKs
3. **Test on Sample Data**: Run migration on test environment first
4. **Monitor FK Application**: Check logs for failed FKs
5. **Keep Audit Trail**: Save the generated SQL scripts for compliance/rollback

## Troubleshooting

### Problem: Foreign Keys Not Being Stripped

**Check:**
- Is FK manager initialized in orchestrator?
- Is FK manager passed to converter agent?
- Are FKs in non-standard format?

### Problem: FK Application Failures

**Check:**
- Do referenced tables exist?
- Does data violate referential integrity?
- Are column names/types correct?
- Check SQL Server error logs

### Problem: Self-Referencing FKs Fail

**Solution:**
- These are applied last
- May need to be applied manually
- Check for data issues (orphaned records)

## Code References

- **FK Manager**: [utils/foreign_key_manager.py](utils/foreign_key_manager.py)
- **Converter Integration**: [agents/converter_agent.py](agents/converter_agent.py#L33-L51)
- **Orchestrator Integration**: [agents/orchestrator_agent.py](agents/orchestrator_agent.py#L82-L91)
- **Main Workflow**: [app.py](app.py#L1315-L1333)
- **Tests**: [test_foreign_key_manager.py](test_foreign_key_manager.py)

## Summary

This two-phase foreign key strategy eliminates one of the most common causes of migration failures: dependency order issues. By separating table creation from foreign key application, the migration system can handle complex database schemas with circular references, self-references, and arbitrary dependency graphs.

The trade-off is that foreign key application happens in a separate phase and may require manual intervention for complex cases, but this is far preferable to migration failures during table creation.
