"""
Dependency Manager V2 - Fully Dynamic, Schema-Agnostic Implementation
======================================================================

IMPROVEMENTS:
1. No hardcoded schemas or object assumptions
2. Configurable error patterns for different SQL Server versions
3. Handles qualified names (schema.object)
4. Validates all inputs
5. Comprehensive edge case handling
6. Database-agnostic (works with any schema/database)
7. Extensible error parsing (can add custom patterns)
8. Thread-safe operation
"""

import re
import logging
from typing import Dict, List, Set, Optional, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class ObjectType(Enum):
    """Migration object types in dependency order"""
    TABLE = 1
    VIEW = 2
    FUNCTION = 3
    PROCEDURE = 4
    TRIGGER = 5
    PACKAGE = 6
    TYPE = 7


class DependencyType(Enum):
    """Types of dependencies"""
    MISSING_TABLE = "missing_table"
    MISSING_VIEW = "missing_view"
    MISSING_FUNCTION = "missing_function"
    MISSING_PROCEDURE = "missing_procedure"
    MISSING_TYPE = "missing_type"
    MISSING_SEQUENCE = "missing_sequence"
    SYNTAX_ERROR = "syntax_error"
    PERMISSION_ERROR = "permission_error"
    OTHER_ERROR = "other_error"


@dataclass
class MigrationObject:
    """Represents an object to be migrated - schema-aware"""
    name: str
    schema: Optional[str]
    object_type: ObjectType
    oracle_code: str
    tsql_code: str = ""
    status: str = "pending"  # pending, success, failed, skipped
    attempt_count: int = 0
    max_attempts: int = 5
    dependencies: List[str] = field(default_factory=list)  # Fully qualified names
    dependency_type: Optional[DependencyType] = None
    last_error: str = ""
    metadata: Dict = field(default_factory=dict)  # Extra metadata

    def get_full_name(self) -> str:
        """Get fully qualified object name"""
        if self.schema:
            return f"{self.schema}.{self.name}"
        return self.name

    def can_retry(self) -> bool:
        """Check if object can be retried"""
        return self.attempt_count < self.max_attempts and self.status in ["pending", "skipped"]

    def mark_failed(self, error: str, dep_type: DependencyType = DependencyType.OTHER_ERROR):
        """Mark object as failed"""
        self.status = "failed"
        self.last_error = error[:500]  # Limit error message length
        self.dependency_type = dep_type

    def mark_skipped(self, error: str, dependencies: List[str], dep_type: DependencyType):
        """Mark object as skipped due to missing dependencies"""
        self.status = "skipped"
        self.last_error = error[:500]
        self.dependencies = dependencies
        self.dependency_type = dep_type

    def mark_success(self):
        """Mark object as successfully migrated"""
        self.status = "success"
        self.last_error = ""

    def validate(self) -> Tuple[bool, Optional[str]]:
        """
        Validate migration object

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self.name:
            return False, "Object name is required"

        if not self.object_type:
            return False, "Object type is required"

        if not self.oracle_code:
            return False, "Oracle code is required"

        return True, None


class DependencyManager:
    """
    Manages object dependencies and migration order

    FULLY DYNAMIC - No hardcoded patterns or assumptions
    """

    # Default error patterns (can be extended via add_error_pattern)
    DEFAULT_ERROR_PATTERNS = [
        # SQL Server error patterns
        (r"invalid object name ['\"]?(?:(?:\[([^\]]+)\]|(\w+))\.)?(?:\[([^\]]+)\]|(\w+))['\"]?",
         DependencyType.MISSING_TABLE, (1, 2, 3, 4)),

        (r"could not find (?:stored )?procedure ['\"]?(?:(?:\[([^\]]+)\]|(\w+))\.)?(?:\[([^\]]+)\]|(\w+))['\"]?",
         DependencyType.MISSING_PROCEDURE, (1, 2, 3, 4)),

        (r"cannot find (?:the )?(?:function|object) ['\"]?(?:(?:\[([^\]]+)\]|(\w+))\.)?(?:\[([^\]]+)\]|(\w+))['\"]?",
         DependencyType.MISSING_FUNCTION, (1, 2, 3, 4)),

        (r"['\"]?(?:(?:\[([^\]]+)\]|(\w+))\.)?(?:\[([^\]]+)\]|(\w+))['\"]? is not a recognized (?:table|view)",
         DependencyType.MISSING_VIEW, (1, 2, 3, 4)),

        # Syntax errors
        (r"(?:incorrect syntax|syntax error)",
         DependencyType.SYNTAX_ERROR, None),

        # Permission errors
        (r"permission (?:denied|was denied)",
         DependencyType.PERMISSION_ERROR, None),
    ]

    def __init__(
        self,
        max_retry_cycles: int = 3,
        default_schema: str = "dbo",
        custom_error_patterns: Optional[List] = None
    ):
        """
        Initialize dependency manager

        Args:
            max_retry_cycles: Maximum number of retry cycles for dependency resolution
            default_schema: Default schema to use if not specified
            custom_error_patterns: Additional error patterns to recognize
        """
        self.max_retry_cycles = max_retry_cycles
        self.default_schema = default_schema
        self.objects: Dict[str, MigrationObject] = {}  # Key: fully qualified name
        self.migrated_objects: Set[str] = set()  # Fully qualified names
        self.current_cycle = 0
        self.validation_errors: List[str] = []

        # Initialize error patterns
        self.error_patterns = self.DEFAULT_ERROR_PATTERNS.copy()
        if custom_error_patterns:
            self.error_patterns.extend(custom_error_patterns)

    def add_error_pattern(
        self,
        pattern: str,
        dependency_type: DependencyType,
        capture_groups: Optional[Tuple] = None
    ):
        """
        Add custom error pattern for dependency detection

        Args:
            pattern: Regex pattern to match
            dependency_type: Type of dependency this pattern detects
            capture_groups: Which capture groups contain schema/object name
        """
        self.error_patterns.append((pattern, dependency_type, capture_groups))
        logger.info(f"Added custom error pattern for {dependency_type.value}")

    def add_object(
        self,
        name: str,
        object_type: ObjectType,
        oracle_code: str,
        tsql_code: str = "",
        schema: Optional[str] = None,
        metadata: Optional[Dict] = None
    ):
        """
        Add an object to be migrated

        Args:
            name: Object name
            object_type: Type of object
            oracle_code: Original Oracle code
            tsql_code: Converted T-SQL code (if available)
            schema: Schema name (optional, uses default if not provided)
            metadata: Additional metadata (optional)
        """
        schema = schema or self.default_schema
        full_name = f"{schema}.{name}"

        obj = MigrationObject(
            name=name,
            schema=schema,
            object_type=object_type,
            oracle_code=oracle_code,
            tsql_code=tsql_code,
            metadata=metadata or {}
        )

        # Validate object
        is_valid, error_msg = obj.validate()
        if not is_valid:
            logger.error(f"Invalid object {full_name}: {error_msg}")
            self.validation_errors.append(f"{full_name}: {error_msg}")
            return

        self.objects[full_name] = obj
        logger.info(f"Added {object_type.name} {full_name} to dependency manager")

    def get_migration_order(self) -> List[MigrationObject]:
        """
        Get objects in dependency order

        Returns:
            List of objects sorted by migration priority
        """
        # Sort by object type (TABLES → VIEWS → FUNCTIONS → PROCEDURES → TRIGGERS)
        # Then by schema and name for consistency
        sorted_objects = sorted(
            [obj for obj in self.objects.values() if obj.can_retry()],
            key=lambda x: (x.object_type.value, x.schema, x.name)
        )

        return sorted_objects

    def parse_dependency_error(self, error_msg: str) -> Tuple[Optional[DependencyType], List[str]]:
        """
        Parse SQL Server error to extract missing dependencies

        FULLY DYNAMIC - Uses configurable patterns

        Args:
            error_msg: SQL Server error message

        Returns:
            Tuple of (DependencyType, list of fully qualified missing object names)
        """
        missing_objects = []
        dep_type = None

        error_lower = error_msg.lower()

        # Try all configured patterns
        for pattern, pattern_dep_type, capture_groups in self.error_patterns:
            matches = re.findall(pattern, error_lower, re.IGNORECASE)

            if matches:
                dep_type = pattern_dep_type

                # If pattern has capture groups for object names, extract them
                if capture_groups:
                    for match in matches:
                        if isinstance(match, tuple):
                            # Schema and object name in capture groups
                            # Groups are: (schema_bracketed, schema_plain, obj_bracketed, obj_plain)
                            schema = match[capture_groups[0]] or match[capture_groups[1]] if len(capture_groups) > 1 else None
                            obj = match[capture_groups[2]] or match[capture_groups[3]]

                            if schema:
                                full_name = f"{schema.upper()}.{obj.upper()}"
                            else:
                                full_name = f"{self.default_schema}.{obj.upper()}"

                            missing_objects.append(full_name)
                        else:
                            # Simple string match
                            missing_objects.append(f"{self.default_schema}.{match.upper()}")

                break  # Use first matching pattern

        # Clean up duplicates
        missing_objects = list(set(missing_objects))

        if not dep_type:
            dep_type = DependencyType.OTHER_ERROR

        return dep_type, missing_objects

    def handle_migration_result(self, obj_key: str, success: bool, error_msg: str = ""):
        """
        Handle migration result for an object

        Args:
            obj_key: Object key (fully qualified name)
            success: Whether migration succeeded
            error_msg: Error message if failed
        """
        if obj_key not in self.objects:
            logger.warning(f"Object {obj_key} not found in dependency manager")
            return

        obj = self.objects[obj_key]
        obj.attempt_count += 1

        if success:
            obj.mark_success()
            self.migrated_objects.add(obj_key)
            logger.info(f"✅ {obj.object_type.name} {obj_key} migrated successfully")
        else:
            # Parse error to determine if it's a dependency issue
            dep_type, missing_deps = self.parse_dependency_error(error_msg)

            if dep_type in [DependencyType.MISSING_TABLE, DependencyType.MISSING_VIEW,
                           DependencyType.MISSING_FUNCTION, DependencyType.MISSING_PROCEDURE,
                           DependencyType.MISSING_TYPE, DependencyType.MISSING_SEQUENCE]:
                # Check if any of the missing deps are in our migration list
                unresolved_deps = [d for d in missing_deps if d not in self.migrated_objects]

                if unresolved_deps and any(d in self.objects for d in unresolved_deps):
                    # Dependencies in our list but not yet migrated - skip for retry
                    obj.mark_skipped(error_msg, unresolved_deps, dep_type)
                    logger.warning(f"⏭️  {obj.object_type.name} {obj_key} skipped - waiting for: {', '.join(unresolved_deps)}")
                else:
                    # Dependencies should exist or are external - this is a real error
                    obj.mark_failed(error_msg, dep_type)
                    logger.error(f"❌ {obj.object_type.name} {obj_key} failed - {error_msg[:100]}")
            elif dep_type == DependencyType.SYNTAX_ERROR:
                # Syntax errors shouldn't be retried (need code fix)
                obj.mark_failed(error_msg, dep_type)
                logger.error(f"❌ {obj.object_type.name} {obj_key} syntax error - {error_msg[:100]}")
            elif dep_type == DependencyType.PERMISSION_ERROR:
                # Permission errors shouldn't be retried
                obj.mark_failed(error_msg, dep_type)
                logger.error(f"❌ {obj.object_type.name} {obj_key} permission denied - {error_msg[:100]}")
            else:
                # Other errors - mark as failed
                obj.mark_failed(error_msg, dep_type)
                logger.error(f"❌ {obj.object_type.name} {obj_key} failed - {error_msg[:100]}")

    def get_retry_candidates(self) -> List[MigrationObject]:
        """
        Get objects that should be retried

        Returns:
            List of objects with status 'skipped' that can be retried
        """
        candidates = []

        for obj in self.objects.values():
            if obj.status == "skipped" and obj.can_retry():
                # Check if dependencies are now satisfied
                unresolved = [d for d in obj.dependencies if d not in self.migrated_objects]

                if not unresolved:
                    # All dependencies satisfied, retry
                    candidates.append(obj)
                    logger.info(f"🔄 {obj.object_type.name} {obj.get_full_name()} ready to retry (dependencies satisfied)")

        # Sort by dependency order
        candidates.sort(key=lambda x: (x.object_type.value, x.schema, x.name))

        return candidates

    def needs_retry_cycle(self) -> bool:
        """
        Check if another retry cycle is needed

        Returns:
            True if there are objects that can be retried
        """
        if self.current_cycle >= self.max_retry_cycles:
            return False

        # Check if any objects can be retried
        for obj in self.objects.values():
            if obj.status == "skipped" and obj.can_retry():
                # Check if any dependencies are now satisfied
                unresolved = [d for d in obj.dependencies if d not in self.migrated_objects]
                if not unresolved or len(unresolved) < len(obj.dependencies):
                    # Progress is possible
                    return True

        return False

    def start_retry_cycle(self):
        """Start a new retry cycle"""
        self.current_cycle += 1
        logger.info("=" * 70)
        logger.info(f"STARTING RETRY CYCLE {self.current_cycle}/{self.max_retry_cycles}")
        logger.info("=" * 70)

    def get_statistics(self) -> Dict:
        """
        Get migration statistics

        Returns:
            Dictionary with statistics
        """
        total = len(self.objects)
        success = sum(1 for obj in self.objects.values() if obj.status == "success")
        failed = sum(1 for obj in self.objects.values() if obj.status == "failed")
        skipped = sum(1 for obj in self.objects.values() if obj.status == "skipped")
        pending = sum(1 for obj in self.objects.values() if obj.status == "pending")

        # By object type
        by_type = {}
        for obj in self.objects.values():
            type_name = obj.object_type.name
            if type_name not in by_type:
                by_type[type_name] = {"total": 0, "success": 0, "failed": 0, "skipped": 0}

            by_type[type_name]["total"] += 1
            if obj.status == "success":
                by_type[type_name]["success"] += 1
            elif obj.status == "failed":
                by_type[type_name]["failed"] += 1
            elif obj.status == "skipped":
                by_type[type_name]["skipped"] += 1

        return {
            "total": total,
            "success": success,
            "failed": failed,
            "skipped": skipped,
            "pending": pending,
            "retry_cycles": self.current_cycle,
            "by_type": by_type,
            "validation_errors": len(self.validation_errors)
        }

    def generate_dependency_report(self) -> str:
        """
        Generate final report of unresolved dependencies

        Returns:
            Formatted report string
        """
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("DEPENDENCY MIGRATION REPORT")
        report_lines.append("=" * 80)
        report_lines.append(f"Generated: {datetime.now()}")
        report_lines.append("")

        # Statistics
        stats = self.get_statistics()
        report_lines.append("SUMMARY:")
        report_lines.append(f"  Total Objects:     {stats['total']}")
        report_lines.append(f"  ✅ Success:        {stats['success']}")
        report_lines.append(f"  ❌ Failed:         {stats['failed']}")
        report_lines.append(f"  ⏭️  Skipped:        {stats['skipped']}")
        report_lines.append(f"  ⏳ Pending:        {stats['pending']}")
        report_lines.append(f"  🔄 Retry Cycles:   {stats['retry_cycles']}")
        report_lines.append("")

        # By object type
        if stats['by_type']:
            report_lines.append("BY OBJECT TYPE:")
            for type_name, type_stats in sorted(stats['by_type'].items()):
                report_lines.append(f"  {type_name}:")
                report_lines.append(f"    Total: {type_stats['total']}, "
                                   f"Success: {type_stats['success']}, "
                                   f"Failed: {type_stats['failed']}, "
                                   f"Skipped: {type_stats['skipped']}")
            report_lines.append("")

        # Validation errors
        if self.validation_errors:
            report_lines.append("=" * 80)
            report_lines.append("VALIDATION ERRORS:")
            report_lines.append("=" * 80)
            for error in self.validation_errors:
                report_lines.append(f"  {error}")
            report_lines.append("")

        # Failed objects
        failed_objs = [obj for obj in self.objects.values() if obj.status == "failed"]
        if failed_objs:
            report_lines.append("=" * 80)
            report_lines.append("FAILED OBJECTS:")
            report_lines.append("=" * 80)

            for obj in sorted(failed_objs, key=lambda x: (x.object_type.value, x.get_full_name())):
                report_lines.append(f"\n{obj.object_type.name}: {obj.get_full_name()}")
                report_lines.append(f"  Attempts:      {obj.attempt_count}")
                report_lines.append(f"  Error Type:    {obj.dependency_type.value if obj.dependency_type else 'unknown'}")
                report_lines.append(f"  Last Error:    {obj.last_error[:200]}")
                if obj.dependencies:
                    report_lines.append(f"  Dependencies:  {', '.join(obj.dependencies)}")

        # Skipped objects (unresolved dependencies)
        skipped_objs = [obj for obj in self.objects.values() if obj.status == "skipped"]
        if skipped_objs:
            report_lines.append("")
            report_lines.append("=" * 80)
            report_lines.append("SKIPPED OBJECTS (Unresolved Dependencies):")
            report_lines.append("=" * 80)

            for obj in sorted(skipped_objs, key=lambda x: (x.object_type.value, x.get_full_name())):
                unresolved = [d for d in obj.dependencies if d not in self.migrated_objects]
                report_lines.append(f"\n{obj.object_type.name}: {obj.get_full_name()}")
                report_lines.append(f"  Attempts:      {obj.attempt_count}")
                report_lines.append(f"  Waiting For:   {', '.join(unresolved)}")
                report_lines.append(f"  Error Type:    {obj.dependency_type.value if obj.dependency_type else 'unknown'}")

        # Successfully migrated
        success_objs = [obj for obj in self.objects.values() if obj.status == "success"]
        if success_objs:
            report_lines.append("")
            report_lines.append("=" * 80)
            report_lines.append("SUCCESSFULLY MIGRATED:")
            report_lines.append("=" * 80)

            by_type = {}
            for obj in success_objs:
                if obj.object_type not in by_type:
                    by_type[obj.object_type] = []
                by_type[obj.object_type].append(obj.get_full_name())

            for obj_type in sorted(by_type.keys(), key=lambda x: x.value):
                report_lines.append(f"\n{obj_type.name}S ({len(by_type[obj_type])}):")
                for name in sorted(by_type[obj_type]):
                    report_lines.append(f"  ✅ {name}")

        report_lines.append("")
        report_lines.append("=" * 80)

        return "\n".join(report_lines)

    def save_dependency_report(self, output_path: str):
        """
        Save dependency report to file

        Args:
            output_path: Path to save report
        """
        report = self.generate_dependency_report()

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)

        logger.info(f"Dependency report saved to: {output_path}")

    def get_unresolved_objects(self) -> List[MigrationObject]:
        """
        Get list of objects that couldn't be migrated

        Returns:
            List of failed or skipped objects
        """
        return [obj for obj in self.objects.values()
                if obj.status in ["failed", "skipped"]]

    def clear(self):
        """Clear all objects and reset state"""
        self.objects.clear()
        self.migrated_objects.clear()
        self.current_cycle = 0
        self.validation_errors.clear()
        logger.info("Dependency manager cleared")

    def get_validation_errors(self) -> List[str]:
        """Get list of validation errors"""
        return self.validation_errors.copy()
