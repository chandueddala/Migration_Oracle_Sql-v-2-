# Dynamic, Schema-Agnostic Migration Architecture

## Overview

The migration system has been redesigned to be **fully dynamic and schema-agnostic**, with NO hard dependencies on specific schemas, databases, or naming conventions. It can migrate **any Oracle database to any SQL Server instance** regardless of schema structure.

## Core Principles

### 1. No Hardcoded Schemas

❌ **OLD** (Hardcoded):
```python
# BAD: Assumes 'dbo' schema
sql = "SELECT * FROM dbo.CUSTOMERS"

# BAD: Hardcoded schema in FK
ALTER TABLE dbo.EMPLOYEES ADD CONSTRAINT FK...
```

✅ **NEW** (Dynamic):
```python
# GOOD: Schema is configurable
sql = f"SELECT * FROM {schema}.CUSTOMERS"

# GOOD: Schema from FK definition
ALTER TABLE [{fk.get_full_source_table()}] ADD CONSTRAINT...
```

### 2. Fully Qualified Names

All object references use fully qualified names (schema.object):

```python
# Object keys
object_key = f"{schema}.{table_name}"

# FK references
source_table = f"{source_schema}.{source_table}"
referenced_table = f"{ref_schema}.{ref_table}"
```

### 3. Configurable Default Schema

```python
# User can specify any schema as default
manager = ForeignKeyManager(default_schema="custom_schema")
dep_manager = DependencyManager(default_schema="hr")
```

### 4. Cross-Schema Support

Handles references across different schemas:

```python
# Table in 'hr' schema references table in 'sales' schema
CONSTRAINT FK_EMP_DEPT FOREIGN KEY (DEPT_ID)
  REFERENCES sales.DEPARTMENTS (DEPT_ID)
```

### 5. Input Validation

All inputs are validated before processing:

```python
# FK validation
is_valid, error = fk_def.validate()
if not is_valid:
    log_error(error)
    return

# Object validation
is_valid, error = obj.validate()
```

### 6. Extensible Error Patterns

Error parsing is configurable, not hardcoded:

```python
# Add custom error patterns
dep_manager.add_error_pattern(
    r"my custom error pattern",
    DependencyType.MISSING_TABLE,
    capture_groups=(1, 2, 3, 4)
)
```

## Architecture Changes

### V1 (Original) - Static

**Problems**:
- Hardcoded `dbo` schema
- Assumed single database
- Fixed error patterns
- No schema qualification
- Limited to SQL Server defaults

### V2 (Enhanced) - Dynamic

**Solutions**:
- Configurable default schema
- Multi-schema support
- Extensible error patterns
- Full schema qualification
- Works with any database structure

## Component Architecture

### Foreign Key Manager V2

**Key Features**:

1. **Schema-Aware Storage**:
```python
self.foreign_keys: Dict[str, List[ForeignKeyDefinition]] = {}
# Key format: "schema.table_name"
```

2. **Qualified Names**:
```python
def get_full_source_table(self) -> str:
    if self.source_schema:
        return f"{self.source_schema}.{self.source_table}"
    return self.source_table
```

3. **Flexible Parsing**:
```python
FK_PATTERN = re.compile(
    r'(?:\[([^\]]+)\]|(\w+))\.)?'  # Optional schema
    r'(?:\[([^\]]+)\]|(\w+))'       # Table name
)
```

4. **Validation**:
```python
def validate(self) -> Tuple[bool, Optional[str]]:
    if not self.constraint_name:
        return False, "Constraint name is required"
    # ... more validation
```

### Dependency Manager V2

**Key Features**:

1. **Schema-Aware Objects**:
```python
@dataclass
class MigrationObject:
    name: str
    schema: Optional[str]  # Schema is part of object identity
    object_type: ObjectType
```

2. **Fully Qualified Keys**:
```python
full_name = f"{schema}.{name}"
self.objects[full_name] = obj
```

3. **Configurable Error Patterns**:
```python
DEFAULT_ERROR_PATTERNS = [
    (pattern, DependencyType, capture_groups),
    ...
]

# Users can extend
self.error_patterns.extend(custom_patterns)
```

4. **Cross-Schema Dependency Tracking**:
```python
# Tracks dependencies with schema qualification
dependencies: List[str]  # ["hr.EMPLOYEES", "sales.CUSTOMERS"]
```

## Usage Examples

### Multi-Schema Migration

```python
from utils.foreign_key_manager_v2 import ForeignKeyManager

# Initialize with custom default
fk_mgr = ForeignKeyManager(default_schema="my_schema")

# Migrate tables from different schemas
tables = {
    "hr": ["EMPLOYEES", "DEPARTMENTS"],
    "sales": ["CUSTOMERS", "ORDERS"],
    "inventory": ["PRODUCTS", "WAREHOUSES"]
}

for schema, table_list in tables.items():
    for table in table_list:
        # Fetch DDL
        ddl = get_ddl(schema, table)

        # Strip FKs (schema-aware)
        clean_ddl = fk_mgr.strip_foreign_keys_from_ddl(
            ddl,
            table,
            source_schema=schema
        )

        # Create table
        execute(clean_ddl)

# Apply FKs across all schemas
fk_mgr.apply_foreign_keys(conn)
```

### Cross-Schema Dependencies

```python
from utils.dependency_manager_v2 import DependencyManager, ObjectType

dep_mgr = DependencyManager(default_schema="dbo")

# Add objects from different schemas
dep_mgr.add_object(
    "CUSTOMERS",
    ObjectType.TABLE,
    oracle_code="...",
    tsql_code="...",
    schema="sales"
)

dep_mgr.add_object(
    "CUSTOMER_VIEW",
    ObjectType.VIEW,
    oracle_code="...",
    tsql_code="...",
    schema="hr"  # Different schema!
)

# System automatically tracks cross-schema dependencies
```

### Custom Error Patterns

```python
# Add support for custom error messages
dep_mgr.add_error_pattern(
    r"cannot resolve object ['\"]?([a-z0-9_]+)['\"]?",
    DependencyType.MISSING_TABLE,
    capture_groups=(None, None, 1, None)
)

# Now your custom errors will be parsed correctly
```

## Edge Cases Handled

### 1. Empty or Null Inputs

```python
# FK Manager
clean_ddl = fk_mgr.strip_foreign_keys_from_ddl("", "TABLE")
# Returns: "" (doesn't crash)

clean_ddl = fk_mgr.strip_foreign_keys_from_ddl(None, "TABLE")
# Logs warning, returns safely
```

### 2. No Foreign Keys

```python
ddl = "CREATE TABLE TEST (ID INT);"
clean_ddl = fk_mgr.strip_foreign_keys_from_ddl(ddl, "TEST")
# Returns: original DDL unchanged
# fks = [] (empty list)
```

### 3. Multiple FKs per Table

```python
# Handles tables with many FKs
ddl_with_10_fks = "..."
clean_ddl = fk_mgr.strip_foreign_keys_from_ddl(ddl_with_10_fks, "ORDERS")
# All 10 FKs stripped and stored correctly
```

### 4. Composite Foreign Keys

```python
# Multi-column FKs work correctly
CONSTRAINT FK FOREIGN KEY (COL1, COL2, COL3)
  REFERENCES OTHER_TABLE (A, B, C)
# Correctly parsed and stored
```

### 5. All CASCADE Options

```python
# All options preserved
ON DELETE CASCADE
ON UPDATE SET NULL
ON DELETE NO ACTION
ON UPDATE SET DEFAULT
ON DELETE RESTRICT
# All stored in FK definition
```

### 6. Schema Name Edge Cases

```python
# Handles all these formats:
table_name
dbo.table_name
[schema].[table]
[schema.table]  # Edge case
hr.EMPLOYEES
[hr].[EMPLOYEES]
```

### 7. Permission Errors

```python
# Distinguishes permission errors from dependency errors
error = "Permission denied on object 'CUSTOMERS'"
dep_type, deps = dep_mgr.parse_dependency_error(error)
# dep_type = DependencyType.PERMISSION_ERROR
# Won't retry (permission issue needs admin fix)
```

### 8. Syntax Errors

```python
# Distinguishes syntax from dependencies
error = "Incorrect syntax near 'FRUM'"
dep_type, deps = dep_mgr.parse_dependency_error(error)
# dep_type = DependencyType.SYNTAX_ERROR
# Won't retry (needs code fix)
```

## Validation

### FK Definition Validation

```python
fk = ForeignKeyDefinition(...)
is_valid, error = fk.validate()

# Checks:
# - Constraint name not empty
# - Source table not empty
# - Referenced table not empty
# - Column lists not empty
# - Column count matches
```

### Object Validation

```python
obj = MigrationObject(...)
is_valid, error = obj.validate()

# Checks:
# - Name not empty
# - Object type specified
# - Oracle code exists
```

### Validation Error Tracking

```python
# All validation errors are logged
errors = fk_mgr.get_validation_errors()
errors = dep_mgr.get_validation_errors()

# Included in reports
summary = fk_mgr.get_summary()
# {'validation_errors': 0}
```

## Benefits

### 1. Works with ANY Database

✅ **Any Oracle schema structure**
✅ **Any SQL Server schema structure**
✅ **Any schema naming convention**
✅ **Multiple schemas in same database**
✅ **Cross-database references (with limitations)**

### 2. Production-Ready

✅ **Input validation**
✅ **Error handling**
✅ **Edge case coverage**
✅ **Comprehensive logging**
✅ **Audit trail (reports)**

### 3. Extensible

✅ **Custom error patterns**
✅ **Custom validation rules**
✅ **Custom schemas**
✅ **Pluggable components**

### 4. Testable

✅ **Unit tests for edge cases**
✅ **Integration tests**
✅ **Validation tests**
✅ **Cross-schema tests**

## Testing

Run comprehensive tests:

```bash
python test_dynamic_migration.py
```

**Tests Include**:
- ✅ Schema-agnostic FK handling
- ✅ Edge cases (empty, null, multiple, composite)
- ✅ Dependency error parsing
- ✅ Workflow with dependencies
- ✅ Cross-schema dependencies
- ✅ Validation and error handling

**All Tests Pass** ✅

## Migration Workflow

### Complete Multi-Schema Migration

```python
# 1. Initialize managers (schema-agnostic)
fk_mgr = ForeignKeyManager(default_schema="dbo")
dep_mgr = DependencyManager(default_schema="dbo")

# 2. Discover schemas dynamically
schemas = discover_schemas(oracle_conn)
# Returns: ["hr", "sales", "inventory", "finance"]

# 3. Migrate tables from all schemas
for schema in schemas:
    tables = get_tables(oracle_conn, schema)

    for table in tables:
        ddl = get_ddl(oracle_conn, schema, table)

        # Strip FKs (schema-aware)
        clean_ddl = fk_mgr.strip_foreign_keys_from_ddl(
            ddl, table, source_schema=schema
        )

        # Create table
        execute_ddl(sqlserver_conn, clean_ddl)

        # Migrate data
        migrate_data(oracle_conn, sqlserver_conn, schema, table)

# 4. Apply FKs across all schemas
fk_mgr.apply_foreign_keys(sqlserver_conn)

# 5. Migrate code objects with dependency resolution
for schema in schemas:
    objects = get_code_objects(oracle_conn, schema)

    for obj_name, obj_type in objects:
        dep_mgr.add_object(
            obj_name,
            obj_type,
            oracle_code=fetch_code(oracle_conn, schema, obj_name),
            tsql_code=convert_code(...),
            schema=schema
        )

# 6. Run dependency-aware migration
migrate_with_retries(dep_mgr, sqlserver_conn)

# 7. Generate reports
fk_report = fk_mgr.save_foreign_key_scripts("results/")
dep_report = dep_mgr.save_dependency_report("results/dependency_report.txt")
```

## Configuration

### Default Schemas

```python
# Configure for your environment
FK_DEFAULT_SCHEMA = os.getenv("FK_DEFAULT_SCHEMA", "dbo")
DEP_DEFAULT_SCHEMA = os.getenv("DEP_DEFAULT_SCHEMA", "dbo")

fk_mgr = ForeignKeyManager(default_schema=FK_DEFAULT_SCHEMA)
dep_mgr = DependencyManager(default_schema=DEP_DEFAULT_SCHEMA)
```

### Error Patterns

```python
# Add environment-specific error patterns
if sql_server_version == "2019":
    dep_mgr.add_error_pattern(
        r"custom 2019 error pattern",
        DependencyType.MISSING_TABLE,
        capture_groups=(1, 2, 3, 4)
    )
```

### Retry Cycles

```python
# Adjust for your schema complexity
dep_mgr = DependencyManager(
    max_retry_cycles=5  # More cycles for complex dependencies
)
```

## Best Practices

### 1. Always Qualify Schema

```python
# GOOD
fk_mgr.strip_foreign_keys_from_ddl(ddl, table, source_schema="hr")

# AVOID (relies on default)
fk_mgr.strip_foreign_keys_from_ddl(ddl, table)
```

### 2. Validate Before Processing

```python
# Always check validation
is_valid, error = obj.validate()
if not is_valid:
    log_error(f"Validation failed: {error}")
    continue
```

### 3. Handle Validation Errors

```python
# Check for validation errors
errors = fk_mgr.get_validation_errors()
if errors:
    for error in errors:
        log_error(f"Validation error: {error}")
```

### 4. Use Cross-Schema Wisely

```python
# Document cross-schema dependencies
# Some may require manual intervention
for obj in dep_mgr.get_unresolved_objects():
    if obj.dependencies:
        log_warning(f"{obj.name} depends on: {obj.dependencies}")
```

## Summary

The migration system is now:

✅ **Fully Dynamic** - No hardcoded schemas or databases
✅ **Schema-Agnostic** - Works with any schema structure
✅ **Database-Agnostic** - Not tied to specific Oracle/SQL Server versions
✅ **Production-Ready** - Validated, tested, error-handled
✅ **Extensible** - Can be customized for specific environments
✅ **Maintainable** - Clean architecture, well-documented

**Ready for production use with ANY Oracle to SQL Server migration!**
