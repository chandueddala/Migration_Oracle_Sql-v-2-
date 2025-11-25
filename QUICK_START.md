# Quick Start Guide

## Oracle to SQL Server Migration - Upfront Selection Mode

This guide shows you how to use the **upfront selection workflow** - perfect for frontend integration!

---

## 🚀 Quick Start (5 minutes)

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure API Keys

Edit `config/config_enhanced.py`:

```python
ANTHROPIC_API_KEY = "your-anthropic-api-key"
OPENAI_API_KEY = "your-openai-api-key"  # Optional
```

### 3. Run Migration

```bash
python migrate_upfront.py
```

That's it! The system will:
1. ✅ Ask for Oracle & SQL Server credentials
2. ✅ Discover ALL database objects (tables, packages, etc.)
3. ✅ Ask you to select EVERYTHING upfront
4. ✅ Migrate all selected objects **without interruption**

---

## 📋 What Gets Migrated

### Tables
- ✅ Schema (columns, data types, constraints)
- ✅ Data (optional - you choose per table)
- ✅ Indexes
- ✅ Primary keys & foreign keys

### Packages (Automatically Decomposed!)
- ✅ **Packages → Stored Procedures & Functions**
- ✅ SQL Server doesn't have packages, so we decompose them
- ✅ `PKG_LOAN_PROCESSOR.PROCESS_LOAN` → `PKG_LOAN_PROCESSOR_PROCESS_LOAN`
- ✅ LLM-powered conversion (NO hardcoded patterns!)

### Procedures, Functions, Triggers
- ✅ Standalone procedures
- ✅ Standalone functions
- ✅ Triggers (BEFORE/AFTER/INSTEAD OF)

### Optional
- ✅ Views
- ✅ Sequences

---

## 🎯 Upfront Selection Mode

### Why Upfront?

**Traditional Mode:**
```
Discover tables → Ask user → Migrate table 1 → Ask about data → Migrate data
→ Discover packages → Ask user → Migrate package 1 → Ask about next package
→ Discover procedures → Ask user → ... (keeps interrupting!)
```

**Upfront Mode (This System):**
```
Discover EVERYTHING → Ask user for ALL selections → Migrate ALL (no interruptions!)
```

### Perfect For:
- ✅ **Frontend Integration** (web UI, REST API)
- ✅ **Automation** (scripted migrations)
- ✅ **Batch Processing** (migrate multiple databases)
- ✅ **CI/CD Pipelines** (automated testing)

---

## 📊 Example Session

```
================================================================================
 ORACLE TO SQL SERVER MIGRATION - UPFRONT SELECTION MODE
================================================================================

  This mode:
    1. Discovers ALL database objects
    2. Asks you to select EVERYTHING upfront
    3. Migrates all selected objects without interruption
    4. Perfect for automation and frontend integration

================================================================================
 STEP 1: CREDENTIALS
================================================================================

Oracle Host: localhost
Oracle Port [1521]:
Oracle Service Name: XEPDB1
Oracle Username: your_user
Oracle Password: ********

SQL Server: localhost
SQL Server Database: MigrationTarget
SQL Server Username: sa
SQL Server Password: ********

================================================================================
 STEP 2: COMPREHENSIVE DISCOVERY
================================================================================

  Discovering ALL database objects...

  📊 Discovering tables...
    ✅ Found 45 tables
  📦 Discovering packages...
    ✅ Found 12 packages
  🔧 Discovering procedures...
    ✅ Found 28 procedures
  ⚙️ Discovering functions...
    ✅ Found 35 functions
  ⚡ Discovering triggers...
    ✅ Found 18 triggers

  Discovery complete!
    Time: 3.45s
    Total objects: 138

    Discovery data saved: output/discovery_result.json

================================================================================
 STEP 3: SELECT OBJECTS TO MIGRATE
================================================================================

  Select EVERYTHING you want to migrate now!
  No more questions after this...

================================================================================
 STEP 1: SELECT TABLES TO MIGRATE
================================================================================

  Found 45 tables:

     1. CUSTOMERS                   (15,678 rows, 12.50 MB)
     2. ORDERS                      (48,923 rows, 45.23 MB)
     3. PRODUCTS                    (1,234 rows, 2.10 MB)
     ...

  Options:
    - Enter numbers (e.g., 1,3,5)
    - Enter range (e.g., 1-5)
    - Enter 'all' for all tables
    - Press Enter to skip tables

  Select tables to migrate: 1-3

  ✅ Selected 3 tables

================================================================================
 STEP 2: SELECT WHICH TABLES TO MIGRATE DATA
================================================================================

  For each table, choose:
    - Schema + Data
    - Schema Only (no data)

  Quick options:
    - Enter 'all' to migrate data for ALL tables
    - Enter 'none' for schema only (no data)
    - Enter specific numbers for tables to include data

  Migrate data for which tables? [all/none/numbers]: 1,2

  ✅ Data migration selected for 2 tables

================================================================================
 STEP 3: SELECT PACKAGES TO MIGRATE
================================================================================

  Found 12 packages:

     1. PKG_LOAN_PROCESSOR          (5 members) [OK]
     2. PKG_ACCOUNT_MANAGER         (8 members) [OK]
     ...

  Select packages to migrate: 1

  ✅ Selected 1 package

================================================================================
 SELECTION SUMMARY
================================================================================

  Tables:
    Total selected: 3
    With data: 2
    Schema only: 1

  Code Objects:
    Packages: 1
    Procedures: 0
    Functions: 0
    Triggers: 0

  TOTAL OBJECTS TO MIGRATE: 4

================================================================================

  Proceed with migration? [Y/n]: y

  Starting migration...

================================================================================
 STEP 4: MIGRATION EXECUTION
================================================================================

  Migrating 4 objects...
  This will run without interruption!

  [TABLES] Migrating 3 tables...

    [1/3] CUSTOMERS
      [OK] Schema migrated
      [DATA] Migrating data...
       📥 Fetching data from Oracle...
       ✅ Fetched 15,678 rows from Oracle
       📤 Inserting into SQL Server...
       ✅ Successfully migrated 15,678 rows
      [OK] Data migrated: 15,678 rows

    [2/3] ORDERS
      [OK] Schema migrated
      [DATA] Migrating data...
      [OK] Data migrated: 48,923 rows

    [3/3] PRODUCTS
      [OK] Schema migrated
      [SKIP] Data migration (schema only)

  [PACKAGES] Migrating 1 package...

    [1/1] PKG_LOAN_PROCESSOR
      🔄 Orchestrating: PKG_LOAN_PROCESSOR (PACKAGE)

      📦 PACKAGE DECOMPOSITION: PKG_LOAN_PROCESSOR
      ⚠️  SQL Server does not support packages - decomposing into individual objects

        📥 Step 1/4: Fetching package code from Oracle...
        ✅ Retrieved package code: 9809 chars

        🔧 Step 2/4: Decomposing package using LLM...
        🤖 Using LLM to analyze package structure...
        ✅ LLM analyzed package: PKG_LOAN_PROCESSOR - 3 procedures, 2 functions

        Found 5 members to migrate:
        - 3 procedures
        - 2 functions

        🚀 Step 3/4: Migrating individual members...

           [1/5] Migrating: PROCESS_LOAN (PROCEDURE)
                              → SQL Server name: PKG_LOAN_PROCESSOR_PROCESS_LOAN
                              🔄 Converting with LLM...
                              👁️ Reviewing...
                              🚀 Deploying...
                              ✅ Success

           [2/5] Migrating: VALIDATE_APPLICATION (PROCEDURE)
                              → SQL Server name: PKG_LOAN_PROCESSOR_VALIDATE_APPLICATION
                              ✅ Success

           [3/5] Migrating: LOG_ERROR (PROCEDURE)
                              → SQL Server name: PKG_LOAN_PROCESSOR_LOG_ERROR
                              ✅ Success

           [4/5] Migrating: GET_LOAN_STATUS (FUNCTION)
                              → SQL Server name: PKG_LOAN_PROCESSOR_GET_LOAN_STATUS
                              ✅ Success

           [5/5] Migrating: CALCULATE_INTEREST (FUNCTION)
                              → SQL Server name: PKG_LOAN_PROCESSOR_CALCULATE_INTEREST
                              ✅ Success

        📊 Step 4/4: Package decomposition summary
           ✅ Successfully migrated: 5/5
           ❌ Failed: 0/5

      [OK] Package migrated

================================================================================
 MIGRATION COMPLETE
================================================================================

  Total objects: 4
  Successful: 4
  Failed: 0

  Total Cost: $0.42 | Anthropic: $0.38 (Claude Sonnet 4) | OpenAI: $0.04

  Results saved: output/migration_results.json

================================================================================
```

---

## 📁 Output Files

After migration, you'll have 3 JSON files in `output/`:

### 1. `discovery_result.json`
- All discovered objects
- Metadata (row counts, sizes, status)
- Perfect for displaying in frontend

### 2. `migration_selection.json`
- User's selections
- Can be saved and reused
- Can be loaded from file for automation

### 3. `migration_results.json`
- Complete migration results
- Success/failure status per object
- Error messages
- Cost breakdown

---

## 🔧 Advanced Usage

### Load Selection from JSON

```python
import json
from utils.interactive_selection import MigrationSelection

# Load saved selection
with open('my_selection.json') as f:
    selection_data = json.load(f)

selection = MigrationSelection(
    selected_tables=selection_data['tables']['selected'],
    tables_with_data=selection_data['tables']['with_data'],
    selected_packages=selection_data['packages']['selected']
)

# Run migration with saved selection
# ... (see FRONTEND_INTEGRATION_GUIDE.md)
```

### Programmatic Migration

```python
from utils.comprehensive_discovery import ComprehensiveDiscovery
from database.oracle_connector import OracleConnector
from agents.orchestrator_agent import MigrationOrchestrator

# Discovery
oracle_conn = OracleConnector(oracle_creds)
oracle_conn.connect()

discovery = ComprehensiveDiscovery(oracle_conn)
result = discovery.discover_all()

# Manual selection (no interactive prompts)
selected_tables = ["CUSTOMERS", "ORDERS"]

# Migration
orchestrator = MigrationOrchestrator(oracle_creds, sqlserver_creds, cost_tracker)

for table_name in selected_tables:
    result = orchestrator.orchestrate(table_name, "TABLE")
    print(f"{table_name}: {result['status']}")
```

---

## 🎓 Documentation

- **[FRONTEND_INTEGRATION_GUIDE.md](FRONTEND_INTEGRATION_GUIDE.md)** - Build a web UI or REST API
- **[PACKAGE_TO_SQL_SERVER_FLOW.md](PACKAGE_TO_SQL_SERVER_FLOW.md)** - How packages are migrated
- **[LLM_POWERED_DYNAMIC_MIGRATION.md](LLM_POWERED_DYNAMIC_MIGRATION.md)** - Why LLM vs regex

---

## ❓ FAQ

**Q: Why use LLM for package decomposition?**

A: SQL Server doesn't have packages. We use LLM to intelligently understand package structure and decompose it into individual stored procedures and functions. NO hardcoded patterns - works with ANY package structure!

**Q: What if a migration fails?**

A: The system has automatic error repair! If deployment fails, the LLM analyzes the error and fixes it automatically (up to 3 attempts). Most errors are syntax issues that get resolved automatically.

**Q: Can I migrate just the schema without data?**

A: Yes! During selection, you choose which tables to include data for. Others will be schema-only.

**Q: What about triggers and views?**

A: Both are supported! Triggers are converted from Oracle syntax (`:NEW`, `:OLD`) to SQL Server (`INSERTED`, `DELETED`). Views are migrated as-is with syntax conversion.

**Q: How much does it cost?**

A: Very affordable! Example: Migrating 100 tables + 10 packages ≈ $2-5 in LLM API costs. The system tracks costs in real-time.

**Q: Can I use this in production?**

A: Yes! The system is production-ready. For large migrations, we recommend:
- Test on a staging environment first
- Review the generated SQL before deploying
- Use the frontend integration for better control

---

## 🆘 Troubleshooting

### Connection Issues

```
Error: ORA-12154: TNS:could not resolve the connect identifier
```

**Solution:** Check your Oracle service name and ensure the Oracle client is installed.

### Package Migration Shows 0 Members

```
Found 0 procedures, 0 functions
```

**Solution:** The system now uses LLM-powered decomposition which handles raw package code. If this still happens, check the package status in Oracle:

```sql
SELECT status FROM user_objects WHERE object_name = 'YOUR_PACKAGE';
```

### Data Migration Fails

```
Error: Cannot insert explicit value for identity column
```

**Solution:** The system automatically handles IDENTITY columns. If this error occurs, it's a bug - please report it!

---

## 📞 Support

- **GitHub Issues:** [Report bugs](https://github.com/your-repo/issues)
- **Documentation:** See `docs/` folder
- **Examples:** See `examples/` folder

---

## ✅ Summary

This migration system is **ready for production**:

✅ **Upfront Selection** - No interruptions
✅ **LLM-Powered** - Works with ANY Oracle code
✅ **Frontend-Ready** - JSON everywhere
✅ **Automatic Repair** - Fixes errors automatically
✅ **Cost-Effective** - Tracks and optimizes LLM usage
✅ **Battle-Tested** - Handles complex packages, triggers, and data

**Start migrating now!**

```bash
python migrate_upfront.py
```
