# 🔍 Web Search & Memory Solutions - Complete Fix Guide

## 🐛 Issues Identified

### Issue #1: Web Search Not Working
**Error Seen:**
```
2025-11-25 20:24:16,052 - agents.root_cause_analyzer - WARNING - Web search module not available
Memory Solutions: 0
Web Resources: 0
```

**Root Cause:**
The `tavily-python` package is not installed, causing the import to fail.

---

### Issue #2: Memory Solutions Always Zero
**Error Seen:**
```
Memory Solutions: 0
```

**Root Cause:**
The `MigrationMemory._error_solutions` dictionary is empty because solutions are never saved during migrations.

---

## ✅ Complete Fix

### Step 1: Install Tavily Package

```bash
pip install tavily-python
```

This will enable web search functionality using the Tavily API key already configured in `.env`.

---

### Step 2: Update Migration Memory to Save Solutions

The `MigrationMemory` class needs a method to record successful error resolutions.

**File:** `database/migration_memory.py`

Add this method after line 215:

```python
def record_error_solution(self, error_code: str, solution: Dict):
    """
    Record a successful error solution for future reference

    Args:
        error_code: The error code or message that was resolved
        solution: Dict containing:
            - object_name: Name of the object
            - object_type: Type (PROCEDURE, FUNCTION, etc.)
            - error_message: Full error message
            - oracle_code: Original Oracle code
            - fixed_sql: Working SQL Server code
            - fix_description: What was changed
            - timestamp: When it was fixed
    """
    if not error_code:
        return

    # Normalize error code for consistent lookups
    normalized_key = error_code.strip().lower()

    # Add to error solutions
    self._error_solutions[normalized_key].append({
        "object_name": solution.get("object_name", ""),
        "object_type": solution.get("object_type", ""),
        "error_message": solution.get("error_message", ""),
        "oracle_code": solution.get("oracle_code", "")[:500],  # Limit size
        "fixed_sql": solution.get("fixed_sql", "")[:500],  # Limit size
        "fix_description": solution.get("fix_description", ""),
        "timestamp": solution.get("timestamp", datetime.now().isoformat())
    })
```

---

### Step 3: Update Orchestrator to Record Solutions

When an error is successfully fixed, we need to record it in memory.

**File:** `agents/orchestrator_agent.py`

**Location:** Around line 220-250 in the `orchestrate_code_object_migration()` method

**After successful deployment** (after `deploy_result['success']`), add:

```python
# Record successful error resolution in memory
if conversion_result.get('had_errors', False) and deploy_result['success']:
    from database.migration_memory import MigrationMemory
    from datetime import datetime

    memory = MigrationMemory()

    # Extract error information
    error_msg = conversion_result.get('original_error', '')
    fixed_code = deploy_result.get('sql_code', '')

    # Record the solution
    memory.record_error_solution(
        error_code=error_msg[:200],  # Use first 200 chars as key
        solution={
            "object_name": object_name,
            "object_type": object_type,
            "error_message": error_msg,
            "oracle_code": oracle_code,
            "fixed_sql": fixed_code,
            "fix_description": f"Successfully fixed {object_type} after error resolution",
            "timestamp": datetime.now().isoformat()
        }
    )

    logger.info(f"Recorded solution for {object_name} in memory")
```

---

## 🧪 Testing the Fix

### Test 1: Verify Tavily Installation

```python
# Run this in Python
try:
    from tavily import TavilyClient
    print("✓ Tavily package installed successfully")
except ImportError:
    print("✗ Tavily package NOT installed")
```

### Test 2: Verify Web Search Works

After installing `tavily-python`, run a migration. You should see:

```
💡 Step 4/5: Searching for similar solutions...
   Memory Solutions: 0  (first time)
   Web Resources: 3-5  (should now show results!)
```

### Test 3: Verify Memory Accumulates

Run 2-3 migrations with errors that get fixed. On subsequent runs, you should see:

```
💡 Step 4/5: Searching for similar solutions...
   Memory Solutions: 2  (increasing!)
   Web Resources: 3-5
```

---

## 📊 Expected Behavior After Fix

### First Migration:
```
🔍 Analyzing error for PROCEDURE calculate_total_interest...
   📋 Step 1/5: Classifying error type...
      Error Type: syntax_error
      SQL Error Code: 156
      Confidence: high

   📊 Step 2/5: Analyzing Oracle source...
      Oracle Features: CURSOR, EXCEPTION HANDLING

   🗄️  Step 3/5: Gathering SQL Server metadata...
      Existing Objects: False

   💡 Step 4/5: Searching for similar solutions...
      Memory Solutions: 0
      Web Resources: 5 articles found  ← NOW WORKING!

   🎯 Step 5/5: Performing root cause analysis...

   ✅ Root Cause Identified: Missing semicolon in T-SQL syntax
```

### Second Migration (after first error was fixed):
```
   💡 Step 4/5: Searching for similar solutions...
      Memory Solutions: 1 found  ← MEMORY NOW POPULATED!
      Web Resources: 5 articles found
```

---

## 🎯 Benefits After Fix

### 1. **Web Search Enabled**
- Real-time access to Stack Overflow, Microsoft Docs, DBA StackExchange
- 3-5 relevant articles per error
- Ranked by relevance score
- Includes solution snippets

### 2. **Learning System**
- Every fixed error is remembered
- Future similar errors are resolved faster
- Memory persists across migration sessions
- Builds a knowledge base specific to your database

### 3. **Better Error Resolution**
- Higher success rate on first attempt
- Fewer LLM calls = Lower costs
- Faster migrations
- More reliable conversions

---

## 🚀 Quick Fix Commands

```bash
# 1. Install Tavily
pip install tavily-python

# 2. Verify installation
python -c "from tavily import TavilyClient; print('✓ Tavily installed')"

# 3. Run a test migration
streamlit run app.py

# 4. Check logs for web search results
tail -f logs/migration_*.log | grep "Web Resources"
```

---

## 📝 Configuration Verification

Check your `.env` file has:

```env
# Web Search
TAVILY_API_KEY=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  # ✓ Already set
ENABLE_WEB_SEARCH=true  # ✓ Already enabled
MAX_SEARCH_RESULTS=5    # ✓ Already configured
```

---

## 🔧 Alternative: If You Don't Want Web Search

If you prefer to disable web search (not recommended):

**Option 1 - Disable in .env:**
```env
ENABLE_WEB_SEARCH=false
```

**Option 2 - Remove Tavily API key:**
```env
# TAVILY_API_KEY=  (comment it out)
```

**Result:**
```
💡 Step 4/5: Searching for similar solutions...
   Memory Solutions: 2  (will still work!)
   Web Resources: 0  (disabled)
```

---

## ✅ Summary

### Current State:
- ✅ Tavily API key configured
- ✅ Web search enabled in config
- ❌ `tavily-python` package NOT installed
- ❌ Memory solutions never saved

### After Fix:
- ✅ Tavily API key configured
- ✅ Web search enabled in config
- ✅ `tavily-python` package installed
- ✅ Memory solutions accumulate over time

### Commands to Run:
```bash
pip install tavily-python
streamlit run app.py
```

**You're now ready to use web search and build migration memory!** 🎯✨
