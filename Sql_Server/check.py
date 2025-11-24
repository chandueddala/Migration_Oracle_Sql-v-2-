# verify_sqlserver_schema.py
# Post-migration checker for SQL Server schema objects:
# - Tables (+ approx row counts)
# - Stored Procedures
# - Functions (scalar, inline TVF, multi-statement TVF)
# - Triggers (database-level & table-level)

import os
import sys
import pyodbc
from datetime import datetime
from textwrap import shorten

# --- CONFIG ------------------------------------------------------------
SERVER   = os.getenv("MSSQL_SERVER",   "localhost")
PORT     = os.getenv("MSSQL_PORT",     "1433")
DB       = os.getenv("MSSQL_DATABASE", "master")
USER     = os.getenv("MSSQL_USER",     "sa")
PASSWORD = os.getenv("MSSQL_PASSWORD", "Bujji@9866")
DRIVER   = os.getenv("MSSQL_DRIVER",   "{ODBC Driver 18 for SQL Server}")
TRUST    = os.getenv("MSSQL_TRUST_CERT", "yes")  # yes/no for TrustServerCertificate

# Optional: filter by schema (comma-separated list), or leave empty for all
SCHEMA_FILTER = os.getenv("MSSQL_SCHEMAS", "")  # e.g., "dbo,sales"
# ----------------------------------------------------------------------


def connect():
    conn_str = (
        f"DRIVER={DRIVER};"
        f"SERVER={SERVER},{PORT};"
        f"DATABASE={DB};"
        f"UID={USER};PWD={PASSWORD};"
        f"TrustServerCertificate={TRUST};"
    )
    return pyodbc.connect(conn_str, autocommit=True)


def fmt(row):
    # Helper to make printing less noisy
    return [("" if v is None else str(v)) for v in row]


def schema_predicate(alias="s"):
    if not SCHEMA_FILTER.strip():
        return "1=1", []
    schemas = [s.strip() for s in SCHEMA_FILTER.split(",") if s.strip()]
    placeholders = ",".join(["?"] * len(schemas))
    return f"{alias}.name IN ({placeholders})", schemas


def main():
    print("=" * 70)
    print("SQL Server Post-Migration Report")
    print("=" * 70)

    try:
        cn = connect()
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        sys.exit(1)

    with cn.cursor() as cur:
        # Header: server & db info
        cur.execute("SELECT @@SERVERNAME, DB_NAME(), CONVERT(varchar(30), SYSDATETIME(), 120)")
        server_name, db_name, now_ts = cur.fetchone()
        print(f"🗄️  Server: {server_name}   Database: {db_name}   At: {now_ts}\n")

        # ------------------- TABLES (with approx row counts) -------------------
        # Use sys.dm_db_partition_stats for accurate-ish counts without scanning
        pred, params = schema_predicate("sc")
        tables_sql = f"""
        SELECT
            sc.name AS schema_name,
            t.name  AS table_name,
            SUM(CASE WHEN p.index_id IN (0,1) THEN p.row_count ELSE 0 END) AS row_count
        FROM sys.tables t
        JOIN sys.schemas sc ON sc.schema_id = t.schema_id
        JOIN sys.dm_db_partition_stats p ON p.object_id = t.object_id
        WHERE {pred}
        GROUP BY sc.name, t.name
        ORDER BY sc.name, t.name;
        """
        cur.execute(tables_sql, params)
        rows = cur.fetchall()
        print("📦 Tables")
        if not rows:
            print("  (none)")
        else:
            for r in rows:
                schema_name, table_name, row_count = fmt(r)
                print(f"  - {schema_name}.{table_name}  (rows≈{row_count})")
        print("")

        # ------------------- PROCEDURES ---------------------------------------
        proc_sql = f"""
        SELECT
            sc.name AS schema_name,
            p.name  AS proc_name,
            p.create_date,
            p.modify_date
        FROM sys.procedures p
        JOIN sys.schemas   sc ON sc.schema_id = p.schema_id
        WHERE {pred}
        ORDER BY sc.name, p.name;
        """
        cur.execute(proc_sql, params)
        procs = cur.fetchall()
        print("🛠️  Stored Procedures")
        if not procs:
            print("  (none)")
        else:
            for r in procs:
                schema_name, name, cdt, mdt = r
                print(f"  - {schema_name}.{name}  (created {cdt:%Y-%m-%d}, modified {mdt:%Y-%m-%d})")
        print("")

        # ------------------- FUNCTIONS ----------------------------------------
        # Types: FN (scalar), IF (inline TVF), TF (multi-statement TVF), FS/FT (CLR)
        func_sql = f"""
        SELECT
            sc.name AS schema_name,
            o.name  AS func_name,
            o.type  AS func_type,
            o.create_date,
            o.modify_date
        FROM sys.objects o
        JOIN sys.schemas sc ON sc.schema_id = o.schema_id
        WHERE o.type IN ('FN','IF','TF','FS','FT') AND {pred}
        ORDER BY sc.name, o.name;
        """
        cur.execute(func_sql, params)
        funcs = cur.fetchall()
        print("🧮 Functions")
        if not funcs:
            print("  (none)")
        else:
            type_map = {"FN":"scalar","IF":"inline TVF","TF":"TVF","FS":"CLR scalar","FT":"CLR TVF"}
            for r in funcs:
                schema_name, name, typ, cdt, mdt = r
                kind = type_map.get(typ, typ)
                print(f"  - {schema_name}.{name}  [{kind}]  (created {cdt:%Y-%m-%d}, modified {mdt:%Y-%m-%d})")
        print("")

        # ------------------- TRIGGERS -----------------------------------------
        # Table triggers & DB-level triggers
        trig_sql = f"""
        SELECT
            tr.name        AS trigger_name,
            CASE WHEN tr.parent_id = 0 THEN NULL ELSE sch.name END AS schema_name,
            CASE WHEN tr.parent_id = 0 THEN NULL ELSE tbl.name END  AS table_name,
            tr.is_disabled,
            tr.is_instead_of_trigger,
            tr.create_date,
            tr.modify_date
        FROM sys.triggers tr
        LEFT JOIN sys.tables  tbl ON tbl.object_id = tr.parent_id
        LEFT JOIN sys.schemas sch ON sch.schema_id = tbl.schema_id
        WHERE ({pred} OR tr.parent_id = 0)  -- include DB-level triggers too
        ORDER BY schema_name, table_name, trigger_name;
        """
        cur.execute(trig_sql, params)
        trigs = cur.fetchall()
        print("🧨 Triggers")
        if not trigs:
            print("  (none)")
        else:
            for (tname, schema_name, table_name, disabled, instead_of, cdt, mdt) in trigs:
                loc = "DATABASE" if schema_name is None else f"{schema_name}.{table_name}"
                flags = []
                if disabled: flags.append("disabled")
                if instead_of: flags.append("INSTEAD OF")
                flags_txt = f" ({', '.join(flags)})" if flags else ""
                print(f"  - {tname} on {loc}{flags_txt}  (created {cdt:%Y-%m-%d}, modified {mdt:%Y-%m-%d})")
        print("")

        print("✅ Done.")
        print("=" * 70)


if __name__ == "__main__":
    main()
