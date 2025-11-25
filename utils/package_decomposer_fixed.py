"""
FIXED Package Decomposer with Robust Parsing

This version fixes the regex patterns that were failing to extract procedures/functions
from Oracle packages.

Key fixes:
1. Better handling of nested parentheses in parameter lists
2. More flexible END matching (with or without procedure/function name)
3. Handles procedures/functions with no parameters
4. Better handling of multi-line declarations
"""

import re
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


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

    def get_sql_server_name(self, package_name: str) -> str:
        """Generate SQL Server object name"""
        base_name = f"{package_name}_{self.name}"
        if self.overload_index > 0:
            base_name += f"_v{self.overload_index}"
        return base_name


def extract_balanced_block(text: str, start_pos: int) -> tuple[str, int]:
    """
    Extract a balanced BEGIN...END block starting from start_pos

    Returns: (extracted_block, end_position)
    """
    depth = 0
    in_string = False
    string_char = None
    i = start_pos

    while i < len(text):
        char = text[i]

        # Handle strings
        if char in ("'", '"'):
            if not in_string:
                in_string = True
                string_char = char
            elif char == string_char:
                # Check if escaped
                if i + 1 < len(text) and text[i+1] == char:
                    i += 1  # Skip escaped quote
                else:
                    in_string = False
                    string_char = None

        # Count BEGIN/END depth (only outside strings)
        if not in_string:
            # Check for BEGIN
            if text[i:i+5].upper() == 'BEGIN':
                # Make sure it's a word boundary
                if (i == 0 or not text[i-1].isalnum()) and \
                   (i+5 >= len(text) or not text[i+5].isalnum()):
                    depth += 1

            # Check for END
            elif text[i:i+3].upper() == 'END':
                # Make sure it's a word boundary
                if (i == 0 or not text[i-1].isalnum()) and \
                   (i+3 >= len(text) or not text[i+3].isalnum()):
                    depth -= 1
                    if depth == 0:
                        # Found matching END, find the semicolon
                        j = i + 3
                        while j < len(text) and text[j] != ';':
                            j += 1
                        return text[start_pos:j+1], j+1

        i += 1

    return text[start_pos:], len(text)


def parse_parameters_robust(params_str: str) -> List[str]:
    """Parse parameter list handling nested parentheses"""
    if not params_str or params_str.strip() in ['()', '']:
        return []

    # Remove outer parentheses
    params_str = params_str.strip()
    if params_str.startswith('(') and params_str.endswith(')'):
        params_str = params_str[1:-1]

    params = []
    current_param = ""
    paren_depth = 0

    for char in params_str:
        if char == '(':
            paren_depth += 1
            current_param += char
        elif char == ')':
            paren_depth -= 1
            current_param += char
        elif char == ',' and paren_depth == 0:
            if current_param.strip():
                params.append(current_param.strip())
            current_param = ""
        else:
            current_param += char

    if current_param.strip():
        params.append(current_param.strip())

    return params


def parse_package_body_procedures(body_text: str) -> List[PackageMember]:
    """
    Parse procedures from package body using a more robust approach

    Strategy:
    1. Find PROCEDURE keyword
    2. Extract name
    3. Find parameter list (if any)
    4. Find IS/AS keyword
    5. Extract body using balanced BEGIN/END matching
    """
    procedures = []

    # Find all PROCEDURE declarations
    proc_starts = []
    for match in re.finditer(r'\bPROCEDURE\s+([\w$#]+)', body_text, re.IGNORECASE):
        proc_starts.append((match.start(), match.group(1)))

    logger.info(f"Found {len(proc_starts)} PROCEDURE keywords")

    for start_pos, proc_name in proc_starts:
        try:
            # Extract from PROCEDURE to the end
            remaining = body_text[start_pos:]

            # Find parameters (if any) - everything between name and IS/AS
            # Pattern: PROCEDURE name (params) IS  or  PROCEDURE name IS
            param_match = re.search(
                r'PROCEDURE\s+' + re.escape(proc_name) + r'\s*(\([^)]*(?:\([^)]*\)[^)]*)*\))?\s+(?:IS|AS)',
                remaining,
                re.IGNORECASE | re.DOTALL
            )

            if not param_match:
                logger.warning(f"Could not find IS/AS for procedure {proc_name}")
                continue

            params = param_match.group(1) or '()'

            # Find where the body starts (after IS/AS)
            is_as_match = re.search(r'\b(?:IS|AS)\b', remaining, re.IGNORECASE)
            if not is_as_match:
                continue

            body_start = is_as_match.end()

            # Check if there's a BEGIN block or if it's a declaration only
            # Look ahead to see if there's a BEGIN
            lookahead = remaining[body_start:body_start+500].upper()

            if 'BEGIN' in lookahead:
                # Find the BEGIN and extract balanced block
                begin_match = re.search(r'\bBEGIN\b', remaining[body_start:], re.IGNORECASE)
                if begin_match:
                    begin_pos = body_start + begin_match.start()
                    proc_body, end_pos = extract_balanced_block(remaining, begin_pos)

                    # Build full procedure text
                    full_proc = remaining[:end_pos]

                    member = PackageMember(
                        name=proc_name,
                        member_type='PROCEDURE',
                        specification=f"PROCEDURE {proc_name}{params}",
                        body=full_proc,
                        parameters=parse_parameters_robust(params),
                        is_public=False  # Body procedures, will match with spec later
                    )
                    procedures.append(member)
                    logger.info(f"Extracted procedure: {proc_name}")
            else:
                # Just a forward declaration, find the semicolon
                semicolon_pos = remaining[body_start:].find(';')
                if semicolon_pos != -1:
                    full_decl = remaining[:body_start + semicolon_pos + 1]
                    member = PackageMember(
                        name=proc_name,
                        member_type='PROCEDURE',
                        specification=f"PROCEDURE {proc_name}{params}",
                        body="",  # Just a declaration
                        parameters=parse_parameters_robust(params),
                        is_public=True  # Spec only
                    )
                    procedures.append(member)
                    logger.info(f"Extracted procedure declaration: {proc_name}")

        except Exception as e:
            logger.error(f"Error parsing procedure {proc_name}: {e}")
            continue

    return procedures


def parse_package_body_functions(body_text: str) -> List[PackageMember]:
    """Parse functions from package body using robust approach"""
    functions = []

    # Find all FUNCTION declarations
    func_starts = []
    for match in re.finditer(r'\bFUNCTION\s+([\w$#]+)', body_text, re.IGNORECASE):
        func_starts.append((match.start(), match.group(1)))

    logger.info(f"Found {len(func_starts)} FUNCTION keywords")

    for start_pos, func_name in func_starts:
        try:
            remaining = body_text[start_pos:]

            # Pattern: FUNCTION name (params) RETURN type IS
            func_header_match = re.search(
                r'FUNCTION\s+' + re.escape(func_name) +
                r'\s*(\([^)]*(?:\([^)]*\)[^)]*)*\))?\s+RETURN\s+([\w%]+(?:\([^)]*\))?)\s+(?:IS|AS)',
                remaining,
                re.IGNORECASE | re.DOTALL
            )

            if not func_header_match:
                logger.warning(f"Could not find RETURN clause for function {func_name}")
                continue

            params = func_header_match.group(1) or '()'
            return_type = func_header_match.group(2)

            # Find where the body starts
            is_as_match = re.search(r'\b(?:IS|AS)\b', remaining, re.IGNORECASE)
            if not is_as_match:
                continue

            body_start = is_as_match.end()

            # Check for BEGIN block
            lookahead = remaining[body_start:body_start+500].upper()

            if 'BEGIN' in lookahead or 'RETURN' in lookahead:
                # Find the BEGIN or direct RETURN
                begin_match = re.search(r'\bBEGIN\b', remaining[body_start:], re.IGNORECASE)
                if begin_match:
                    begin_pos = body_start + begin_match.start()
                    func_body, end_pos = extract_balanced_block(remaining, begin_pos)
                    full_func = remaining[:end_pos]
                else:
                    # Direct RETURN statement, find the semicolon
                    # Simple functions might be: RETURN expression;
                    end_match = re.search(r';', remaining[body_start:])
                    if end_match:
                        end_pos = body_start + end_match.end()
                        full_func = remaining[:end_pos]
                    else:
                        continue

                member = PackageMember(
                    name=func_name,
                    member_type='FUNCTION',
                    specification=f"FUNCTION {func_name}{params} RETURN {return_type}",
                    body=full_func,
                    return_type=return_type,
                    parameters=parse_parameters_robust(params),
                    is_public=False
                )
                functions.append(member)
                logger.info(f"Extracted function: {func_name} RETURN {return_type}")
            else:
                # Just a declaration
                semicolon_pos = remaining[body_start:].find(';')
                if semicolon_pos != -1:
                    full_decl = remaining[:body_start + semicolon_pos + 1]
                    member = PackageMember(
                        name=func_name,
                        member_type='FUNCTION',
                        specification=f"FUNCTION {func_name}{params} RETURN {return_type}",
                        body="",
                        return_type=return_type,
                        parameters=parse_parameters_robust(params),
                        is_public=True
                    )
                    functions.append(member)
                    logger.info(f"Extracted function declaration: {func_name}")

        except Exception as e:
            logger.error(f"Error parsing function {func_name}: {e}")
            continue

    return functions


def decompose_oracle_package(package_name: str, package_code: str) -> Dict[str, Any]:
    """
    Decompose Oracle package into individual members

    This FIXED version uses a more robust parsing strategy that doesn't rely
    on complex regex patterns.
    """
    logger.info(f"Decomposing package {package_name}")

    # Separate spec and body
    spec = ""
    body = ""

    # Find package specification
    spec_match = re.search(
        r'(CREATE\s+(?:OR\s+REPLACE\s+)?PACKAGE\s+(?!BODY)[\s\S]*?END\s+[\w$#]*\s*;)',
        package_code,
        re.IGNORECASE
    )
    if spec_match:
        spec = spec_match.group(1)
        logger.info(f"Found package spec: {len(spec)} chars")

    # Find package body
    body_match = re.search(
        r'(CREATE\s+(?:OR\s+REPLACE\s+)?PACKAGE\s+BODY[\s\S]*)',
        package_code,
        re.IGNORECASE
    )
    if body_match:
        body = body_match.group(1)
        logger.info(f"Found package body: {len(body)} chars")

    # Parse specification for public declarations
    spec_procedures = []
    spec_functions = []

    if spec:
        # Extract content between IS/AS and END
        spec_content_match = re.search(
            r'PACKAGE\s+[\w$#]+\s+(?:IS|AS)(.*?)END\s+[\w$#]*',
            spec,
            re.IGNORECASE | re.DOTALL
        )
        if spec_content_match:
            spec_content = spec_content_match.group(1)

            # Find procedure declarations (PROCEDURE name ... ;)
            for match in re.finditer(r'PROCEDURE\s+([\w$#]+)\s*([^;]*);', spec_content, re.IGNORECASE):
                proc_name = match.group(1)
                params_etc = match.group(2)

                # Extract just parameters (before any IS/AS)
                params_match = re.match(r'\s*(\([^)]*\))?', params_etc)
                params = params_match.group(1) if params_match else '()'

                spec_procedures.append(PackageMember(
                    name=proc_name,
                    member_type='PROCEDURE',
                    specification=f"PROCEDURE {proc_name}{params}",
                    body="",
                    parameters=parse_parameters_robust(params),
                    is_public=True
                ))

            # Find function declarations
            for match in re.finditer(
                r'FUNCTION\s+([\w$#]+)\s*(\([^)]*\))?\s+RETURN\s+([\w%]+(?:\([^)]*\))?)\s*;',
                spec_content,
                re.IGNORECASE
            ):
                func_name = match.group(1)
                params = match.group(2) or '()'
                return_type = match.group(3)

                spec_functions.append(PackageMember(
                    name=func_name,
                    member_type='FUNCTION',
                    specification=f"FUNCTION {func_name}{params} RETURN {return_type}",
                    body="",
                    return_type=return_type,
                    parameters=parse_parameters_robust(params),
                    is_public=True
                ))

    logger.info(f"Spec: {len(spec_procedures)} procedure decls, {len(spec_functions)} function decls")

    # Parse body for implementations
    body_procedures = []
    body_functions = []

    if body:
        body_procedures = parse_package_body_procedures(body)
        body_functions = parse_package_body_functions(body)

    logger.info(f"Body: {len(body_procedures)} procedures, {len(body_functions)} functions")

    # Match spec declarations with body implementations
    all_members = []

    # Match procedures
    for spec_proc in spec_procedures:
        # Find matching body implementation
        for body_proc in body_procedures:
            if body_proc.name.upper() == spec_proc.name.upper():
                spec_proc.body = body_proc.body
                break
        all_members.append(spec_proc)

    # Add private procedures (not in spec)
    for body_proc in body_procedures:
        if not any(sp.name.upper() == body_proc.name.upper() for sp in spec_procedures):
            body_proc.is_public = False
            all_members.append(body_proc)

    # Match functions
    for spec_func in spec_functions:
        for body_func in body_functions:
            if body_func.name.upper() == spec_func.name.upper():
                spec_func.body = body_func.body
                break
        all_members.append(spec_func)

    # Add private functions
    for body_func in body_functions:
        if not any(sf.name.upper() == body_func.name.upper() for sf in spec_functions):
            body_func.is_public = False
            all_members.append(body_func)

    # Generate migration plan
    components = []
    for member in all_members:
        component = {
            "name": member.get_sql_server_name(package_name),
            "original_name": member.name,
            "type": member.member_type,
            "visibility": "public" if member.is_public else "private",
            "oracle_code": member.body if member.body else member.specification,
            "migration_action": "CONVERT_TO_STANDALONE"
        }
        if member.member_type == 'FUNCTION':
            component["return_type"] = member.return_type
        components.append(component)

    total_procedures = sum(1 for m in all_members if m.member_type == 'PROCEDURE')
    total_functions = sum(1 for m in all_members if m.member_type == 'FUNCTION')

    logger.info(f"Total extracted: {total_procedures} procedures, {total_functions} functions")

    return {
        "package_name": package_name,
        "members": all_members,
        "global_variables": [],
        "initialization": "",
        "total_procedures": total_procedures,
        "total_functions": total_functions,
        "migration_plan": {
            "package_name": package_name,
            "strategy": "DECOMPOSE",
            "components": components,
            "notes": []
        }
    }
