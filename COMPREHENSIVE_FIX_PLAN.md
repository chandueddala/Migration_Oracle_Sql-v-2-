# Comprehensive Fix Plan for Migration System

## Current Issues from Logs

### 1. **Tables Already Exist Error**
```
Error: "There is already an object named 'LOANS' in the database"
```
**Root Cause:** System tries to CREATE tables that already exist
**Solution:** Add DROP IF EXISTS with user confirmation

### 2. **Package Conversion Errors**
- Incorrect syntax near backticks (`)
- GO statements causing issues
- CREATE OR ALTER not properly formatted
- Variable scope issues

### 3. **Missing Enhancements**
- No web search for error resolution
- Limited memory usage during repairs
- No user confirmation for existing objects
- No detailed tool usage analysis

---

## Solution Implementation Plan

### Phase 1: Handle Existing Objects ✅

**File:** `agents/debugger_agent.py`

Add object existence check before deployment:

```python
def check_object_exists(self, object_name: str, object_type: str, sqlserver_creds: Dict) -> bool:
    """Check if object already exists in SQL Server"""
    from database.sqlserver_connector import SQLServerConnector

    conn = SQLServerConnector(sqlserver_creds)
    if not conn.connect():
        return False

    # Query to check object existence
    check_query = """
    SELECT COUNT(*) as count
    FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_NAME = ?
    """ if object_type == 'TABLE' else """
    SELECT COUNT(*) as count
    FROM INFORMATION_SCHEMA.ROUTINES
    WHERE ROUTINE_NAME = ?
    """

    cursor = conn.connection.cursor()
    cursor.execute(check_query, object_name)
    result = cursor.fetchone()
    exists = result[0] > 0 if result else False

    cursor.close()
    conn.disconnect()

    return exists

def handle_existing_object(self, object_name: str, object_type: str) -> str:
    """Ask user what to do with existing object"""
    print(f"\n⚠️  Object '{object_name}' already exists in SQL Server")
    print(f"   Type: {object_type}")
    print(f"\n   Options:")
    print(f"     1. Drop and recreate")
    print(f"     2. Skip this object")
    print(f"     3. Try ALTER instead of CREATE")

    while True:
        choice = input(f"\n   Your choice (1/2/3): ").strip()
        if choice in ['1', '2', '3']:
            return {'1': 'drop', '2': 'skip', '3': 'alter'}[choice]
        print("   Invalid choice. Please enter 1, 2, or 3")

def add_drop_statement(self, sql_code: str, object_name: str, object_type: str) -> str:
    """Add DROP IF EXISTS statement"""
    if object_type == 'TABLE':
        drop_stmt = f"DROP TABLE IF EXISTS [{object_name}];\nGO\n\n"
    elif object_type in ['PROCEDURE', 'FUNCTION']:
        drop_stmt = f"DROP {object_type} IF EXISTS [dbo].[{object_name}];\nGO\n\n"
    else:
        drop_stmt = f"IF OBJECT_ID('{object_name}', 'U') IS NOT NULL DROP TABLE [{object_name}];\nGO\n\n"

    return drop_stmt + sql_code
```

### Phase 2: Add Web Search for Errors ✅

**File:** `agents/debugger_agent.py`

```python
def search_error_solution(self, error_message: str) -> Optional[Dict]:
    """Search web for SQL Server error solutions"""
    try:
        from external_tools.web_search import search_web

        # Extract error code
        error_code = self._extract_error_code(error_message)

        # Search queries
        queries = [
            f"SQL Server error {error_code} solution",
            f"Fix {error_code} SQL Server migration",
            f"SQL Server {error_code} Oracle to SQL Server"
        ]

        results = []
        for query in queries:
            search_result = search_web(query, max_results=3)
            if search_result:
                results.extend(search_result)

        print(f"       🔍 Found {len(results)} web resources for error resolution")

        return {
            "error_code": error_code,
            "resources": results[:5],  # Top 5 results
            "query_used": queries[0]
        }

    except Exception as e:
        logger.warning(f"Web search failed: {e}")
        return None

def _extract_error_code(self, error_message: str) -> str:
    """Extract SQL Server error code from message"""
    import re
    # Match patterns like [42S01], (2714), etc.
    match = re.search(r'\[([0-9A-Z]+)\]|\((\d+)\)', error_message)
    if match:
        return match.group(1) or match.group(2)
    return "unknown"
```

### Phase 3: Enhanced Memory Context ✅

**File:** `agents/debugger_agent.py`

```python
def get_comprehensive_context(self,
                             object_name: str,
                             error_message: str,
                             oracle_code: Optional[str],
                             error_history: List[Dict]) -> str:
    """Build comprehensive context for LLM"""
    from database.migration_memory import MigrationMemory

    memory = MigrationMemory()
    context_parts = []

    # 1. Oracle Code Context
    if oracle_code:
        context_parts.append(f"📊 **Oracle Code:**\n```sql\n{oracle_code}\n```\n")

    # 2. Error History
    if error_history:
        context_parts.append(f"📜 **Previous Attempts:** {len(error_history)}")
        for hist in error_history[-3:]:  # Last 3 attempts
            context_parts.append(f"  - Attempt {hist['attempt']}: {hist['error'][:100]}")

    # 3. Memory: Similar Errors
    similar_solutions = memory.find_similar_error_solutions(error_message)
    if similar_solutions:
        context_parts.append(f"\n💡 **Similar Errors Resolved:**")
        for sol in similar_solutions[:2]:
            context_parts.append(f"  - Solution: {sol['solution'][:150]}")

    # 4. Memory: Table Metadata
    if object_name in memory.table_mappings:
        meta = memory.table_mappings[object_name]
        context_parts.append(f"\n📋 **SQL Server Metadata:**")
        context_parts.append(f"  - Columns: {len(meta.get('columns', []))}")
        if meta.get('identity_columns'):
            context_parts.append(f"  - Identity: {meta['identity_columns']}")

    # 5. Web Search Results
    web_results = self.search_error_solution(error_message)
    if web_results and web_results['resources']:
        context_parts.append(f"\n🌐 **External Resources ({len(web_results['resources'])}):**")
        for idx, res in enumerate(web_results['resources'][:3], 1):
            context_parts.append(f"  {idx}. {res.get('title', 'Resource')} - {res.get('url', '')}")
            if res.get('snippet'):
                context_parts.append(f"     Summary: {res['snippet'][:100]}...")

    return "\n".join(context_parts)
```

### Phase 4: Enhanced Error Repair with All Resources ✅

**File:** `agents/debugger_agent.py`

```python
def debug_and_repair(self,
                    sql_code: str,
                    error_message: str,
                    object_name: str,
                    object_type: str,
                    error_history: List[Dict],
                    oracle_code: Optional[str] = None) -> Dict[str, Any]:
    """
    Debug and repair SQL code using ALL available resources

    Resources used:
    1. Oracle original code
    2. Current SQL Server code
    3. Error history from previous attempts
    4. Shared memory (similar errors, patterns)
    5. SQL Server metadata from memory
    6. External web search results
    """

    logger.info(f"Debugging {object_name}: {error_message[:100]}...")

    # Build comprehensive context
    print(f"       🔍 Analyzing error with all available resources...")
    print(f"          - Oracle code: {'✓' if oracle_code else '✗'}")
    print(f"          - Error history: {len(error_history)} attempts")

    # Get memory context
    print(f"          - Memory: Searching similar solutions...")
    memory_context = self._get_memory_context(object_name, error_message)

    # Get web search results
    print(f"          - Web search: Looking for solutions...")
    web_context = self.search_error_solution(error_message)

    # Get SQL Server metadata
    print(f"          - SQL Server metadata: Checking schema...")
    metadata_context = self._get_sqlserver_metadata(object_name, object_type)

    # Build comprehensive context
    full_context = self.get_comprehensive_context(
        object_name=object_name,
        error_message=error_message,
        oracle_code=oracle_code,
        error_history=error_history
    )

    # Create detailed prompt
    prompt = f"""You are a SQL Server migration expert. Fix the following T-SQL code that failed to deploy.

**COMPREHENSIVE CONTEXT:**
{full_context}

**CURRENT ERROR:**
```
{error_message}
```

**FAILED SQL CODE:**
```sql
{sql_code}
```

**YOUR TASK:**
1. Analyze the error using ALL provided context
2. Identify the root cause
3. Generate corrected SQL code
4. Explain what you fixed

**IMPORTANT RULES:**
- Return ONLY valid T-SQL code
- Start with CREATE or ALTER statement
- Do NOT use GO statements in procedures/functions
- Do NOT use backticks (`)
- Use proper T-SQL syntax
- Handle existing objects appropriately
- Consider previous attempt failures

**RESPONSE FORMAT:**
Provide explanation first, then corrected code.
"""

    try:
        response = self.model.invoke([{"role": "user", "content": prompt}])

        # Track cost
        if self.cost_tracker:
            self.cost_tracker.track_request(
                model=CLAUDE_SONNET_MODEL,
                input_tokens=len(prompt.split()) * 1.3,
                output_tokens=len(response.content.split()) * 1.3
            )

        # Extract SQL from response
        repaired_sql = self._extract_sql_from_response(response.content)

        logger.info(f"Generated repair attempt {len(error_history) + 1} for {object_name}")

        return {
            "status": "success",
            "sql": repaired_sql,
            "explanation": response.content,
            "resources_used": {
                "oracle_code": bool(oracle_code),
                "error_history": len(error_history),
                "memory": bool(memory_context),
                "web_search": bool(web_context),
                "metadata": bool(metadata_context)
            }
        }

    except Exception as e:
        logger.error(f"Repair generation failed: {e}")
        return {
            "status": "error",
            "message": str(e)
        }
```

### Phase 5: Tool Usage Analysis ✅

**File:** `agents/debugger_agent.py`

```python
def analyze_tool_usage(self, error_message: str, resources_used: Dict) -> Dict:
    """Analyze which tools/resources were most helpful"""

    analysis = {
        "error_code": self._extract_error_code(error_message),
        "resources_consulted": [],
        "recommendations": []
    }

    # Track what was used
    if resources_used.get('oracle_code'):
        analysis['resources_consulted'].append("Oracle original code")

    if resources_used.get('error_history'):
        analysis['resources_consulted'].append(f"Previous {resources_used['error_history']} attempts")

    if resources_used.get('memory'):
        analysis['resources_consulted'].append("Shared memory solutions")

    if resources_used.get('web_search'):
        analysis['resources_consulted'].append("External web resources")

    if resources_used.get('metadata'):
        analysis['resources_consulted'].append("SQL Server metadata")

    # Generate recommendations
    if not resources_used.get('web_search'):
        analysis['recommendations'].append("Consider enabling web search for better error resolution")

    if not resources_used.get('memory'):
        analysis['recommendations'].append("Build memory of successful solutions")

    return analysis
```

### Phase 6: User Interaction Flow ✅

```python
def deploy_with_user_confirmation(self,
                                 sql_code: str,
                                 object_name: str,
                                 object_type: str,
                                 sqlserver_creds: Dict,
                                 oracle_code: Optional[str] = None) -> Dict[str, Any]:
    """
    Deploy with user confirmation for existing objects
    """

    # Check if object exists
    if self.check_object_exists(object_name, object_type, sqlserver_creds):
        action = self.handle_existing_object(object_name, object_type)

        if action == 'skip':
            logger.info(f"User chose to skip {object_name}")
            return {
                "status": "skipped",
                "message": f"User skipped {object_name} (already exists)"
            }

        elif action == 'drop':
            logger.info(f"User chose to drop and recreate {object_name}")
            sql_code = self.add_drop_statement(sql_code, object_name, object_type)

        elif action == 'alter':
            logger.info(f"User chose to ALTER {object_name}")
            sql_code = sql_code.replace('CREATE ', 'ALTER ', 1)

    # Proceed with deployment
    return self.deploy_with_repair(
        sql_code=sql_code,
        object_name=object_name,
        object_type=object_type,
        sqlserver_creds=sqlserver_creds,
        oracle_code=oracle_code
    )
```

---

## Expected Output After Fixes

### Example 1: Existing Table

```
[1/5] Table: LOANS
  🔄 Orchestrating: LOANS
    📥 Step 1/5: Fetching Oracle DDL...
    🔄 Step 2/5: Converting to SQL Server...
    👁️ Step 3/5: Reviewing conversion...
    🚀 Step 4/5: Deploying to SQL Server...

⚠️  Object 'LOANS' already exists in SQL Server
   Type: TABLE

   Options:
     1. Drop and recreate
     2. Skip this object
     3. Try ALTER instead of CREATE

   Your choice (1/2/3): 1

    ✅ Deploying with DROP IF EXISTS...
    ✅ Table migration successful
```

### Example 2: Error Resolution with All Resources

```
[1/1] PACKAGE: PKG_LOAN_PROCESSOR
  🔄 Orchestrating: PKG_LOAN_PROCESSOR (PACKAGE)
    📥 Step 1/5: Fetching Oracle code...
    🔄 Step 2/5: Converting to T-SQL...
    🚀 Step 3/5: Deploying to SQL Server...
    ❌ Deployment failed: Incorrect syntax near '`'

    🔧 Auto-repair attempt 1/3
       🔍 Analyzing error with all available resources...
          - Oracle code: ✓
          - Error history: 1 attempts
          - Memory: Searching similar solutions... Found 2
          - Web search: Looking for solutions... Found 5
          - SQL Server metadata: Checking schema... ✓

       💡 Resources consulted:
          ✓ Oracle original code
          ✓ Previous 1 attempts
          ✓ Shared memory solutions (2 similar cases)
          ✓ External web resources (5 articles)
          ✓ SQL Server metadata

       🔨 Generating fix using comprehensive context...
       ✅ Fix generated - deploying...

    ✅ Package migration successful
```

---

## Implementation Priority

1. ✅ **Phase 1** - Handle existing objects (CRITICAL)
2. ✅ **Phase 2** - Add web search (HIGH)
3. ✅ **Phase 3** - Enhanced memory (HIGH)
4. ✅ **Phase 4** - Comprehensive error repair (CRITICAL)
5. ✅ **Phase 5** - Tool usage analysis (MEDIUM)
6. ✅ **Phase 6** - User interaction (HIGH)

---

## Files to Modify

| File | Changes | Priority |
|------|---------|----------|
| `agents/debugger_agent.py` | Add all enhancement methods | CRITICAL |
| `external_tools/web_search.py` | Verify/create web search integration | HIGH |
| `database/migration_memory.py` | Add find_similar_solutions method | HIGH |
| `agents/orchestrator_agent.py` | Use new deploy_with_user_confirmation | HIGH |

---

## Testing Plan

1. Run migration with existing tables
2. Verify user prompts appear
3. Test each option (drop/skip/alter)
4. Verify web search works
5. Check memory integration
6. Validate tool usage reporting

---

This plan addresses ALL your requirements! Ready to implement?
