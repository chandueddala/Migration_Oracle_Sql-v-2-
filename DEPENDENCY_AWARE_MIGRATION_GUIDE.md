# Dependency-Aware Migration Guide

## Overview

The migration system now implements **intelligent dependency resolution** for PL/SQL code objects (views, functions, procedures, triggers). Objects with missing dependencies are automatically retried after their dependencies are migrated.

## The Problem

When migrating PL/SQL code objects, dependency issues cause failures:

1. **View references table** that hasn't been migrated yet
2. **Procedure calls function** that doesn't exist yet
3. **Trigger references procedure** that hasn't been created
4. **Circular dependencies** between procedures/functions
5. **Unknown migration order** - which objects to migrate first?

## The Solution: Dependency-Aware Migration

### Multi-Phase Approach

**Phase 1: Preparation**
- Fetch all Oracle code
- Convert to T-SQL (syntax translation)
- Add to dependency manager
- NO validation of referenced objects yet

**Phase 2: Initial Migration** (in dependency order)
- Migrate in order: TABLES → VIEWS → FUNCTIONS → PROCEDURES → TRIGGERS
- Let SQL Server detect missing dependencies
- Skip objects with missing dependencies
- Track which dependencies are missing

**Phase 3: Retry Cycles** (up to 3 cycles)
- Retry skipped objects whose dependencies are now satisfied
- Automatic dependency resolution
- Continue until no more progress or max cycles reached

**Phase 4: Final Report**
- Generate comprehensive report
- List all migrated objects
- List failed objects with reasons
- List skipped objects with missing dependencies

## Key Principles

### 1. Always Migrate in This Order

```
TABLES → VIEWS → FUNCTIONS → PROCEDURES → TRIGGERS
```

This minimizes dependency issues since:
- Views typically reference tables
- Functions are often used by procedures
- Procedures call other procedures/functions
- Triggers reference tables/procedures

### 2. Skip and Retry, Never Drop Logic

- If an object references something missing, **SKIP IT** (don't fail)
- Add to retry queue with dependency information
- Retry after dependencies are satisfied
- Never remove/hide dependencies from code

### 3. Let SQL Server Detect Dependencies

- Don't try to parse code to find dependencies (complex, error-prone)
- Let SQL Server compilation errors tell us what's missing
- Parse error messages to extract missing object names
- Use this information for intelligent retries

### 4. Only Mark Success After SQL Server Compilation

- Object is only "migrated" if SQL Server successfully creates it
- Compilation errors = not migrated
- Retry until it works or max attempts reached

### 5. Produce Final Report

- Show exactly which objects couldn't be migrated
- List their missing dependencies
- Provide actionable information for manual fixes

## Implementation Details

### Dependency Manager

**Location**: `utils/dependency_manager.py`

**Key Components**:

1. **ObjectType Enum** - Migration order priority
```python
class ObjectType(Enum):
    TABLE = 1      # Migrated first
    VIEW = 2
    FUNCTION = 3
    PROCEDURE = 4
    TRIGGER = 5    # Migrated last
```

2. **DependencyType Enum** - Types of errors
```python
class DependencyType(Enum):
    MISSING_TABLE = "missing_table"
    MISSING_VIEW = "missing_view"
    MISSING_FUNCTION = "missing_function"
    MISSING_PROCEDURE = "missing_procedure"
    SYNTAX_ERROR = "syntax_error"
    OTHER_ERROR = "other_error"
```

3. **MigrationObject** - Tracks each object
```python
@dataclass
class MigrationObject:
    name: str
    object_type: ObjectType
    oracle_code: str
    tsql_code: str
    status: str  # pending, success, failed, skipped
    attempt_count: int
    dependencies: List[str]  # Missing dependencies
    dependency_type: DependencyType
    last_error: str
```

4. **DependencyManager** - Orchestrates migration
- Tracks all objects and their status
- Parses SQL Server errors to extract dependencies
- Implements retry logic
- Generates final report

### Error Parsing

The dependency manager intelligently parses SQL Server errors:

```python
# Example errors and parsing:

"Invalid object name 'dbo.CUSTOMERS'"
→ DependencyType.MISSING_TABLE, dependencies: ["CUSTOMERS"]

"Could not find stored procedure 'GET_CUSTOMER_NAME'"
→ DependencyType.MISSING_PROCEDURE, dependencies: ["GET_CUSTOMER_NAME"]

"Incorrect syntax near 'FROM'"
→ DependencyType.SYNTAX_ERROR, dependencies: []
```

### Retry Logic

```python
while dep_manager.needs_retry_cycle():
    dep_manager.start_retry_cycle()

    # Get objects whose dependencies are now satisfied
    retry_candidates = dep_manager.get_retry_candidates()

    for obj in retry_candidates:
        result = migrate_object(obj)
        dep_manager.handle_migration_result(obj.name, success, error_msg)
```

## Usage

### Option 1: Automatic (Recommended)

The dependency manager is integrated into the orchestrator. Use the new method:

```python
from agents.orchestrator_agent import MigrationOrchestrator

orchestrator = MigrationOrchestrator(oracle_creds, sqlserver_creds, cost_tracker)

# Migrate with automatic dependency resolution
objects = {
    "views": ["CUSTOMER_VIEW", "ORDER_VIEW"],
    "functions": ["GET_CUSTOMER_NAME", "CALCULATE_TOTAL"],
    "procedures": ["INSERT_ORDER", "UPDATE_CUSTOMER"],
    "triggers": ["AUDIT_TRIGGER"]
}

results = orchestrator.migrate_with_dependency_resolution(objects)

# Check results
print(f"Success: {results['dependency_stats']['success']}")
print(f"Failed: {results['dependency_stats']['failed']}")
print(f"Skipped: {results['dependency_stats']['skipped']}")

# View final report
print(results['final_report'])
```

### Option 2: Manual Tracking

Track individual objects manually:

```python
from utils.dependency_manager import DependencyManager, ObjectType

dep_manager = DependencyManager(max_retry_cycles=3)

# Add objects
dep_manager.add_object("CUSTOMER_VIEW", ObjectType.VIEW, oracle_code, tsql_code)
dep_manager.add_object("GET_NAME", ObjectType.FUNCTION, oracle_code, tsql_code)

# Get migration order
for obj in dep_manager.get_migration_order():
    success, error = migrate_object(obj)
    dep_manager.handle_migration_result(obj.name, success, error)

# Retry cycles
while dep_manager.needs_retry_cycle():
    dep_manager.start_retry_cycle()

    for obj in dep_manager.get_retry_candidates():
        success, error = migrate_object(obj)
        dep_manager.handle_migration_result(obj.name, success, error)

# Generate report
report = dep_manager.generate_dependency_report()
print(report)
```

## Migration Workflow

```
┌─────────────────────────────────────────────────────────────┐
│ PHASE 1: PREPARATION                                        │
├─────────────────────────────────────────────────────────────┤
│ For each object:                                            │
│   1. Fetch Oracle code                                      │
│   2. Convert to T-SQL (LLM)                                 │
│   3. Add to dependency manager                              │
│   4. NO validation yet                                      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ PHASE 2: INITIAL MIGRATION (Dependency Order)               │
├─────────────────────────────────────────────────────────────┤
│ Migrate in order:                                           │
│   1. VIEWS (reference tables)                               │
│   2. FUNCTIONS (standalone logic)                           │
│   3. PROCEDURES (call functions/procedures)                 │
│   4. TRIGGERS (reference tables/procedures)                 │
│                                                              │
│ For each object:                                            │
│   - Attempt to create in SQL Server                         │
│   - If SUCCESS → Mark as migrated                           │
│   - If MISSING DEPENDENCY → Skip, add to retry queue        │
│   - If SYNTAX ERROR → Mark as failed (need code fix)        │
│   - If OTHER ERROR → Mark as failed                         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ PHASE 3: RETRY CYCLES (Up to 3 cycles)                      │
├─────────────────────────────────────────────────────────────┤
│ Cycle 1:                                                     │
│   - Get skipped objects whose dependencies are satisfied    │
│   - Retry migration                                          │
│   - Track results                                            │
│                                                              │
│ Cycle 2:                                                     │
│   - Retry objects that failed in Cycle 1                    │
│   - More dependencies may now be satisfied                  │
│                                                              │
│ Cycle 3:                                                     │
│   - Final retry attempt                                      │
│   - Remaining failures are permanent                        │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ PHASE 4: FINAL REPORT                                       │
├─────────────────────────────────────────────────────────────┤
│ Generate report with:                                       │
│   - Successfully migrated objects                           │
│   - Failed objects (with reasons)                           │
│   - Skipped objects (with missing dependencies)            │
│   - Statistics (success/failed/skipped counts)             │
│                                                              │
│ Save to: results/migration_XXX/dependency_report.txt        │
└─────────────────────────────────────────────────────────────┘
```

## Example Scenario

### Initial State

```
Objects to migrate:
  VIEW:      CUSTOMER_VIEW (references CUSTOMERS table)
  FUNCTION:  GET_CUSTOMER_NAME (references CUSTOMERS table)
  PROCEDURE: INSERT_ORDER (calls GET_CUSTOMER_NAME function)
  PROCEDURE: PROCESS_ORDERS (calls INSERT_ORDER procedure)

Tables already migrated: CUSTOMERS, ORDERS
```

### Phase 2: Initial Migration

```
[VIEW] CUSTOMER_VIEW
  → Execute CREATE VIEW in SQL Server
  → ✅ SUCCESS (CUSTOMERS table exists)

[FUNCTION] GET_CUSTOMER_NAME
  → Execute CREATE FUNCTION in SQL Server
  → ✅ SUCCESS (CUSTOMERS table exists)

[PROCEDURE] INSERT_ORDER
  → Execute CREATE PROCEDURE in SQL Server
  → ✅ SUCCESS (GET_CUSTOMER_NAME function exists)

[PROCEDURE] PROCESS_ORDERS
  → Execute CREATE PROCEDURE in SQL Server
  → ✅ SUCCESS (INSERT_ORDER procedure exists)
```

**Result**: All objects migrated in Phase 2, no retries needed!

### Example with Dependencies

```
Objects to migrate:
  PROCEDURE: PROC_A (calls PROC_B)
  PROCEDURE: PROC_B (calls PROC_C)
  PROCEDURE: PROC_C (standalone)
```

**Phase 2**: Initial attempt
```
[PROCEDURE] PROC_A
  → ❌ SKIP: Missing procedure 'PROC_B'

[PROCEDURE] PROC_B
  → ❌ SKIP: Missing procedure 'PROC_C'

[PROCEDURE] PROC_C
  → ✅ SUCCESS (no dependencies)
```

**Phase 3 - Cycle 1**:
```
PROC_C now exists, retry PROC_B

[PROCEDURE] PROC_B
  → ✅ SUCCESS (PROC_C exists)
```

**Phase 3 - Cycle 2**:
```
PROC_B now exists, retry PROC_A

[PROCEDURE] PROC_A
  → ✅ SUCCESS (PROC_B exists)
```

**Result**: All procedures migrated after 2 retry cycles!

## Final Report Format

```
================================================================================
DEPENDENCY MIGRATION REPORT
================================================================================

SUMMARY:
  Total Objects:     10
  ✅ Success:        7
  ❌ Failed:         1
  ⏭️  Skipped:        2
  ⏳ Pending:        0
  🔄 Retry Cycles:   2

================================================================================
FAILED OBJECTS:
================================================================================

PROCEDURE: INVALID_PROC
  Attempts:      3
  Error Type:    syntax_error
  Last Error:    Incorrect syntax near 'FRUM'. (Expected 'FROM')

================================================================================
SKIPPED OBJECTS (Unresolved Dependencies):
================================================================================

PROCEDURE: ORPHAN_PROC
  Attempts:      3
  Waiting For:   MISSING_FUNCTION (not in migration list)
  Error Type:    missing_function

VIEW: EXTERNAL_VIEW
  Attempts:      3
  Waiting For:   EXTERNAL_TABLE (not migrated)
  Error Type:    missing_table

================================================================================
SUCCESSFULLY MIGRATED:
================================================================================

VIEWS (2):
  ✅ CUSTOMER_VIEW
  ✅ ORDER_VIEW

FUNCTIONS (2):
  ✅ CALCULATE_TOTAL
  ✅ GET_CUSTOMER_NAME

PROCEDURES (3):
  ✅ INSERT_ORDER
  ✅ PROCESS_ORDERS
  ✅ UPDATE_CUSTOMER

================================================================================
```

## Configuration

### Max Retry Cycles

Control how many retry cycles to attempt:

```python
dep_manager = DependencyManager(max_retry_cycles=3)  # Default: 3
```

### Max Attempts Per Object

Control max attempts for each object:

```python
obj = MigrationObject(name="PROC_A", max_attempts=5)  # Default: 5
```

## Error Handling

### Syntax Errors

**Detected**: `Incorrect syntax near 'FROM'`

**Action**: Mark as FAILED (no retries)

**Reason**: Needs code fix, not a dependency issue

### Missing Objects

**Detected**: `Invalid object name 'dbo.CUSTOMERS'`

**Action**: SKIP for retry (if CUSTOMERS in migration list)

**Action**: Mark as FAILED (if CUSTOMERS not in migration list)

### Other Errors

**Action**: Mark as FAILED after max attempts

## Benefits

✅ **Automatic Dependency Resolution** - No manual ordering needed

✅ **Intelligent Retry Logic** - Only retries when dependencies satisfied

✅ **Clear Error Classification** - Syntax vs dependency vs other errors

✅ **Comprehensive Reporting** - Know exactly what failed and why

✅ **Never Drops Logic** - All code preserved, dependencies tracked

✅ **SQL Server Validation** - Real compilation errors, not guesses

✅ **Circular Dependency Handling** - Retry cycles resolve circular refs

## Limitations

⚠️ **External Dependencies** - Objects referencing external databases will fail

⚠️ **Max Retry Cycles** - After 3 cycles, remaining objects marked as skipped

⚠️ **Syntax Errors** - Require manual code fixes

⚠️ **Cross-Schema References** - May need manual intervention

## Best Practices

1. **Migrate Tables First** - Always complete table migration before code objects

2. **Review Dependency Report** - Check for patterns in failed objects

3. **Fix Syntax Errors First** - These won't resolve with retries

4. **Check External Dependencies** - Identify objects referencing external systems

5. **Use Migration Order** - Respect TABLES→VIEWS→FUNCTIONS→PROCEDURES→TRIGGERS

6. **Increase Retry Cycles** - For complex schemas, consider 4-5 cycles

## Troubleshooting

### Problem: All Objects Skipped

**Cause**: Base dependencies (tables) not migrated

**Solution**: Migrate tables first, then code objects

### Problem: Objects Still Skipped After 3 Cycles

**Cause**: Missing external dependencies

**Solution**: Check dependency report, migrate missing objects manually

### Problem: Syntax Errors

**Cause**: Conversion issues in T-SQL

**Solution**: Review converted code, fix syntax manually

### Problem: Circular Dependencies Not Resolved

**Cause**: SQL Server requires forward declarations

**Solution**: May need to add stub declarations manually

## Code References

- **Dependency Manager**: [utils/dependency_manager.py](utils/dependency_manager.py)
- **Orchestrator Integration**: [agents/orchestrator_agent.py](agents/orchestrator_agent.py#L774-L977)
- **Migration Workflow**: `orchestrator.migrate_with_dependency_resolution()`

## Summary

The dependency-aware migration system eliminates manual dependency tracking and ordering. Objects are automatically retried when their dependencies are satisfied, with comprehensive reporting of any unresolved issues.

**Key Features**:
- Automatic dependency detection via SQL Server errors
- Intelligent retry logic with max 3 cycles
- Proper migration order (TABLES→VIEWS→FUNCTIONS→PROCEDURES→TRIGGERS)
- Never drops code logic
- Comprehensive final report
- Clear error classification

This approach ensures maximum migration success while providing clear actionable information for any remaining manual fixes needed.
