"""
Reviewer Agent
Reviews converted SQL Server code for quality and compliance

This agent ensures that converted T-SQL meets:
- SQL Server 2022 best practices
- Performance standards
- Security requirements
- Code quality standards
"""

import logging
from typing import Dict, Any
from langchain_anthropic import ChatAnthropic
from config.config_enhanced import CLAUDE_OPUS_MODEL, CostTracker

logger = logging.getLogger(__name__)


class ReviewerAgent:
    """
    Agent responsible for reviewing converted T-SQL code
    Uses Claude Opus for high-quality reviews
    """
    
    def __init__(self, cost_tracker: CostTracker = None):
        self.model = ChatAnthropic(
            model=CLAUDE_OPUS_MODEL,
            temperature=0.2,
            max_tokens=4096
        )
        self.cost_tracker = cost_tracker
        logger.info("Reviewer Agent initialized with Claude Opus")
    
    def review_code(self, oracle_code: str, tsql_code: str,
                   object_name: str, object_type: str, cost_tracker: CostTracker) -> Dict[str, Any]:
        """
        Review converted T-SQL code

        Args:
            oracle_code: Original Oracle PL/SQL
            tsql_code: Converted T-SQL code
            object_name: Name of the object
            object_type: Type of object (TABLE, PROCEDURE, FUNCTION, etc.)
            cost_tracker: Cost tracking instance

        Returns:
            Review results with quality assessment
        """
        logger.info(f"Reviewing code for {object_name}")
        
        prompt = self._build_review_prompt(oracle_code, tsql_code, object_name)
        
        try:
            response = self.model.invoke(prompt)
            result_text = response.content
            
            # Track cost
            cost_tracker.add("anthropic", CLAUDE_OPUS_MODEL, prompt, result_text)
            
            # Parse review results
            review_result = self._parse_review_result(result_text)
            review_result["object_name"] = object_name
            
            logger.info(f"Review complete: {review_result.get('overall_quality', 'unknown')}")
            
            return review_result
            
        except Exception as e:
            logger.error(f"Review failed for {object_name}: {e}", exc_info=True)
            return {
                "status": "error",
                "object_name": object_name,
                "message": str(e)
            }
    
    def _build_review_prompt(self, oracle_code: str, tsql_code: str, 
                            object_name: str) -> str:
        """Build comprehensive review prompt"""
        
        prompt = f"""You are an expert SQL Server DBA and code reviewer.

Review the following T-SQL conversion from Oracle PL/SQL.

OBJECT NAME: {object_name}

ORIGINAL ORACLE CODE:
```sql
{oracle_code[:2000]}
```

CONVERTED T-SQL CODE:
```sql
{tsql_code}
```

REVIEW CRITERIA:
1. SQL Server 2022 Compatibility
2. Syntax Correctness
3. Performance Optimization
4. Security Best Practices
5. Code Quality Standards
6. Completeness of Conversion

Provide a structured JSON review with:
{{
  "overall_quality": "excellent|good|needs_improvement|poor",
  "approval_status": "approved|requires_changes",
  "issues_found": [
    {{"severity": "critical|major|minor", "description": "...", "line": number}}
  ],
  "recommendations": ["...", "..."],
  "sql_server_compliance": true|false,
  "performance_concerns": ["...", "..."],
  "security_issues": ["...", "..."],
  "summary": "Overall assessment..."
}}

IMPORTANT: Return ONLY valid JSON, no other text."""

        return prompt
    
    def _parse_review_result(self, result_text: str) -> Dict[str, Any]:
        """Parse JSON review result"""
        import json
        
        try:
            # Clean markdown formatting if present
            cleaned = result_text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
            
            # Parse JSON
            review = json.loads(cleaned)
            
            return {
                "status": "success",
                "overall_quality": review.get("overall_quality", "unknown"),
                "approval_status": review.get("approval_status", "requires_changes"),
                "issues_found": review.get("issues_found", []),
                "recommendations": review.get("recommendations", []),
                "sql_server_compliance": review.get("sql_server_compliance", False),
                "performance_concerns": review.get("performance_concerns", []),
                "security_issues": review.get("security_issues", []),
                "summary": review.get("summary", "No summary provided"),
                "raw_response": result_text
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse review JSON: {e}")
            return {
                "status": "error",
                "message": "Failed to parse review response",
                "raw_response": result_text,
                "overall_quality": "unknown",
                "approval_status": "requires_changes"
            }


# Global instance
_reviewer_agent = None


def get_reviewer_agent() -> ReviewerAgent:
    """Get or create global reviewer agent instance"""
    global _reviewer_agent
    if _reviewer_agent is None:
        _reviewer_agent = ReviewerAgent()
    return _reviewer_agent
