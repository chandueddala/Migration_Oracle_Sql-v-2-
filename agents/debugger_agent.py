"""
Debugger Agent
Automatically debugs and repairs SQL Server deployment errors

This agent:
- Analyzes SQL Server error messages
- Searches for solutions (web + memory)
- Generates fixes
- Retries deployment
"""

import logging
from typing import Dict, Any, List, Optional
from langchain_anthropic import ChatAnthropic
from config.config_enhanced import CLAUDE_SONNET_MODEL, CostTracker, MAX_REPAIR_ATTEMPTS

logger = logging.getLogger(__name__)


class DebuggerAgent:
    """
    Agent responsible for debugging and repairing SQL Server errors
    Uses Claude Sonnet for efficient error analysis and repair
    """
    
    def __init__(self, cost_tracker: CostTracker = None, migration_options: Dict = None):
        self.model = ChatAnthropic(
            model=CLAUDE_SONNET_MODEL,
            temperature=0.1,  # Low temperature for consistent fixes
            max_tokens=8192
        )
        self.cost_tracker = cost_tracker
        self.migration_options = migration_options or {}
        self.max_attempts = MAX_REPAIR_ATTEMPTS
        logger.info(f"Debugger Agent initialized (max {self.max_attempts} attempts)")

    def deploy_with_repair(self,
                          sql_code: str,
                          object_name: str,
                          object_type: str,
                          sqlserver_creds: Dict,
                          oracle_code: Optional[str] = None) -> Dict[str, Any]:
        """
        Deploy SQL code to SQL Server with automatic repair on errors

        Args:
            sql_code: T-SQL code to deploy
            object_name: Name of the object
            object_type: Type (TABLE, PROCEDURE, FUNCTION, TRIGGER, PACKAGE)
            sqlserver_creds: SQL Server credentials
            oracle_code: Original Oracle code (optional)

        Returns:
            Deployment result
        """
        from database.sqlserver_connector import SQLServerConnector

        error_history = []

        for attempt in range(1, self.max_attempts + 1):
            logger.info(f"Deployment attempt {attempt}/{self.max_attempts} for {object_name}")

            # Try to deploy
            try:
                sqlserver_conn = SQLServerConnector(sqlserver_creds)
                if not sqlserver_conn.connect():
                    return {
                        "status": "error",
                        "message": "Failed to connect to SQL Server"
                    }

                result = sqlserver_conn.execute_ddl(sql_code)
                sqlserver_conn.disconnect()

                if result.get("status") == "success":
                    logger.info(f"✅ Successfully deployed {object_name}")
                    return {
                        "status": "success",
                        "message": f"Deployed {object_name} successfully",
                        "attempts": attempt
                    }
                else:
                    # Deployment failed - check if object already exists
                    error_msg = result.get("message", "Unknown error")
                    logger.warning(f"Deployment failed (attempt {attempt}): {error_msg[:100]}")

                    # Check for "object already exists" error (42S01)
                    if self._is_object_exists_error(error_msg):
                        logger.info(f"Object {object_name} already exists (detected in attempt {attempt})")
                        
                        # Check if strategy is provided in options
                        strategy = self.migration_options.get('conflict_strategy')
                        
                        if strategy:
                            logger.info(f"Using configured conflict strategy: {strategy}")
                            if strategy == 'SKIP_EXISTING':
                                user_choice = 'skip'
                            elif strategy == 'DROP_AND_CREATE':
                                user_choice = 'drop'
                            elif strategy == 'CREATE_OR_ALTER':
                                # Try to convert to CREATE OR ALTER if possible, else drop
                                user_choice = 'drop' 
                            elif strategy == 'FAIL_ON_CONFLICT':
                                return {
                                    "status": "error",
                                    "message": f"Object {object_name} already exists (FAIL_ON_CONFLICT selected)"
                                }
                            else:
                                # Default fallback
                                user_choice = 'drop'
                        else:
                            # Interactive prompt (legacy/CLI mode)
                            logger.info(f"No strategy configured - prompting user")
                            
                            # Import here to avoid circular dependency
                            from utils.user_prompt import prompt_existing_object
    
                            user_choice = prompt_existing_object(
                                object_name=object_name,
                                object_type=object_type,
                                timeout=30
                            )

                        if user_choice == 'skip':
                            logger.info(f"User chose to skip {object_name}")
                            return {
                                "status": "skipped",
                                "message": f"Skipped {object_name} (user choice)",
                                "user_action": "skip"
                            }
                        elif user_choice == 'drop':
                            logger.info(f"User chose to drop and recreate {object_name}")
                            # Prepend DROP statement to SQL
                            if object_type.upper() == "TABLE":
                                sql_code = f"DROP TABLE IF EXISTS [{object_name}];\n{sql_code}"
                            elif object_type.upper() in ["PROCEDURE", "PROC"]:
                                sql_code = f"DROP PROCEDURE IF EXISTS [{object_name}];\n{sql_code}"
                            elif object_type.upper() == "FUNCTION":
                                sql_code = f"DROP FUNCTION IF EXISTS [{object_name}];\n{sql_code}"
                            elif object_type.upper() == "TRIGGER":
                                sql_code = f"DROP TRIGGER IF EXISTS [{object_name}];\n{sql_code}"
                            elif object_type.upper() == "VIEW":
                                sql_code = f"DROP VIEW IF EXISTS [{object_name}];\n{sql_code}"

                            # Retry deployment with DROP statement
                            continue
                        elif user_choice == 'append':
                            logger.info(f"User chose to append data to existing {object_name}")
                            # For tables, skip structure creation and go straight to data migration
                            return {
                                "status": "success",
                                "message": f"Table {object_name} exists - will append data",
                                "user_action": "append",
                                "skip_structure": True
                            }

                    error_history.append({
                        "attempt": attempt,
                        "sql": sql_code,
                        "error": error_msg
                    })

                    if attempt < self.max_attempts:
                        # Try to repair using AGENTIC approach
                        repair_result = self.debug_and_repair(
                            sql_code=sql_code,
                            error_message=error_msg,
                            object_name=object_name,
                            object_type=object_type,
                            error_history=error_history,
                            web_search_results=None,
                            memory_solutions=[],
                            cost_tracker=self.cost_tracker,
                            oracle_code=oracle_code,
                            sqlserver_creds=sqlserver_creds
                        )

                        if repair_result.get("status") == "success":
                            sql_code = repair_result.get("fixed_sql", sql_code)
                            logger.info(f"Generated repair for {object_name}")
                        else:
                            logger.error(f"Repair failed: {repair_result.get('message')}")
                            break
                    else:
                        logger.error(f"Max attempts ({self.max_attempts}) reached for {object_name}")
                        break

            except Exception as e:
                logger.error(f"Deployment error: {e}")
                return {
                    "status": "error",
                    "message": str(e)
                }

        # All attempts failed
        return {
            "status": "error",
            "message": f"Failed to deploy after {self.max_attempts} attempts",
            "error_history": error_history
        }

    def debug_and_repair(self,
                        sql_code: str,
                        error_message: str,
                        object_name: str,
                        object_type: str,
                        error_history: List[Dict],
                        web_search_results: Optional[str],
                        memory_solutions: List[Dict],
                        cost_tracker: CostTracker,
                        oracle_code: Optional[str] = None,
                        sqlserver_creds: Optional[Dict] = None) -> Dict[str, Any]:
        """
        AGENTIC ERROR REPAIR - Uses intelligent Root Cause Analyzer

        This method uses a multi-step agentic approach:
        1. Classify error intelligently
        2. Gather context from multiple sources (Oracle + SQL + Memory + Web)
        3. Perform root cause analysis
        4. Generate targeted fix based on deep understanding

        Args:
            sql_code: Failed SQL code
            error_message: SQL Server error message
            object_name: Object name
            object_type: TABLE, PROCEDURE, FUNCTION, TRIGGER
            error_history: List of previous attempts
            web_search_results: Results from web search (will be gathered if needed)
            memory_solutions: Known solutions from memory
            cost_tracker: Cost tracking
            oracle_code: Original Oracle code (optional)
            sqlserver_creds: SQL Server credentials for metadata gathering

        Returns:
            Repair result with fixed SQL
        """
        logger.info(f"🤖 Starting AGENTIC repair for {object_name}: {error_message[:100]}...")

        attempt_num = len(error_history) + 1

        if attempt_num > self.max_attempts:
            logger.error(f"Max repair attempts ({self.max_attempts}) exceeded for {object_name}")
            return {
                "status": "error",
                "message": f"Max repair attempts exceeded",
                "fixed_sql": sql_code
            }

        # Use Root Cause Analyzer for intelligent, agentic repair
        try:
            from agents.root_cause_analyzer import RootCauseAnalyzer

            print(f"\n       🤖 AGENTIC REPAIR MODE - Attempt {attempt_num}/{self.max_attempts}")
            print(f"       📝 Using multi-step root cause analysis...")

            # Initialize Root Cause Analyzer
            analyzer = RootCauseAnalyzer(cost_tracker=cost_tracker)

            # Perform intelligent analysis and fix generation
            analysis_result = analyzer.analyze_and_fix(
                sql_code=sql_code,
                error_message=error_message,
                object_name=object_name,
                object_type=object_type,
                oracle_code=oracle_code,
                sqlserver_creds=sqlserver_creds
            )

            if analysis_result.get("status") == "success":
                # Safely get fixed_sql, defaulting to None if missing
                fix_data = analysis_result.get("fix", {})
                fixed_sql = fix_data.get("fixed_sql")
                
                if not fixed_sql:
                    logger.warning("Analysis successful but 'fixed_sql' missing")
                    # Fall through to fallback repair
                else:
                    root_cause = analysis_result["root_cause"]

                    print(f"       ✅ Root Cause: {root_cause['diagnosis'][:100]}")
                    print(f"       🔧 Confidence: {root_cause['confidence']}")
                    print(f"       📊 Fix Strategy: {analysis_result['fix']['strategy']}")

                    logger.info(f"Agentic repair generated for {object_name} (attempt {attempt_num})")

                    return {
                        "status": "success",
                        "fixed_sql": fixed_sql,
                        "attempt_num": attempt_num,
                        "root_cause": root_cause['diagnosis'],
                        "confidence": root_cause['confidence'],
                        "analysis": analysis_result,
                        "method": "agentic_root_cause_analysis"
                    }
            
            # Fallback if status not success OR fixed_sql missing
            logger.warning(f"Root Cause Analyzer failed or returned no fix, falling back to standard repair")
            # Fall back to standard repair if analyzer fails
            return self._fallback_repair(
                sql_code=sql_code,
                error_message=error_message,
                object_name=object_name,
                object_type=object_type,
                error_history=error_history,
                oracle_code=oracle_code,
                cost_tracker=cost_tracker,
                attempt_num=attempt_num
            )

        except ImportError:
            logger.warning("Root Cause Analyzer not available, using standard repair")
            return self._fallback_repair(
                sql_code=sql_code,
                error_message=error_message,
                object_name=object_name,
                object_type=object_type,
                error_history=error_history,
                oracle_code=oracle_code,
                cost_tracker=cost_tracker,
                attempt_num=attempt_num
            )
        except Exception as e:
            logger.error(f"Agentic repair failed: {e}", exc_info=True)
            return self._fallback_repair(
                sql_code=sql_code,
                error_message=error_message,
                object_name=object_name,
                object_type=object_type,
                error_history=error_history,
                oracle_code=oracle_code,
                cost_tracker=cost_tracker,
                attempt_num=attempt_num
            )

    def _fallback_repair(self,
                        sql_code: str,
                        error_message: str,
                        object_name: str,
                        object_type: str,
                        error_history: List[Dict],
                        oracle_code: Optional[str],
                        cost_tracker: CostTracker,
                        attempt_num: int) -> Dict[str, Any]:
        """Fallback to basic repair if agentic approach unavailable"""
        logger.info(f"Using fallback repair method for {object_name}")

        # Build comprehensive repair prompt
        prompt = self._build_repair_prompt(
            sql_code=sql_code,
            error_message=error_message,
            object_name=object_name,
            object_type=object_type,
            error_history=error_history,
            web_search_results=None,
            memory_solutions=[],
            oracle_code=oracle_code,
            attempt_num=attempt_num
        )

        try:
            response = self.model.invoke(prompt)
            result_text = response.content

            # Track cost
            cost_tracker.add("anthropic", CLAUDE_SONNET_MODEL, prompt, result_text)

            # Extract fixed SQL
            fixed_sql = self._extract_sql(result_text, object_type)

            logger.info(f"Generated fallback repair attempt {attempt_num} for {object_name}")

            return {
                "status": "success",
                "fixed_sql": fixed_sql,
                "attempt_num": attempt_num,
                "explanation": result_text[:500],
                "method": "fallback_repair"
            }

        except Exception as e:
            logger.error(f"Fallback repair generation failed for {object_name}: {e}", exc_info=True)
            return {
                "status": "error",
                "message": str(e),
                "fixed_sql": sql_code  # Return original as fallback
            }
    
    def _build_repair_prompt(self, 
                            sql_code: str,
                            error_message: str,
                            object_name: str,
                            object_type: str,
                            error_history: List[Dict],
                            web_search_results: Optional[str],
                            memory_solutions: List[Dict],
                            oracle_code: Optional[str],
                            attempt_num: int) -> str:
        """Build comprehensive repair prompt"""
        
        prompt = f"""You are an expert SQL Server DBA fixing deployment errors.

OBJECT: {object_name} ({object_type})
ATTEMPT: {attempt_num}/{self.max_attempts}

CURRENT ERROR:
{error_message}

FAILED SQL CODE:
```sql
{sql_code}
```
"""

        # Add error history
        if error_history:
            prompt += f"\n\nPREVIOUS ATTEMPTS ({len(error_history)}):\n"
            for i, hist in enumerate(error_history[-3:], 1):  # Last 3 attempts
                prompt += f"{i}. Error: {hist.get('error', 'Unknown')[:100]}\n"
        
        # Add web search results
        if web_search_results:
            prompt += f"\n\nWEB SEARCH SOLUTIONS:\n{web_search_results}\n"
        
        # Add memory solutions
        if memory_solutions:
            prompt += f"\n\nKNOWN SOLUTIONS FROM MEMORY:\n"
            for sol in memory_solutions[:3]:  # Top 3
                prompt += f"- {sol.get('solution', 'N/A')}\n"
        
        # Add original Oracle code if available
        if oracle_code:
            prompt += f"\n\nORIGINAL ORACLE CODE (for reference):\n```sql\n{oracle_code[:1000]}\n```\n"
        
        # Add object-specific guidance
        prompt += f"\n\n{object_type} SPECIFIC GUIDANCE:\n"
        if object_type == "TABLE":
            prompt += """- Ensure all column types are SQL Server compatible
- Check for IDENTITY columns vs Oracle sequences
- Verify constraint syntax
- Ensure schema exists: [dbo] or [schema_name]
"""
        elif object_type == "PROCEDURE":
            prompt += """- Use CREATE PROCEDURE not CREATE OR REPLACE
- Replace Oracle packages with schema.procedure
- Convert %TYPE and %ROWTYPE to explicit types
- Use BEGIN...END blocks properly
"""
        elif object_type == "FUNCTION":
            prompt += """- Use CREATE FUNCTION not CREATE OR REPLACE
- Ensure RETURNS clause before AS
- Use proper return syntax: RETURN value
- Check if function should be inline table-valued
- DO NOT use THROW or RAISEERROR inside functions (side-effects not allowed)
- Use RETURN NULL or specific error value instead of raising exceptions
"""
        elif object_type == "TRIGGER":
            prompt += """- Use CREATE TRIGGER not CREATE OR REPLACE
- Use INSERTED and DELETED tables not :NEW/:OLD
- Proper trigger syntax: ON table AFTER/INSTEAD OF
"""
        
        prompt += """
CRITICAL INSTRUCTIONS:
1. Analyze the error message carefully
2. Apply solutions from web search and memory if relevant
3. Fix ONLY the specific error - don't rewrite everything
4. Return ONLY the fixed SQL code, no explanations
5. Start with CREATE or ALTER, DO NOT use markdown fences (```sql)
6. Ensure SQL Server 2022 compatibility
7. Test logic before suggesting

OUTPUT: Return ONLY executable SQL code, nothing else."""

        return prompt
    
    def _extract_sql(self, response_text: str, object_type: str) -> str:
        """Extract SQL code from response"""
        
        text = response_text.strip()
        
        # Aggressive markdown stripping
        # Handle ```sql ... ```
        if "```sql" in text:
            text = text.split("```sql")[1]
            if "```" in text:
                text = text.split("```")[0]
        # Handle ``` ... ``` (no language)
        elif "```" in text:
            parts = text.split("```")
            # Find the part that looks like SQL
            for part in parts:
                clean_part = part.strip().upper()
                if clean_part.startswith(("CREATE", "ALTER", "INSERT", "UPDATE", "DELETE", "DROP")):
                    text = part
                    break
        
        text = text.strip()
        
        # Remove any leading backticks that might have survived
        text = text.replace("`", "")
        
        # Ensure it starts with CREATE or ALTER
        if not text.upper().startswith(("CREATE", "ALTER", "INSERT", "UPDATE", "DELETE", "DROP")):
            logger.warning(f"Response doesn't start with SQL keyword, attempting to extract")
            # Try to find SQL code
            lines = text.split('\n')
            for i, line in enumerate(lines):
                if line.strip().upper().startswith(("CREATE", "ALTER", "INSERT", "UPDATE", "DELETE", "DROP")):
                    text = '\n'.join(lines[i:])
                    break
        
        return text

    def _is_object_exists_error(self, error_message: str) -> bool:
        """
        Check if error is "object already exists" error

        Args:
            error_message: SQL Server error message

        Returns:
            True if object already exists error
        """
        error_patterns = [
            "42S01",  # SQLSTATE code for object already exists
            "2714",   # SQL Server error code for object already exists
            "There is already an object named",
            "already exists",
            "Cannot create",
            "object name"
        ]

        error_lower = error_message.lower()
        for pattern in error_patterns:
            if pattern.lower() in error_lower:
                return True

        return False


# Global instance
_debugger_agent = None


def get_debugger_agent() -> DebuggerAgent:
    """Get or create global debugger agent instance"""
    global _debugger_agent
    if _debugger_agent is None:
        _debugger_agent = DebuggerAgent()
    return _debugger_agent
