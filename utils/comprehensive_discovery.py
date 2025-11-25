"""
Comprehensive Database Discovery System

Discovers ALL database objects upfront in a single pass:
- Tables (with row counts)
- Packages
- Procedures
- Functions
- Triggers
- Views
- Sequences
- Synonyms
- Types

Returns structured data perfect for frontend integration.
"""

import logging
from typing import Dict, List, Any
from dataclasses import dataclass, field
from database.oracle_connector import OracleConnector

logger = logging.getLogger(__name__)


@dataclass
class DatabaseObject:
    """Represents a database object"""
    name: str
    object_type: str  # TABLE, PACKAGE, PROCEDURE, FUNCTION, TRIGGER, etc.
    status: str  # VALID, INVALID
    created: str = ""
    last_ddl: str = ""
    row_count: int = 0  # For tables
    size_mb: float = 0.0  # For tables
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DiscoveryResult:
    """Complete discovery results"""
    tables: List[DatabaseObject]
    packages: List[DatabaseObject]
    procedures: List[DatabaseObject]
    functions: List[DatabaseObject]
    triggers: List[DatabaseObject]
    views: List[DatabaseObject]
    sequences: List[DatabaseObject]
    types: List[DatabaseObject]
    synonyms: List[DatabaseObject]

    total_objects: int = 0
    discovery_time_seconds: float = 0.0
    errors: List[str] = field(default_factory=list)


class ComprehensiveDiscovery:
    """
    Discovers ALL database objects in one pass
    Perfect for frontend integration - returns structured JSON
    """

    def __init__(self, oracle_connector: OracleConnector):
        self.oracle_conn = oracle_connector
        self.logger = logging.getLogger(__name__)

    def discover_all(self) -> DiscoveryResult:
        """
        Discover ALL database objects upfront

        Returns:
            DiscoveryResult with all objects categorized
        """
        import time
        start_time = time.time()

        self.logger.info("🔍 Starting comprehensive database discovery...")

        result = DiscoveryResult(
            tables=[],
            packages=[],
            procedures=[],
            functions=[],
            triggers=[],
            views=[],
            sequences=[],
            types=[],
            synonyms=[]
        )

        try:
            # Discover all object types
            result.tables = self._discover_tables()
            result.packages = self._discover_packages()
            result.procedures = self._discover_procedures()
            result.functions = self._discover_functions()
            result.triggers = self._discover_triggers()
            result.views = self._discover_views()
            result.sequences = self._discover_sequences()
            result.types = self._discover_types()
            result.synonyms = self._discover_synonyms()

            # Calculate totals
            result.total_objects = (
                len(result.tables) +
                len(result.packages) +
                len(result.procedures) +
                len(result.functions) +
                len(result.triggers) +
                len(result.views) +
                len(result.sequences) +
                len(result.types) +
                len(result.synonyms)
            )

            result.discovery_time_seconds = time.time() - start_time

            self.logger.info(f"✅ Discovery complete: {result.total_objects} objects found in {result.discovery_time_seconds:.2f}s")

        except Exception as e:
            self.logger.error(f"Discovery failed: {e}")
            result.errors.append(str(e))

        return result

    def _discover_tables(self) -> List[DatabaseObject]:
        """Discover all tables with row counts and sizes"""
        self.logger.info("  📊 Discovering tables...")

        query = """
        SELECT
            t.table_name,
            t.num_rows,
            s.bytes / 1024 / 1024 as size_mb,
            o.created,
            o.last_ddl_time,
            o.status
        FROM user_tables t
        LEFT JOIN user_segments s ON s.segment_name = t.table_name AND s.segment_type = 'TABLE'
        LEFT JOIN user_objects o ON o.object_name = t.table_name AND o.object_type = 'TABLE'
        ORDER BY t.table_name
        """

        tables = []
        try:
            results = self.oracle_conn.execute_query(query)
            for row in results:
                # Get actual row count (user_tables.num_rows might be stale)
                try:
                    count_query = f"SELECT COUNT(*) FROM {row[0]}"
                    count_result = self.oracle_conn.execute_query(count_query)
                    actual_count = count_result[0][0] if count_result else 0
                except:
                    actual_count = row[1] or 0

                tables.append(DatabaseObject(
                    name=row[0],
                    object_type='TABLE',
                    row_count=actual_count,
                    size_mb=float(row[2] or 0),
                    created=str(row[3]) if row[3] else "",
                    last_ddl=str(row[4]) if row[4] else "",
                    status=row[5] or "UNKNOWN"
                ))

            self.logger.info(f"    ✅ Found {len(tables)} tables")
        except Exception as e:
            self.logger.error(f"    ❌ Table discovery failed: {e}")

        return tables

    def _discover_packages(self) -> List[DatabaseObject]:
        """Discover all packages"""
        self.logger.info("  📦 Discovering packages...")

        query = """
        SELECT
            object_name,
            status,
            created,
            last_ddl_time
        FROM user_objects
        WHERE object_type = 'PACKAGE'
        ORDER BY object_name
        """

        packages = []
        try:
            results = self.oracle_conn.execute_query(query)
            for row in results:
                # Get package member count
                member_query = f"""
                SELECT COUNT(*)
                FROM user_procedures
                WHERE object_name = '{row[0]}' AND object_type = 'PACKAGE'
                """
                try:
                    member_count = self.oracle_conn.execute_query(member_query)[0][0]
                except:
                    member_count = 0

                packages.append(DatabaseObject(
                    name=row[0],
                    object_type='PACKAGE',
                    status=row[1],
                    created=str(row[2]) if row[2] else "",
                    last_ddl=str(row[3]) if row[3] else "",
                    metadata={'member_count': member_count}
                ))

            self.logger.info(f"    ✅ Found {len(packages)} packages")
        except Exception as e:
            self.logger.error(f"    ❌ Package discovery failed: {e}")

        return packages

    def _discover_procedures(self) -> List[DatabaseObject]:
        """Discover standalone procedures"""
        self.logger.info("  🔧 Discovering procedures...")

        query = """
        SELECT
            object_name,
            status,
            created,
            last_ddl_time
        FROM user_objects
        WHERE object_type = 'PROCEDURE'
        ORDER BY object_name
        """

        procedures = []
        try:
            results = self.oracle_conn.execute_query(query)
            for row in results:
                procedures.append(DatabaseObject(
                    name=row[0],
                    object_type='PROCEDURE',
                    status=row[1],
                    created=str(row[2]) if row[2] else "",
                    last_ddl=str(row[3]) if row[3] else ""
                ))

            self.logger.info(f"    ✅ Found {len(procedures)} procedures")
        except Exception as e:
            self.logger.error(f"    ❌ Procedure discovery failed: {e}")

        return procedures

    def _discover_functions(self) -> List[DatabaseObject]:
        """Discover standalone functions"""
        self.logger.info("  ⚙️ Discovering functions...")

        query = """
        SELECT
            object_name,
            status,
            created,
            last_ddl_time
        FROM user_objects
        WHERE object_type = 'FUNCTION'
        ORDER BY object_name
        """

        functions = []
        try:
            results = self.oracle_conn.execute_query(query)
            for row in results:
                functions.append(DatabaseObject(
                    name=row[0],
                    object_type='FUNCTION',
                    status=row[1],
                    created=str(row[2]) if row[2] else "",
                    last_ddl=str(row[3]) if row[3] else ""
                ))

            self.logger.info(f"    ✅ Found {len(functions)} functions")
        except Exception as e:
            self.logger.error(f"    ❌ Function discovery failed: {e}")

        return functions

    def _discover_triggers(self) -> List[DatabaseObject]:
        """Discover all triggers"""
        self.logger.info("  ⚡ Discovering triggers...")

        query = """
        SELECT
            trigger_name,
            status,
            table_name,
            triggering_event,
            trigger_type
        FROM user_triggers
        ORDER BY trigger_name
        """

        triggers = []
        try:
            results = self.oracle_conn.execute_query(query)
            for row in results:
                triggers.append(DatabaseObject(
                    name=row[0],
                    object_type='TRIGGER',
                    status=row[1],
                    metadata={
                        'table_name': row[2],
                        'event': row[3],
                        'type': row[4]
                    }
                ))

            self.logger.info(f"    ✅ Found {len(triggers)} triggers")
        except Exception as e:
            self.logger.error(f"    ❌ Trigger discovery failed: {e}")

        return triggers

    def _discover_views(self) -> List[DatabaseObject]:
        """Discover all views"""
        self.logger.info("  👁️ Discovering views...")

        query = """
        SELECT
            view_name
        FROM user_views
        ORDER BY view_name
        """

        views = []
        try:
            results = self.oracle_conn.execute_query(query)
            for row in results:
                views.append(DatabaseObject(
                    name=row[0],
                    object_type='VIEW',
                    status='VALID'
                ))

            self.logger.info(f"    ✅ Found {len(views)} views")
        except Exception as e:
            self.logger.error(f"    ❌ View discovery failed: {e}")

        return views

    def _discover_sequences(self) -> List[DatabaseObject]:
        """Discover all sequences"""
        self.logger.info("  🔢 Discovering sequences...")

        query = """
        SELECT
            sequence_name,
            min_value,
            max_value,
            increment_by,
            last_number
        FROM user_sequences
        ORDER BY sequence_name
        """

        sequences = []
        try:
            results = self.oracle_conn.execute_query(query)
            for row in results:
                sequences.append(DatabaseObject(
                    name=row[0],
                    object_type='SEQUENCE',
                    status='VALID',
                    metadata={
                        'min_value': row[1],
                        'max_value': row[2],
                        'increment': row[3],
                        'current_value': row[4]
                    }
                ))

            self.logger.info(f"    ✅ Found {len(sequences)} sequences")
        except Exception as e:
            self.logger.error(f"    ❌ Sequence discovery failed: {e}")

        return sequences

    def _discover_types(self) -> List[DatabaseObject]:
        """Discover custom types"""
        self.logger.info("  📝 Discovering types...")

        query = """
        SELECT
            object_name,
            status
        FROM user_objects
        WHERE object_type IN ('TYPE', 'TYPE BODY')
        ORDER BY object_name
        """

        types = []
        try:
            results = self.oracle_conn.execute_query(query)
            for row in results:
                types.append(DatabaseObject(
                    name=row[0],
                    object_type='TYPE',
                    status=row[1]
                ))

            self.logger.info(f"    ✅ Found {len(types)} types")
        except Exception as e:
            self.logger.error(f"    ❌ Type discovery failed: {e}")

        return types

    def _discover_synonyms(self) -> List[DatabaseObject]:
        """Discover synonyms"""
        self.logger.info("  🔗 Discovering synonyms...")

        query = """
        SELECT
            synonym_name,
            table_owner,
            table_name
        FROM user_synonyms
        ORDER BY synonym_name
        """

        synonyms = []
        try:
            results = self.oracle_conn.execute_query(query)
            for row in results:
                synonyms.append(DatabaseObject(
                    name=row[0],
                    object_type='SYNONYM',
                    status='VALID',
                    metadata={
                        'target_owner': row[1],
                        'target_name': row[2]
                    }
                ))

            self.logger.info(f"    ✅ Found {len(synonyms)} synonyms")
        except Exception as e:
            self.logger.error(f"    ❌ Synonym discovery failed: {e}")

        return synonyms

    def to_json(self, result: DiscoveryResult) -> Dict[str, Any]:
        """
        Convert discovery result to JSON (perfect for frontend)

        Returns:
            JSON-serializable dictionary
        """
        return {
            "summary": {
                "total_objects": result.total_objects,
                "discovery_time": f"{result.discovery_time_seconds:.2f}s",
                "errors": result.errors
            },
            "counts": {
                "tables": len(result.tables),
                "packages": len(result.packages),
                "procedures": len(result.procedures),
                "functions": len(result.functions),
                "triggers": len(result.triggers),
                "views": len(result.views),
                "sequences": len(result.sequences),
                "types": len(result.types),
                "synonyms": len(result.synonyms)
            },
            "objects": {
                "tables": [self._object_to_dict(obj) for obj in result.tables],
                "packages": [self._object_to_dict(obj) for obj in result.packages],
                "procedures": [self._object_to_dict(obj) for obj in result.procedures],
                "functions": [self._object_to_dict(obj) for obj in result.functions],
                "triggers": [self._object_to_dict(obj) for obj in result.triggers],
                "views": [self._object_to_dict(obj) for obj in result.views],
                "sequences": [self._object_to_dict(obj) for obj in result.sequences],
                "types": [self._object_to_dict(obj) for obj in result.types],
                "synonyms": [self._object_to_dict(obj) for obj in result.synonyms]
            }
        }

    def _object_to_dict(self, obj: DatabaseObject) -> Dict[str, Any]:
        """Convert DatabaseObject to dictionary"""
        return {
            "name": obj.name,
            "type": obj.object_type,
            "status": obj.status,
            "created": obj.created,
            "last_modified": obj.last_ddl,
            "row_count": obj.row_count,
            "size_mb": obj.size_mb,
            "metadata": obj.metadata
        }
