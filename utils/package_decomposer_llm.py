"""
LLM-POWERED Dynamic Package Decomposer

This uses LLMs (Claude) to understand and decompose Oracle packages intelligently.
NO hardcoded regex patterns - the LLM understands the structure dynamically.

Works with:
- ANY Oracle package (any structure, any complexity)
- ANY database (Oracle, PostgreSQL, DB2, etc.)
- ANY formatting style
- NO configuration needed

The LLM figures out the structure on its own!
"""

import re
import json
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage
from config.config_enhanced import ANTHROPIC_API_KEY, CLAUDE_SONNET_MODEL, CostTracker

logger = logging.getLogger(__name__)

# Initialize Claude
claude_sonnet = ChatAnthropic(
    model=CLAUDE_SONNET_MODEL,
    api_key=ANTHROPIC_API_KEY,
    temperature=0
)


@dataclass
class PackageMember:
    """Represents a procedure or function within a package"""
    name: str
    member_type: str  # 'PROCEDURE' or 'FUNCTION'
    specification: str
    body: str
    return_type: Optional[str] = None
    parameters: List[str] = field(default_factory=list)
    is_public: bool = True
    overload_index: int = 0
    package_name: str = ""

    def get_sql_server_name(self, package_name: str = None) -> str:
        """Generate SQL Server object name"""
        pkg = package_name or self.package_name
        base_name = f"{pkg}_{self.name}"
        if self.overload_index > 0:
            base_name += f"_v{self.overload_index}"
        return base_name


class LLMPackageAnalyzer:
    """
    Uses LLM to analyze and understand Oracle package structure
    NO hardcoded patterns - pure AI-driven analysis
    """

    def __init__(self, cost_tracker: CostTracker = None):
        self.cost_tracker = cost_tracker or CostTracker()
        self.logger = logging.getLogger(__name__)

    def analyze_package(self, package_code: str, package_name_hint: str = None) -> Dict[str, Any]:
        """
        Use LLM to analyze Oracle package structure

        Args:
            package_code: Raw Oracle package code (any format)
            package_name_hint: Optional hint about package name

        Returns:
            Structured analysis of the package
        """
        self.logger.info("🤖 Using LLM to analyze package structure...")

        prompt = f"""You are analyzing an Oracle database package to prepare it for migration to SQL Server.

TASK: Analyze this Oracle package code and extract its structure.

Package Code:
```sql
{package_code}
```

OUTPUT FORMAT (JSON):
{{
    "package_name": "NAME_OF_PACKAGE",
    "has_specification": true/false,
    "has_body": true/false,
    "procedures": [
        {{
            "name": "PROCEDURE_NAME",
            "is_public": true/false,
            "parameters": ["p_param1 IN NUMBER", "p_param2 OUT VARCHAR2"],
            "code": "complete procedure code including body"
        }}
    ],
    "functions": [
        {{
            "name": "FUNCTION_NAME",
            "is_public": true/false,
            "return_type": "VARCHAR2",
            "parameters": ["p_param IN NUMBER"],
            "code": "complete function code including body"
        }}
    ],
    "notes": ["any important observations about the package"]
}}

RULES:
1. Extract ALL procedures and functions (both public and private)
2. Public members are declared in the specification
3. Private members only exist in the body
4. Include the COMPLETE code for each member (declaration + implementation)
5. Identify parameter types and directions (IN, OUT, IN OUT)
6. For functions, identify the return type
7. Handle overloaded procedures/functions (same name, different parameters)
8. If the package has global variables or initialization code, note them

OUTPUT ONLY THE JSON - NO EXPLANATIONS OR MARKDOWN."""

        try:
            response = claude_sonnet.invoke([HumanMessage(content=prompt)])

            # Track cost
            self.cost_tracker.add(
                "anthropic",
                CLAUDE_SONNET_MODEL,
                prompt,
                response.content
            )

            # Parse JSON response
            # Remove markdown code blocks if present
            content = response.content.strip()
            if content.startswith('```'):
                content = re.sub(r'^```(?:json)?\n', '', content)
                content = re.sub(r'\n```$', '', content)

            analysis = json.loads(content)

            self.logger.info(
                f"✅ LLM analyzed package: {analysis['package_name']} - "
                f"{len(analysis['procedures'])} procedures, {len(analysis['functions'])} functions"
            )

            return analysis

        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse LLM response as JSON: {e}")
            self.logger.error(f"Response was: {response.content[:500]}")
            # Return empty structure
            return {
                "package_name": package_name_hint or "UNKNOWN",
                "has_specification": False,
                "has_body": False,
                "procedures": [],
                "functions": [],
                "notes": [f"LLM analysis failed: {str(e)}"]
            }

        except Exception as e:
            self.logger.error(f"LLM analysis failed: {e}")
            return {
                "package_name": package_name_hint or "UNKNOWN",
                "has_specification": False,
                "has_body": False,
                "procedures": [],
                "functions": [],
                "notes": [f"Analysis error: {str(e)}"]
            }


class LLMPackageDecomposer:
    """
    Main decomposer that uses LLM to understand and decompose packages
    """

    def __init__(self, cost_tracker: CostTracker = None):
        self.analyzer = LLMPackageAnalyzer(cost_tracker)
        self.cost_tracker = cost_tracker or CostTracker()
        self.logger = logging.getLogger(__name__)

    def decompose_package(self, package_name: str, package_code: str) -> Dict[str, Any]:
        """
        Decompose Oracle package using LLM intelligence

        Args:
            package_name: Package name hint
            package_code: Raw Oracle package code

        Returns:
            Decomposed package structure ready for migration
        """
        self.logger.info(f"🤖 LLM-powered decomposition starting for: {package_name}")

        # Step 1: LLM analyzes the package
        analysis = self.analyzer.analyze_package(package_code, package_name)

        # Step 2: Convert LLM analysis to PackageMember objects
        members = []

        # Process procedures
        for proc_data in analysis.get("procedures", []):
            member = PackageMember(
                name=proc_data["name"],
                member_type="PROCEDURE",
                specification=f"PROCEDURE {proc_data['name']}",
                body=proc_data["code"],
                parameters=proc_data.get("parameters", []),
                is_public=proc_data.get("is_public", True),
                package_name=analysis["package_name"]
            )
            members.append(member)

        # Process functions
        for func_data in analysis.get("functions", []):
            member = PackageMember(
                name=func_data["name"],
                member_type="FUNCTION",
                specification=f"FUNCTION {func_data['name']} RETURN {func_data.get('return_type', 'VARCHAR2')}",
                body=func_data["code"],
                return_type=func_data.get("return_type"),
                parameters=func_data.get("parameters", []),
                is_public=func_data.get("is_public", True),
                package_name=analysis["package_name"]
            )
            members.append(member)

        # Step 3: Build migration plan
        total_procedures = len([m for m in members if m.member_type == "PROCEDURE"])
        total_functions = len([m for m in members if m.member_type == "FUNCTION"])

        components = []
        for member in members:
            component = {
                "name": member.get_sql_server_name(analysis["package_name"]),
                "original_name": member.name,
                "type": member.member_type,
                "visibility": "public" if member.is_public else "private",
                "oracle_code": member.body,
                "migration_action": "CONVERT_TO_STANDALONE"
            }
            if member.member_type == "FUNCTION":
                component["return_type"] = member.return_type
            components.append(component)

        self.logger.info(
            f"✅ LLM decomposition complete: {total_procedures} procedures, {total_functions} functions"
        )

        return {
            "package_name": analysis["package_name"],
            "members": members,
            "global_variables": [],
            "initialization": "",
            "total_procedures": total_procedures,
            "total_functions": total_functions,
            "migration_plan": {
                "package_name": analysis["package_name"],
                "strategy": "LLM_DECOMPOSED",
                "components": components,
                "notes": analysis.get("notes", []) + [
                    "✅ Decomposed using LLM (Claude Sonnet 4)",
                    "✅ Works with ANY package structure",
                    "✅ No hardcoded patterns needed"
                ]
            }
        }


# Global cost tracker for the module
_global_cost_tracker = CostTracker()


def decompose_oracle_package(package_name: str, package_code: str) -> Dict[str, Any]:
    """
    LLM-powered package decomposition - works with ANY Oracle package

    This function uses Claude Sonnet to intelligently understand and decompose
    Oracle packages without relying on hardcoded regex patterns.

    Args:
        package_name: Package name
        package_code: Raw package code (any format)

    Returns:
        Decomposed package structure
    """
    decomposer = LLMPackageDecomposer(_global_cost_tracker)
    return decomposer.decompose_package(package_name, package_code)


def get_cost_summary() -> str:
    """Get cost summary for LLM-based decomposition"""
    return str(_global_cost_tracker)
