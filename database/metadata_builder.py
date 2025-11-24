"""
Full Oracle Memory Builder
--------------------------------
Extracts CLEAN Oracle metadata ONLY for real application schemas.
System schemas are automatically excluded.

Extracts:
    - Schemas
    - Tables + Columns
    - Constraints (PK, FK, Unique, Check)
    - Indexes
    - Triggers
    - Views
    - Procedures
    - Functions
    - Packages
    - Sequences

Outputs a clean OracleDatabaseMemory object.
"""

from __future__ import annotations

from typing import List, Optional, Dict, Any
from sqlalchemy import text
from sqlalchemy.engine import Engine

from memory.migration_memory import (
    OracleDatabaseMemory,
    SchemaInfo,
    TableInfo,
    ColumnInfo,
    ConstraintInfo,
    IndexInfo,
    TriggerInfo,
    ViewInfo,
    ProcedureInfo,
    FunctionInfo,
    PackageInfo,
    SequenceInfo,
)

from connection.db_connections import DBConnectionManager


# ------------------------------------------------------------------
# COMPLETE ORACLE SYSTEM SCHEMA LIST (DO NOT MIGRATE THESE)
# ------------------------------------------------------------------
ORACLE_SYSTEM_SCHEMAS = {
    "SYS", "SYSTEM", "XDB", "OUTLN", "MDSYS", "CTXSYS", "ORDSYS", "ORDDATA",
    "ORDPLUGINS", "LBACSYS", "DVSYS", "DVF", "WMSYS", "GSMADMIN_INTERNAL",
    "ANONYMOUS", "GSMCATUSER", "GGSYS", "DBSNMP", "REMOTE_SCHEDULER_AGENT",
    "XS$NULL", "APPQOSSYS", "AUDSYS", "OJVMSYS", "GSMUSER", "SYSBACKUP",
    "SYSDG", "SYSKM", "SYSRAC", "PDBADMIN", "DGPDB_INT", "VECSYS",
    "DBSFWUSER", "GGSHAREDCAP", "VBENCHMARK", "OLAPSYS", "OWBSYS",
    "OWBSYS_AUDIT", "EXFSYS", "SI_INFORMTN_SCHEMA", "TSMSYS","BAASSYS","DIP","SYS$UMF"
}


class OracleMemoryBuilder:

    def __init__(self, conn_manager: DBConnectionManager, oracle_connection_name: str):
        self.conn_manager = conn_manager
        self.oracle_connection_name = oracle_connection_name

    # ================================
    # PUBLIC INTERFACE
    # ================================
    def build_memory(
        self,
        target_schemas: Optional[List[str]] = None,
        include_system_schemas: bool = False,
    ) -> OracleDatabaseMemory:

        engine = self.conn_manager.get_engine(self.oracle_connection_name)
        instance_name = self._get_instance_name(engine)

        schema_list = self._get_schema_names(
            engine,
            target_schemas=target_schemas,
            include_system=include_system_schemas
        )

        memory = OracleDatabaseMemory(
            connection_name=self.oracle_connection_name,
            instance_name=instance_name,
            schemas=[],
        )

        for schema in schema_list:
            schema_info = SchemaInfo(name=schema)

            schema_info.tables.extend(self._extract_tables(engine, schema))
            schema_info.views.extend(self._extract_views(engine, schema))
            schema_info.sequences.extend(self._extract_sequences(engine, schema))
            schema_info.procedures.extend(self._extract_procedures(engine, schema))
            schema_info.functions.extend(self._extract_functions(engine, schema))
            schema_info.packages.extend(self._extract_packages(engine, schema))

            memory.schemas.append(schema_info)

        return memory

    # ================================
    # HELPERS
    # ================================
    def _get_engine(self) -> Engine:
        return self.conn_manager.get_engine(self.oracle_connection_name)

    def _get_instance_name(self, engine: Engine) -> Optional[str]:
        sql = "SELECT instance_name FROM v$instance"
        try:
            with engine.connect() as conn:
                row = conn.execute(text(sql)).fetchone()
                return row[0] if row else None
        except Exception:
            return None

    def _get_schema_names(
        self,
        engine: Engine,
        target_schemas: Optional[List[str]],
        include_system: bool,
    ) -> List[str]:

        desired = {s.upper() for s in target_schemas} if target_schemas else None

        schemas = []

        sql = "SELECT username FROM all_users"

        with engine.connect() as conn:
            for (username,) in conn.execute(text(sql)):
                u = username.upper()

                # Explicit list from the user
                if desired:
                    if u in desired:
                        schemas.append(u)
                    continue

                # System schemas excluded
                if not include_system and u in ORACLE_SYSTEM_SCHEMAS:
                    continue

                schemas.append(u)

        return schemas

    # ====================================================
    # TABLES + COLUMNS + CONSTRAINTS + INDEXES + TRIGGERS
    # ====================================================
    def _extract_tables(self, engine: Engine, schema: str) -> List[TableInfo]:
        tables: Dict[str, TableInfo] = {}

        sql_tables = """
            SELECT owner, table_name
            FROM all_tables
            WHERE owner = :owner
        """

        sql_columns = """
            SELECT owner, table_name, column_name,
                   data_type, data_length, nullable, data_default
            FROM all_tab_columns
            WHERE owner = :owner
            ORDER BY table_name, column_id
        """

        sql_constraints = """
            SELECT ac.constraint_name,
                   ac.constraint_type,
                   acc.table_name,
                   acc.column_name,
                   ac.r_constraint_name
            FROM all_constraints ac
            LEFT JOIN all_cons_columns acc
              ON ac.owner = acc.owner
             AND ac.constraint_name = acc.constraint_name
            WHERE ac.owner = :owner
        """

        sql_indexes = """
            SELECT index_name, table_name, uniqueness
            FROM all_indexes
            WHERE owner = :owner
        """

        sql_ind_cols = """
            SELECT index_name, column_name
            FROM all_ind_columns
            WHERE index_owner = :owner
        """

        sql_trigger_list = """
            SELECT trigger_name, triggering_event, table_name
            FROM all_triggers
            WHERE owner = :owner
        """

        sql_trigger_body = """
            SELECT text
            FROM all_source
            WHERE owner = :owner
              AND name = :trg
            ORDER BY line
        """

        with engine.connect() as conn:

            # ---- Tables ----
            for owner, tbl in conn.execute(text(sql_tables), {"owner": schema}):
                tables[tbl] = TableInfo(
                    owner=owner,
                    name=tbl,
                    columns=[],
                    constraints=[],
                    indexes=[],
                    triggers=[],
                    to_migrate=True,
                )

            # ---- Columns ----
            for row in conn.execute(text(sql_columns), {"owner": schema}):
                owner, tbl, col, dtype, length, nullable, default = row
                if tbl not in tables:
                    continue

                tables[tbl].columns.append(
                    ColumnInfo(
                        name=col,
                        data_type=dtype,
                        data_length=length,
                        nullable=(nullable == "Y"),
                        default=default if isinstance(default, str) else None
                    )
                )

            # ---- Constraint Parsing ----
            ctr_raw = list(conn.execute(text(sql_constraints), {"owner": schema}))
            fk_targets = self._resolve_fk_targets(engine, ctr_raw, schema)

            for cname, ctype, tbl, col, rname in ctr_raw:
                if tbl not in tables or col is None:
                    continue

                if ctype == "P":
                    cinfo = ConstraintInfo(
                        name=cname,
                        constraint_type="PRIMARY_KEY",
                        table=tbl,
                        columns=[col],
                    )
                elif ctype == "U":
                    cinfo = ConstraintInfo(
                        name=cname,
                        constraint_type="UNIQUE",
                        table=tbl,
                        columns=[col],
                    )
                elif ctype == "R":
                    ref_tbl, ref_cols = fk_targets.get(rname, (None, []))
                    cinfo = ConstraintInfo(
                        name=cname,
                        constraint_type="FOREIGN_KEY",
                        table=tbl,
                        columns=[col],
                        referenced_table=ref_tbl,
                        referenced_columns=ref_cols,
                    )
                elif ctype == "C":
                    cinfo = ConstraintInfo(
                        name=cname,
                        constraint_type="CHECK",
                        table=tbl,
                        columns=[col],
                    )
                else:
                    continue

                tables[tbl].constraints.append(cinfo)

            # ---- Indexes ----
            idx_colmap = {}
            for idx, col in conn.execute(text(sql_ind_cols), {"owner": schema}):
                idx_colmap.setdefault(idx, []).append(col)

            for idx, tbl, uniq in conn.execute(text(sql_indexes), {"owner": schema}):
                if tbl not in tables:
                    continue
                tables[tbl].indexes.append(
                    IndexInfo(
                        name=idx,
                        columns=idx_colmap.get(idx, []),
                        uniqueness=uniq
                    )
                )

            # ---- Triggers ----
            for tname, event, tbl in conn.execute(text(sql_trigger_list), {"owner": schema}):
                if tbl not in tables:
                    continue

                lines = conn.execute(
                    text(sql_trigger_body),
                    {"owner": schema, "trg": tname}
                ).fetchall()

                body = "".join([l[0] for l in lines]) if lines else ""

                tables[tbl].triggers.append(
                    TriggerInfo(
                        name=tname,
                        event=event,
                        body=body
                    )
                )

        return list(tables.values())

    # Resolve FK referenced tables
    def _resolve_fk_targets(self, engine: Engine, ctr_raw: List, schema: str):
        fk_parent_names = [c[4] for c in ctr_raw if c[1] == "R"]
        if not fk_parent_names:
            return {}

        sql = """
            SELECT constraint_name, table_name, column_name
            FROM all_cons_columns
            WHERE owner = :owner
              AND constraint_name IN :cset
        """

        result = {}
        with engine.connect() as conn:
            rows = conn.execute(
                text(sql),
                {"owner": schema, "cset": tuple(fk_parent_names)}
            ).fetchall()

            for cname, tbl, col in rows:
                if cname not in result:
                    result[cname] = (tbl, [])
                result[cname][1].append(col)

        return result

    # ========================================
    # VIEWS
    # ========================================
    def _extract_views(self, engine: Engine, schema: str) -> List[ViewInfo]:
        sql = """
            SELECT view_name, text
            FROM all_views
            WHERE owner = :owner
        """

        views = []
        with engine.connect() as conn:
            for name, query in conn.execute(text(sql), {"owner": schema}):
                views.append(ViewInfo(name=name, query=query))

        return views

    # ========================================
    # SEQUENCES
    # ========================================
    def _extract_sequences(self, engine: Engine, schema: str) -> List[SequenceInfo]:
        sql = """
            SELECT sequence_name, min_value, max_value, increment_by, cycle_flag
            FROM all_sequences
            WHERE sequence_owner = :owner
        """

        seqs = []
        with engine.connect() as conn:
            for row in conn.execute(text(sql), {"owner": schema}):
                seqs.append(
                    SequenceInfo(
                        name=row[0],
                        min_value=row[1],
                        max_value=row[2],
                        increment_by=row[3],
                        cycle_flag=row[4],
                    )
                )

        return seqs

    # ========================================
    # PROCEDURES
    # ========================================
    def _extract_procedures(self, engine: Engine, schema: str) -> List[ProcedureInfo]:
        sql_list = """
            SELECT object_name
            FROM all_procedures
            WHERE owner = :owner
              AND object_type = 'PROCEDURE'
        """

        sql_src = """
            SELECT text FROM all_source
            WHERE owner = :owner AND name = :name
            ORDER BY line
        """

        procs = []

        with engine.connect() as conn:
            for (name,) in conn.execute(text(sql_list), {"owner": schema}):
                src = conn.execute(text(sql_src), {"owner": schema, "name": name}).fetchall()
                body = "".join([s[0] for s in src]) if src else ""
                procs.append(ProcedureInfo(name=name, arguments=[], body=body))

        return procs

    # ========================================
    # FUNCTIONS
    # ========================================
    def _extract_functions(self, engine: Engine, schema: str) -> List[FunctionInfo]:
        sql_funcs = """
            SELECT object_name
            FROM all_objects
            WHERE owner = :owner
              AND object_type = 'FUNCTION'
        """

        sql_src = """
            SELECT text FROM all_source
            WHERE owner = :owner AND name = :name
            ORDER BY line
        """

        funcs = []

        with engine.connect() as conn:
            for (name,) in conn.execute(text(sql_funcs), {"owner": schema}):
                src = conn.execute(text(sql_src), {"owner": schema, "name": name}).fetchall()
                body = "".join([s[0] for s in src]) if src else ""
                funcs.append(
                    FunctionInfo(
                        name=name,
                        arguments=[],
                        return_type="UNKNOWN",
                        body=body
                    )
                )

        return funcs

    # ========================================
    # PACKAGES (SPEC + BODY)
    # ========================================
    def _extract_packages(self, engine: Engine, schema: str) -> List[PackageInfo]:
        sql_packages = """
            SELECT object_name
            FROM all_objects
            WHERE owner = :owner
              AND object_type IN ('PACKAGE', 'PACKAGE BODY')
            GROUP BY object_name
        """

        sql_spec = """
            SELECT text FROM all_source
            WHERE owner = :owner
              AND name = :name
              AND type = 'PACKAGE'
            ORDER BY line
        """

        sql_body = """
            SELECT text FROM all_source
            WHERE owner = :owner
              AND name = :name
              AND type = 'PACKAGE BODY'
            ORDER BY line
        """

        pkgs = []

        with engine.connect() as conn:
            for (name,) in conn.execute(text(sql_packages), {"owner": schema}):

                spec_rows = conn.execute(text(sql_spec), {"owner": schema, "name": name}).fetchall()
                spec = "".join([r[0] for r in spec_rows]) if spec_rows else ""

                body_rows = conn.execute(text(sql_body), {"owner": schema, "name": name}).fetchall()
                body = "".join([r[0] for r in body_rows]) if body_rows else ""

                pkgs.append(
                    PackageInfo(
                        name=name,
                        spec=spec,
                        body=body,
                    )
                )

        return pkgs
