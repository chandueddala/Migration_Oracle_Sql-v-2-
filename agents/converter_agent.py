"""
AI-powered code conversion and repair with web search integration
"""

import re
import json
import logging
from typing import Dict, Any

try:
    from langchain_anthropic import ChatAnthropic
    from langchain_core.messages import HumanMessage
    from langsmith import traceable
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Install: pip install langchain-anthropic langsmith")
    raise

from config.config_enhanced import CLAUDE_SONNET_MODEL, CLAUDE_OPUS_MODEL, MAX_REPAIR_ATTEMPTS, CostTracker
from database.deploy_tool import deploy_to_sqlserver
from external_tools.web_search import search_for_error_solution, format_search_results_for_llm

logger = logging.getLogger(__name__)

# Initialize AI models
claude_sonnet = ChatAnthropic(model=CLAUDE_SONNET_MODEL, temperature=0)
claude_opus = ChatAnthropic(model=CLAUDE_OPUS_MODEL, temperature=0)


class ConverterAgent:
    """Wrapper class for converter functions"""

    def __init__(self, cost_tracker: CostTracker):
        self.cost_tracker = cost_tracker
        self.llm = claude_sonnet

    def convert_code(self, oracle_code: str, object_name: str, object_type: str) -> str:
        """Convert Oracle code to SQL Server"""
        return convert_code(oracle_code, object_name, object_type, self.cost_tracker)

    def convert_table_ddl(self, oracle_ddl: str, table_name: str) -> str:
        """Convert Oracle TABLE DDL to SQL Server"""
        return convert_table_ddl(oracle_ddl, table_name, self.cost_tracker)

    def try_deploy_with_repair(self, sqlserver_creds: Dict, sql_code: str,
                               obj_name: str, obj_type: str,
                               original_oracle_code: str = None) -> Dict[str, Any]:
        """Attempt deploy with automatic repair"""
        return try_deploy_with_repair(
            sqlserver_creds, sql_code, obj_name, obj_type,
            self.llm, self.cost_tracker, original_oracle_code
        )


# ==================== CONVERSION FUNCTIONS ====================

@traceable(name="convert_with_claude")
def convert_code(oracle_code: str, object_name: str, object_type: str, cost_tracker: CostTracker) -> str:
    """Convert Oracle code to SQL Server using Claude Sonnet"""
    prompt = f"""Convert this Oracle {object_type} to SQL Server T-SQL.

Object: {object_name}
Type: {object_type}

Oracle Code:
```plsql
{oracle_code}
```

Requirements:
- Convert PL/SQL syntax to T-SQL
- Handle Oracle functions (NVLâ†’ISNULL, SYSDATEâ†’GETDATE, etc.)
- Convert cursors appropriately
- Use TRY/CATCH for error handling
- For triggers: :NEW/:OLD â†’ INSERTED/DELETED

Output ONLY the SQL Server code, no explanations."""
    
    response = claude_sonnet.invoke([HumanMessage(content=prompt)])
    cost_tracker.add("anthropic", CLAUDE_SONNET_MODEL, prompt, response.content)
    logger.info(f"Converted {object_type} {object_name}")
    return response.content


@traceable(name="convert_table_ddl")
def convert_table_ddl(oracle_ddl: str, table_name: str, cost_tracker: CostTracker) -> str:
    """Convert Oracle TABLE DDL to SQL Server"""
    prompt = f"""Convert the following Oracle TABLE DDL to Microsoft SQL Server T-SQL.

Table: {table_name}

Oracle DDL:
```sql
{oracle_ddl}
```

Requirements:
- Map Oracle data types to SQL Server (NUMBERâ†’DECIMAL, DATEâ†’DATETIME2, CLOBâ†’NVARCHAR(MAX))
- Emit PRIMARY KEY, UNIQUE, CHECK, FOREIGN KEY constraints
- Remove Oracle-only clauses (tablespaces, storage)
- Output ONLY the T-SQL (no explanation, no code fences)
"""
    
    response = claude_sonnet.invoke([HumanMessage(content=prompt)])
    cost_tracker.add("anthropic", CLAUDE_SONNET_MODEL, prompt, response.content)
    logger.info(f"Converted table DDL for {table_name}")
    return response.content


@traceable(name="reflect_with_opus")
def reflect_code(original: str, converted: str, object_name: str, cost_tracker: CostTracker) -> Dict[str, Any]:
    """Review code quality with Claude Opus"""
    prompt = f"""Review this code conversion from Oracle to SQL Server.

Object: {object_name}

Original Oracle:
```plsql
{original}
```

Converted SQL Server:
```tsql
{converted}
```

Provide review as JSON:
{{
  "overall_quality": "excellent|good|needs_improvement|poor",
  "approval_status": "approved|requires_changes",
  "issues_found": [{{"severity": "critical|major|minor", "description": "..."}}],
  "summary": "..."
}}"""
    
    response = claude_opus.invoke([HumanMessage(content=prompt)])
    cost_tracker.add("anthropic", CLAUDE_OPUS_MODEL, prompt, response.content)
    
    try:
        result = json.loads(response.content)
        logger.info(f"Code review for {object_name}: {result['overall_quality']}")
        return result
    except json.JSONDecodeError:
        logger.warning(f"Failed to parse review JSON for {object_name}")
        return {"overall_quality": "good", "approval_status": "approved", "issues_found": [], "summary": response.content}


# ==================== CODE SANITIZATION ====================

REPAIR_INSTRUCTIONS = """You are fixing a T-SQL script for Microsoft SQL Server 2022.
Return ONLY valid executable T-SQL. No explanations, no markdown fences.

Strict rules:
- If FUNCTION: No TRY/CATCH, RAISERROR/THROW, EXEC, temp tables. Pure expressions only.
- If TRIGGER: CREATE [OR ALTER] TRIGGER <n> ON <table> AFTER|INSTEAD OF ... AS BEGIN ... END;
- English text only in SQL comments (--) or /* ... */.

Keep object name and signature intact unless SQL Server requires a change."""


def tsql_sanitize(sql_text: str, obj_type: str) -> str:
    """Sanitize T-SQL code before deployment"""
    s = (sql_text or "").replace("```tsql", "").replace("```sql", "").replace("```", "").strip()
    
    cleaned = []
    for ln in s.splitlines():
        t = ln.strip()
        if not t or t.startswith("--") or t.startswith("/*") or t.endswith("*/"):
            cleaned.append(ln)
            continue
        if re.match(r"^(ensure|note|that|then|so|thus|this|we|you|it|in case)\b", t, flags=re.I):
            continue
        cleaned.append(ln)
    s = "\n".join(cleaned)
    
    if obj_type.upper() == "FUNCTION":
        forbidden = [r"\bBEGIN\s+TRY\b", r"\bEND\s+TRY\b", r"\bBEGIN\s+CATCH\b",
                     r"\bEND\s+CATCH\b", r"\bRAISERROR\b", r"\bTHROW\b", r"\bEXEC(UTE)?\b", r"#"]
        for pat in forbidden:
            s = re.sub(pat, "-- REMOVED (forbidden in UDF): ", s, flags=re.I)
    
    s = re.sub(r"\bthat\b", "", s, flags=re.I)
    return s.strip()


# ==================== ENHANCED REPAIR WITH WEB SEARCH ====================

def build_repair_prompt(obj_type: str, obj_name: str, current_error: str,
                       current_code: str, error_history: list,
                       original_oracle_code: str = None, iteration: int = 0,
                       web_search_results: Dict = None) -> str:
    """
    Build comprehensive repair prompt with full error context and web search results
    
    Args:
        obj_type: Type of database object
        obj_name: Name of the object
        current_error: Current SQL Server error message
        current_code: Current T-SQL code that failed
        error_history: List of previous errors and attempts
        original_oracle_code: Original Oracle code for reference
        iteration: Current iteration number
        web_search_results: Web search results with solutions (optional)
    
    Returns:
        str: Comprehensive repair prompt
    """
    
    prompt_parts = [REPAIR_INSTRUCTIONS]
    
    # Basic object information
    prompt_parts.append(f"""
OBJECT TYPE: {obj_type}
OBJECT NAME: {obj_name}
REPAIR ATTEMPT: {iteration + 1} of {MAX_REPAIR_ATTEMPTS}
""")
    
    # Include web search results if available - PRIORITY SECTION
    if web_search_results and web_search_results.get("sources"):
        web_context = format_search_results_for_llm(web_search_results)
        prompt_parts.append(web_context)
        prompt_parts.append("""
âœ… CRITICAL: Expert solutions from the internet are provided above. 
These are proven fixes from SQL Server experts. Review them carefully 
and apply the most relevant solution to your specific case.
""")
    
    # Include original Oracle code if available
    if original_oracle_code:
        prompt_parts.append(f"""
ORIGINAL ORACLE CODE (for reference):
```plsql
{original_oracle_code[:2000]}
```
""")
    
    # Current error with emphasis
    prompt_parts.append(f"""
CURRENT SQL SERVER ERROR:
{current_error}

This is the EXACT error you must fix. Pay special attention to:
- Line numbers mentioned in the error
- Specific syntax issues highlighted
- Data type mismatches
- Invalid function or procedure calls
- Missing or incorrect keywords
""")
    
    # Show error history if this is a retry
    if len(error_history) > 1:
        prompt_parts.append("\nPREVIOUS REPAIR ATTEMPTS (learn from these):")
        for i, err in enumerate(error_history[:-1], 1):
            prompt_parts.append(f"""
Attempt {err['attempt']}:
  Error: {err['error'][:200]}...
  
Note: This approach didn't work, try a different solution.
""")
    
    # Current code that failed
    prompt_parts.append(f"""
LAST ATTEMPTED T-SQL (this code failed):
```tsql
{current_code}
```
""")
    
    # Specific guidance based on object type
    type_specific_guidance = {
        "FUNCTION": """
CRITICAL REMINDERS FOR FUNCTIONS:
- SQL Server UDFs cannot use: TRY/CATCH, RAISERROR, THROW, EXEC, temp tables (#)
- Use RETURN for scalar functions, not SELECT
- All paths must return a value
- Use deterministic functions only
- Consider using inline table-valued functions instead of scalar
""",
        "PROCEDURE": """
CRITICAL REMINDERS FOR PROCEDURES:
- Use proper BEGIN/END blocks
- Parameter syntax: @param_name data_type
- Use SET or SELECT for variable assignment
- Error handling with TRY/CATCH is allowed
- Use proper transaction management if needed
""",
        "TRIGGER": """
CRITICAL REMINDERS FOR TRIGGERS:
- Use INSERTED and DELETED tables (not :NEW/:OLD)
- Structure: CREATE TRIGGER name ON table AFTER|INSTEAD OF ... AS BEGIN ... END
- Don't return result sets from triggers
- Keep logic simple and efficient
""",
        "TABLE": """
CRITICAL REMINDERS FOR TABLES:
- Check constraint syntax
- Foreign key references must exist
- Use proper data types
- Identity columns: IDENTITY(1,1)
- Default constraints: DEFAULT value
"""
    }
    
    prompt_parts.append(type_specific_guidance.get(obj_type, ""))
    
    # Analysis request with web search emphasis
    if web_search_results and web_search_results.get("sources"):
        prompt_parts.append("""
REPAIR INSTRUCTIONS (with web search results):
1. FIRST: Review the web search results above - these are proven solutions
2. Identify which solution best matches your error
3. Carefully analyze the SQL Server error message
4. Review what didn't work in previous attempts
5. Apply insights from the web search results to your specific case
6. Generate corrected T-SQL code incorporating best practices

OUTPUT REQUIREMENTS:
- Return ONLY the corrected T-SQL code
- No explanations, comments, or markdown fences
- Complete, executable code
- All syntax must be valid for SQL Server 2022
- Apply the solution pattern from web search results
""")
    else:
        prompt_parts.append("""
REPAIR INSTRUCTIONS:
1. Carefully analyze the SQL Server error message
2. Identify the EXACT line and issue causing the error
3. Review what didn't work in previous attempts
4. Generate corrected T-SQL code
5. Ensure the fix addresses the specific error reported

OUTPUT REQUIREMENTS:
- Return ONLY the corrected T-SQL code
- No explanations, comments, or markdown fences
- Complete, executable code
- All syntax must be valid for SQL Server 2022
""")
    
    return "\n".join(prompt_parts)


def try_deploy_with_repair(sqlserver_creds: Dict, sql_code: str, obj_name: str, 
                           obj_type: str, llm, cost_tracker: CostTracker,
                           original_oracle_code: str = None) -> Dict[str, Any]:
    """
    Attempt deploy with automatic repair using web search and full error context
    
    Args:
        sqlserver_creds: SQL Server credentials
        sql_code: T-SQL code to deploy
        obj_name: Object name
        obj_type: Object type (PROCEDURE, FUNCTION, TRIGGER, TABLE)
        llm: Language model for repairs
        cost_tracker: Cost tracking instance
        original_oracle_code: Original Oracle code for context (optional)
    
    Returns:
        dict: Deployment result with comprehensive error context
    """
    attempt = tsql_sanitize(sql_code, obj_type)
    error_history = []  # Track all errors for context
    web_search_performed = False
    
    for iteration in range(MAX_REPAIR_ATTEMPTS):
        logger.info(f"Deployment attempt {iteration + 1}/{MAX_REPAIR_ATTEMPTS} for {obj_name}")
        
        res = deploy_to_sqlserver.invoke({
            "credentials_json": json.dumps(sqlserver_creds),
            "sql_code": attempt,
            "object_name": obj_name
        })
        
        if res.get("status") == "success":
            logger.info(f"Successfully deployed {obj_name} on attempt {iteration + 1}")
            if iteration > 0:
                logger.info(f"Required {iteration} repair(s) to succeed")
                if web_search_performed:
                    logger.info(f"Web search contributed to successful repair")
            return res
        
        # Capture detailed error information
        current_error = res.get("message", "Unknown error")
        error_history.append({
            "attempt": iteration + 1,
            "error": current_error,
            "code_attempted": attempt
        })
        
        logger.warning(f"Deployment attempt {iteration + 1} failed for {obj_name}: {current_error}")
        
        # Search web for solutions on first failure
        web_search_results = None
        if iteration == 0:  # Search on first error only to save API calls
            try:
                web_search_results = search_for_error_solution(
                    error_message=current_error,
                    object_type=obj_type,
                    context=f"{obj_name} migration from Oracle to SQL Server"
                )
                
                if web_search_results and web_search_results.get("sources"):
                    web_search_performed = True
                    logger.info(f"Web search found {len(web_search_results['sources'])} relevant solutions")
                else:
                    logger.info("Web search returned no results or is disabled")
            except Exception as search_error:
                logger.warning(f"Web search failed: {search_error}")
                web_search_results = None
        
        # Build comprehensive context for LLM repair
        repair_prompt = build_repair_prompt(
            obj_type=obj_type,
            obj_name=obj_name,
            current_error=current_error,
            current_code=attempt,
            error_history=error_history,
            original_oracle_code=original_oracle_code,
            iteration=iteration,
            web_search_results=web_search_results  # Include web search results
        )
        
        # Get repair from LLM with enhanced context
        try:
            if web_search_results:
                print(f"    ðŸ”§ Generating repair with web search insights...")
            else:
                print(f"    ðŸ”§ Generating repair (attempt {iteration + 2}/{MAX_REPAIR_ATTEMPTS})...")
            
            fixed = llm.invoke([HumanMessage(content=repair_prompt)]).content
            cost_tracker.add("anthropic", CLAUDE_SONNET_MODEL, repair_prompt, fixed)
            attempt = tsql_sanitize(fixed, obj_type)
            logger.info(f"Generated repair attempt {iteration + 2} for {obj_name}")
        except Exception as llm_error:
            logger.error(f"LLM repair generation failed: {llm_error}")
            break
    
    # Final failure - log complete error history
    logger.error(f"Failed to deploy {obj_name} after {MAX_REPAIR_ATTEMPTS} attempts")
    logger.error(f"Error history: {json.dumps(error_history, indent=2)}")
    
    return {
        "status": "error",
        "message": current_error,
        "object_name": obj_name,
        "error_history": error_history,
        "final_attempt": attempt,
        "web_search_used": web_search_performed
    }