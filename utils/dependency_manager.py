"""
Dependency Manager - Handles object dependencies during migration
===================================================================

This module implements dependency-aware migration for PL/SQL code objects:
- Tracks object dependencies (tables, views, functions, procedures, triggers)
- Implements retry logic for objects with missing dependencies
- Maintains migration order: TABLES → VIEWS → FUNCTIONS → PROCEDURES → TRIGGERS
- Produces final report of unresolved dependencies
"""

import re
import logging
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ObjectType(Enum):
    """Migration object types in dependency order"""
    TABLE = 1
    VIEW = 2
    FUNCTION = 3
    PROCEDURE = 4
    TRIGGER = 5
    PACKAGE = 6  # Packages are complex, handled separately


class DependencyType(Enum):
    """Types of dependencies"""
    MISSING_TABLE = "missing_table"
    MISSING_VIEW = "missing_view"
    MISSING_FUNCTION = "missing_function"
    MISSING_PROCEDURE = "missing_procedure"
    MISSING_TYPE = "missing_type"
    SYNTAX_ERROR = "syntax_error"
    OTHER_ERROR = "other_error"


@dataclass
class MigrationObject:
    """Represents an object to be migrated"""
    name: str
    object_type: ObjectType
    oracle_code: str
    tsql_code: str = ""
    status: str = "pending"  # pending, success, failed, skipped
    attempt_count: int = 0
    max_attempts: int = 5
    dependencies: List[str] = field(default_factory=list)
    dependency_type: Optional[DependencyType] = None
    last_error: str = ""

    def can_retry(self) -> bool:
        """Check if object can be retried"""
        return self.attempt_count < self.max_attempts and self.status in ["pending", "skipped"]

    def mark_failed(self, error: str, dep_type: DependencyType = DependencyType.OTHER_ERROR):
        """Mark object as failed"""
        self.status = "failed"
        self.last_error = error
        self.dependency_type = dep_type

    def mark_skipped(self, error: str, dependencies: List[str], dep_type: DependencyType):
        """Mark object as skipped due to missing dependencies"""
        self.status = "skipped"
        self.last_error = error
        self.dependencies = dependencies
        self.dependency_type = dep_type

    def mark_success(self):
        """Mark object as successfully migrated"""
        self.status = "success"
        self.last_error = ""


class DependencyManager:
    """
    Manages object dependencies and migration order
    """

    def __init__(self, max_retry_cycles: int = 3):
        """
        Initialize dependency manager

        Args:
            max_retry_cycles: Maximum number of retry cycles for dependency resolution
        """
        self.max_retry_cycles = max_retry_cycles
        self.objects: Dict[str, MigrationObject] = {}
        self.migrated_objects: Set[str] = set()
        self.current_cycle = 0

    def add_object(self, name: str, object_type: ObjectType, oracle_code: str, tsql_code: str = ""):
        """
        Add an object to be migrated

        Args:
            name: Object name
            object_type: Type of object
            oracle_code: Original Oracle code
            tsql_code: Converted T-SQL code (if available)
        """
        self.objects[name] = MigrationObject(
            name=name,
            object_type=object_type,
            oracle_code=oracle_code,
            tsql_code=tsql_code
        )
        logger.info(f"Added {object_type.name} {name} to dependency manager")

    def get_migration_order(self) -> List[MigrationObject]:
        """
        Get objects in dependency order

        Returns:
            List of objects sorted by migration priority
        """
        # Sort by object type (TABLES → VIEWS → FUNCTIONS → PROCEDURES → TRIGGERS)
        sorted_objects = sorted(
            [obj for obj in self.objects.values() if obj.can_retry()],
            key=lambda x: (x.object_type.value, x.name)
        )

        return sorted_objects

    def parse_dependency_error(self, error_msg: str) -> Tuple[Optional[DependencyType], List[str]]:
        """
        Parse SQL Server error to extract missing dependencies

        Args:
            error_msg: SQL Server error message

        Returns:
            Tuple of (DependencyType, list of missing object names)
        """
        missing_objects = []
        dep_type = None

        error_lower = error_msg.lower()

        # Pattern: Invalid object name 'dbo.TABLE_NAME'
        invalid_obj_pattern = r"invalid object name ['\"]?(?:dbo\.)?([a-z0-9_]+)['\"]?"
        invalid_matches = re.findall(invalid_obj_pattern, error_lower, re.IGNORECASE)
        if invalid_matches:
            missing_objects.extend(invalid_matches)
            dep_type = DependencyType.MISSING_TABLE

        # Pattern: Could not find stored procedure 'PROC_NAME'
        proc_pattern = r"could not find (?:stored )?procedure ['\"]?(?:dbo\.)?([a-z0-9_]+)['\"]?"
        proc_matches = re.findall(proc_pattern, error_lower, re.IGNORECASE)
        if proc_matches:
            missing_objects.extend(proc_matches)
            dep_type = DependencyType.MISSING_PROCEDURE

        # Pattern: Cannot find the object "FUNCTION_NAME"
        obj_pattern = r"cannot find (?:the )?object ['\"]?(?:dbo\.)?([a-z0-9_]+)['\"]?"
        obj_matches = re.findall(obj_pattern, error_lower, re.IGNORECASE)
        if obj_matches:
            missing_objects.extend(obj_matches)
            if dep_type is None:
                dep_type = DependencyType.MISSING_TABLE

        # Pattern: 'VIEW_NAME' is not a recognized table
        view_pattern = r"['\"]?([a-z0-9_]+)['\"]? is not a recognized (?:table|view)"
        view_matches = re.findall(view_pattern, error_lower, re.IGNORECASE)
        if view_matches:
            missing_objects.extend(view_matches)
            dep_type = DependencyType.MISSING_VIEW

        # Syntax errors
        if "syntax" in error_lower or "incorrect syntax" in error_lower:
            dep_type = DependencyType.SYNTAX_ERROR

        # Clean up duplicates and convert to uppercase
        missing_objects = list(set([obj.upper() for obj in missing_objects]))

        if not dep_type:
            dep_type = DependencyType.OTHER_ERROR

        return dep_type, missing_objects

    def handle_migration_result(self, name: str, success: bool, error_msg: str = ""):
        """
        Handle migration result for an object

        Args:
            name: Object name
            success: Whether migration succeeded
            error_msg: Error message if failed
        """
        if name not in self.objects:
            logger.warning(f"Object {name} not found in dependency manager")
            return

        obj = self.objects[name]
        obj.attempt_count += 1

        if success:
            obj.mark_success()
            self.migrated_objects.add(name)
            logger.info(f"✅ {obj.object_type.name} {name} migrated successfully")
        else:
            # Parse error to determine if it's a dependency issue
            dep_type, missing_deps = self.parse_dependency_error(error_msg)

            if dep_type in [DependencyType.MISSING_TABLE, DependencyType.MISSING_VIEW,
                           DependencyType.MISSING_FUNCTION, DependencyType.MISSING_PROCEDURE]:
                # Check if any of the missing deps are in our migration list
                unresolved_deps = [d for d in missing_deps if d not in self.migrated_objects]

                if unresolved_deps:
                    # Skip for now, retry later
                    obj.mark_skipped(error_msg, unresolved_deps, dep_type)
                    logger.warning(f"⏭️  {obj.object_type.name} {name} skipped - waiting for: {', '.join(unresolved_deps)}")
                else:
                    # Dependencies should exist, this is a real error
                    obj.mark_failed(error_msg, dep_type)
                    logger.error(f"❌ {obj.object_type.name} {name} failed - {error_msg[:100]}")
            elif dep_type == DependencyType.SYNTAX_ERROR:
                # Syntax errors shouldn't be retried (need code fix)
                obj.mark_failed(error_msg, dep_type)
                logger.error(f"❌ {obj.object_type.name} {name} syntax error - {error_msg[:100]}")
            else:
                # Other errors - mark as failed
                obj.mark_failed(error_msg, dep_type)
                logger.error(f"❌ {obj.object_type.name} {name} failed - {error_msg[:100]}")

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
                    logger.info(f"🔄 {obj.object_type.name} {obj.name} ready to retry (dependencies satisfied)")

        # Sort by dependency order
        candidates.sort(key=lambda x: (x.object_type.value, x.name))

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

        return {
            "total": total,
            "success": success,
            "failed": failed,
            "skipped": skipped,
            "pending": pending,
            "retry_cycles": self.current_cycle
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

        # Failed objects
        failed_objs = [obj for obj in self.objects.values() if obj.status == "failed"]
        if failed_objs:
            report_lines.append("=" * 80)
            report_lines.append("FAILED OBJECTS:")
            report_lines.append("=" * 80)

            for obj in sorted(failed_objs, key=lambda x: (x.object_type.value, x.name)):
                report_lines.append(f"\n{obj.object_type.name}: {obj.name}")
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

            for obj in sorted(skipped_objs, key=lambda x: (x.object_type.value, x.name)):
                unresolved = [d for d in obj.dependencies if d not in self.migrated_objects]
                report_lines.append(f"\n{obj.object_type.name}: {obj.name}")
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
                by_type[obj.object_type].append(obj.name)

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
