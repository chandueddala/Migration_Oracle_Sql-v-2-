# Package to SQL Server Migration - Complete Flow

## Overview

This document explains how Oracle packages are **automatically decomposed** and **converted to SQL Server** using LLMs, since **SQL Server does not support packages**.

## The Problem

**Oracle Packages:**
```sql
CREATE OR REPLACE PACKAGE PKG_LOAN_PROCESSOR IS
    -- Public procedures
    PROCEDURE PROCESS_LOAN(p_loan_id IN NUMBER);
    PROCEDURE VALIDATE_APPLICATION(p_app_id IN NUMBER);

    -- Public functions
    FUNCTION GET_LOAN_STATUS(p_loan_id IN NUMBER) RETURN VARCHAR2;
END PKG_LOAN_PROCESSOR;

CREATE OR REPLACE PACKAGE BODY PKG_LOAN_PROCESSOR IS
    -- Private procedure
    PROCEDURE LOG_ERROR(p_msg VARCHAR2) IS BEGIN ... END;

    -- Public implementations
    PROCEDURE PROCESS_LOAN(...) IS BEGIN ... END;
    PROCEDURE VALIDATE_APPLICATION(...) IS BEGIN ... END;
    FUNCTION GET_LOAN_STATUS(...) RETURN VARCHAR2 IS BEGIN ... END;
END PKG_LOAN_PROCESSOR;
```

**SQL Server Problem:**
- ❌ SQL Server does NOT have a PACKAGE concept
- ❌ Cannot directly migrate Oracle packages
- ✅ **Solution: Decompose into individual stored procedures and functions**

## The Solution: 4-Step Automated Flow

### Step 1: Discovery & Decomposition

**Multi-Package Parser** ([`utils/package_decomposer_multi.py`](utils/package_decomposer_multi.py)):

```python
# Automatically discovers ALL packages
packages = discover_all_packages(oracle_code)

# Decomposes each package
for pkg in packages:
    members = parse_single_package(pkg)
    # Returns: List of procedures and functions
```

**What gets extracted:**
- ✅ All procedures (public and private)
- ✅ All functions (public and private)
- ✅ Parameter lists
- ✅ Return types (for functions)
- ✅ Full implementation code

**Example Output:**
```python
{
    "package_name": "PKG_LOAN_PROCESSOR",
    "members": [
        PackageMember(
            name="PROCESS_LOAN",
            member_type="PROCEDURE",
            body="PROCEDURE PROCESS_LOAN(...) IS BEGIN ... END;",
            is_public=True
        ),
        PackageMember(
            name="LOG_ERROR",
            member_type="PROCEDURE",
            body="PROCEDURE LOG_ERROR(...) IS BEGIN ... END;",
            is_public=False  # Private
        ),
        PackageMember(
            name="GET_LOAN_STATUS",
            member_type="FUNCTION",
            body="FUNCTION GET_LOAN_STATUS(...) RETURN VARCHAR2 IS BEGIN ... END;",
            return_type="VARCHAR2",
            is_public=True
        )
    ],
    "total_procedures": 2,
    "total_functions": 1
}
```

### Step 2: LLM Conversion (Each Member Separately)

**Orchestrator** ([`agents/orchestrator_agent.py:549-553`](agents/orchestrator_agent.py#L549-L553)):

```python
for member in decomposed["members"]:
    # Generate SQL Server name: PackageName_MemberName
    sqlserver_name = f"{package_name}_{member.name}"
    # e.g., PKG_LOAN_PROCESSOR_PROCESS_LOAN

    # Convert Oracle code to T-SQL using LLM
    tsql = self.converter.convert_code(
        oracle_code=member.body,           # Oracle PL/SQL
        object_name=sqlserver_name,         # SQL Server name
        object_type=member.member_type      # PROCEDURE or FUNCTION
    )
```

**Converter Agent** ([`agents/converter_agent.py:58-82`](agents/converter_agent.py#L58-L82)):

Uses **Claude Sonnet 4** to convert:

```python
prompt = f"""Convert this Oracle {object_type} to SQL Server T-SQL.

Object: {object_name}
Type: {object_type}

Oracle Code:
```plsql
{oracle_code}
```

Requirements:
- Convert PL/SQL syntax to T-SQL
- Handle Oracle functions (NVL→ISNULL, SYSDATE→GETDATE, etc.)
- Convert cursors appropriately
- Use TRY/CATCH for error handling
- For triggers: :NEW/:OLD → INSERTED/DELETED

Output ONLY the SQL Server code, no explanations."""

response = claude_sonnet.invoke([HumanMessage(content=prompt)])
```

**Example Conversion:**

**Input (Oracle):**
```sql
PROCEDURE PROCESS_LOAN(p_loan_id IN NUMBER) IS
    v_status VARCHAR2(20);
BEGIN
    UPDATE LOANS
    SET status = 'PROCESSING',
        process_date = SYSDATE
    WHERE loan_id = p_loan_id;
    COMMIT;
EXCEPTION
    WHEN OTHERS THEN
        LOG_ERROR('Error: ' || SQLERRM);
        RAISE;
END PROCESS_LOAN;
```

**Output (SQL Server):**
```sql
CREATE PROCEDURE PKG_LOAN_PROCESSOR_PROCESS_LOAN
    @p_loan_id INT
AS
BEGIN
    DECLARE @v_status VARCHAR(20);

    BEGIN TRY
        UPDATE LOANS
        SET status = 'PROCESSING',
            process_date = GETDATE()
        WHERE loan_id = @p_loan_id;

        COMMIT;
    END TRY
    BEGIN CATCH
        DECLARE @error_msg VARCHAR(MAX) = ERROR_MESSAGE();
        EXEC PKG_LOAN_PROCESSOR_LOG_ERROR @p_msg = @error_msg;
        THROW;
    END CATCH
END;
GO
```

**Key Conversions:**
- ✅ `IN NUMBER` → `INT`
- ✅ `VARCHAR2(20)` → `VARCHAR(20)`
- ✅ `SYSDATE` → `GETDATE()`
- ✅ `EXCEPTION` → `TRY/CATCH`
- ✅ `SQLERRM` → `ERROR_MESSAGE()`
- ✅ Package calls updated: `LOG_ERROR` → `PKG_LOAN_PROCESSOR_LOG_ERROR`

### Step 3: Review & Quality Check

**Reviewer Agent** ([`agents/reviewer_agent.py`](agents/reviewer_agent.py)):

```python
review = self.reviewer.review_code(
    oracle_code=member.body,
    tsql_code=tsql,
    object_name=sqlserver_name,
    object_type=member.member_type,
    cost_tracker=self.cost_tracker
)
```

**What it checks:**
- ✅ Syntax correctness
- ✅ Logic equivalence
- ✅ Data type compatibility
- ✅ Function mapping accuracy
- ✅ Error handling completeness

### Step 4: Deploy with Automatic Repair

**Debugger Agent** ([`agents/debugger_agent.py`](agents/debugger_agent.py)):

```python
deploy_result = self.debugger.deploy_with_repair(
    sql_code=tsql,
    object_name=sqlserver_name,
    object_type=member.member_type,
    oracle_code=member.body,
    sqlserver_creds=self.sqlserver_creds
)
```

**What happens:**
1. Attempts to execute the T-SQL on SQL Server
2. If syntax error occurs, captures the error
3. Uses LLM to fix the error
4. Retries (up to MAX_REPAIR_ATTEMPTS)
5. Returns success or failure

**Example repair:**
```
Error: "Incorrect syntax near 'NUMBER'"
Fix: Change "NUMBER" to "INT"
Retry: Success!
```

## Complete Example: PKG_LOAN_PROCESSOR

### Input: Oracle Package (1 package with 3 procedures, 2 functions)

```sql
PACKAGE PKG_LOAN_PROCESSOR IS
    PROCEDURE PROCESS_LOAN(p_loan_id IN NUMBER);
    PROCEDURE VALIDATE_APPLICATION(p_app_id IN NUMBER, p_status OUT VARCHAR2);
    FUNCTION GET_LOAN_STATUS(p_loan_id IN NUMBER) RETURN VARCHAR2;
    FUNCTION CALCULATE_INTEREST(p_amount IN NUMBER, p_rate IN NUMBER) RETURN NUMBER;
END PKG_LOAN_PROCESSOR;

PACKAGE BODY PKG_LOAN_PROCESSOR IS
    -- Private procedure
    PROCEDURE LOG_ERROR(p_message IN VARCHAR2) IS
    BEGIN
        INSERT INTO ERROR_LOG VALUES (p_message, SYSDATE);
    END;

    -- Public implementations
    PROCEDURE PROCESS_LOAN(...) IS BEGIN ... END;
    PROCEDURE VALIDATE_APPLICATION(...) IS BEGIN ... END;
    FUNCTION GET_LOAN_STATUS(...) RETURN VARCHAR2 IS BEGIN ... END;
    FUNCTION CALCULATE_INTEREST(...) RETURN NUMBER IS BEGIN ... END;
END PKG_LOAN_PROCESSOR;
```

### Output: 5 Separate SQL Server Objects

**1. PKG_LOAN_PROCESSOR_PROCESS_LOAN** (Stored Procedure)
```sql
CREATE PROCEDURE PKG_LOAN_PROCESSOR_PROCESS_LOAN
    @p_loan_id INT
AS BEGIN ... END;
GO
```

**2. PKG_LOAN_PROCESSOR_VALIDATE_APPLICATION** (Stored Procedure)
```sql
CREATE PROCEDURE PKG_LOAN_PROCESSOR_VALIDATE_APPLICATION
    @p_app_id INT,
    @p_status VARCHAR(255) OUTPUT
AS BEGIN ... END;
GO
```

**3. PKG_LOAN_PROCESSOR_LOG_ERROR** (Stored Procedure - Private)
```sql
CREATE PROCEDURE PKG_LOAN_PROCESSOR_LOG_ERROR
    @p_message VARCHAR(MAX)
AS BEGIN
    INSERT INTO ERROR_LOG VALUES (@p_message, GETDATE());
END;
GO
```

**4. PKG_LOAN_PROCESSOR_GET_LOAN_STATUS** (Function)
```sql
CREATE FUNCTION PKG_LOAN_PROCESSOR_GET_LOAN_STATUS
    (@p_loan_id INT)
RETURNS VARCHAR(255)
AS BEGIN
    DECLARE @v_status VARCHAR(255);
    -- ... implementation
    RETURN @v_status;
END;
GO
```

**5. PKG_LOAN_PROCESSOR_CALCULATE_INTEREST** (Function)
```sql
CREATE FUNCTION PKG_LOAN_PROCESSOR_CALCULATE_INTEREST
    (@p_amount DECIMAL(10,2),
     @p_rate DECIMAL(5,2))
RETURNS DECIMAL(10,2)
AS BEGIN
    RETURN @p_amount * (@p_rate / 100.0);
END;
GO
```

## Migration Workflow

### What You See During Migration

```
[1/1] PACKAGE: PKG_LOAN_PROCESSOR
  🔄 Orchestrating: PKG_LOAN_PROCESSOR (PACKAGE)

  📦 PACKAGE DECOMPOSITION: PKG_LOAN_PROCESSOR
  ⚠️  SQL Server does not support packages - decomposing into individual objects

    📥 Step 1/4: Fetching package code from Oracle...
    ✅ Retrieved package code: 9809 chars

    🔧 Step 2/4: Decomposing package into procedures/functions...
    ✅ Decomposed into 5 members: 3 procedures, 2 functions
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
```

## Key Features

### 1. **Truly Dynamic**
- Works with ANY number of packages
- No hardcoded package names
- Automatically discovers all members

### 2. **LLM-Powered Conversion**
- Uses Claude Sonnet 4 for intelligent conversion
- Handles complex PL/SQL to T-SQL translation
- Understands context and Oracle-specific functions

### 3. **Automatic Error Repair**
- Detects deployment errors
- Uses LLM to fix errors
- Retries until success or max attempts

### 4. **Complete Traceability**
- Logs every step
- Tracks costs per operation
- Stores success patterns for learning

### 5. **Handles Edge Cases**
- Private vs public members
- Overloaded procedures/functions
- Package-level variables (warns user)
- Initialization blocks (warns user)
- Cross-procedure calls (updates names)

## Verification

### Check SQL Server After Migration

```sql
-- List all migrated objects from the package
SELECT name, type_desc
FROM sys.objects
WHERE name LIKE 'PKG_LOAN_PROCESSOR_%'
ORDER BY name;

-- Expected output:
-- PKG_LOAN_PROCESSOR_CALCULATE_INTEREST    SQL_SCALAR_FUNCTION
-- PKG_LOAN_PROCESSOR_GET_LOAN_STATUS       SQL_SCALAR_FUNCTION
-- PKG_LOAN_PROCESSOR_LOG_ERROR             SQL_STORED_PROCEDURE
-- PKG_LOAN_PROCESSOR_PROCESS_LOAN          SQL_STORED_PROCEDURE
-- PKG_LOAN_PROCESSOR_VALIDATE_APPLICATION  SQL_STORED_PROCEDURE
```

### Test Migrated Objects

```sql
-- Test procedure
EXEC PKG_LOAN_PROCESSOR_PROCESS_LOAN @p_loan_id = 123;

-- Test function
SELECT dbo.PKG_LOAN_PROCESSOR_GET_LOAN_STATUS(123);

-- Test calculation function
SELECT dbo.PKG_LOAN_PROCESSOR_CALCULATE_INTEREST(1000.00, 5.5);
```

## Configuration

### LLM Model Used

**Claude Sonnet 4** (`claude-sonnet-4-20250514`):
- Input: $3.00 per 1M tokens
- Output: $15.00 per 1M tokens
- High accuracy for code conversion

### Conversion Settings

```python
# config/config_enhanced.py
MAX_REFLECTION_ITERATIONS = 2  # Review iterations
MAX_REPAIR_ATTEMPTS = 3        # Error repair attempts
SSMA_ENABLED = False           # Use LLM, not SSMA
```

## Cost Estimation

**Example: PKG_LOAN_PROCESSOR (5 members)**

| Member | Input Tokens | Output Tokens | Cost |
|--------|--------------|---------------|------|
| PROCESS_LOAN | 500 | 200 | $0.004 |
| VALIDATE_APPLICATION | 400 | 180 | $0.003 |
| LOG_ERROR | 200 | 100 | $0.002 |
| GET_LOAN_STATUS | 350 | 150 | $0.003 |
| CALCULATE_INTEREST | 250 | 120 | $0.002 |
| **Total** | **1700** | **750** | **$0.014** |

**Very affordable!** Even 1000 packages = ~$14

## Summary

**The system automatically:**

1. ✅ **Discovers** all packages dynamically
2. ✅ **Decomposes** each package into procedures/functions
3. ✅ **Converts** each member using Claude Sonnet LLM
4. ✅ **Reviews** conversion quality
5. ✅ **Deploys** to SQL Server with auto-repair
6. ✅ **Verifies** and updates metadata

**No manual work required!**

Just run:
```bash
python main.py
```

And watch your Oracle packages become SQL Server stored procedures and functions!

---

**Your PKG_LOAN_PROCESSOR package will be successfully migrated as 5 separate SQL Server objects!** 🚀
