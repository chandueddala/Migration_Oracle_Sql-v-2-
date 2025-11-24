# Automatic Migration Guide - ALL Objects

## Overview

The migration tool supports **TWO modes**:

1. **Interactive Mode** (default) - User selects which objects to migrate
2. **Automatic Mode** (NEW) - Automatically migrates ALL objects without user selection

## Automatic Mode Features

### ✅ Processes ALL Object Types Automatically

- **Tables** - Structure + data migration
- **Procedures** - All stored procedures
- **Functions** - All functions
- **Triggers** - All triggers
- **Packages** - Automatically decomposed into individual procedures/functions
- **Views** (optional) - With manual review recommendation
- **Sequences** (optional) - With manual review recommendation

### ✅ Zero User Interaction Required

The system automatically:
1. Discovers ALL objects in Oracle database
2. Processes each object type sequentially
3. Handles errors gracefully (continues with next object)
4. Generates comprehensive migration report
5. Logs all activities for troubleshooting

## Usage

### Method 1: Migrate Everything (Recommended)

```bash
python migrate_all.py
```

This will:
- ✅ Migrate ALL tables (structure + data)
- ✅ Migrate ALL procedures
- ✅ Migrate ALL functions
- ✅ Migrate ALL triggers
- ✅ Migrate ALL packages (auto-decomposed)

### Method 2: Migrate Structures Only (No Data)

```bash
python migrate_all.py --no-data
```

This will migrate all table structures and code objects, but **skip table data**.

### Method 3: Tables Only

```bash
python migrate_all.py --tables-only
```

This will migrate **only tables** (structure + data), skipping all code objects.

### Method 4: Code Objects Only

```bash
python migrate_all.py --code-only
```

This will migrate **only code objects** (procedures, functions, triggers, packages), skipping tables.

### Method 5: Selective Migration

```bash
# Exclude specific object types
python migrate_all.py --no-packages
python migrate_all.py --no-triggers
python migrate_all.py --no-procedures --no-functions

# Include optional objects
python migrate_all.py --include-views
python migrate_all.py --include-sequences
```

## Comparison: Interactive vs Automatic

| Feature | Interactive Mode | Automatic Mode |
|---------|-----------------|----------------|
| **Entry Point** | `python Sql_Server/check.py` | `python migrate_all.py` |
| **User Selection** | Yes - select specific objects | No - processes ALL objects |
| **Best For** | Selective migration, testing | Complete database migration |
| **Error Handling** | Stops on critical errors | Continues with next object |
| **Report** | Summary at end | Comprehensive JSON report |
| **Time Required** | Depends on selections | Longer (processes everything) |

## Output Example

```
🤖 AUTOMATIC MIGRATION MODE - ALL OBJECTS
======================================================================

Configuration:
  Tables: ✅
  Data: ✅
  Procedures: ✅
  Functions: ✅
  Triggers: ✅
  Packages: ✅
  Views: ❌
  Sequences: ❌
======================================================================

[STEP 1/6] Collecting credentials...
✅ Database connections established

[STEP 2/6] Initializing orchestrator...
✅ Orchestrator ready

[STEP 3/6] Discovering all database objects...

Discovered:
  📊 Tables: 25
  🔧 Procedures: 45
  🔍 Functions: 30
  ⚡ Triggers: 12
  📦 Packages: 8

📊 Total objects to process: 120

[STEP 4/6] Preparing SQL Server schemas...
✅ Schemas ready

[STEP 5/6] Migrating all objects...
======================================================================

📊 Migrating 25 tables...
  [1/25] CUSTOMERS... ✅
      → Migrating data... ✅ (15,234 rows)
  [2/25] ORDERS... ✅
      → Migrating data... ✅ (45,892 rows)
  [3/25] PRODUCTS... ✅
      → Migrating data... ✅ (1,250 rows)
  ...

🔧 Migrating 45 procedures...
  [1/45] SP_GET_CUSTOMER... ✅
  [2/45] SP_CREATE_ORDER... ✅
  [3/45] SP_UPDATE_INVENTORY... ✅
  ...

🔍 Migrating 30 functions...
  [1/30] FN_CALCULATE_TAX... ✅
  [2/30] FN_GET_DISCOUNT... ✅
  ...

⚡ Migrating 12 triggers...
  [1/12] TRG_AUDIT_CUSTOMERS... ✅
  [2/12] TRG_UPDATE_TIMESTAMP... ✅
  ...

📦 Migrating 8 packages (will be decomposed)...
  [1/8] PKG_CUSTOMER (will decompose)... ✅ (7/7 members)
  [2/8] PKG_INVENTORY (will decompose)... ✅ (12/12 members)
  ...

[STEP 6/6] Generating migration report...

======================================================================
AUTOMATIC MIGRATION SUMMARY
======================================================================

TABLES:
  ✅ Migrated: 25
  ❌ Failed: 0
  📊 Data Rows: 125,450

PROCEDURES:
  ✅ Migrated: 45
  ❌ Failed: 0

FUNCTIONS:
  ✅ Migrated: 30
  ❌ Failed: 0

TRIGGERS:
  ✅ Migrated: 12
  ❌ Failed: 0

PACKAGES:
  ✅ Migrated: 8
  ❌ Failed: 0
  🔧 Decomposed Members: 95

======================================================================
TOTALS:
  ✅ Successfully Migrated: 120
  ❌ Failed: 0
  📈 Success Rate: 100.0%

📄 Report saved: output/automatic_migration_20251124_153045.json

======================================================================
✅ AUTOMATIC MIGRATION COMPLETE
======================================================================
```

## Migration Report

The system generates a detailed JSON report containing:

```json
{
  "mode": "AUTOMATIC",
  "start_time": "2025-11-24T15:30:00",
  "end_time": "2025-11-24T15:45:30",
  "tables": {
    "migrated": 25,
    "failed": 0,
    "skipped": 0,
    "data_rows": 125450
  },
  "procedures": {
    "migrated": 45,
    "failed": 0,
    "skipped": 0
  },
  "functions": {
    "migrated": 30,
    "failed": 0,
    "skipped": 0
  },
  "triggers": {
    "migrated": 12,
    "failed": 0,
    "skipped": 0
  },
  "packages": {
    "migrated": 8,
    "failed": 0,
    "skipped": 0,
    "decomposed_members": 95
  },
  "cost": {
    "total_cost": "$12.45",
    "total_tokens": 250000
  }
}
```

## Error Handling

### Graceful Failure

If an object fails to migrate, the system:
1. ✅ Logs the error with full details
2. ✅ Continues with the next object
3. ✅ Includes failed objects in the summary
4. ✅ Creates detailed error logs in `logs/unresolved/`

### Example with Errors

```
📊 Migrating 25 tables...
  [1/25] CUSTOMERS... ✅
  [2/25] INVALID_TABLE... ❌ Table not found
  [3/25] ORDERS... ✅
  ...

TOTALS:
  ✅ Successfully Migrated: 24
  ❌ Failed: 1
  📈 Success Rate: 96.0%
```

## Performance Considerations

### Large Databases

For databases with many objects:

1. **Tables**: Processed sequentially with data
2. **Code Objects**: Processed sequentially
3. **Packages**: Each package decomposed, members processed individually

**Estimated Time:**
- Small database (< 50 objects): 5-10 minutes
- Medium database (50-200 objects): 15-30 minutes
- Large database (200+ objects): 30-60+ minutes

### Memory Usage

The automatic mode:
- ✅ Processes objects one at a time
- ✅ Closes connections between batches
- ✅ Cleans up temporary data
- ✅ Suitable for large databases

## Best Practices

### 1. Run in Test Environment First

```bash
# Test with structures only (no data)
python migrate_all.py --no-data
```

Verify everything migrates correctly before migrating data.

### 2. Backup Target Database

Before running automatic migration, backup your SQL Server database:

```sql
BACKUP DATABASE [YourDatabase]
TO DISK = 'C:\Backups\before_migration.bak'
```

### 3. Monitor Progress

The automatic mode provides real-time progress:
- Each object shows ✅ (success) or ❌ (failed)
- Data row counts shown for tables
- Package decomposition details shown

### 4. Review Failed Objects

After migration, check `logs/unresolved/` for detailed error logs of any failed objects.

### 5. Re-run for Failed Objects

If some objects fail, you can:
1. Fix the issue (e.g., schema conflicts)
2. Use interactive mode to selectively re-migrate failed objects

## Advanced Usage

### Custom Migration Script

You can programmatically control migration:

```python
from utils.automatic_migration import run_automatic_migration

# Custom configuration
stats = run_automatic_migration(
    migrate_tables=True,
    migrate_data=True,
    migrate_procedures=True,
    migrate_functions=True,
    migrate_triggers=False,  # Skip triggers
    migrate_packages=True,
    migrate_views=False,
    migrate_sequences=False
)

print(f"Migrated {stats['tables']['migrated']} tables")
print(f"Migrated {stats['packages']['decomposed_members']} package members")
```

### Integrate with CI/CD

```bash
#!/bin/bash
# migration.sh - Automated deployment script

# Run automatic migration
python migrate_all.py --no-data

# Check exit code
if [ $? -eq 0 ]; then
    echo "Migration successful"
    # Deploy application
    ./deploy.sh
else
    echo "Migration failed"
    exit 1
fi
```

## Troubleshooting

### Issue: "Connection Failed"

**Solution**: Verify credentials and network connectivity
```bash
# Test connections manually
python -c "from database.oracle_connector import OracleConnector; ..."
```

### Issue: "Object Already Exists"

**Solution**: The object exists in SQL Server. Options:
1. Drop existing objects first
2. Use interactive mode to selectively update
3. Check error logs for conflict details

### Issue: "Package Decomposition Failed"

**Solution**: Package has complex structure
1. Check `logs/unresolved/` for details
2. Use interactive mode to manually select package
3. Review package members individually

## Summary

**Automatic Migration** is the fastest way to migrate an entire Oracle database:

✅ **Zero user interaction** - processes everything automatically
✅ **Handles ALL object types** - tables, procedures, functions, triggers, packages
✅ **Graceful error handling** - continues on failure
✅ **Comprehensive reporting** - detailed JSON report
✅ **Production ready** - tested with large databases

**Command:**
```bash
python migrate_all.py
```

That's it! The system handles the rest automatically.
