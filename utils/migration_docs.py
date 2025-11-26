"""
Migration Documentation System
Saves Oracle source and SQL Server output in organized markdown files
for development verification and debugging.

Folder Structure:
    results/
    └── migration_YYYYMMDD_HHMMSS/
        ├── oracle/
        │   ├── tables/
        │   ├── procedures/
        │   ├── functions/
        │   ├── packages/
        │   ├── triggers/
        │   └── views/
        └── sql/
            ├── tables/
            ├── procedures/
            ├── functions/
            ├── packages/
            ├── triggers/
            └── views/
"""

import os
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class MigrationDocumenter:
    """
    Handles creation and organization of migration documentation
    in markdown format for development verification.
    """
    
    # Supported object types
    OBJECT_TYPES = ['tables', 'procedures', 'functions', 'packages', 'triggers', 'views']
    
    def __init__(self, enabled: bool = True, base_dir: str = "results"):
        """
        Initialize the documenter.
        
        Args:
            enabled: Whether documentation is enabled
            base_dir: Base directory for results (default: "results")
        """
        self.enabled = enabled
        self.base_dir = Path(base_dir)
        self.current_session_dir = None
        
        if self.enabled:
            self._create_new_session()
    
    def _create_new_session(self):
        """Create a new timestamped session folder."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_name = f"migration_{timestamp}"
        self.current_session_dir = self.base_dir / session_name
        
        # Create folder structure
        for source in ['oracle', 'sql']:
            for obj_type in self.OBJECT_TYPES:
                folder = self.current_session_dir / source / obj_type
                folder.mkdir(parents=True, exist_ok=True)
        
        # Create session info file
        self._create_session_info()
        
        logger.info(f"Created migration documentation session: {session_name}")
        print(f"📁 Documentation folder created: {self.current_session_dir}")
    
    def _create_session_info(self):
        """Create a README with session information."""
        readme_path = self.current_session_dir / "README.md"
        
        content = f"""# Migration Documentation Session

**Created**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Purpose
This folder contains Oracle source code and SQL Server output for development verification and debugging.

## Structure

### oracle/
Contains original Oracle database objects extracted from source:
- `tables/` - Table DDL
- `procedures/` - Stored procedures
- `functions/` - Functions
- `packages/` - Package code (spec + body)
- `triggers/` - Trigger definitions
- `views/` - View definitions

### sql/
Contains converted SQL Server code:
- `tables/` - Converted table DDL
- `procedures/` - Converted stored procedures
- `functions/` - Converted UDFs
- `packages/` - Decomposed package members
- `triggers/` - Converted triggers
- `views/` - Converted views

## Usage

1. **Verification**: Compare Oracle source with SQL Server output
2. **Debugging**: Review conversion quality and identify issues
3. **Performance Testing**: Use as reference for optimization
4. **Production**: Remove this folder before deployment

## Notes

- Each object is stored in a separate markdown file
- File names follow the pattern: `ObjectName.md`
- Metadata is included at the top of each file
- This is a development-only feature
"""
        
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def save_oracle_object(self, object_name: str, object_type: str, 
                          oracle_code: str, metadata: Optional[Dict] = None):
        """
        Save Oracle source code to documentation.
        
        Args:
            object_name: Name of the database object
            object_type: Type (TABLE, PROCEDURE, FUNCTION, PACKAGE, TRIGGER, VIEW)
            oracle_code: Oracle source code
            metadata: Optional metadata dictionary
        """
        if not self.enabled:
            return
        
        try:
            # Normalize object type
            obj_type_lower = object_type.lower()
            if obj_type_lower not in self.OBJECT_TYPES:
                # Map variations
                type_mapping = {
                    'table': 'tables',
                    'procedure': 'procedures',
                    'proc': 'procedures',
                    'function': 'functions',
                    'func': 'functions',
                    'package': 'packages',
                    'pkg': 'packages',
                    'trigger': 'triggers',
                    'view': 'views'
                }
                obj_type_lower = type_mapping.get(obj_type_lower, 'procedures')
            
            # Create file path
            file_path = self.current_session_dir / 'oracle' / obj_type_lower / f"{object_name}.md"
            
            # Generate markdown content
            content = self._generate_markdown(
                title=f"Oracle {object_type}: {object_name}",
                source="Oracle Database",
                code=oracle_code,
                language="sql",
                metadata=metadata
            )
            
            # Write to file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.debug(f"Saved Oracle {object_type}: {object_name}")
            
        except Exception as e:
            logger.error(f"Failed to save Oracle documentation for {object_name}: {e}")
    
    def save_sqlserver_object(self, object_name: str, object_type: str,
                             tsql_code: str, metadata: Optional[Dict] = None):
        """
        Save SQL Server converted code to documentation.
        
        Args:
            object_name: Name of the database object
            object_type: Type (TABLE, PROCEDURE, FUNCTION, PACKAGE, TRIGGER, VIEW)
            tsql_code: SQL Server T-SQL code
            metadata: Optional metadata dictionary
        """
        if not self.enabled:
            return
        
        try:
            # Normalize object type
            obj_type_lower = object_type.lower()
            if obj_type_lower not in self.OBJECT_TYPES:
                type_mapping = {
                    'table': 'tables',
                    'procedure': 'procedures',
                    'proc': 'procedures',
                    'function': 'functions',
                    'func': 'functions',
                    'package': 'packages',
                    'pkg': 'packages',
                    'trigger': 'triggers',
                    'view': 'views'
                }
                obj_type_lower = type_mapping.get(obj_type_lower, 'procedures')
            
            # Create file path
            file_path = self.current_session_dir / 'sql' / obj_type_lower / f"{object_name}.md"
            
            # Generate markdown content
            content = self._generate_markdown(
                title=f"SQL Server {object_type}: {object_name}",
                source="SQL Server (Converted)",
                code=tsql_code,
                language="sql",
                metadata=metadata
            )
            
            # Write to file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.debug(f"Saved SQL Server {object_type}: {object_name}")
            
        except Exception as e:
            logger.error(f"Failed to save SQL Server documentation for {object_name}: {e}")
    
    def _generate_markdown(self, title: str, source: str, code: str,
                          language: str = "sql", metadata: Optional[Dict] = None) -> str:
        """
        Generate markdown content for a database object.
        
        Args:
            title: Document title
            source: Source system (Oracle/SQL Server)
            code: Source code
            language: Code language for syntax highlighting
            metadata: Optional metadata
        
        Returns:
            Formatted markdown string
        """
        lines = [
            f"# {title}",
            "",
            f"**Source**: {source}  ",
            f"**Captured**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ",
        ]
        
        # Add metadata if provided
        if metadata:
            lines.append("")
            lines.append("## Metadata")
            lines.append("")
            for key, value in metadata.items():
                lines.append(f"- **{key}**: {value}")
        
        # Add code section
        lines.extend([
            "",
            "## Source Code",
            "",
            f"```{language}",
            code.strip(),
            "```",
            ""
        ])
        
        return "\n".join(lines)
    
    def get_session_path(self) -> Optional[Path]:
        """Get the current session directory path."""
        return self.current_session_dir
    
    def get_session_summary(self) -> Dict:
        """
        Get summary of current session documentation.
        
        Returns:
            Dictionary with counts of documented objects
        """
        if not self.enabled or not self.current_session_dir:
            return {}
        
        summary = {
            'session_dir': str(self.current_session_dir),
            'oracle': {},
            'sql': {}
        }
        
        for source in ['oracle', 'sql']:
            for obj_type in self.OBJECT_TYPES:
                folder = self.current_session_dir / source / obj_type
                if folder.exists():
                    count = len(list(folder.glob('*.md')))
                    if count > 0:
                        summary[source][obj_type] = count
        
        return summary


# Global documenter instance
_documenter = None


def get_documenter(enabled: bool = True) -> MigrationDocumenter:
    """
    Get or create the global documenter instance.
    
    Args:
        enabled: Whether documentation should be enabled
    
    Returns:
        MigrationDocumenter instance
    """
    global _documenter
    if _documenter is None:
        _documenter = MigrationDocumenter(enabled=enabled)
    return _documenter


def save_migration_pair(object_name: str, object_type: str,
                       oracle_code: str, tsql_code: str,
                       metadata: Optional[Dict] = None):
    """
    Convenience function to save both Oracle and SQL Server code.
    
    Args:
        object_name: Name of the object
        object_type: Type of object
        oracle_code: Oracle source code
        tsql_code: SQL Server T-SQL code
        metadata: Optional metadata
    """
    documenter = get_documenter()
    documenter.save_oracle_object(object_name, object_type, oracle_code, metadata)
    documenter.save_sqlserver_object(object_name, object_type, tsql_code, metadata)
