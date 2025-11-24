# Root Cause Analysis Integration Guide

## Overview

The new **Root Cause Analyzer** performs intelligent, step-by-step error analysis before attempting fixes. This is a complete re-thinking of how errors are handled.

## Architecture

### Old Approach (Single-Step):
```
Error → LLM → Fix → Deploy
```
**Problem:** LLM tries to fix without understanding context

### New Approach (Multi-Step Agentic):
```
Error → Classify → Gather Context → Analyze → Generate Fix → Deploy
         ↓            ↓                ↓          ↓
      Category    Oracle Code      Root Cause   Targeted
                  SQL Server       Analysis     Solution
                  Memory
                  Web Search
```

---

## How It Works

### Step-by-Step Process

#### 1. Error Classification
```
🔍 Starting Root Cause Analysis for LOANS...
📋 Step 1/5: Classifying error type...
   Error Category: object_exists
   Severity: medium
```

**What happens:**
- LLM analyzes error message
- Classifies into category (syntax/permission/object_exists/etc.)
- Determines severity
- Extracts error code

#### 2. Oracle Code Analysis
```
📊 Step 2/5: Analyzing Oracle source...
   Oracle Features: SEQUENCES, TRIGGERS, NUMBER type
```

**What happens:**
- Analyzes original Oracle code
- Identifies Oracle-specific features
- Notes complex constructs
- Lists dependencies

#### 3. SQL Server Context
```
🗄️  Step 3/5: Gathering SQL Server metadata...
   Existing Objects: True
   Existing Columns: 10
```

**What happens:**
- Checks if object already exists
- Gets existing column metadata
- Retrieves constraints
- Checks shared memory

#### 4. Knowledge Search
```
💡 Step 4/5: Searching for similar solutions...
   Memory Solutions: 2
   Web Resources: 5
```

**What happens:**
- Searches shared memory for similar errors
- Performs web search for solutions
- Collects best practices
- Gathers Stack Overflow answers

#### 5. Root Cause Analysis
```
🎯 Step 5/5: Performing root cause analysis...

✅ Root Cause Identified: Table already exists - need DROP or ALTER
🔧 Confidence Level: high
```

**What happens:**
- LLM analyzes ALL gathered context
- Identifies primary root cause
- Explains Oracle vs SQL Server differences
- Recommends specific fix strategy
- Assigns confidence level

#### 6. Generate Targeted Fix
```
🛠️  Generating targeted fix...
   Applied: DROP IF EXISTS before CREATE
✅ Fix deployed successfully
```

---

## Integration with Debugger Agent

### Modified `debugger_agent.py`

```python
from agents.root_cause_analyzer import RootCauseAnalyzer

class DebuggerAgent:
    def __init__(self, cost_tracker: CostTracker = None):
        self.analyzer = RootCauseAnalyzer(cost_tracker)
        # ... existing code ...

    def debug_and_repair(self,
                        sql_code: str,
                        error_message: str,
                        object_name: str,
                        object_type: str,
                        error_history: List[Dict],
                        oracle_code: Optional[str] = None,
                        sqlserver_creds: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Debug using comprehensive root cause analysis
        """

        # Use root cause analyzer for first 2 attempts
        if len(error_history) < 2:
            logger.info(f"Using root cause analyzer for {object_name}")

            analysis_result = self.analyzer.analyze_and_fix(
                sql_code=sql_code,
                error_message=error_message,
                object_name=object_name,
                object_type=object_type,
                oracle_code=oracle_code,
                sqlserver_creds=sqlserver_creds
            )

            if analysis_result.get("status") == "success":
                fix = analysis_result.get("fix", {})

                # Store root cause in memory for future use
                self._store_root_cause_solution(
                    object_name=object_name,
                    root_cause=analysis_result["root_cause"],
                    fix=fix
                )

                return {
                    "status": "success",
                    "sql": fix.get("sql", sql_code),
                    "explanation": fix.get("explanation", ""),
                    "root_cause": analysis_result["root_cause"],
                    "resources_used": {
                        "root_cause_analysis": True,
                        "oracle_analysis": bool(oracle_code),
                        "sql_context": bool(sqlserver_creds),
                        "knowledge_search": True
                    }
                }

        # Fallback to simple repair for final attempt
        return self._simple_repair(sql_code, error_message, object_name)

    def _store_root_cause_solution(self,
                                   object_name: str,
                                   root_cause: Dict,
                                   fix: Dict):
        """Store successful root cause solution in memory"""
        from database.migration_memory import MigrationMemory

        memory = MigrationMemory()
        memory.store_error_solution(
            error_message=root_cause.get("diagnosis", ""),
            solution={
                "fix": fix.get("sql", ""),
                "explanation": fix.get("explanation", ""),
                "root_cause": root_cause.get("primary_cause", ""),
                "confidence": fix.get("confidence", "medium"),
                "object_type": object_name
            }
        )
        logger.info(f"Stored root cause solution for {object_name}")
```

---

## Expected Output

### Complete Error Resolution Flow

```
[1/5] Table: LOANS
  🔄 Orchestrating: LOANS
    📥 Step 1/5: Fetching Oracle DDL...
    🔄 Step 2/5: Converting to SQL Server...
    🚀 Step 3/5: Deploying to SQL Server...
    ❌ Deployment failed: There is already an object named 'LOANS'

    🔧 Auto-repair attempt 1/3

       🔍 Starting Root Cause Analysis for LOANS...

       📋 Step 1/5: Classifying error type...
          Error Category: object_exists
          Severity: medium
          Error Code: 42S01

       📊 Step 2/5: Analyzing Oracle source...
          Oracle Features: SEQUENCES, NOT NULL constraints, DEFAULT values
          Complex Constructs: Composite keys
          Data Types: NUMBER, VARCHAR2, DATE

       🗄️  Step 3/5: Gathering SQL Server metadata...
          Existing Objects: True
          Existing Columns: 10
          Schema: dbo

       💡 Step 4/5: Searching for similar solutions...
          Memory Solutions: 2 similar cases found
            • Solution 1: Add DROP TABLE IF EXISTS
            • Solution 2: Use ALTER TABLE instead
          Web Resources: 5 articles found
            • Microsoft Docs: Handling existing objects
            • Stack Overflow: DROP IF EXISTS best practices
            • SQL Server Central: Migration patterns

       🎯 Step 5/5: Performing root cause analysis...

       ✅ Root Cause Identified:
          Primary Cause: Table already exists from previous migration run
          Oracle Feature: N/A (deployment issue, not conversion)
          SQL Server Issue: CREATE TABLE fails when object exists
          Similar Solutions: 2 cases resolved with DROP IF EXISTS
          Recommended Fix: Add DROP TABLE IF EXISTS before CREATE
          🔧 Confidence Level: high

       🛠️  Generating targeted fix...
          Strategy: Add DROP IF EXISTS statement
          Applied fix: DROP TABLE IF EXISTS [LOANS]; GO

       🚀 Deploying fixed code...
       ✅ Deployment successful!

    ✅ Table migration successful
```

---

## Benefits of Root Cause Analysis

### 1. **Better Understanding**
- Knows WHY the error occurred
- Understands Oracle → SQL Server differences
- Identifies specific problem areas

### 2. **Targeted Fixes**
- Applies specific solution for root cause
- Not generic "try to fix" approach
- Higher success rate

### 3. **Learning System**
- Stores successful root cause solutions
- Reuses patterns for similar errors
- Improves over time

### 4. **Transparency**
- Shows each analysis step
- Displays resources consulted
- Explains the fix applied

### 5. **Multi-Source Context**
- Oracle code analysis
- SQL Server metadata
- Memory of past solutions
- External web resources
- Error history

---

## Configuration

### Enable/Disable Features

**File:** `config/config_enhanced.py`

```python
# Root Cause Analysis Settings
ENABLE_ROOT_CAUSE_ANALYSIS = True
ROOT_CAUSE_ANALYSIS_MAX_ATTEMPTS = 2  # Use RCA for first 2 attempts
ENABLE_WEB_SEARCH = True
WEB_SEARCH_MAX_RESULTS = 5
```

### Cost Optimization

Root cause analysis uses more LLM calls but results in:
- Fewer retry attempts needed
- Higher success rate
- Less wasted API calls on failed attempts

**Cost Per Error:**
- Old approach: 3 attempts × failed fixes = High cost + failure
- New approach: 1-2 analysis steps = Fixed correctly

---

## Memory Integration

### Storing Solutions

```python
# After successful fix
memory.store_error_solution(
    error_message="Table already exists",
    solution={
        "fix": "DROP TABLE IF EXISTS [table_name];",
        "explanation": "Object exists from previous run",
        "root_cause": "Deployment issue - not conversion",
        "confidence": "high"
    }
)
```

### Retrieving Similar Solutions

```python
# When new error occurs
similar_solutions = memory.find_similar_error_solutions("Table already exists")

# Returns:
[
    {
        "solution": "DROP TABLE IF EXISTS [table_name];",
        "confidence": "high",
        "success_count": 5
    }
]
```

---

## Testing

### Test Root Cause Analyzer

```python
from agents.root_cause_analyzer import RootCauseAnalyzer

analyzer = RootCauseAnalyzer()

result = analyzer.analyze_and_fix(
    sql_code="CREATE TABLE [LOANS] (...)",
    error_message="There is already an object named 'LOANS'",
    object_name="LOANS",
    object_type="TABLE",
    oracle_code="CREATE TABLE LOANS (...)",
    sqlserver_creds=your_creds
)

print(f"Root Cause: {result['root_cause']['diagnosis']}")
print(f"Confidence: {result['root_cause']['confidence']}")
print(f"Fixed SQL: {result['fix']['sql'][:100]}...")
```

---

## Migration Path

### Phase 1: Add Root Cause Analyzer (Done ✅)
- Created `root_cause_analyzer.py`
- Implemented 5-step analysis
- Integrated multi-source context

### Phase 2: Update Debugger Agent
**File:** `agents/debugger_agent.py`

Add import and integration code (shown above)

### Phase 3: Add Web Search Module
**File:** `external_tools/web_search.py`

```python
def search_web(query: str, max_results: int = 5) -> List[Dict]:
    """Search web for solutions"""
    # Implement using your preferred search API
    # Options: SerpAPI, Google Custom Search, Bing API
    pass
```

### Phase 4: Test & Refine
- Run test migrations
- Collect metrics
- Refine prompts
- Optimize costs

---

## Troubleshooting

### Issue: Root cause analysis is slow
**Solution:**
- Reduce web search results
- Cache common solutions
- Use haiku model for classification

### Issue: Low confidence fixes
**Solution:**
- Add more context sources
- Improve Oracle code analysis
- Enhance memory with successful patterns

### Issue: Web search not working
**Solution:**
- Verify API keys
- Check network connectivity
- Fallback to memory-only mode

---

## Summary

The Root Cause Analyzer transforms error handling from:

**❌ Old:** "Try to fix it and hope it works"

**✅ New:** "Understand the problem deeply, then apply the right fix"

This is a **game-changer** for migration success rates!

---

**Ready to integrate? See the code in `agents/root_cause_analyzer.py`!** 🚀
