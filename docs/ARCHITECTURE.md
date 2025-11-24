# System Architecture Documentation
## Oracle to SQL Server Migration System v2.0

## 1. Overview

This document describes the complete architecture of the Oracle → SQL Server migration system, which implements a multi-agent, AI-powered approach with SSMA integration and shared memory learning.

## 2. System Prompt v1.0 Compliance

### 2.1 Core Requirements Met

✅ **SSMA as Primary Converter**: Integrated via `ssma_agent.py` with LLM fallback  
✅ **Orchestrator Agent**: Central workflow manager in `orchestrator.py`  
✅ **Multi-Agent Architecture**: 6 specialized agents (Orchestrator, SSMA, Converter, Reviewer, Debugger, Researcher)  
✅ **Shared Memory**: Cross-agent learning system in `shared_memory.py`  
✅ **Security Compliance**: Table data never sent to LLMs, comprehensive audit logging  
✅ **Metadata Refresh**: SQL Server metadata synced after each successful deployment  
✅ **Unresolved Error Logging**: Detailed logs for failed migrations in `logs/unresolved/`  
✅ **Modular Architecture**: Pluggable connectors for future sources/targets  

## 3. Agent Architecture

### 3.1 Agent Hierarchy

```
┌───────────────────────────────────────────────────────────┐
│                   ORCHESTRATOR AGENT                      │
│   - Manages complete workflow                             │
│   - Coordinates all other agents                          │
│   - Updates shared memory                                 │
│   - Handles error escalation                              │
└─────────────┬─────────────────────────────────────────────┘
              │
    ┌─────────┴─────────┐
    │                   │
┌───▼────────┐    ┌─────▼──────┐
│ SSMA AGENT │    │   CONVERTER│
│  (Primary) │    │    AGENT   │
│            │───>│  (Fallback)│
└────────────┘    └─────┬──────┘
                        │
              ┌─────────┴─────────┐
              │                   │
        ┌─────▼──────┐     ┌──────▼─────┐
        │  REVIEWER  │     │  DEBUGGER  │
        │   AGENT    │<────│   AGENT    │
        └────────────┘     └──────┬─────┘
                                  │
                           ┌──────▼─────┐
                           │ RESEARCHER │
                           │   AGENT    │
                           └──────┬─────┘
                                  │
                           ┌──────▼─────┐
                           │   SHARED   │
                           │   MEMORY   │
                           └────────────┘
```

### 3.2 Agent Responsibilities

#### 3.2.1 Orchestrator Agent (`orchestrator.py`)
**Purpose**: Central workflow coordinator

**Responsibilities**:
- Manage complete migration workflow for each object
- Coordinate execution order: Discovery → Conversion → Review → Deploy → Memory Update
- Handle agent selection (SSMA vs LLM)
- Update shared memory after successful deployments
- Log unresolved errors
- Collect statistics and generate reports

**Key Methods**:
```python
orchestrate_table_migration(table_name) -> Dict
orchestrate_code_object_migration(obj_name, obj_type) -> Dict
_refresh_and_update_memory(obj_name, obj_type)
_log_unresolved_error(obj_name, obj_type, error_history, ...)
```

#### 3.2.2 SSMA Agent (`ssma_agent.py`)
**Purpose**: Primary rule-based conversion tool

**Responsibilities**:
- Execute Microsoft SSMA for Oracle conversions
- Parse SSMA output, warnings, and errors
- Determine if LLM fallback is needed
- Batch process multiple objects
- Generate conversion statistics

**Decision Logic**:
```python
Use LLM Fallback if:
- SSMA returns errors
- SSMA produces no output
- More than 5 warnings
- Critical warnings detected ("not supported", "cannot convert")
```

**Key Methods**:
```python
convert_object(oracle_code, object_name, object_type) -> Dict
_should_use_llm_fallback(tsql, warnings, errors, returncode) -> bool
convert_batch(objects) -> List[Dict]
```

#### 3.2.3 Converter Agent (`ai_converter.py`)
**Purpose**: LLM-based code conversion (fallback)

**Responsibilities**:
- Convert Oracle PL/SQL to SQL Server T-SQL
- Convert Oracle DDL to SQL Server DDL
- Handle complex syntax transformations
- Apply Oracle → SQL Server mappings
- Sanitize output for deployment

**Model**: Claude Sonnet 4

**Key Functions**:
```python
convert_code(oracle_code, object_name, object_type, cost_tracker) -> str
convert_table_ddl(oracle_ddl, table_name, cost_tracker) -> str
tsql_sanitize(sql_text, obj_type) -> str
```

#### 3.2.4 Reviewer Agent (`ai_converter.py::reflect_code`)
**Purpose**: Quality assurance and best practices validation

**Responsibilities**:
- Review converted T-SQL for quality
- Check SQL Server 2022 compliance
- Identify potential issues
- Provide structured feedback
- Recommend improvements

**Model**: Claude Opus 4

**Output Structure**:
```json
{
  "overall_quality": "excellent|good|needs_improvement|poor",
  "approval_status": "approved|requires_changes",
  "issues_found": [
    {"severity": "critical|major|minor", "description": "..."}
  ],
  "summary": "..."
}
```

#### 3.2.5 Debugger Agent (`ai_converter.py::try_deploy_with_repair`)
**Purpose**: Automatic error repair

**Responsibilities**:
- Analyze SQL Server deployment errors
- Generate repair attempts (up to MAX_REPAIR_ATTEMPTS)
- Use error history for context
- Integrate web search solutions
- Apply learned patterns from memory
- Track repair iterations

**Repair Loop**:
```
1. Deploy → Error
2. Analyze error message
3. Check shared memory for known solutions
4. Search web for expert solutions (first error only)
5. Build comprehensive repair prompt with:
   - Current error
   - Error history
   - Web search results
   - Original Oracle code
   - Object-type specific guidance
6. Generate fix with LLM
7. Sanitize and retry deployment
8. Repeat up to MAX_REPAIR_ATTEMPTS times
```

**Key Function**:
```python
try_deploy_with_repair(
    sqlserver_creds, sql_code, obj_name, obj_type,
    llm, cost_tracker, original_oracle_code
) -> Dict
```

#### 3.2.6 Researcher Agent (`web_search_helper.py`)
**Purpose**: Web search for error solutions

**Responsibilities**:
- Search web for SQL Server error solutions
- Parse and rank search results
- Format results for LLM consumption
- Provide expert solutions from community

**Search Strategy**:
```python
Query = "SQL Server 2022 [object_type] error solution '[error_snippet]'"
Sources: Stack Overflow, Microsoft Docs, DBA StackExchange, blogs
Max Results: 5
Ranking: By relevance score
```

**Key Methods**:
```python
search_error_solution(error_message, object_type, context) -> Dict
format_search_results_for_llm(search_results) -> str
```

## 4. Shared Memory System

### 4.1 Purpose
Cross-agent learning system that stores patterns, solutions, and metadata to improve migration quality over time.

### 4.2 Memory Components

#### Schemas (`Dict[str, Any]`)
```python
{
  "sqlserver.dbo": {
    "database": "sqlserver",
    "schema": "dbo",
    "exists": True,
    "created_at": "2025-01-17T10:30:00",
    "last_verified": "2025-01-17T10:35:00"
  }
}
```

#### Identity Columns (`Dict[str, List[str]]`)
```python
{
  "EMPLOYEES": ["EMPLOYEE_ID"],
  "DEPARTMENTS": ["DEPT_ID", "LOCATION_ID"]
}
```

#### Error Solutions (`Dict[str, List[Dict]]`)
```python
{
  "schema_does_not_exist": [
    {
      "solution": "CREATE SCHEMA [schema_name]",
      "object_type": "TABLE",
      "success_count": 5,
      "timestamp": "2025-01-17T10:40:00",
      "context": {...}
    }
  ]
}
```

#### Successful Patterns (`List[Dict]`)
```python
[
  {
    "name": "PROCEDURE_GET_EMPLOYEE",
    "object_type": "PROCEDURE",
    "oracle_code_sample": "CREATE OR REPLACE PROCEDURE...",
    "tsql_sample": "CREATE PROCEDURE...",
    "review_quality": "excellent",
    "timestamp": "2025-01-17T10:45:00"
  }
]
```

#### Table Mappings (`Dict[str, Dict]`)
```python
{
  "HR.EMPLOYEES": {
    "sqlserver_table": "EMPLOYEES",
    "schema": "dbo",
    "mapped_at": "2025-01-17T10:50:00"
  }
}
```

### 4.3 Memory Operations

```python
# Register identity column
memory.register_identity_column("EMPLOYEES", "EMPLOYEE_ID")

# Store error solution
memory.store_error_solution(error_msg, {
    "fix": "SET IDENTITY_INSERT ON",
    "object_type": "TABLE"
})

# Get known solutions
solutions = memory.get_error_solutions(error_msg, limit=5)

# Store successful pattern
memory.store_successful_pattern({
    "name": "proc_example",
    "object_type": "PROCEDURE",
    ...
})

# Check schema existence
if memory.schema_exists("sqlserver", "dbo"):
    # Use existing schema
```

### 4.4 Persistence
- File: `output/shared_memory.json`
- Auto-saved after each operation
- Loaded at system startup
- Survives across migration sessions

## 5. Security Architecture

### 5.1 Data Protection Rules

#### STRICT RULES:
1. **NEVER** send table row data to LLMs
2. **NEVER** send sensitive values to LLMs
3. **ALWAYS** mask credentials in logs
4. **ALWAYS** log data access events

#### What LLMs Can Access:
✅ DDL (CREATE TABLE statements)  
✅ Object code (procedures, functions, triggers)  
✅ Schema metadata (column names, types, constraints)  
✅ Error messages  
✅ SSMA logs  

#### What LLMs Cannot Access:
❌ Actual table row data  
❌ Sensitive values in data  
❌ Connection credentials  
❌ Passwords  

### 5.2 Security Logging

```python
# Log data migration (NO LLM involvement)
SecurityLogger.log_data_access(
    operation="migrate",
    table_name="EMPLOYEES",
    row_count=1000
)
# Output: DATA_ACCESS: operation=migrate, table=EMPLOYEES, rows=1000, llm_involved=False

# Log credential usage (masked)
SecurityLogger.log_credential_usage(
    credential_type="oracle",
    masked_value="ap****"
)
```

### 5.3 Security Configuration

```python
# config_enhanced.py
ALLOW_TABLE_DATA_TO_LLM = False  # NEVER change
LOG_SECURITY_EVENTS = True
MASK_CREDENTIALS_IN_LOGS = True
```

## 6. Migration Workflow

### 6.1 Complete Workflow Diagram

```
START
  │
  ├─> 1. CONNECT TO DATABASES
  │     ├─> Collect credentials
  │     ├─> Validate connections
  │     └─> Log security events
  │
  ├─> 2. INITIALIZE ORCHESTRATOR
  │     ├─> Create orchestrator instance
  │     ├─> Check SSMA availability
  │     └─> Load shared memory
  │
  ├─> 3. DISCOVER SCHEMAS
  │     ├─> Query Oracle metadata
  │     ├─> Create SQL Server schemas
  │     └─> Update shared memory
  │
  ├─> 4. USER SELECTION
  │     ├─> List tables, procedures, functions, triggers
  │     ├─> User selects objects to migrate
  │     └─> Data migration option
  │
  ├─> 5. MIGRATE OBJECTS (for each object)
  │     │
  │     ├─> 5a. FETCH ORACLE SOURCE
  │     │     └─> Get DDL or code from Oracle
  │     │
  │     ├─> 5b. CONVERT
  │     │     ├─> Try SSMA (if available)
  │     │     │     ├─> Success? → Use SSMA output
  │     │     │     └─> Fail/Warn? → LLM Converter
  │     │     └─> Apply schema fixes
  │     │
  │     ├─> 5c. REVIEW
  │     │     ├─> Reviewer Agent validates
  │     │     └─> Return quality assessment
  │     │
  │     ├─> 5d. DEPLOY WITH REPAIR LOOP
  │     │     ├─> Attempt deployment
  │     │     ├─> Success? → Go to 5e
  │     │     └─> Error? → Repair Loop:
  │     │           ├─> Analyze error
  │     │           ├─> Search web (first error)
  │     │           ├─> Check shared memory
  │     │           ├─> Generate fix with Debugger
  │     │           ├─> Retry deployment
  │     │           └─> Repeat up to MAX_REPAIR_ATTEMPTS
  │     │
  │     ├─> 5e. REFRESH METADATA (if success)
  │     │     ├─> Query SQL Server for object metadata
  │     │     ├─> Detect identity columns
  │     │     ├─> Update shared memory
  │     │     └─> Store successful pattern
  │     │
  │     └─> 5f. LOG UNRESOLVED (if all attempts fail)
  │           ├─> Create detailed error log
  │           ├─> Save to logs/unresolved/
  │           └─> Store failed pattern in memory
  │
  ├─> 6. MIGRATE DATA (if requested)
  │     ├─> SECURITY: Direct DB-to-DB transfer
  │     ├─> Use identity insert if needed
  │     ├─> Log data access (NO LLM)
  │     └─> Batch insert with error handling
  │
  └─> 7. GENERATE REPORT
        ├─> Collect statistics
        ├─> Calculate costs
        ├─> Generate JSON report
        ├─> Print summary
        └─> Save to output/

END
```

### 6.2 Repair Loop Detail

```
DEPLOY ATTEMPT 1
  │
  └─> SQL Server Error: "Incorrect syntax near 'BEGIN'"
        │
        ├─> Analyze error
        ├─> Web Search: "SQL Server 2022 PROCEDURE error syntax BEGIN"
        │     └─> Found 5 solutions from Stack Overflow, Microsoft Docs
        │
        ├─> Check Shared Memory
        │     └─> Found 2 similar error solutions
        │
        ├─> Build Repair Prompt:
        │     ├─> Current error with line number
        │     ├─> Web search results (prioritized)
        │     ├─> Previous attempt's code
        │     ├─> Original Oracle code
        │     ├─> Object-type specific rules
        │     └─> Shared memory patterns
        │
        ├─> Debugger Agent → Generate Fix
        │     └─> Returns corrected T-SQL
        │
        └─> DEPLOY ATTEMPT 2
              │
              ├─> Success? → Update Memory → DONE
              └─> Error? → Continue to Attempt 3
```

## 7. Error Handling & Escalation

### 7.1 Error Levels

1. **Recoverable** (handled by repair loop)
   - Syntax errors
   - Type mismatches
   - Missing schema references
   - Function name differences

2. **Semi-Recoverable** (may require human intervention)
   - Complex logic transformations
   - Unsupported Oracle features
   - Performance-critical rewrites

3. **Unrecoverable** (logged for manual review)
   - Fundamental incompatibilities
   - Business logic requiring domain knowledge
   - Security/compliance issues

### 7.2 Unresolved Error Log Format

```json
{
  "object_name": "CALCULATE_BONUS",
  "object_type": "FUNCTION",
  "timestamp": "2025-01-17T11:00:00",
  "oracle_code": "CREATE OR REPLACE FUNCTION...",
  "error_history": [
    {
      "attempt": 1,
      "error": "Cannot use TRY/CATCH in scalar functions",
      "code_attempted": "CREATE FUNCTION..."
    },
    {
      "attempt": 2,
      "error": "RETURN statement must be scalar",
      "code_attempted": "CREATE FUNCTION..."
    }
  ],
  "final_sql_attempt": "CREATE FUNCTION...",
  "total_repair_attempts": 3,
  "unresolved_reason": "Max repair attempts exceeded",
  "memory_context": {
    "identity_columns": [],
    "similar_patterns": ["func_get_salary", "func_calculate_tax"],
    "error_solutions_available": 2
  },
  "recommendations": [
    "Review error history for patterns",
    "Consider converting to inline table-valued function",
    "Check if scalar function can be rewritten as computed column"
  ]
}
```

### 7.3 Error Escalation Path

```
Error Occurs
  │
  ├─> Attempt 1: Basic repair with web search
  │     └─> Success? → DONE
  │
  ├─> Attempt 2: Advanced repair with memory patterns
  │     └─> Success? → DONE
  │
  ├─> Attempt 3: Final attempt with all context
  │     └─> Success? → DONE
  │
  └─> All Failed
        ├─> Create unresolved error log
        ├─> Store in logs/unresolved/
        ├─> Update shared memory with failed pattern
        ├─> Continue with next object
        └─> Include in final report
```

## 8. Modular Architecture for Future Extensions

### 8.1 Pluggable Source Connectors

```
/connectors/
  ├─ /oracle/
  │    ├─ discovery.py      # Oracle-specific discovery
  │    ├─ extractor.py      # Oracle metadata extraction
  │    └─ connector.py      # Oracle connection management
  │
  ├─ /mysql/  (future)
  │    ├─ discovery.py
  │    ├─ extractor.py
  │    └─ connector.py
  │
  └─ /postgresql/  (future)
       ├─ discovery.py
       ├─ extractor.py
       └─ connector.py
```

### 8.2 Pluggable Target Connectors

```
/targets/
  ├─ /sqlserver/
  │    ├─ deployer.py       # SQL Server deployment
  │    ├─ validator.py      # SQL Server validation
  │    └─ metadata.py       # SQL Server metadata refresh
  │
  ├─ /postgresql/  (future)
  │    ├─ deployer.py
  │    ├─ validator.py
  │    └─ metadata.py
  │
  └─ /snowflake/  (future)
       ├─ deployer.py
       ├─ validator.py
       └─ metadata.py
```

### 8.3 Converter Plugins

```
/converters/
  ├─ /ssma/
  │    └─ ssma_agent.py     # SSMA integration
  │
  ├─ /llm/
  │    ├─ anthropic_converter.py
  │    ├─ openai_converter.py
  │    └─ custom_converter.py
  │
  └─ /rule_based/  (future)
       └─ custom_rules.py
```

## 9. Performance Considerations

### 9.1 Optimization Strategies

1. **Batch Processing**: Process multiple objects in parallel (future)
2. **Caching**: Cache SSMA results for identical code
3. **Memory Efficiency**: Stream large table data instead of loading all
4. **API Rate Limiting**: Respect LLM API rate limits
5. **Connection Pooling**: Reuse database connections

### 9.2 Cost Optimization

1. **SSMA First**: Use free SSMA before expensive LLM calls
2. **Smart Fallback**: Only use LLM when SSMA truly fails
3. **Efficient Prompts**: Minimize token usage in prompts
4. **Model Selection**: Use cheaper Sonnet for conversion, Opus only for review
5. **Web Search**: One search per object failure (not per repair attempt)

## 10. Testing Strategy

### 10.1 Unit Tests
- Test each agent independently
- Mock database connections
- Mock LLM responses
- Test shared memory operations

### 10.2 Integration Tests
- Test complete workflow end-to-end
- Test error recovery
- Test memory persistence
- Test SSMA integration

### 10.3 Test Cases
- Simple table migration
- Complex procedure with cursors
- Function with error handling
- Trigger with INSERTED/DELETED
- Failed migration with repair
- Unresolved error logging

## 11. Monitoring & Observability

### 11.1 Logs

- `logs/migration.log`: Main system log
- `logs/security.log`: Security events
- `logs/ssma.log`: SSMA operations
- `logs/unresolved/*.json`: Failed migrations

### 11.2 Metrics

- Migration success rate
- Average repair attempts
- SSMA vs LLM usage ratio
- API costs per object
- Migration duration
- Memory growth rate

### 11.3 Tracing

- LangSmith integration for LLM call tracing
- Full workflow traceability
- Error tracking and analysis

## 12. Deployment

### 12.1 Prerequisites
- Python 3.9+
- Oracle client libraries
- SQL Server ODBC driver
- Optional: SSMA for Oracle

### 12.2 Installation Steps
```bash
git clone <repo>
cd oracle-sqlserver-migration
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with API keys
python main_v2.py
```

### 12.3 Production Considerations
- Secure credential management (Azure Key Vault, AWS Secrets Manager)
- Dedicated migration server
- Network security (VPN, firewall rules)
- Backup strategy before migration
- Rollback plan
- Performance baseline testing

---

**Document Version**: 2.0  
**Last Updated**: 2025-01-17  
**Author**: AI Migration System Team
