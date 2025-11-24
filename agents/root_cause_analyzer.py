"""
Root Cause Analyzer Agent
Multi-step intelligent error analysis using agentic workflow

This agent:
1. Analyzes the error message
2. Gathers context from multiple sources
3. Performs root cause analysis
4. Generates targeted fix

Uses a chain of thought approach rather than trying to fix everything at once.
"""

import logging
from typing import Dict, Any, List, Optional
from langchain_anthropic import ChatAnthropic
from config.config_enhanced import CLAUDE_SONNET_MODEL, CostTracker

logger = logging.getLogger(__name__)


class RootCauseAnalyzer:
    """
    Intelligent agent that performs deep root cause analysis before attempting fixes.

    Workflow:
    1. Error Classification
    2. Context Gathering (Oracle + SQL + Memory + Web)
    3. Root Cause Analysis
    4. Solution Generation
    """

    def __init__(self, cost_tracker: CostTracker = None):
        self.model = ChatAnthropic(
            model=CLAUDE_SONNET_MODEL,
            temperature=0.1,
            max_tokens=8192
        )
        self.cost_tracker = cost_tracker
        logger.info("Root Cause Analyzer initialized")

    def analyze_and_fix(self,
                       sql_code: str,
                       error_message: str,
                       object_name: str,
                       object_type: str,
                       oracle_code: Optional[str] = None,
                       sqlserver_creds: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Perform complete root cause analysis and generate fix

        Args:
            sql_code: Failed T-SQL code
            error_message: SQL Server error message
            object_name: Name of the object
            object_type: Type of object
            oracle_code: Original Oracle code (optional)
            sqlserver_creds: SQL Server credentials for metadata

        Returns:
            Analysis result with fix
        """
        print(f"\n       🔍 Starting Root Cause Analysis for {object_name}...")

        # Step 1: Classify Error
        print(f"       📋 Step 1/5: Classifying error type...")
        error_classification = self._classify_error(error_message)
        print(f"          Error Category: {error_classification['category']}")
        print(f"          Severity: {error_classification['severity']}")

        # Step 2: Gather Oracle Context
        print(f"       📊 Step 2/5: Analyzing Oracle source...")
        oracle_context = self._analyze_oracle_code(oracle_code, object_type) if oracle_code else None
        if oracle_context:
            print(f"          Oracle Features: {', '.join(oracle_context['features'][:3])}")

        # Step 3: Gather SQL Server Context
        print(f"       🗄️  Step 3/5: Gathering SQL Server metadata...")
        sql_context = self._gather_sql_context(object_name, object_type, sqlserver_creds)
        if sql_context:
            print(f"          Existing Objects: {sql_context.get('object_exists', 'Unknown')}")

        # Step 4: Search Memory & Web
        print(f"       💡 Step 4/5: Searching for similar solutions...")
        knowledge_context = self._search_knowledge_base(
            error_classification=error_classification,
            object_type=object_type
        )
        print(f"          Memory Solutions: {knowledge_context['memory_solutions']}")
        print(f"          Web Resources: {knowledge_context['web_resources']}")

        # Step 5: Root Cause Analysis
        print(f"       🎯 Step 5/5: Performing root cause analysis...")
        root_cause = self._perform_root_cause_analysis(
            error_classification=error_classification,
            oracle_context=oracle_context,
            sql_context=sql_context,
            knowledge_context=knowledge_context,
            sql_code=sql_code,
            error_message=error_message
        )

        print(f"\n       ✅ Root Cause Identified: {root_cause['diagnosis']}")
        print(f"       🔧 Confidence Level: {root_cause['confidence']}")

        # Generate Fix
        print(f"       🛠️  Generating targeted fix...")
        fix_result = self._generate_fix(
            root_cause=root_cause,
            sql_code=sql_code,
            object_name=object_name,
            oracle_code=oracle_code
        )

        return {
            "status": "success",
            "root_cause": root_cause,
            "fix": fix_result,
            "analysis_steps": {
                "error_classification": error_classification,
                "oracle_context": oracle_context,
                "sql_context": sql_context,
                "knowledge_context": knowledge_context
            }
        }

    def _classify_error(self, error_message: str) -> Dict[str, Any]:
        """
        Step 1: Classify the error type using LLM
        """
        prompt = f"""Classify this SQL Server error:

ERROR MESSAGE:
{error_message}

Analyze and classify:
1. Error Category (syntax/permission/object_exists/data_type/constraint/other)
2. Severity (critical/high/medium/low)
3. Error Code (extract from message)
4. Key Problem Indicators (list specific issues)

Respond in this format:
CATEGORY: <category>
SEVERITY: <severity>
ERROR_CODE: <code>
INDICATORS: <comma-separated list>
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

            # Parse response
            classification = self._parse_classification(response.content)
            return classification

        except Exception as e:
            logger.error(f"Error classification failed: {e}")
            return {
                "category": "unknown",
                "severity": "medium",
                "error_code": "unknown",
                "indicators": []
            }

    def _parse_classification(self, response: str) -> Dict[str, Any]:
        """Parse LLM classification response"""
        lines = response.strip().split('\n')
        result = {
            "category": "unknown",
            "severity": "medium",
            "error_code": "unknown",
            "indicators": []
        }

        for line in lines:
            line = line.strip()
            if line.startswith("CATEGORY:"):
                result["category"] = line.split(":", 1)[1].strip()
            elif line.startswith("SEVERITY:"):
                result["severity"] = line.split(":", 1)[1].strip()
            elif line.startswith("ERROR_CODE:"):
                result["error_code"] = line.split(":", 1)[1].strip()
            elif line.startswith("INDICATORS:"):
                indicators = line.split(":", 1)[1].strip()
                result["indicators"] = [i.strip() for i in indicators.split(",")]

        return result

    def _analyze_oracle_code(self, oracle_code: str, object_type: str) -> Dict[str, Any]:
        """
        Step 2: Analyze Oracle code to understand what needs to be migrated
        """
        prompt = f"""Analyze this Oracle {object_type} code:

ORACLE CODE:
```sql
{oracle_code[:2000]}
```

Identify:
1. Key Oracle-specific features used
2. Complex constructs that need translation
3. Data types used
4. Dependencies on other objects

Respond in this format:
FEATURES: <comma-separated list>
COMPLEX_CONSTRUCTS: <comma-separated list>
DATA_TYPES: <comma-separated list>
DEPENDENCIES: <comma-separated list>
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

            # Parse response
            return self._parse_oracle_analysis(response.content)

        except Exception as e:
            logger.error(f"Oracle analysis failed: {e}")
            return None

    def _parse_oracle_analysis(self, response: str) -> Dict[str, Any]:
        """Parse Oracle code analysis"""
        lines = response.strip().split('\n')
        result = {
            "features": [],
            "complex_constructs": [],
            "data_types": [],
            "dependencies": []
        }

        for line in lines:
            line = line.strip()
            if line.startswith("FEATURES:"):
                features = line.split(":", 1)[1].strip()
                result["features"] = [f.strip() for f in features.split(",")]
            elif line.startswith("COMPLEX_CONSTRUCTS:"):
                constructs = line.split(":", 1)[1].strip()
                result["complex_constructs"] = [c.strip() for c in constructs.split(",")]
            elif line.startswith("DATA_TYPES:"):
                types = line.split(":", 1)[1].strip()
                result["data_types"] = [t.strip() for t in types.split(",")]
            elif line.startswith("DEPENDENCIES:"):
                deps = line.split(":", 1)[1].strip()
                result["dependencies"] = [d.strip() for d in deps.split(",")]

        return result

    def _gather_sql_context(self,
                          object_name: str,
                          object_type: str,
                          sqlserver_creds: Optional[Dict]) -> Dict[str, Any]:
        """
        Step 3: Gather SQL Server metadata and context
        """
        if not sqlserver_creds:
            return None

        try:
            from database.sqlserver_connector import SQLServerConnector
            from database.migration_memory import MigrationMemory

            # Check if object exists
            conn = SQLServerConnector(sqlserver_creds)
            if not conn.connect():
                return None

            context = {
                "object_exists": False,
                "schema": "dbo",
                "existing_columns": [],
                "constraints": []
            }

            # Check object existence
            if object_type == "TABLE":
                check_query = """
                SELECT COUNT(*) as cnt
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_NAME = ?
                """
                cursor = conn.connection.cursor()
                cursor.execute(check_query, object_name)
                result = cursor.fetchone()
                context["object_exists"] = (result[0] > 0) if result else False

                # Get columns if table exists
                if context["object_exists"]:
                    col_query = """
                    SELECT COLUMN_NAME, DATA_TYPE
                    FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_NAME = ?
                    """
                    cursor.execute(col_query, object_name)
                    context["existing_columns"] = [
                        {"name": row[0], "type": row[1]}
                        for row in cursor.fetchall()
                    ]

                cursor.close()

            conn.disconnect()

            # Get from memory
            memory = MigrationMemory()
            if object_name in memory.table_mappings:
                context["memory"] = memory.table_mappings[object_name]

            return context

        except Exception as e:
            logger.error(f"SQL context gathering failed: {e}")
            return None

    def _search_knowledge_base(self,
                              error_classification: Dict,
                              object_type: str) -> Dict[str, Any]:
        """
        Step 4: Search memory and web for similar solutions
        """
        from database.migration_memory import MigrationMemory

        memory = MigrationMemory()
        result = {
            "memory_solutions": 0,
            "web_resources": 0,
            "solutions": []
        }

        # Search memory
        error_code = error_classification.get("error_code", "")
        similar_solutions = memory.find_similar_error_solutions(error_code)
        if similar_solutions:
            result["memory_solutions"] = len(similar_solutions)
            result["solutions"].extend(similar_solutions[:3])

        # Search web (if available)
        try:
            web_results = self._search_web_for_solution(
                error_code=error_code,
                category=error_classification.get("category", ""),
                object_type=object_type
            )
            if web_results:
                result["web_resources"] = len(web_results)
                result["solutions"].extend(web_results[:3])
        except Exception as e:
            logger.warning(f"Web search failed: {e}")

        return result

    def _search_web_for_solution(self,
                                error_code: str,
                                category: str,
                                object_type: str) -> List[Dict]:
        """Search web for solutions"""
        try:
            from external_tools.web_search import search_web

            queries = [
                f"SQL Server error {error_code} solution",
                f"Fix SQL Server {category} error {object_type}",
                f"Oracle to SQL Server {error_code} migration"
            ]

            all_results = []
            for query in queries:
                results = search_web(query, max_results=2)
                if results:
                    all_results.extend(results)

            return all_results

        except ImportError:
            logger.warning("Web search module not available")
            return []

    def _perform_root_cause_analysis(self,
                                    error_classification: Dict,
                                    oracle_context: Optional[Dict],
                                    sql_context: Optional[Dict],
                                    knowledge_context: Dict,
                                    sql_code: str,
                                    error_message: str) -> Dict[str, Any]:
        """
        Step 5: Perform comprehensive root cause analysis using all gathered context
        """
        # Build comprehensive context
        context_summary = self._build_context_summary(
            error_classification,
            oracle_context,
            sql_context,
            knowledge_context
        )

        prompt = f"""You are a database migration expert. Perform root cause analysis.

CONTEXT GATHERED:
{context_summary}

FAILED SQL CODE:
```sql
{sql_code}
```

ERROR MESSAGE:
{error_message}

Perform deep root cause analysis:
1. What is the PRIMARY root cause?
2. What specific Oracle feature is causing the issue?
3. What SQL Server limitation or difference is involved?
4. Are there similar known solutions?
5. What is the BEST approach to fix this?

Respond in this format:
DIAGNOSIS: <one-line diagnosis>
PRIMARY_CAUSE: <detailed explanation>
ORACLE_FEATURE: <specific Oracle feature>
SQL_SERVER_ISSUE: <SQL Server constraint/difference>
SIMILAR_SOLUTIONS: <reference to similar cases>
RECOMMENDED_FIX: <high-level fix strategy>
CONFIDENCE: <high/medium/low>
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

            # Parse response
            return self._parse_root_cause(response.content)

        except Exception as e:
            logger.error(f"Root cause analysis failed: {e}")
            return {
                "diagnosis": "Analysis failed",
                "confidence": "low"
            }

    def _build_context_summary(self,
                              error_classification: Dict,
                              oracle_context: Optional[Dict],
                              sql_context: Optional[Dict],
                              knowledge_context: Dict) -> str:
        """Build comprehensive context summary for LLM"""
        parts = []

        # Error classification
        parts.append(f"ERROR CLASSIFICATION:")
        parts.append(f"  Category: {error_classification.get('category', 'unknown')}")
        parts.append(f"  Severity: {error_classification.get('severity', 'unknown')}")
        parts.append(f"  Error Code: {error_classification.get('error_code', 'unknown')}")
        parts.append(f"  Indicators: {', '.join(error_classification.get('indicators', []))}")

        # Oracle context
        if oracle_context:
            parts.append(f"\nORACLE CODE ANALYSIS:")
            parts.append(f"  Features: {', '.join(oracle_context.get('features', []))}")
            parts.append(f"  Complex Constructs: {', '.join(oracle_context.get('complex_constructs', []))}")
            parts.append(f"  Data Types: {', '.join(oracle_context.get('data_types', []))}")

        # SQL Server context
        if sql_context:
            parts.append(f"\nSQL SERVER CONTEXT:")
            parts.append(f"  Object Exists: {sql_context.get('object_exists', False)}")
            if sql_context.get('existing_columns'):
                parts.append(f"  Existing Columns: {len(sql_context['existing_columns'])}")

        # Knowledge base
        parts.append(f"\nKNOWLEDGE BASE:")
        parts.append(f"  Similar Solutions in Memory: {knowledge_context.get('memory_solutions', 0)}")
        parts.append(f"  Web Resources Found: {knowledge_context.get('web_resources', 0)}")

        if knowledge_context.get('solutions'):
            parts.append(f"  Top Solutions:")
            for idx, sol in enumerate(knowledge_context['solutions'][:3], 1):
                parts.append(f"    {idx}. {sol.get('summary', 'N/A')[:100]}")

        return "\n".join(parts)

    def _parse_root_cause(self, response: str) -> Dict[str, Any]:
        """Parse root cause analysis response"""
        lines = response.strip().split('\n')
        result = {
            "diagnosis": "",
            "primary_cause": "",
            "oracle_feature": "",
            "sql_server_issue": "",
            "similar_solutions": "",
            "recommended_fix": "",
            "confidence": "medium"
        }

        current_key = None
        current_value = []

        for line in lines:
            line = line.strip()

            if line.startswith("DIAGNOSIS:"):
                if current_key and current_value:
                    result[current_key] = " ".join(current_value)
                current_key = "diagnosis"
                current_value = [line.split(":", 1)[1].strip()]
            elif line.startswith("PRIMARY_CAUSE:"):
                if current_key and current_value:
                    result[current_key] = " ".join(current_value)
                current_key = "primary_cause"
                current_value = [line.split(":", 1)[1].strip()]
            elif line.startswith("ORACLE_FEATURE:"):
                if current_key and current_value:
                    result[current_key] = " ".join(current_value)
                current_key = "oracle_feature"
                current_value = [line.split(":", 1)[1].strip()]
            elif line.startswith("SQL_SERVER_ISSUE:"):
                if current_key and current_value:
                    result[current_key] = " ".join(current_value)
                current_key = "sql_server_issue"
                current_value = [line.split(":", 1)[1].strip()]
            elif line.startswith("SIMILAR_SOLUTIONS:"):
                if current_key and current_value:
                    result[current_key] = " ".join(current_value)
                current_key = "similar_solutions"
                current_value = [line.split(":", 1)[1].strip()]
            elif line.startswith("RECOMMENDED_FIX:"):
                if current_key and current_value:
                    result[current_key] = " ".join(current_value)
                current_key = "recommended_fix"
                current_value = [line.split(":", 1)[1].strip()]
            elif line.startswith("CONFIDENCE:"):
                if current_key and current_value:
                    result[current_key] = " ".join(current_value)
                result["confidence"] = line.split(":", 1)[1].strip().lower()
                current_key = None
                current_value = []
            elif current_key and line:
                current_value.append(line)

        # Save last key
        if current_key and current_value:
            result[current_key] = " ".join(current_value)

        return result

    def _generate_fix(self,
                     root_cause: Dict,
                     sql_code: str,
                     object_name: str,
                     oracle_code: Optional[str]) -> Dict[str, Any]:
        """
        Generate targeted fix based on root cause analysis
        """
        prompt = f"""You are a SQL Server migration expert. Generate a FIX based on root cause analysis.

ROOT CAUSE ANALYSIS:
- Diagnosis: {root_cause.get('diagnosis', '')}
- Primary Cause: {root_cause.get('primary_cause', '')}
- Oracle Feature: {root_cause.get('oracle_feature', '')}
- SQL Server Issue: {root_cause.get('sql_server_issue', '')}
- Recommended Fix: {root_cause.get('recommended_fix', '')}

FAILED SQL CODE:
```sql
{sql_code}
```

{"ORIGINAL ORACLE CODE:" if oracle_code else ""}
{f"```sql\\n{oracle_code}\\n```" if oracle_code else ""}

Generate CORRECTED SQL Server code that addresses the root cause.

IMPORTANT:
- Apply the recommended fix strategy
- Address the specific Oracle feature issue
- Handle the SQL Server constraint
- Return ONLY valid T-SQL code
- No explanations, just code

CORRECTED CODE:
```sql
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

            # Extract SQL
            fixed_sql = self._extract_sql(response.content)

            return {
                "sql": fixed_sql,
                "explanation": f"Applied fix for: {root_cause.get('diagnosis', 'N/A')}",
                "confidence": root_cause.get("confidence", "medium")
            }

        except Exception as e:
            logger.error(f"Fix generation failed: {e}")
            return {
                "sql": sql_code,
                "explanation": f"Fix generation failed: {str(e)}",
                "confidence": "low"
            }

    def _extract_sql(self, response: str) -> str:
        """Extract SQL code from response"""
        # Try to find SQL code block
        if "```sql" in response:
            parts = response.split("```sql")
            if len(parts) > 1:
                sql_part = parts[1].split("```")[0]
                return sql_part.strip()

        # Try generic code block
        if "```" in response:
            parts = response.split("```")
            for part in parts[1::2]:  # Every other part is code
                if any(keyword in part.upper() for keyword in ["CREATE", "ALTER", "DROP", "SELECT", "INSERT"]):
                    return part.strip()

        # Return as-is if no code block found
        return response.strip()
