# Foreign Key Migration Workflow Diagram

## Complete Migration Flow with FK Manager

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         MIGRATION START                                  │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    INITIALIZATION                                        │
├─────────────────────────────────────────────────────────────────────────┤
│  • MigrationOrchestrator created                                        │
│  • ForeignKeyManager initialized                                        │
│  • FK Manager passed to ConverterAgent                                  │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    PHASE 1: TABLE MIGRATION                              │
│                    (For Each Table)                                      │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
        ┌─────────────────────────┴─────────────────────────┐
        ▼                                                     ▼
┌─────────────────┐                                  ┌─────────────────┐
│ Table: DEPT     │                                  │ Table: EMPLOYEES │
└─────────────────┘                                  └─────────────────┘
        │                                                     │
        ▼                                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ STEP 1: Fetch Oracle DDL                                                │
├─────────────────────────────────────────────────────────────────────────┤
│  OracleConnector.get_table_ddl(table_name)                             │
│                                                                          │
│  Oracle DDL Example:                                                     │
│  CREATE TABLE EMPLOYEES (                                                │
│    ID INT PRIMARY KEY,                                                   │
│    NAME VARCHAR(50),                                                     │
│    DEPT_ID INT,                                                          │
│    MANAGER_ID INT,                                                       │
│    CONSTRAINT FK_DEPT FOREIGN KEY (DEPT_ID)                             │
│      REFERENCES DEPARTMENTS (DEPT_ID),                                  │
│    CONSTRAINT FK_MGR FOREIGN KEY (MANAGER_ID)                           │
│      REFERENCES EMPLOYEES (ID)                                          │
│  );                                                                      │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ STEP 2: Convert to SQL Server (with LLM)                                │
├─────────────────────────────────────────────────────────────────────────┤
│  ConverterAgent.convert_table_ddl()                                     │
│  → Claude converts Oracle → SQL Server                                  │
│                                                                          │
│  T-SQL DDL (with FKs):                                                   │
│  CREATE TABLE EMPLOYEES (                                                │
│    ID INT PRIMARY KEY,                                                   │
│    NAME NVARCHAR(50),                                                    │
│    DEPT_ID INT,                                                          │
│    MANAGER_ID INT,                                                       │
│    CONSTRAINT FK_DEPT FOREIGN KEY (DEPT_ID)                             │
│      REFERENCES DEPARTMENTS (DEPT_ID),                                  │
│    CONSTRAINT FK_MGR FOREIGN KEY (MANAGER_ID)                           │
│      REFERENCES EMPLOYEES (ID)                                          │
│  );                                                                      │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ STEP 3: Strip Foreign Keys ⭐ NEW                                       │
├─────────────────────────────────────────────────────────────────────────┤
│  ForeignKeyManager.strip_foreign_keys_from_ddl()                        │
│                                                                          │
│  STRIPPED:                           STORED IN FK MANAGER:              │
│  ┌─────────────────────────┐        ┌──────────────────────────────┐   │
│  │ CREATE TABLE EMPLOYEES (│        │ FK_DEPT:                     │   │
│  │   ID INT PRIMARY KEY,   │        │   Source: EMPLOYEES.DEPT_ID  │   │
│  │   NAME NVARCHAR(50),    │        │   Target: DEPARTMENTS.ID     │   │
│  │   DEPT_ID INT,          │        │                              │   │
│  │   MANAGER_ID INT         │        │ FK_MGR:                      │   │
│  │ );                      │        │   Source: EMPLOYEES.MGR_ID   │   │
│  └─────────────────────────┘        │   Target: EMPLOYEES.ID       │   │
│                                      │   (self-reference)           │   │
│  ✅ No FOREIGN KEY constraints!     └──────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ STEP 4: Deploy to SQL Server                                            │
├─────────────────────────────────────────────────────────────────────────┤
│  DebuggerAgent.deploy_with_repair()                                     │
│  → Execute CREATE TABLE (without FKs)                                   │
│                                                                          │
│  ✅ Table created successfully!                                         │
│  ✅ No FK dependency errors!                                            │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ STEP 5: Migrate Data                                                    │
├─────────────────────────────────────────────────────────────────────────┤
│  migrate_table_data(table_name)                                         │
│  → Bulk insert from Oracle to SQL Server                               │
│                                                                          │
│  ✅ Data migrated successfully!                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────┐
                    │  Repeat for all tables  │
                    │  (in ANY order)         │
                    └─────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│               ALL TABLES MIGRATED ✅                                     │
│                                                                          │
│  Tables created:     10/10                                               │
│  Data migrated:      10/10                                               │
│  Foreign keys in:    FK Manager storage                                 │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│               PHASE 2: FOREIGN KEY APPLICATION ⭐ NEW                   │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ STEP 1: Retrieve Stored FKs                                             │
├─────────────────────────────────────────────────────────────────────────┤
│  ForeignKeyManager.get_all_foreign_keys()                               │
│                                                                          │
│  Retrieved: 15 foreign keys from 8 tables                               │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ STEP 2: Sort by Dependency                                              │
├─────────────────────────────────────────────────────────────────────────┤
│  ForeignKeyManager._sort_foreign_keys_by_dependency()                   │
│                                                                          │
│  Order:                                                                  │
│  1. FKs to leaf tables (no outgoing FKs)                                │
│     └─> EMPLOYEES.FK_DEPT → DEPARTMENTS                                │
│  2. Regular FKs                                                          │
│     └─> ORDERS.FK_CUST → CUSTOMERS                                     │
│  3. Self-referencing FKs (last)                                         │
│     └─> EMPLOYEES.FK_MGR → EMPLOYEES                                   │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ STEP 3: Generate ALTER TABLE Statements                                 │
├─────────────────────────────────────────────────────────────────────────┤
│  ForeignKeyManager.generate_alter_table_statements()                    │
│                                                                          │
│  Generated statements:                                                   │
│                                                                          │
│  ALTER TABLE EMPLOYEES ADD CONSTRAINT FK_DEPT                           │
│    FOREIGN KEY (DEPT_ID)                                                │
│    REFERENCES DEPARTMENTS (DEPT_ID);                                    │
│                                                                          │
│  ALTER TABLE EMPLOYEES ADD CONSTRAINT FK_MGR                            │
│    FOREIGN KEY (MANAGER_ID)                                             │
│    REFERENCES EMPLOYEES (ID);                                           │
│                                                                          │
│  ... (13 more)                                                           │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ STEP 4: Save SQL Script                                                 │
├─────────────────────────────────────────────────────────────────────────┤
│  ForeignKeyManager.save_foreign_key_scripts()                           │
│                                                                          │
│  File: results/migration_20251126_143000/apply_foreign_keys.sql        │
│                                                                          │
│  ✅ Script saved for manual review/replay                               │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ STEP 5: Apply Foreign Keys                                              │
├─────────────────────────────────────────────────────────────────────────┤
│  For each ALTER TABLE statement:                                        │
│                                                                          │
│  [1/15] ALTER TABLE EMPLOYEES ADD CONSTRAINT FK_DEPT...                 │
│         ✅ Applied successfully                                          │
│                                                                          │
│  [2/15] ALTER TABLE ORDERS ADD CONSTRAINT FK_CUST...                    │
│         ✅ Applied successfully                                          │
│                                                                          │
│  ...                                                                     │
│                                                                          │
│  [15/15] ALTER TABLE EMPLOYEES ADD CONSTRAINT FK_MGR...                 │
│          ✅ Applied successfully                                         │
│                                                                          │
│  Result:                                                                 │
│    Applied:  15/15                                                       │
│    Failed:   0/15                                                        │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    MIGRATION COMPLETE ✅                                 │
├─────────────────────────────────────────────────────────────────────────┤
│  Tables migrated:        10/10                                          │
│  Data migrated:          10/10                                          │
│  Foreign keys applied:   15/15                                          │
│                                                                          │
│  All referential integrity constraints in place!                        │
└─────────────────────────────────────────────────────────────────────────┘
```

## Error Scenario: FK Application Failure

```
┌─────────────────────────────────────────────────────────────────────────┐
│ STEP 5: Apply Foreign Keys (with error)                                 │
├─────────────────────────────────────────────────────────────────────────┤
│  [1/15] ALTER TABLE EMPLOYEES ADD CONSTRAINT FK_DEPT...                 │
│         ✅ Applied successfully                                          │
│                                                                          │
│  [2/15] ALTER TABLE ORDERS ADD CONSTRAINT FK_CUST...                    │
│         ❌ Failed: Referenced table CUSTOMERS not found                 │
│                                                                          │
│  [3/15] ALTER TABLE SALES ADD CONSTRAINT FK_PROD...                     │
│         ❌ Failed: Data integrity violation                             │
│                                                                          │
│  ... (continue with remaining FKs)                                       │
│                                                                          │
│  Result:                                                                 │
│    Applied:  13/15                                                       │
│    Failed:   2/15                                                        │
│                                                                          │
│  ⚠️ Check apply_foreign_keys.sql for failed statements                  │
│  ⚠️ Review error log for details                                        │
│  ⚠️ Fix issues and rerun failed statements manually                     │
└─────────────────────────────────────────────────────────────────────────┘
```

## Data Flow

```
┌──────────────┐
│ Oracle       │
│ Database     │
└──────┬───────┘
       │
       │ 1. Fetch DDL (with FKs)
       ▼
┌──────────────────────┐
│ ConverterAgent       │
│ (Claude LLM)         │
└──────┬───────────────┘
       │
       │ 2. Convert to T-SQL (with FKs)
       ▼
┌─────────────────────────────────────┐
│ ForeignKeyManager                   │
│ ┌─────────────────────────────────┐ │
│ │ strip_foreign_keys_from_ddl()   │ │
│ └─────────────────────────────────┘ │
└──┬──────────────────────┬───────────┘
   │                      │
   │ 3a. Cleaned DDL      │ 3b. FK Definitions
   │ (no FKs)             │     (stored)
   ▼                      ▼
┌──────────────────┐  ┌──────────────────┐
│ SQL Server       │  │ FK Storage       │
│ (Tables)         │  │ ┌──────────────┐ │
└──────────────────┘  │ │ FK_DEPT      │ │
                      │ │ FK_MGR       │ │
                      │ │ FK_CUST      │ │
                      │ │ ...          │ │
                      │ └──────────────┘ │
                      └──────┬───────────┘
                             │
       ┌─────────────────────┘
       │ 4. After all tables exist
       │
       ▼
┌─────────────────────────────────────┐
│ ForeignKeyManager                   │
│ ┌─────────────────────────────────┐ │
│ │ apply_foreign_keys()            │ │
│ └─────────────────────────────────┘ │
└──────┬──────────────────────────────┘
       │
       │ 5. ALTER TABLE statements
       ▼
┌──────────────────┐
│ SQL Server       │
│ (FKs applied)    │
└──────────────────┘
```

## Component Interaction

```
┌────────────────────────────────────────────────────────────────────┐
│                    MigrationOrchestrator                           │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │ __init__():                                                   │ │
│  │   self.fk_manager = ForeignKeyManager()                      │ │
│  │   self.converter = ConverterAgent(..., fk_manager)           │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                    │
│  orchestrate_table_migration(table):                              │
│    1. oracle_ddl = oracle_conn.get_table_ddl(table)              │
│    2. tsql = converter.convert_table_ddl(oracle_ddl, table)      │
│       └─> FKs stripped here                                       │
│    3. deploy_result = debugger.deploy_with_repair(tsql)          │
│                                                                    │
│  apply_all_foreign_keys():                                        │
│    1. fk_manager.save_foreign_key_scripts(results_dir)           │
│    2. result = fk_manager.apply_foreign_keys(sqlserver_conn)     │
│    3. return result                                               │
└────────────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┴───────────────────┐
          ▼                                       ▼
┌─────────────────────┐              ┌────────────────────────┐
│  ConverterAgent     │              │  ForeignKeyManager     │
│  ┌────────────────┐ │              │  ┌───────────────────┐ │
│  │ fk_manager     │─┼──────────────┼─▶│ foreign_keys: {}  │ │
│  └────────────────┘ │              │  │ stripped_count: 0 │ │
│                     │              │  │ applied_count: 0  │ │
│  convert_table_ddl()│              │  └───────────────────┘ │
│    ddl = LLM(...)   │              │                        │
│    if fk_manager:   │              │  Methods:              │
│      ddl = fk_mgr...│──────────────┼─▶strip_foreign_keys()  │
│    return ddl       │              │  generate_alters()     │
└─────────────────────┘              │  apply_foreign_keys()  │
                                     └────────────────────────┘
```

## Key Points

1. **FK Manager is initialized once** in MigrationOrchestrator
2. **FK Manager is passed** to ConverterAgent
3. **FKs are stripped automatically** during table DDL conversion
4. **FKs are stored** with full metadata in FK Manager
5. **Tables are created** WITHOUT foreign keys
6. **After all tables exist**, FKs are applied as ALTER TABLE statements
7. **SQL script is saved** for manual review/replay
8. **Statistics tracked** throughout the process

## Benefits Visualization

### Without FK Manager (OLD)

```
Table 1 ──FK──> Table 2 ──FK──> Table 3
   │                               ▲
   └───────────FK─────────────────┘

Problem: Must create in order 3 → 2 → 1
         Circular reference fails!
         ❌ Migration fails
```

### With FK Manager (NEW)

```
Phase 1: Create All Tables (no FKs)
  Table 1 ✅
  Table 2 ✅
  Table 3 ✅

Phase 2: Apply FKs (all tables exist)
  Table 1 ──FK──> Table 2 ✅
  Table 2 ──FK──> Table 3 ✅
  Table 3 ──FK──> Table 1 ✅

Result: ✅ All tables and FKs migrated successfully!
```
