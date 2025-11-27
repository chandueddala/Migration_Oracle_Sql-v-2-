# Foreign Key Migration - Quick Start Guide

## TL;DR

Foreign keys are now **automatically handled** in two phases:

1. **Phase 1**: Tables created WITHOUT foreign keys (no dependency issues)
2. **Phase 2**: Foreign keys applied AFTER all tables exist (via ALTER TABLE)

**You don't need to do anything special - it just works!**

## What Changed

### Before (Manual FK Handling Required)

```
❌ Table creation fails due to FK dependency order
❌ Circular references cause errors
❌ Self-references are problematic
❌ Must manually create tables in correct order
```

### After (Automatic FK Handling)

```
✅ Tables created in ANY order
✅ Circular references handled automatically
✅ Self-references work correctly
✅ FK script saved for review/replay
✅ Statistics tracked automatically
```

## How To Use

### Option 1: Streamlit Web App (Recommended)

```bash
streamlit run app.py
```

The FK manager is **already integrated**. Just run your migration normally:

1. Enter database credentials
2. Select tables to migrate
3. Click "Start Migration"
4. Watch the magic happen!

**You'll see:**

```
📋 Migrating Tables: 10 objects
  [1/10] DEPARTMENTS
    ✅ Structure migrated
  [2/10] EMPLOYEES
    ✅ Structure migrated
  ...
  [10/10] PROJECTS
    ✅ Structure migrated

🔗 Applying Foreign Key Constraints...
  📊 Found 15 foreign key(s) from 8 table(s)
  💾 Saved FK script: results/migration_20251126_143000/apply_foreign_keys.sql
  ✅ Successfully applied all 15 foreign key(s)
```

### Option 2: Python API

```python
from agents.orchestrator_agent import MigrationOrchestrator
from config.config_enhanced import CostTracker

# Initialize orchestrator (FK manager automatically created)
orchestrator = MigrationOrchestrator(
    oracle_creds=oracle_creds,
    sqlserver_creds=sqlserver_creds,
    cost_tracker=CostTracker()
)

# Migrate tables (FKs automatically stripped and stored)
for table_name in tables:
    result = orchestrator.orchestrate_table_migration(table_name)

# Apply foreign keys (after all tables migrated)
fk_result = orchestrator.apply_all_foreign_keys()

print(f"Applied {fk_result['applied']} of {fk_result['total']} foreign keys")
```

## What You'll Get

### 1. Migration Logs

```
2025-11-26 14:30:00 - INFO - Stripping foreign keys from EMPLOYEES
2025-11-26 14:30:00 - INFO -   Stripped FK: FK_EMP_DEPT -> DEPARTMENTS
2025-11-26 14:30:00 - INFO -   Stripped FK: FK_EMP_MGR -> EMPLOYEES
2025-11-26 14:30:01 - INFO - Foreign keys stripped from EMPLOYEES and stored for later application
...
2025-11-26 14:35:00 - INFO - APPLYING FOREIGN KEY CONSTRAINTS
2025-11-26 14:35:00 - INFO - Generated 15 ALTER TABLE statements
2025-11-26 14:35:01 - INFO - [1/15] Applying FK constraint...
2025-11-26 14:35:01 - INFO -   ✅ Success
...
```

### 2. SQL Script (for review/replay)

**File**: `results/migration_YYYYMMDD_HHMMSS/apply_foreign_keys.sql`

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
ALTER TABLE EMPLOYEES ADD CONSTRAINT FK_EMP_MGR
  FOREIGN KEY (MANAGER_ID)
  REFERENCES EMPLOYEES (EMPLOYEE_ID);

GO

-- ... (13 more)
```

**Use this script to:**
- Review what FKs were applied
- Manually replay if needed
- Share with DBAs for review
- Keep for compliance/audit

### 3. Statistics

```json
{
  "total_tables_with_fks": 8,
  "total_foreign_keys": 15,
  "foreign_keys_stripped": 15,
  "foreign_keys_applied": 13,
  "pending_application": 2
}
```

## What If FK Application Fails?

### Scenario

```
🔗 Applying Foreign Key Constraints...
  📊 Found 15 foreign key(s)
  ⚠️  Applied 13 of 15 foreign key(s)
  ❌ 2 foreign key(s) failed
```

### What To Do

1. **Check the logs** for error details
2. **Review the SQL script**: `apply_foreign_keys.sql`
3. **Common issues**:
   - Referenced table missing (wasn't migrated)
   - Data integrity violation (bad data)
   - Column type mismatch
4. **Fix the issue** (clean data, create missing table, etc.)
5. **Manually run** the failed ALTER TABLE statements from the script

### Example Fix

```sql
-- Failed statement from apply_foreign_keys.sql:
ALTER TABLE ORDERS ADD CONSTRAINT FK_ORDER_CUST
  FOREIGN KEY (CUSTOMER_ID)
  REFERENCES CUSTOMERS (CUSTOMER_ID);

-- Error: Data integrity violation

-- Fix: Find orphaned records
SELECT o.* FROM ORDERS o
LEFT JOIN CUSTOMERS c ON o.CUSTOMER_ID = c.CUSTOMER_ID
WHERE c.CUSTOMER_ID IS NULL;

-- Clean up orphaned records
DELETE FROM ORDERS WHERE CUSTOMER_ID NOT IN (SELECT CUSTOMER_ID FROM CUSTOMERS);

-- Retry FK creation
ALTER TABLE ORDERS ADD CONSTRAINT FK_ORDER_CUST
  FOREIGN KEY (CUSTOMER_ID)
  REFERENCES CUSTOMERS (CUSTOMER_ID);
```

## Testing

Want to verify FK manager works? Run the test suite:

```bash
python test_foreign_key_manager.py
```

**Expected output:**

```
======================================================================
✅ Test 1: Basic FK stripping - PASSED
✅ Test 2: Multiple tables with FKs - PASSED
✅ Test 3: FKs with CASCADE options - PASSED
✅ Test 4: Tables without FKs - PASSED
✅ Test 5: Composite FKs - PASSED

✅ ALL TESTS PASSED
======================================================================
```

## Common Questions

### Q: Do I need to configure anything?

**A**: No! FK manager is automatically initialized and used.

### Q: Can I disable FK stripping?

**A**: Technically yes, but not recommended. Just don't pass `fk_manager` to `ConverterAgent`.

### Q: What if I want to review FKs before applying?

**A**: The SQL script is saved before applying. You can:
1. Review `apply_foreign_keys.sql`
2. Comment out the auto-apply in `app.py`
3. Manually run the script

### Q: Does this work with self-referencing FKs?

**A**: Yes! Self-referencing FKs are applied last to avoid issues.

### Q: What about circular references?

**A**: Yes! That's the whole point. Circular refs are handled automatically.

### Q: What if a table has no FKs?

**A**: No problem. The FK manager only processes tables that have FKs.

### Q: Are composite FKs (multi-column) supported?

**A**: Yes! The manager handles composite FKs correctly.

### Q: What about ON DELETE CASCADE?

**A**: Yes! All FK options are preserved:
- ON DELETE (CASCADE, SET NULL, NO ACTION, SET DEFAULT)
- ON UPDATE (CASCADE, SET NULL, NO ACTION, SET DEFAULT)

## Example End-to-End

```
1. Start migration
   → Orchestrator creates FK manager
   → FK manager passed to converter

2. Migrate DEPARTMENTS table
   → Oracle DDL fetched
   → Converted to T-SQL
   → No FKs (leaf table)
   → Table created
   → Data migrated

3. Migrate EMPLOYEES table
   → Oracle DDL fetched (has FKs)
   → Converted to T-SQL (includes FK_DEPT, FK_MGR)
   → FKs stripped by FK manager
   → FK_DEPT and FK_MGR stored
   → Table created (without FKs)
   → Data migrated

4. ... (migrate remaining tables)

5. All tables migrated
   → FK manager has 15 FKs stored

6. Apply foreign keys
   → 15 ALTER TABLE statements generated
   → Sorted by dependency
   → Saved to apply_foreign_keys.sql
   → Executed one by one
   → 13 applied successfully
   → 2 failed (logged)

7. Migration complete!
   → Tables: ✅
   → Data: ✅
   → FKs: ⚠️ 13/15 (2 need manual review)
```

## Documentation

- **Quick Start**: This document
- **Full Guide**: [FOREIGN_KEY_MIGRATION_GUIDE.md](FOREIGN_KEY_MIGRATION_GUIDE.md)
- **Workflow Diagram**: [FK_WORKFLOW_DIAGRAM.md](FK_WORKFLOW_DIAGRAM.md)
- **Implementation Summary**: [FK_IMPLEMENTATION_SUMMARY.md](FK_IMPLEMENTATION_SUMMARY.md)
- **Test Suite**: [test_foreign_key_manager.py](test_foreign_key_manager.py)

## Key Takeaways

1. **Foreign keys are handled automatically** - just run your migration
2. **Tables can be migrated in any order** - no dependency issues
3. **Circular references work** - that's the whole point
4. **SQL script is saved** - for review/replay/audit
5. **Statistics are tracked** - know what happened
6. **Manual intervention may be needed** - but only for failed FKs

## Need Help?

1. Check the logs in `logs/migration_webapp.log`
2. Review the SQL script in `results/.../apply_foreign_keys.sql`
3. Run the test suite: `python test_foreign_key_manager.py`
4. Read the full guide: [FOREIGN_KEY_MIGRATION_GUIDE.md](FOREIGN_KEY_MIGRATION_GUIDE.md)

## Summary

**Before**: FK dependency order caused migration failures

**After**: Two-phase approach handles FKs automatically

**Result**: More reliable migrations with better error handling

**Action Required**: None - just run your migration as usual! 🎉
