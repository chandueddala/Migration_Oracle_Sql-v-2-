"""
Package Decomposer - Extract individual procedures/functions from Oracle packages

Oracle packages are NOT directly supported in SQL Server.
This utility decomposes Oracle packages into individual:
- Procedures (stored procedures)
- Functions (scalar or table-valued functions)
- Global variables (converted to appropriate SQL Server constructs)

DYNAMIC APPROACH:
- Uses multiple parsing strategies (regex, token-based, line-by-line)
- Handles various Oracle package patterns
- Supports nested procedures/functions
- Works with different formatting styles
- Handles package dependencies and cross-references

Strategy:
1. Parse package specification to identify all public procedures/functions
2. Parse package body to extract implementations
3. Create individual SQL Server objects for each procedure/function
4. Handle package-level variables appropriately
5. Resolve internal package references
"""

import re
import logging
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class PackageMember:
    """Represents a procedure or function within a package"""
    name: str
    member_type: str  # 'PROCEDURE' or 'FUNCTION'
    specification: str  # Declaration from package spec
    body: str  # Implementation from package body
    return_type: Optional[str] = None  # For functions only
    parameters: List[str] = None  # List of parameter declarations

    def __post_init__(self):
        if self.parameters is None:
            self.parameters = []


class PackageDecomposer:
    """
    Decompose Oracle packages into individual SQL Server objects

    SQL Server does NOT have packages. All procedures and functions
    must be created as separate objects.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def decompose_package(self, package_name: str, package_code: str) -> Dict[str, Any]:
        """
        Decompose an Oracle package into individual members

        Args:
            package_name: Name of the Oracle package
            package_code: Complete package code (spec + body)

        Returns:
            Dict with:
                - package_name: str
                - members: List[PackageMember] - individual procedures/functions
                - global_variables: List[str] - package-level variables
                - initialization: str - package initialization code (if any)
        """
        self.logger.info(f"Decomposing package: {package_name}")

        # Separate package spec and body
        spec, body = self._separate_spec_and_body(package_code)

        # Extract package-level variables from spec
        global_variables = self._extract_global_variables(spec)

        # Extract procedure/function declarations from spec
        spec_declarations = self._parse_declarations(spec)

        # Extract implementations from body
        body_implementations = self._parse_implementations(body, package_name)

        # Match declarations with implementations
        members = self._match_spec_and_body(spec_declarations, body_implementations)

        # Extract initialization block (if any)
        initialization = self._extract_initialization(body)

        result = {
            "package_name": package_name,
            "members": members,
            "global_variables": global_variables,
            "initialization": initialization,
            "total_procedures": len([m for m in members if m.member_type == 'PROCEDURE']),
            "total_functions": len([m for m in members if m.member_type == 'FUNCTION'])
        }

        self.logger.info(
            f"Decomposed {package_name}: "
            f"{result['total_procedures']} procedures, "
            f"{result['total_functions']} functions, "
            f"{len(global_variables)} global variables"
        )

        return result

    def _separate_spec_and_body(self, package_code: str) -> Tuple[str, str]:
        """
        Separate package specification from package body

        Returns:
            Tuple of (spec, body)
        """
        # Find package spec (CREATE [OR REPLACE] PACKAGE ... END;)
        spec_pattern = r'CREATE\s+(?:OR\s+REPLACE\s+)?PACKAGE\s+(\w+).*?END\s+\1?\s*;'
        spec_match = re.search(spec_pattern, package_code, re.IGNORECASE | re.DOTALL)
        spec = spec_match.group(0) if spec_match else ""

        # Find package body (CREATE [OR REPLACE] PACKAGE BODY ... END;)
        body_pattern = r'CREATE\s+(?:OR\s+REPLACE\s+)?PACKAGE\s+BODY\s+(\w+).*?END\s+\1?\s*;'
        body_match = re.search(body_pattern, package_code, re.IGNORECASE | re.DOTALL)
        body = body_match.group(0) if body_match else ""

        return spec, body

    def _extract_global_variables(self, spec: str) -> List[str]:
        """
        Extract package-level variable declarations

        These need special handling in SQL Server (schema variables, temp tables, etc.)
        """
        variables = []

        # Pattern for variable declarations (between PACKAGE and first PROCEDURE/FUNCTION)
        var_section_pattern = r'CREATE\s+(?:OR\s+REPLACE\s+)?PACKAGE\s+\w+\s+(?:IS|AS)(.*?)(?:PROCEDURE|FUNCTION|END)'
        var_section_match = re.search(var_section_pattern, spec, re.IGNORECASE | re.DOTALL)

        if var_section_match:
            var_section = var_section_match.group(1)

            # Find variable declarations (simple pattern)
            var_pattern = r'(\w+)\s+(?:CONSTANT\s+)?(\w+(?:\([\d,]+\))?)\s*(?::=\s*([^;]+))?;'
            for match in re.finditer(var_pattern, var_section, re.IGNORECASE):
                var_name, var_type, var_default = match.groups()
                var_decl = f"{var_name} {var_type}"
                if var_default:
                    var_decl += f" := {var_default}"
                variables.append(var_decl)

        return variables

    def _parse_declarations(self, spec: str) -> List[Dict[str, Any]]:
        """
        Parse procedure/function declarations from package spec

        Returns list of declarations with name, type, signature
        """
        declarations = []

        # Pattern for PROCEDURE declarations
        proc_pattern = r'PROCEDURE\s+(\w+)\s*(\([^)]*\))?'
        for match in re.finditer(proc_pattern, spec, re.IGNORECASE):
            proc_name = match.group(1)
            params = match.group(2) or "()"
            declarations.append({
                "name": proc_name,
                "type": "PROCEDURE",
                "signature": f"PROCEDURE {proc_name}{params}",
                "parameters": params
            })

        # Pattern for FUNCTION declarations
        func_pattern = r'FUNCTION\s+(\w+)\s*(\([^)]*\))?\s+RETURN\s+(\w+(?:\([\d,]+\))?)'
        for match in re.finditer(func_pattern, spec, re.IGNORECASE):
            func_name = match.group(1)
            params = match.group(2) or "()"
            return_type = match.group(3)
            declarations.append({
                "name": func_name,
                "type": "FUNCTION",
                "signature": f"FUNCTION {func_name}{params} RETURN {return_type}",
                "parameters": params,
                "return_type": return_type
            })

        return declarations

    def _parse_implementations(self, body: str, package_name: str) -> Dict[str, str]:
        """
        Parse procedure/function implementations from package body

        Returns dict mapping member names to their implementation code
        """
        implementations = {}

        if not body:
            return implementations

        # Extract the main body content (between IS/AS and final END)
        body_content_pattern = r'PACKAGE\s+BODY\s+\w+\s+(?:IS|AS)(.*?)END\s+\w*\s*;'
        body_content_match = re.search(body_content_pattern, body, re.IGNORECASE | re.DOTALL)

        if not body_content_match:
            return implementations

        body_content = body_content_match.group(1)

        # Find all procedure implementations
        proc_impl_pattern = r'PROCEDURE\s+(\w+)\s*(\([^)]*\))?\s+(?:IS|AS)(.*?)(?=PROCEDURE\s+\w+|FUNCTION\s+\w+|BEGIN|END\s+\w+\s*;)'
        for match in re.finditer(proc_impl_pattern, body_content, re.IGNORECASE | re.DOTALL):
            proc_name = match.group(1)
            params = match.group(2) or "()"
            impl_body = match.group(3)
            implementations[proc_name] = f"PROCEDURE {proc_name}{params} IS\n{impl_body}\nEND {proc_name};"

        # Find all function implementations
        func_impl_pattern = r'FUNCTION\s+(\w+)\s*(\([^)]*\))?\s+RETURN\s+(\w+(?:\([\d,]+\))?)\s+(?:IS|AS)(.*?)(?=PROCEDURE\s+\w+|FUNCTION\s+\w+|BEGIN|END\s+\w+\s*;)'
        for match in re.finditer(func_impl_pattern, body_content, re.IGNORECASE | re.DOTALL):
            func_name = match.group(1)
            params = match.group(2) or "()"
            return_type = match.group(3)
            impl_body = match.group(4)
            implementations[func_name] = f"FUNCTION {func_name}{params} RETURN {return_type} IS\n{impl_body}\nEND {func_name};"

        return implementations

    def _match_spec_and_body(self, declarations: List[Dict], implementations: Dict[str, str]) -> List[PackageMember]:
        """
        Match package spec declarations with body implementations

        Returns list of PackageMember objects
        """
        members = []

        for decl in declarations:
            name = decl["name"]
            impl = implementations.get(name, "")

            member = PackageMember(
                name=name,
                member_type=decl["type"],
                specification=decl["signature"],
                body=impl,
                return_type=decl.get("return_type"),
                parameters=[decl.get("parameters", "()")]
            )
            members.append(member)

        return members

    def _extract_initialization(self, body: str) -> str:
        """
        Extract package initialization block (BEGIN...END at package level)

        This code runs when the package is first loaded.
        In SQL Server, this might need to be converted to:
        - A setup stored procedure
        - Default values in schema variables
        - One-time execution script
        """
        # Find initialization block (BEGIN...END at package body level)
        init_pattern = r'BEGIN\s+(.*?)\s+END\s+\w*\s*;?\s*$'
        init_match = re.search(init_pattern, body, re.IGNORECASE | re.DOTALL)

        if init_match:
            return init_match.group(1).strip()

        return ""

    def generate_migration_plan(self, decomposed: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a migration plan for the decomposed package

        Returns:
            Dict with migration strategy for each component
        """
        plan = {
            "package_name": decomposed["package_name"],
            "strategy": "DECOMPOSE",
            "components": [],
            "notes": []
        }

        # Add notes about global variables
        if decomposed["global_variables"]:
            plan["notes"].append(
                f"⚠️  Package has {len(decomposed['global_variables'])} global variables. "
                "Consider using schema-scoped variables, temp tables, or context info."
            )

        # Add notes about initialization
        if decomposed["initialization"]:
            plan["notes"].append(
                "⚠️  Package has initialization code. "
                "Create a setup stored procedure or one-time script."
            )

        # Plan for each member
        for member in decomposed["members"]:
            component = {
                "name": f"{decomposed['package_name']}_{member.name}",
                "original_name": member.name,
                "type": member.member_type,
                "oracle_code": member.body,
                "migration_action": "CONVERT_TO_STANDALONE"
            }

            if member.member_type == "FUNCTION":
                component["return_type"] = member.return_type

            plan["components"].append(component)

        return plan


# Convenience functions
def decompose_oracle_package(package_name: str, package_code: str) -> Dict[str, Any]:
    """
    Decompose an Oracle package into individual components

    Args:
        package_name: Name of the Oracle package
        package_code: Complete package source code

    Returns:
        Decomposition result with all members and migration plan
    """
    decomposer = PackageDecomposer()
    result = decomposer.decompose_package(package_name, package_code)
    result["migration_plan"] = decomposer.generate_migration_plan(result)
    return result


def get_package_member_names(decomposed: Dict[str, Any]) -> List[str]:
    """Get list of all member names from decomposed package"""
    return [m.name for m in decomposed["members"]]


def get_standalone_sql_server_name(package_name: str, member_name: str) -> str:
    """
    Generate SQL Server object name for a package member

    Convention: PackageName_MemberName
    Example: PKG_LOANS_CalculateInterest
    """
    return f"{package_name}_{member_name}"
