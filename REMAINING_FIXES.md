# 🔧 REMAINING FIXES - QUICK REFERENCE

## 🎯 PRIORITY ORDER

### ⚠️ PRIORITY 0: VERIFY MIGRATION (DO THIS FIRST!)
```powershell
python verify_migration.py
```
**Why:** Data may have migrated successfully despite -1 rowcount display.

---

## 🔧 PRIORITY 1: Fix Rowcount Display (Cosmetic)

**File:** `database/sqlserver_connector.py`
**Method:** `insert_batch()` (lines 182-214)
**Issue:** `cursor.rowcount` returns -1 with some ODBC drivers

### Current Code (Line 202-209):
```python
cursor.executemany(query, rows)
self.connection.commit()

row_count = cursor.rowcount  # ❌ Returns -1
cursor.close()

logger.info(f"✅ Inserted {row_count} rows into {table_name}")
return row_count
```

### Fixed Code:
```python
cursor.executemany(query, rows)
self.connection.commit()

# ✅ Get accurate row count
cursor.execute("SELECT @@ROWCOUNT")
row_count = cursor.fetchone()[0]
cursor.close()

logger.info(f"✅ Inserted {row_count} rows into {table_name}")
return row_count
```

**Impact:** Fixes misleading "-1 rows" display
**Testing:** Re-run migration and check for actual row counts

---

## 🔧 PRIORITY 2: Fix LOB Type Handling

**File:** `database/oracle_connector.py`
**Method:** `fetch_table_data()` (lines 217-248)
**Issue:** CLOB/BLOB cannot be passed as pyodbc parameters

### Current Code (Lines 237-245):
```python
# Fetch all rows
rows = cursor.fetchall()
cursor.close()

# Convert to list of dictionaries
result = []
for row in rows:
    row_dict = dict(zip(columns, row))  # ❌ LOB objects not converted
    result.append(row_dict)

return result
```

### Fixed Code:
```python
# Fetch all rows
rows = cursor.fetchall()
cursor.close()

# Convert to list of dictionaries with LOB handling
result = []
for row in rows:
    row_dict = {}
    for col, value in zip(columns, row):
        # ✅ Check if it's a LOB object (CLOB/BLOB)
        if hasattr(value, 'read'):
            # Read LOB to string/bytes
            try:
                row_dict[col] = value.read() if value else None
            except:
                row_dict[col] = None
        else:
            row_dict[col] = value
    result.append(row_dict)

return result
```

**Impact:** Fixes STG_LOAN_APPS migration
**Testing:** Re-run migration for STG_LOAN_APPS table

---

## 🔧 PRIORITY 3: Fix Package GO Statement Batching

**File:** `database/sqlserver_connector.py`
**Method:** `execute_ddl()` (lines 87-115)
**Issue:** GO statements not split into separate batches

### Current Code (Lines 97-115):
```python
def execute_ddl(self, ddl: str) -> Dict[str, Any]:
    """Execute DDL statement (CREATE, ALTER, DROP)"""
    try:
        cursor = self.connection.cursor()
        cursor.execute(ddl)  # ❌ Fails on GO statements
        self.connection.commit()
        cursor.close()

        logger.info("✅ DDL executed successfully")
        return {"status": "success", "message": "DDL executed successfully"}

    except pyodbc.Error as e:
        self.connection.rollback()
        error_msg = str(e)
        logger.error(f"❌ DDL execution failed: {error_msg}")
        return {"status": "error", "message": error_msg}
```

### Fixed Code:
```python
def execute_ddl(self, ddl: str) -> Dict[str, Any]:
    """
    Execute DDL statement with GO batch separation

    SQL Server GO statements are batch separators, not T-SQL.
    They must be split and executed as separate batches.
    """
    try:
        # ✅ Split on GO statements
        batches = []
        current_batch = []

        for line in ddl.split('\n'):
            # Check if line is a GO statement (case-insensitive, may have whitespace)
            if line.strip().upper() == 'GO':
                # Save current batch and start new one
                if current_batch:
                    batches.append('\n'.join(current_batch))
                    current_batch = []
            else:
                current_batch.append(line)

        # Add final batch if exists
        if current_batch:
            batches.append('\n'.join(current_batch))

        # ✅ Execute each batch separately
        cursor = self.connection.cursor()

        for i, batch in enumerate(batches, 1):
            batch = batch.strip()
            if batch:  # Skip empty batches
                logger.debug(f"Executing batch {i}/{len(batches)}")
                cursor.execute(batch)
                self.connection.commit()

        cursor.close()
        logger.info(f"✅ DDL executed successfully ({len(batches)} batches)")
        return {"status": "success", "message": f"DDL executed successfully ({len(batches)} batches)"}

    except pyodbc.Error as e:
        self.connection.rollback()
        error_msg = str(e)
        logger.error(f"❌ DDL execution failed: {error_msg}")
        return {"status": "error", "message": error_msg}
    except Exception as e:
        self.connection.rollback()
        error_msg = str(e)
        logger.error(f"❌ Unexpected error: {error_msg}")
        return {"status": "error", "message": error_msg}
```

**Impact:** Fixes PKG_LOAN_PROCESSOR migration
**Testing:** Re-run migration for packages

---

## 🔧 PRIORITY 4: Fix Root Cause Analyzer Dependencies (Optional)

**Files:**
- `database/cost_tracker.py` - Add track_request() method
- `database/migration_memory.py` - Add find_similar_error_solutions() method

### Fix for CostTracker

**File:** `database/cost_tracker.py`
**Add Method:**

```python
def track_request(self, model: str, input_tokens: int, output_tokens: int) -> None:
    """
    Track individual API request for detailed cost analysis

    Args:
        model: Model name (e.g., 'claude-sonnet-3.5', 'claude-opus')
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
    """
    # Calculate cost
    if 'opus' in model.lower():
        input_cost = (input_tokens / 1000) * 0.015
        output_cost = (output_tokens / 1000) * 0.075
        self.add_cost('opus', input_cost + output_cost)
    elif 'sonnet' in model.lower():
        input_cost = (input_tokens / 1000) * 0.003
        output_cost = (output_tokens / 1000) * 0.015
        self.add_cost('sonnet', input_cost + output_cost)

    # Log for debugging
    logger.debug(f"Request tracked: {model}, {input_tokens} in, {output_tokens} out")
```

### Fix for MigrationMemory

**File:** `database/migration_memory.py`
**Add Method:**

```python
def find_similar_error_solutions(self, error_message: str, object_type: str) -> List[Dict]:
    """
    Find historical solutions for similar errors

    Args:
        error_message: The error message to search for
        object_type: Type of object (TABLE, PROCEDURE, etc.)

    Returns:
        List of similar error solutions from memory
    """
    try:
        cursor = self.connection.cursor()

        # Search for similar errors using fuzzy matching
        query = """
        SELECT object_name, error_message, solution, fixed_sql
        FROM migration_errors
        WHERE object_type = ?
        AND (
            error_message LIKE ?
            OR error_message LIKE ?
        )
        ORDER BY created_at DESC
        LIMIT 5
        """

        # Extract key error terms for fuzzy matching
        error_terms = error_message.split()[:3]  # First 3 words
        pattern1 = f"%{error_terms[0]}%" if error_terms else "%"
        pattern2 = f"%{' '.join(error_terms)}%" if len(error_terms) > 1 else "%"

        cursor.execute(query, (object_type, pattern1, pattern2))
        results = cursor.fetchall()
        cursor.close()

        solutions = []
        for row in results:
            solutions.append({
                'object_name': row[0],
                'error_message': row[1],
                'solution': row[2],
                'fixed_sql': row[3]
            })

        return solutions

    except Exception as e:
        logger.warning(f"Failed to find similar error solutions: {e}")
        return []
```

**Impact:** Enables full Root Cause Analyzer intelligence
**Testing:** Re-run migration and check for "Root Cause Analysis" output

---

## 📋 TESTING CHECKLIST

After applying fixes, verify each one:

### ✅ Rowcount Fix:
```powershell
python main.py
# Check for actual row counts (not -1)
```

### ✅ LOB Fix:
```powershell
python main.py
# Verify STG_LOAN_APPS migrates without LOB error
```

### ✅ GO Statement Fix:
```powershell
python main.py
# Verify PKG_LOAN_PROCESSOR deploys successfully
```

### ✅ Root Cause Analyzer:
```powershell
python main.py
# Check logs for "Root Cause Analysis" messages
# Should not fall back to basic repair
```

---

## 🚀 QUICK FIX SCRIPT

For convenience, here's a script to apply all fixes at once:

```powershell
# Stop any running migrations
taskkill /F /IM python.exe

# Backup original files
Copy-Item database\oracle_connector.py database\oracle_connector.py.backup
Copy-Item database\sqlserver_connector.py database\sqlserver_connector.py.backup

# Apply fixes manually (edit files as shown above)

# Test migration
python main.py
```

---

## 📊 EXPECTED RESULTS AFTER FIXES

### Before Fixes:
```
✅ Inserted -1 rows into LOANS                          ❌
⚠️  Partial migration: -1/1 rows                        ❌
❌ Table: STG_LOAN_APPS - LOB type error               ❌
❌ Package: PKG_LOAN_PROCESSOR - GO syntax error       ❌
⚠️  Falling back to basic repair                       ⚠️
```

### After Fixes:
```
✅ Inserted 1 rows into LOANS                           ✅
✅ Successfully migrated 1 rows                         ✅
✅ Inserted 1 rows into STG_LOAN_APPS                   ✅
✅ Package PKG_LOAN_PROCESSOR deployed (3 batches)     ✅
🔍 Root Cause Analysis completed successfully          ✅
```

---

## 🎯 SUMMARY

| Fix | Priority | File | Lines | Impact |
|-----|----------|------|-------|--------|
| Rowcount | P1 | sqlserver_connector.py | 202-209 | Display accuracy |
| LOB Handling | P2 | oracle_connector.py | 237-245 | 1 table fix |
| GO Batching | P3 | sqlserver_connector.py | 87-115 | Package migration |
| RCA Methods | P4 | cost_tracker.py + migration_memory.py | New methods | Intelligence |

**Total Fixes:** 4
**Estimated Time:** 30-45 minutes
**Complexity:** Low to Medium

---

## ⚠️ IMPORTANT NOTES

1. **Backup First**: Always backup files before editing
2. **Test Incrementally**: Apply and test one fix at a time
3. **Verify Data**: Run `verify_migration.py` before and after fixes
4. **Check Logs**: Monitor logs for new errors after fixes
5. **Unlock Files**: Kill Python processes before editing files

---

**FIRST STEP: Run verification to confirm data status!**

```powershell
python verify_migration.py
```
