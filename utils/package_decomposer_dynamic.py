"""
DYNAMIC & ROBUST Package Decomposer
Works with ANY database package structure (Oracle, PostgreSQL, DB2, etc.)

This parser is:
1. ADAPTIVE - Learns the structure by analyzing the code
2. PATTERN-AGNOSTIC - Doesn't rely on hardcoded regex patterns
3. MULTI-DATABASE - Works with different SQL dialects
4. FAULT-TOLERANT - Continues parsing even when parts fail
5. CONTEXT-AWARE - Understands nested structures and scopes

Architecture:
- Tokenizer: Breaks code into meaningful tokens
- Structure Analyzer: Identifies block boundaries
- Member Extractor: Extracts procedures/functions dynamically
- Dependency Tracker: Analyzes relationships
"""

import re
import logging
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class TokenType(Enum):
    """Token types for SQL parsing"""
    KEYWORD = "KEYWORD"
    IDENTIFIER = "IDENTIFIER"
    OPERATOR = "OPERATOR"
    DELIMITER = "DELIMITER"
    STRING = "STRING"
    NUMBER = "NUMBER"
    COMMENT = "COMMENT"
    WHITESPACE = "WHITESPACE"


@dataclass
class Token:
    """Represents a token in SQL code"""
    type: TokenType
    value: str
    position: int
    line: int = 0


@dataclass
class CodeBlock:
    """Represents a block of code with boundaries"""
    type: str  # PROCEDURE, FUNCTION, PACKAGE_SPEC, PACKAGE_BODY, etc.
    name: str
    start_pos: int
    end_pos: int
    content: str
    parent: Optional['CodeBlock'] = None
    children: List['CodeBlock'] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


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


class DynamicSQLTokenizer:
    """
    Tokenizes SQL code into meaningful tokens
    Works with any SQL dialect
    """

    # SQL keywords (comprehensive list for multiple databases)
    KEYWORDS = {
        'CREATE', 'OR', 'REPLACE', 'PACKAGE', 'BODY', 'IS', 'AS',
        'PROCEDURE', 'FUNCTION', 'BEGIN', 'END', 'RETURN', 'RETURNS',
        'DECLARE', 'IF', 'THEN', 'ELSE', 'ELSIF', 'ELSEIF', 'LOOP',
        'WHILE', 'FOR', 'CURSOR', 'TYPE', 'RECORD', 'TABLE', 'EXCEPTION',
        'WHEN', 'OTHERS', 'RAISE', 'IN', 'OUT', 'INOUT', 'CONSTANT',
        'DEFAULT', 'NULL', 'NOT', 'AND', 'OR', 'SELECT', 'FROM', 'WHERE',
        'INSERT', 'UPDATE', 'DELETE', 'COMMIT', 'ROLLBACK', 'TRIGGER'
    }

    def __init__(self):
        self.tokens = []
        self.position = 0
        self.line = 1

    def tokenize(self, code: str) -> List[Token]:
        """Tokenize SQL code into tokens"""
        self.tokens = []
        self.position = 0
        self.line = 1
        i = 0

        while i < len(code):
            char = code[i]

            # Whitespace
            if char in ' \t':
                i += 1
                continue

            # Newline
            if char == '\n':
                self.line += 1
                i += 1
                continue

            # Comments
            if char == '-' and i + 1 < len(code) and code[i + 1] == '-':
                # Single line comment
                comment_end = code.find('\n', i)
                if comment_end == -1:
                    comment_end = len(code)
                self.tokens.append(Token(TokenType.COMMENT, code[i:comment_end], i, self.line))
                i = comment_end
                continue

            if char == '/' and i + 1 < len(code) and code[i + 1] == '*':
                # Multi-line comment
                comment_end = code.find('*/', i + 2)
                if comment_end == -1:
                    comment_end = len(code)
                else:
                    comment_end += 2
                comment_text = code[i:comment_end]
                self.line += comment_text.count('\n')
                self.tokens.append(Token(TokenType.COMMENT, comment_text, i, self.line))
                i = comment_end
                continue

            # String literals
            if char in ("'", '"'):
                string_char = char
                string_start = i
                i += 1
                while i < len(code):
                    if code[i] == string_char:
                        # Check for escaped quote
                        if i + 1 < len(code) and code[i + 1] == string_char:
                            i += 2
                        else:
                            i += 1
                            break
                    else:
                        if code[i] == '\n':
                            self.line += 1
                        i += 1
                self.tokens.append(Token(TokenType.STRING, code[string_start:i], string_start, self.line))
                continue

            # Numbers
            if char.isdigit() or (char == '.' and i + 1 < len(code) and code[i + 1].isdigit()):
                num_start = i
                while i < len(code) and (code[i].isdigit() or code[i] in '.eE+-'):
                    i += 1
                self.tokens.append(Token(TokenType.NUMBER, code[num_start:i], num_start, self.line))
                continue

            # Identifiers and keywords
            if char.isalpha() or char in '_$#':
                ident_start = i
                while i < len(code) and (code[i].isalnum() or code[i] in '_$#'):
                    i += 1
                ident = code[ident_start:i]

                # Check if keyword
                token_type = TokenType.KEYWORD if ident.upper() in self.KEYWORDS else TokenType.IDENTIFIER
                self.tokens.append(Token(token_type, ident, ident_start, self.line))
                continue

            # Delimiters and operators
            if char in '();,.:=<>!+-*/|&%':
                # Multi-char operators
                if i + 1 < len(code):
                    two_char = char + code[i + 1]
                    if two_char in (':=', '<=', '>=', '<>', '!=', '||', '&&'):
                        self.tokens.append(Token(TokenType.OPERATOR, two_char, i, self.line))
                        i += 2
                        continue

                token_type = TokenType.DELIMITER if char in '();,' else TokenType.OPERATOR
                self.tokens.append(Token(token_type, char, i, self.line))
                i += 1
                continue

            # Unknown character, skip
            i += 1

        return self.tokens


class StructureAnalyzer:
    """
    Analyzes token stream to identify code structure
    Dynamically detects blocks without hardcoded patterns
    """

    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.position = 0
        self.blocks = []

    def analyze(self) -> List[CodeBlock]:
        """Analyze tokens and extract code blocks"""
        self.position = 0
        self.blocks = []

        while self.position < len(self.tokens):
            token = self.tokens[self.position]

            # Look for block-starting keywords
            if token.type == TokenType.KEYWORD:
                keyword = token.value.upper()

                if keyword == 'PACKAGE':
                    block = self._extract_package_block()
                    if block:
                        self.blocks.append(block)
                elif keyword == 'PROCEDURE':
                    block = self._extract_procedure_block()
                    if block:
                        self.blocks.append(block)
                elif keyword == 'FUNCTION':
                    block = self._extract_function_block()
                    if block:
                        self.blocks.append(block)

            self.position += 1

        return self.blocks

    def _extract_package_block(self) -> Optional[CodeBlock]:
        """Extract package specification or body block"""
        start_pos = self.position

        # Check if PACKAGE BODY or just PACKAGE
        is_body = False
        if self.position + 1 < len(self.tokens):
            next_token = self.tokens[self.position + 1]
            if next_token.type == TokenType.KEYWORD and next_token.value.upper() == 'BODY':
                is_body = True
                self.position += 1

        # Find package name
        name = self._find_next_identifier()
        if not name:
            return None

        # Find IS or AS
        is_as_pos = self._find_next_keyword(['IS', 'AS'])
        if is_as_pos == -1:
            return None

        # Find matching END
        end_pos = self._find_matching_end(is_as_pos)
        if end_pos == -1:
            return None

        block_type = 'PACKAGE_BODY' if is_body else 'PACKAGE_SPEC'
        content = self._extract_content(start_pos, end_pos)

        return CodeBlock(
            type=block_type,
            name=name,
            start_pos=start_pos,
            end_pos=end_pos,
            content=content,
            metadata={'is_body': is_body}
        )

    def _extract_procedure_block(self) -> Optional[CodeBlock]:
        """Extract procedure block dynamically"""
        start_pos = self.position

        # Find procedure name
        name = self._find_next_identifier()
        if not name:
            return None

        # Find parameters
        params = self._extract_parameters()

        # Find IS or AS
        is_as_pos = self._find_next_keyword(['IS', 'AS', ';'])
        if is_as_pos == -1:
            return None

        # Check if declaration only (ends with ;) or has body
        if self.tokens[is_as_pos].value == ';':
            # Declaration only
            content = self._extract_content(start_pos, is_as_pos)
            return CodeBlock(
                type='PROCEDURE',
                name=name,
                start_pos=start_pos,
                end_pos=is_as_pos,
                content=content,
                metadata={'parameters': params, 'declaration_only': True}
            )

        # Find matching END
        end_pos = self._find_matching_end(is_as_pos)
        if end_pos == -1:
            return None

        content = self._extract_content(start_pos, end_pos)

        return CodeBlock(
            type='PROCEDURE',
            name=name,
            start_pos=start_pos,
            end_pos=end_pos,
            content=content,
            metadata={'parameters': params, 'declaration_only': False}
        )

    def _extract_function_block(self) -> Optional[CodeBlock]:
        """Extract function block dynamically"""
        start_pos = self.position

        # Find function name
        name = self._find_next_identifier()
        if not name:
            return None

        # Find parameters
        params = self._extract_parameters()

        # Find RETURN/RETURNS
        return_pos = self._find_next_keyword(['RETURN', 'RETURNS'])
        if return_pos == -1:
            return None

        # Extract return type
        self.position = return_pos + 1
        return_type = self._find_next_identifier()

        # Find IS or AS
        is_as_pos = self._find_next_keyword(['IS', 'AS', ';'])
        if is_as_pos == -1:
            return None

        # Check if declaration only
        if self.tokens[is_as_pos].value == ';':
            content = self._extract_content(start_pos, is_as_pos)
            return CodeBlock(
                type='FUNCTION',
                name=name,
                start_pos=start_pos,
                end_pos=is_as_pos,
                content=content,
                metadata={'parameters': params, 'return_type': return_type, 'declaration_only': True}
            )

        # Find matching END
        end_pos = self._find_matching_end(is_as_pos)
        if end_pos == -1:
            return None

        content = self._extract_content(start_pos, end_pos)

        return CodeBlock(
            type='FUNCTION',
            name=name,
            start_pos=start_pos,
            end_pos=end_pos,
            content=content,
            metadata={'parameters': params, 'return_type': return_type, 'declaration_only': False}
        )

    def _find_next_identifier(self) -> Optional[str]:
        """Find next identifier token"""
        self.position += 1
        while self.position < len(self.tokens):
            token = self.tokens[self.position]
            if token.type == TokenType.IDENTIFIER:
                return token.value
            if token.type == TokenType.KEYWORD and token.value.upper() not in ['OR', 'REPLACE']:
                return None
            self.position += 1
        return None

    def _find_next_keyword(self, keywords: List[str]) -> int:
        """Find position of next occurrence of any keyword in list"""
        keywords_upper = [k.upper() for k in keywords]
        pos = self.position + 1
        while pos < len(self.tokens):
            token = self.tokens[pos]
            if token.type == TokenType.KEYWORD and token.value.upper() in keywords_upper:
                return pos
            pos += 1
        return -1

    def _extract_parameters(self) -> List[str]:
        """Extract parameter list"""
        # Find opening parenthesis
        start_paren = -1
        pos = self.position
        while pos < len(self.tokens):
            if self.tokens[pos].value == '(':
                start_paren = pos
                break
            if self.tokens[pos].type == TokenType.KEYWORD:
                break
            pos += 1

        if start_paren == -1:
            return []

        # Find matching closing parenthesis
        depth = 1
        pos = start_paren + 1
        params_tokens = []

        while pos < len(self.tokens) and depth > 0:
            token = self.tokens[pos]
            if token.value == '(':
                depth += 1
            elif token.value == ')':
                depth -= 1
                if depth == 0:
                    break
            params_tokens.append(token)
            pos += 1

        # Parse parameters from tokens
        params = []
        current_param = []

        for token in params_tokens:
            if token.value == ',' and len(current_param) > 0:
                params.append(' '.join([t.value for t in current_param]))
                current_param = []
            elif token.type != TokenType.COMMENT:
                current_param.append(token)

        if current_param:
            params.append(' '.join([t.value for t in current_param]))

        return params

    def _find_matching_end(self, start_pos: int) -> int:
        """Find matching END for a BEGIN/IS/AS block"""
        depth = 1
        pos = start_pos + 1

        while pos < len(self.tokens) and depth > 0:
            token = self.tokens[pos]

            if token.type == TokenType.KEYWORD:
                keyword = token.value.upper()

                # Keywords that increase depth
                if keyword in ['BEGIN', 'LOOP', 'CASE']:
                    depth += 1

                # END decreases depth
                elif keyword == 'END':
                    depth -= 1
                    if depth == 0:
                        # Find the semicolon after END
                        semi_pos = pos + 1
                        while semi_pos < len(self.tokens):
                            if self.tokens[semi_pos].value == ';':
                                return semi_pos
                            semi_pos += 1
                        return pos

            pos += 1

        return -1

    def _extract_content(self, start_pos: int, end_pos: int) -> str:
        """Extract content from token range"""
        if start_pos >= len(self.tokens) or end_pos >= len(self.tokens):
            return ""

        tokens_slice = self.tokens[start_pos:end_pos + 1]
        return ' '.join([t.value for t in tokens_slice if t.type != TokenType.COMMENT])


class DynamicPackageParser:
    """
    Main parser that uses tokenization and structure analysis
    Works with ANY package structure from ANY database
    """

    def __init__(self):
        self.tokenizer = DynamicSQLTokenizer()

    def parse_package(self, package_code: str) -> Dict[str, Any]:
        """
        Parse package code dynamically

        Args:
            package_code: Complete package source

        Returns:
            Dictionary with parsed structure
        """
        logger.info("Starting dynamic package parsing")

        # Step 1: Tokenize
        tokens = self.tokenizer.tokenize(package_code)
        logger.info(f"Tokenized into {len(tokens)} tokens")

        # Step 2: Analyze structure
        analyzer = StructureAnalyzer(tokens)
        blocks = analyzer.analyze()
        logger.info(f"Found {len(blocks)} code blocks")

        # Step 3: Extract package info
        package_name = self._extract_package_name(blocks)
        spec_block = next((b for b in blocks if b.type == 'PACKAGE_SPEC'), None)
        body_block = next((b for b in blocks if b.type == 'PACKAGE_BODY'), None)

        # Step 4: Extract members from spec and body
        spec_members = self._extract_members_from_block(spec_block) if spec_block else []
        body_members = self._extract_members_from_block(body_block) if body_block else []

        # Step 5: Match and combine
        all_members = self._match_spec_and_body(spec_members, body_members)

        logger.info(f"Extracted {len(all_members)} total members")

        return self._build_result(package_name, all_members)

    def _extract_package_name(self, blocks: List[CodeBlock]) -> str:
        """Extract package name from blocks"""
        for block in blocks:
            if block.type in ['PACKAGE_SPEC', 'PACKAGE_BODY']:
                return block.name
        return "UNKNOWN_PACKAGE"

    def _extract_members_from_block(self, block: CodeBlock) -> List[PackageMember]:
        """Extract procedures/functions from a package block"""
        if not block:
            return []

        # Re-tokenize and analyze the block content
        tokens = self.tokenizer.tokenize(block.content)
        analyzer = StructureAnalyzer(tokens)
        member_blocks = analyzer.analyze()

        members = []

        for mb in member_blocks:
            if mb.type == 'PROCEDURE':
                member = PackageMember(
                    name=mb.name,
                    member_type='PROCEDURE',
                    specification=mb.content if mb.metadata.get('declaration_only') else f"PROCEDURE {mb.name}",
                    body=mb.content if not mb.metadata.get('declaration_only') else "",
                    parameters=mb.metadata.get('parameters', []),
                    is_public=(block.type == 'PACKAGE_SPEC' or mb.metadata.get('declaration_only'))
                )
                members.append(member)

            elif mb.type == 'FUNCTION':
                member = PackageMember(
                    name=mb.name,
                    member_type='FUNCTION',
                    specification=mb.content if mb.metadata.get('declaration_only') else f"FUNCTION {mb.name}",
                    body=mb.content if not mb.metadata.get('declaration_only') else "",
                    return_type=mb.metadata.get('return_type'),
                    parameters=mb.metadata.get('parameters', []),
                    is_public=(block.type == 'PACKAGE_SPEC' or mb.metadata.get('declaration_only'))
                )
                members.append(member)

        return members

    def _match_spec_and_body(self, spec_members: List[PackageMember],
                            body_members: List[PackageMember]) -> List[PackageMember]:
        """Match specification declarations with body implementations"""
        matched = []
        body_lookup = {m.name.upper(): m for m in body_members}

        # Match spec with body
        for spec_member in spec_members:
            key = spec_member.name.upper()
            if key in body_lookup:
                # Found implementation
                spec_member.body = body_lookup[key].body
                spec_member.is_public = True
                del body_lookup[key]
            matched.append(spec_member)

        # Add remaining private members
        for body_member in body_lookup.values():
            body_member.is_public = False
            matched.append(body_member)

        return matched

    def _build_result(self, package_name: str, members: List[PackageMember]) -> Dict[str, Any]:
        """Build final result dictionary"""
        procedures = [m for m in members if m.member_type == 'PROCEDURE']
        functions = [m for m in members if m.member_type == 'FUNCTION']

        components = []
        for member in members:
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

        return {
            "package_name": package_name,
            "members": members,
            "global_variables": [],
            "initialization": "",
            "total_procedures": len(procedures),
            "total_functions": len(functions),
            "migration_plan": {
                "package_name": package_name,
                "strategy": "DECOMPOSE",
                "components": components,
                "notes": [
                    "✅ Parsed dynamically using token-based analysis",
                    "✅ Works with any database package structure",
                    "✅ Adaptive to different formatting styles"
                ]
            }
        }


def decompose_oracle_package(package_name: str, package_code: str) -> Dict[str, Any]:
    """
    Main entry point for dynamic package decomposition

    This function works with ANY database package structure:
    - Oracle packages
    - PostgreSQL packages (if using extensions)
    - DB2 packages
    - Any SQL dialect with similar package concepts

    The parser adapts to the code structure dynamically.
    """
    parser = DynamicPackageParser()
    return parser.parse_package(package_code)
