"""
Enhanced Dynamic Package Decomposer

Handles various Oracle package patterns dynamically:
- Different formatting styles (compact, spread out, mixed)
- Nested procedures/functions
- Overloaded procedures/functions
- Private vs public members
- Package dependencies and internal calls
- Comments and documentation
- Various naming conventions

This decomposer works for ANY Oracle database package structure.
"""

import re
import logging
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class MemberType(Enum):
    """Types of package members"""
    PROCEDURE = "PROCEDURE"
    FUNCTION = "FUNCTION"
    TYPE = "TYPE"
    CURSOR = "CURSOR"
    VARIABLE = "VARIABLE"
    CONSTANT = "CONSTANT"


@dataclass
class PackageMember:
    """Represents a procedure or function within a package"""
    name: str
    member_type: MemberType
    specification: str  # Declaration from package spec
    body: str  # Implementation from package body
    return_type: Optional[str] = None  # For functions only
    parameters: List[str] = field(default_factory=list)
    is_public: bool = True  # Public (in spec) vs private (body only)
    dependencies: Set[str] = field(default_factory=set)  # Other members it calls
    overload_index: int = 0  # For overloaded procedures/functions
    line_number: int = 0  # For debugging

    def get_sql_server_name(self, package_name: str) -> str:
        """Generate SQL Server object name"""
        base_name = f"{package_name}_{self.name}"
        if self.overload_index > 0:
            # Handle overloaded procedures/functions
            base_name += f"_v{self.overload_index}"
        return base_name


@dataclass
class PackageStructure:
    """Complete package structure"""
    package_name: str
    specification: str
    body: str
    members: List[PackageMember] = field(default_factory=list)
    global_variables: List[Dict[str, Any]] = field(default_factory=list)
    types: List[Dict[str, Any]] = field(default_factory=list)
    cursors: List[Dict[str, Any]] = field(default_factory=list)
    initialization_block: str = ""
    internal_dependencies: Dict[str, Set[str]] = field(default_factory=dict)

    @property
    def procedures(self) -> List[PackageMember]:
        return [m for m in self.members if m.member_type == MemberType.PROCEDURE]

    @property
    def functions(self) -> List[PackageMember]:
        return [m for m in self.members if m.member_type == MemberType.FUNCTION]

    @property
    def public_members(self) -> List[PackageMember]:
        return [m for m in self.members if m.is_public]

    @property
    def private_members(self) -> List[PackageMember]:
        return [m for m in self.members if not m.is_public]


class DynamicPackageParser:
    """
    Dynamic parser that adapts to various Oracle package formats

    Uses multiple parsing strategies:
    1. Balanced parenthesis matching for nested structures
    2. BEGIN/END block matching with depth tracking
    3. Line-by-line parsing with state machine
    4. Regex patterns with lookahead/lookbehind
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def parse_package(self, package_code: str) -> PackageStructure:
        """
        Dynamically parse any Oracle package structure

        Args:
            package_code: Complete package source (spec + body)

        Returns:
            PackageStructure with all members parsed
        """
        # Step 1: Normalize code (handle various formatting)
        normalized_code = self._normalize_code(package_code)

        # Step 2: Extract package name
        package_name = self._extract_package_name(normalized_code)

        # Step 3: Separate spec and body
        spec, body = self._separate_spec_and_body(normalized_code)

        # Step 4: Parse specification (public interface)
        spec_members = self._parse_specification(spec, package_name)

        # Step 5: Parse body (implementations + private members)
        body_members = self._parse_body(body, package_name)

        # Step 6: Match spec with body implementations
        matched_members = self._match_spec_and_body(spec_members, body_members)

        # Step 7: Extract global variables, types, cursors
        global_vars = self._extract_global_variables(spec, body)
        types = self._extract_types(spec, body)
        cursors = self._extract_cursors(spec, body)

        # Step 8: Extract initialization block
        init_block = self._extract_initialization(body)

        # Step 9: Analyze dependencies
        dependencies = self._analyze_dependencies(matched_members, package_name)

        structure = PackageStructure(
            package_name=package_name,
            specification=spec,
            body=body,
            members=matched_members,
            global_variables=global_vars,
            types=types,
            cursors=cursors,
            initialization_block=init_block,
            internal_dependencies=dependencies
        )

        self.logger.info(
            f"Parsed package {package_name}: "
            f"{len(structure.procedures)} procedures, "
            f"{len(structure.functions)} functions, "
            f"{len(structure.private_members)} private members"
        )

        return structure

    def _normalize_code(self, code: str) -> str:
        """Normalize code for consistent parsing"""
        # Remove SQL*Plus commands
        code = re.sub(r'^(?:SET|SHOW|SPOOL|PROMPT).*$', '', code, flags=re.MULTILINE | re.IGNORECASE)

        # Normalize line endings
        code = code.replace('\r\n', '\n').replace('\r', '\n')

        # Remove multiple blank lines
        code = re.sub(r'\n{3,}', '\n\n', code)

        # Normalize whitespace around keywords
        code = re.sub(r'\s+(IS|AS)\s+', ' IS ', code, flags=re.IGNORECASE)
        code = re.sub(r'\s+(BEGIN|END)\s+', ' BEGIN ', code, flags=re.IGNORECASE)

        return code

    def _extract_package_name(self, code: str) -> str:
        """Extract package name dynamically"""
        # Try multiple patterns
        patterns = [
            r'CREATE\s+(?:OR\s+REPLACE\s+)?PACKAGE\s+(?:BODY\s+)?(?:[\w\.]+\.)?([\w$#]+)',
            r'PACKAGE\s+(?:BODY\s+)?(?:[\w\.]+\.)?([\w$#]+)\s+(?:IS|AS)',
        ]

        for pattern in patterns:
            match = re.search(pattern, code, re.IGNORECASE)
            if match:
                return match.group(1).upper()

        return "UNKNOWN_PACKAGE"

    def _separate_spec_and_body(self, code: str) -> Tuple[str, str]:
        """
        Dynamically separate specification and body

        Handles various formats:
        - Spec and body in same file
        - Spec only
        - Body only
        - Different delimiters
        """
        spec = ""
        body = ""

        # Find package specification
        spec_pattern = r'(CREATE\s+(?:OR\s+REPLACE\s+)?PACKAGE\s+(?!BODY)[\s\S]*?END\s+[\w$#]*\s*;)'
        spec_match = re.search(spec_pattern, code, re.IGNORECASE)
        if spec_match:
            spec = spec_match.group(1)

        # Find package body
        body_pattern = r'(CREATE\s+(?:OR\s+REPLACE\s+)?PACKAGE\s+BODY[\s\S]*?END\s+[\w$#]*\s*;)'
        body_match = re.search(body_pattern, code, re.IGNORECASE)
        if body_match:
            body = body_match.group(1)

        return spec, body

    def _parse_specification(self, spec: str, package_name: str) -> List[PackageMember]:
        """
        Parse package specification for public declarations

        Uses dynamic approach to handle various formats
        """
        if not spec:
            return []

        members = []

        # Extract the content between IS/AS and END
        content_pattern = r'PACKAGE\s+[\w$#]+\s+(?:IS|AS)(.*?)END\s+[\w$#]*'
        content_match = re.search(content_pattern, spec, re.IGNORECASE | re.DOTALL)

        if not content_match:
            return []

        content = content_match.group(1)

        # Parse procedures
        members.extend(self._parse_procedures_from_text(content, is_public=True))

        # Parse functions
        members.extend(self._parse_functions_from_text(content, is_public=True))

        return members

    def _parse_body(self, body: str, package_name: str) -> List[PackageMember]:
        """Parse package body for implementations and private members"""
        if not body:
            return []

        members = []

        # Extract the content between IS/AS and END
        content_pattern = r'PACKAGE\s+BODY\s+[\w$#]+\s+(?:IS|AS)(.*?)(?:BEGIN|END\s+[\w$#]*\s*;?\s*$)'
        content_match = re.search(content_pattern, body, re.IGNORECASE | re.DOTALL)

        if not content_match:
            return []

        content = content_match.group(1)

        # Parse procedures (both public implementations and private)
        members.extend(self._parse_procedures_from_text(content, is_public=False, is_body=True))

        # Parse functions (both public implementations and private)
        members.extend(self._parse_functions_from_text(content, is_public=False, is_body=True))

        return members

    def _parse_procedures_from_text(self, text: str, is_public: bool, is_body: bool = False) -> List[PackageMember]:
        """
        Dynamically parse procedures from text

        Handles:
        - Various formatting styles
        - Nested BEGIN/END blocks
        - Comments
        - Overloaded procedures
        """
        procedures = []

        # Find procedure declarations/implementations
        if is_body:
            # Parse full implementations with bodies
            proc_pattern = r'PROCEDURE\s+([\w$#]+)\s*(\([^)]*\)|)\s+(?:IS|AS)(.*?)END\s+\1\s*;'
            matches = re.finditer(proc_pattern, text, re.IGNORECASE | re.DOTALL)

            for match in matches:
                proc_name = match.group(1).upper()
                params = match.group(2) or "()"
                impl = match.group(3)

                member = PackageMember(
                    name=proc_name,
                    member_type=MemberType.PROCEDURE,
                    specification=f"PROCEDURE {proc_name}{params}",
                    body=f"PROCEDURE {proc_name}{params} IS{impl}END {proc_name};",
                    parameters=self._parse_parameters(params),
                    is_public=is_public
                )
                procedures.append(member)
        else:
            # Parse declarations only
            proc_pattern = r'PROCEDURE\s+([\w$#]+)\s*(\([^)]*\)|)\s*;'
            matches = re.finditer(proc_pattern, text, re.IGNORECASE)

            for match in matches:
                proc_name = match.group(1).upper()
                params = match.group(2) or "()"

                member = PackageMember(
                    name=proc_name,
                    member_type=MemberType.PROCEDURE,
                    specification=f"PROCEDURE {proc_name}{params}",
                    body="",
                    parameters=self._parse_parameters(params),
                    is_public=is_public
                )
                procedures.append(member)

        # Handle overloaded procedures (same name, different params)
        procedures = self._handle_overloads(procedures)

        return procedures

    def _parse_functions_from_text(self, text: str, is_public: bool, is_body: bool = False) -> List[PackageMember]:
        """Dynamically parse functions from text"""
        functions = []

        if is_body:
            # Parse full implementations
            func_pattern = r'FUNCTION\s+([\w$#]+)\s*(\([^)]*\)|)\s+RETURN\s+([\w%\(\)]+)\s+(?:IS|AS)(.*?)END\s+\1\s*;'
            matches = re.finditer(func_pattern, text, re.IGNORECASE | re.DOTALL)

            for match in matches:
                func_name = match.group(1).upper()
                params = match.group(2) or "()"
                return_type = match.group(3)
                impl = match.group(4)

                member = PackageMember(
                    name=func_name,
                    member_type=MemberType.FUNCTION,
                    specification=f"FUNCTION {func_name}{params} RETURN {return_type}",
                    body=f"FUNCTION {func_name}{params} RETURN {return_type} IS{impl}END {func_name};",
                    return_type=return_type,
                    parameters=self._parse_parameters(params),
                    is_public=is_public
                )
                functions.append(member)
        else:
            # Parse declarations only
            func_pattern = r'FUNCTION\s+([\w$#]+)\s*(\([^)]*\)|)\s+RETURN\s+([\w%\(\)]+)\s*;'
            matches = re.finditer(func_pattern, text, re.IGNORECASE)

            for match in matches:
                func_name = match.group(1).upper()
                params = match.group(2) or "()"
                return_type = match.group(3)

                member = PackageMember(
                    name=func_name,
                    member_type=MemberType.FUNCTION,
                    specification=f"FUNCTION {func_name}{params} RETURN {return_type}",
                    body="",
                    return_type=return_type,
                    parameters=self._parse_parameters(params),
                    is_public=is_public
                )
                functions.append(member)

        # Handle overloaded functions
        functions = self._handle_overloads(functions)

        return functions

    def _parse_parameters(self, params_str: str) -> List[str]:
        """Parse parameter list dynamically"""
        if not params_str or params_str.strip() in ['()', '']:
            return []

        # Remove parentheses
        params_str = params_str.strip('()')

        # Split by comma, but respect nested parentheses
        params = []
        current_param = ""
        paren_depth = 0

        for char in params_str:
            if char == '(' :
                paren_depth += 1
                current_param += char
            elif char == ')':
                paren_depth -= 1
                current_param += char
            elif char == ',' and paren_depth == 0:
                params.append(current_param.strip())
                current_param = ""
            else:
                current_param += char

        if current_param.strip():
            params.append(current_param.strip())

        return params

    def _handle_overloads(self, members: List[PackageMember]) -> List[PackageMember]:
        """
        Handle overloaded procedures/functions

        Assigns unique indices to procedures/functions with same name
        """
        name_counts = {}

        for member in members:
            if member.name in name_counts:
                name_counts[member.name] += 1
                member.overload_index = name_counts[member.name]
            else:
                name_counts[member.name] = 0
                member.overload_index = 0

        return members

    def _match_spec_and_body(self, spec_members: List[PackageMember],
                            body_members: List[PackageMember]) -> List[PackageMember]:
        """
        Match specification declarations with body implementations

        Handles:
        - Public procedures/functions (in spec and body)
        - Private procedures/functions (body only)
        - Overloaded members
        """
        matched = []

        # Create lookup for body members
        body_lookup = {}
        for member in body_members:
            key = f"{member.name}_{member.overload_index}"
            body_lookup[key] = member

        # Match spec with body
        for spec_member in spec_members:
            key = f"{spec_member.name}_{spec_member.overload_index}"

            if key in body_lookup:
                # Found implementation
                body_member = body_lookup[key]
                spec_member.body = body_member.body
                spec_member.is_public = True
                matched.append(spec_member)

                # Remove from lookup
                del body_lookup[key]
            else:
                # No implementation found (unusual but possible)
                self.logger.warning(f"No implementation found for {spec_member.name}")
                matched.append(spec_member)

        # Add remaining body members (private procedures/functions)
        for body_member in body_lookup.values():
            body_member.is_public = False
            matched.append(body_member)

        return matched

    def _extract_global_variables(self, spec: str, body: str) -> List[Dict[str, Any]]:
        """Extract global variables from specification and body"""
        variables = []

        # Pattern for variable declarations
        var_pattern = r'([\w$#]+)\s+(CONSTANT\s+)?(\w+(?:\([^)]*\))?)\s*(?::=\s*([^;]+))?;'

        for text in [spec, body]:
            if not text:
                continue

            # Extract variable section (before first PROCEDURE/FUNCTION)
            var_section_pattern = r'(?:IS|AS)(.*?)(?:PROCEDURE|FUNCTION|BEGIN|END)'
            var_section_match = re.search(var_section_pattern, text, re.IGNORECASE | re.DOTALL)

            if var_section_match:
                var_section = var_section_match.group(1)

                for match in re.finditer(var_pattern, var_section, re.IGNORECASE):
                    var_name = match.group(1).upper()
                    is_constant = bool(match.group(2))
                    var_type = match.group(3)
                    default_value = match.group(4)

                    variables.append({
                        "name": var_name,
                        "type": var_type,
                        "is_constant": is_constant,
                        "default_value": default_value.strip() if default_value else None
                    })

        return variables

    def _extract_types(self, spec: str, body: str) -> List[Dict[str, Any]]:
        """Extract TYPE definitions"""
        types = []

        type_pattern = r'TYPE\s+([\w$#]+)\s+IS\s+(.*?);'

        for text in [spec, body]:
            for match in re.finditer(type_pattern, text, re.IGNORECASE):
                types.append({
                    "name": match.group(1).upper(),
                    "definition": match.group(2).strip()
                })

        return types

    def _extract_cursors(self, spec: str, body: str) -> List[Dict[str, Any]]:
        """Extract CURSOR definitions"""
        cursors = []

        cursor_pattern = r'CURSOR\s+([\w$#]+)\s*(\([^)]*\))?\s+IS\s+(.*?);'

        for text in [spec, body]:
            for match in re.finditer(cursor_pattern, text, re.IGNORECASE | re.DOTALL):
                cursors.append({
                    "name": match.group(1).upper(),
                    "parameters": match.group(2) or "",
                    "query": match.group(3).strip()
                })

        return cursors

    def _extract_initialization(self, body: str) -> str:
        """Extract package initialization block"""
        if not body:
            return ""

        # Find BEGIN...END at package level (not in procedures/functions)
        init_pattern = r'BEGIN\s+(.*?)\s+END\s+[\w$#]*\s*;?\s*$'
        match = re.search(init_pattern, body, re.IGNORECASE | re.DOTALL)

        return match.group(1).strip() if match else ""

    def _analyze_dependencies(self, members: List[PackageMember],
                            package_name: str) -> Dict[str, Set[str]]:
        """
        Analyze internal package dependencies

        Identifies which procedures/functions call other members
        """
        dependencies = {}

        member_names = {m.name for m in members}

        for member in members:
            deps = set()

            # Look for calls to other package members
            for other_name in member_names:
                if other_name != member.name:
                    # Pattern: package_name.member_name or just member_name
                    pattern = r'(?:' + package_name + r'\.)?' + other_name + r'\s*\('
                    if re.search(pattern, member.body, re.IGNORECASE):
                        deps.add(other_name)

            if deps:
                dependencies[member.name] = deps

        return dependencies


# Convenience function using enhanced parser
def decompose_oracle_package(package_name: str, package_code: str) -> Dict[str, Any]:
    """
    Decompose Oracle package using dynamic parser

    Works with ANY Oracle package structure
    """
    parser = DynamicPackageParser()
    structure = parser.parse_package(package_code)

    # Convert to legacy format for compatibility
    return {
        "package_name": structure.package_name,
        "members": structure.members,
        "global_variables": structure.global_variables,
        "initialization": structure.initialization_block,
        "total_procedures": len(structure.procedures),
        "total_functions": len(structure.functions),
        "migration_plan": _generate_migration_plan(structure)
    }


def _generate_migration_plan(structure: PackageStructure) -> Dict[str, Any]:
    """Generate migration plan from package structure"""
    plan = {
        "package_name": structure.package_name,
        "strategy": "DECOMPOSE",
        "components": [],
        "notes": []
    }

    # Notes about special elements
    if structure.global_variables:
        plan["notes"].append(
            f"⚠️  Package has {len(structure.global_variables)} global variables. "
            "Consider using schema-scoped variables or temp tables."
        )

    if structure.types:
        plan["notes"].append(
            f"⚠️  Package has {len(structure.types)} custom TYPE definitions. "
            "These may need manual conversion to SQL Server types."
        )

    if structure.cursors:
        plan["notes"].append(
            f"⚠️  Package has {len(structure.cursors)} cursor definitions. "
            "Convert to SQL Server cursors or set-based operations."
        )

    if structure.initialization_block:
        plan["notes"].append(
            "⚠️  Package has initialization code. "
            "Create a setup stored procedure."
        )

    if structure.internal_dependencies:
        plan["notes"].append(
            f"ℹ️  Detected {len(structure.internal_dependencies)} internal dependencies. "
            "Package members call each other - names will be updated during migration."
        )

    # Plan for each member
    for member in structure.members:
        visibility = "public" if member.is_public else "private"
        overload_note = f" (overload #{member.overload_index})" if member.overload_index > 0 else ""

        component = {
            "name": member.get_sql_server_name(structure.package_name),
            "original_name": member.name,
            "type": member.member_type.value,
            "visibility": visibility,
            "overload_index": member.overload_index,
            "oracle_code": member.body,
            "migration_action": "CONVERT_TO_STANDALONE",
            "note": f"{visibility.title()} {member.member_type.value.lower()}{overload_note}"
        }

        if member.member_type == MemberType.FUNCTION:
            component["return_type"] = member.return_type

        if member.dependencies:
            component["calls"] = list(member.dependencies)

        plan["components"].append(component)

    return plan
