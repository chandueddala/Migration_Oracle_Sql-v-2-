#!/usr/bin/env python3
"""
COMPLETE ORACLE SCHEMA INSPECTOR
=================================

Inspects ALL Oracle database objects and features:
✓ Tables (with columns, data types, constraints, row counts)
✓ Packages (with all procedures/functions)
✓ Procedures (standalone)
✓ Functions (standalone)
✓ Triggers (all types)
✓ Sequences
✓ Views
✓ Materialized Views
✓ Indexes (all types)
✓ Constraints (PK, FK, UK, Check)
✓ Synonyms
✓ Types (Object Types)
✓ Database Links
✓ Scheduled Jobs
✓ Invalid Objects
✓ Object Sizes

Usage:
    python check_oracle_complete_schema.py
    
Requirements:
    pip install oracledb
"""

import oracledb
from datetime import datetime

# ============================================================================
# EDIT YOUR ORACLE CREDENTIALS HERE
# ============================================================================

USER = "app"
PASSWORD = "app"
DSN = "localhost:1521/FREEPDB1"

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def print_header(title):
    """Print formatted section header"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)

def print_subheader(title):
    """Print formatted subsection header"""
    print(f"\n{title}")
    print("-"*80)

def format_bytes(bytes_value):
    """Format bytes to human readable"""
    if bytes_value is None:
        return "N/A"
    
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} PB"

# ============================================================================
# MAIN INSPECTION
# ============================================================================

def main():
    print("="*80)
    print("  COMPLETE ORACLE DATABASE SCHEMA INSPECTOR")
    print("="*80)
    print(f"\nConnection: {DSN}")
    print(f"User:       {USER}")
    print(f"Time:       {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Connect
    try:
        conn = oracledb.connect(user=USER, password=PASSWORD, dsn=DSN)
        print("\n✅ Connected successfully!")
    except Exception as e:
        print(f"\n❌ Connection failed: {e}")
        return 1
    
    cur = conn.cursor()
    
    # ========================================================================
    # 1. TABLES (DETAILED)
    # ========================================================================
    print_header("📋 TABLES")
    
    cur.execute("""
        SELECT table_name, num_rows, blocks, avg_row_len, last_analyzed
        FROM user_tables
        ORDER BY table_name
    """)
    tables = cur.fetchall()
    
    if tables:
        for table_name, num_rows, blocks, avg_row_len, last_analyzed in tables:
            print(f"\n📊 {table_name}")
            
            # Statistics
            rows_display = f"{num_rows:,}" if num_rows else "Not analyzed"
            print(f"    Statistics: {rows_display} rows, {blocks or 0} blocks, {avg_row_len or 0} avg row length")
            if last_analyzed:
                print(f"    Last Analyzed: {last_analyzed}")
            
            # Columns
            cur.execute("""
                SELECT column_name, data_type, data_length, data_precision, 
                       data_scale, nullable, data_default, column_id
                FROM user_tab_columns
                WHERE table_name = :tname
                ORDER BY column_id
            """, {"tname": table_name})
            
            columns = cur.fetchall()
            print(f"    Columns ({len(columns)}):")
            
            for col_name, data_type, data_len, precision, scale, nullable, default, col_id in columns:
                # Format data type
                if data_type in ('VARCHAR2', 'CHAR', 'NVARCHAR2', 'NCHAR'):
                    type_str = f"{data_type}({data_len})"
                elif data_type == 'NUMBER':
                    if precision and scale:
                        type_str = f"NUMBER({precision},{scale})"
                    elif precision:
                        type_str = f"NUMBER({precision})"
                    else:
                        type_str = "NUMBER"
                else:
                    type_str = data_type
                
                null_str = "" if nullable == 'Y' else "NOT NULL"
                default_str = f" DEFAULT {default}" if default else ""
                
                print(f"      {col_id:2d}. {col_name:30s} {type_str:20s} {null_str:8s}{default_str}")
            
            # Primary Key
            cur.execute("""
                SELECT constraint_name, column_name
                FROM user_cons_columns
                WHERE table_name = :tname
                  AND constraint_name IN (
                    SELECT constraint_name 
                    FROM user_constraints 
                    WHERE table_name = :tname AND constraint_type = 'P'
                  )
                ORDER BY position
            """, {"tname": table_name})
            
            pk_cols = cur.fetchall()
            if pk_cols:
                pk_name = pk_cols[0][0]
                pk_columns = ', '.join([col[1] for col in pk_cols])
                print(f"    🔑 Primary Key: {pk_name} ({pk_columns})")
            
            # Foreign Keys
            cur.execute("""
                SELECT c.constraint_name, c.r_constraint_name, 
                       cc.column_name, rc.table_name AS ref_table
                FROM user_constraints c
                JOIN user_cons_columns cc ON c.constraint_name = cc.constraint_name
                JOIN user_constraints rc ON c.r_constraint_name = rc.constraint_name
                WHERE c.table_name = :tname AND c.constraint_type = 'R'
                ORDER BY c.constraint_name, cc.position
            """, {"tname": table_name})
            
            fks = cur.fetchall()
            if fks:
                print(f"    🔗 Foreign Keys:")
                current_fk = None
                for fk_name, ref_constraint, col_name, ref_table in fks:
                    if fk_name != current_fk:
                        if current_fk:
                            print()
                        print(f"       {fk_name}")
                        print(f"         → {ref_table}.{col_name}")
                        current_fk = fk_name
            
            # Indexes
            cur.execute("""
                SELECT index_name, uniqueness, index_type
                FROM user_indexes
                WHERE table_name = :tname
                ORDER BY index_name
            """, {"tname": table_name})
            
            idxs = cur.fetchall()
            if idxs:
                print(f"    📇 Indexes ({len(idxs)}):")
                for idx_name, uniqueness, idx_type in idxs:
                    unique_flag = "UNIQUE" if uniqueness == "UNIQUE" else "NON-UNIQUE"
                    print(f"       {idx_name} ({unique_flag}, {idx_type})")
            
            # Triggers on this table
            cur.execute("""
                SELECT trigger_name, triggering_event, trigger_type, status
                FROM user_triggers
                WHERE table_name = :tname
                ORDER BY trigger_name
            """, {"tname": table_name})
            
            trigs = cur.fetchall()
            if trigs:
                print(f"    🎯 Triggers ({len(trigs)}):")
                for trig_name, event, trig_type, status in trigs:
                    status_icon = "✓" if status == "ENABLED" else "⚠️"
                    print(f"       {status_icon} {trig_name} - {trig_type} {event}")
            
            # Actual row count
            try:
                cur.execute(f"SELECT COUNT(*) FROM {table_name}")
                actual_rows = cur.fetchone()[0]
                print(f"    📊 Actual Rows: {actual_rows:,}")
            except:
                print(f"    📊 Actual Rows: Unable to count")
        
        print(f"\n✅ Total Tables: {len(tables)}")
    else:
        print("  ❌ No tables found")
    
    # ========================================================================
    # 2. PACKAGES (WITH ALL PROCEDURES/FUNCTIONS)
    # ========================================================================
    print_header("📦 PACKAGES")
    
    cur.execute("""
        SELECT object_name, status, created, last_ddl_time
        FROM user_objects
        WHERE object_type = 'PACKAGE'
        ORDER BY object_name
    """)
    packages = cur.fetchall()
    
    if packages:
        for pkg_name, status, created, last_ddl in packages:
            status_icon = "✓" if status == "VALID" else "⚠️"
            print(f"\n{status_icon} {pkg_name} ({status})")
            print(f"   Created: {created}, Last Modified: {last_ddl}")
            
            # Get all procedures/functions in this package
            cur.execute("""
                SELECT procedure_name, object_type, 
                       CASE WHEN aggregate = 'YES' THEN 'AGGREGATE' ELSE '' END AS agg
                FROM user_procedures
                WHERE object_name = :pkg
                  AND procedure_name IS NOT NULL
                ORDER BY procedure_name
            """, {"pkg": pkg_name})
            
            procs = cur.fetchall()
            if procs:
                print(f"   Contains {len(procs)} procedure(s)/function(s):")
                for proc_name, obj_type, agg in procs:
                    agg_str = f" [{agg}]" if agg else ""
                    print(f"      • {proc_name} ({obj_type}){agg_str}")
                
                # Try to get parameters (skip if USER_ARGUMENTS not available)
                try:
                    for proc_name, obj_type, agg in procs[:3]:  # Show params for first 3
                        cur.execute("""
                            SELECT argument_name, data_type, in_out, position
                            FROM user_arguments
                            WHERE object_name = :pkg
                              AND (procedure_name = :proc OR procedure_name IS NULL)
                            ORDER BY position
                        """, {"pkg": pkg_name, "proc": proc_name})

                        params = cur.fetchall()
                        if params:
                            print(f"        {proc_name} parameters:")
                            for arg_name, data_type, in_out, position in params:
                                if arg_name:  # Skip return value with NULL name
                                    print(f"          {position}. {arg_name} {in_out} {data_type}")
                except Exception as e:
                    # Parameter query failed - skip it
                    pass
            else:
                print(f"   (no procedures/functions listed)")
            
            # Package body status
            cur.execute("""
                SELECT status
                FROM user_objects
                WHERE object_type = 'PACKAGE BODY'
                  AND object_name = :pkg
            """, {"pkg": pkg_name})
            
            body_status = cur.fetchone()
            if body_status:
                body_icon = "✓" if body_status[0] == "VALID" else "⚠️"
                print(f"   {body_icon} Package Body: {body_status[0]}")
        
        print(f"\n✅ Total Packages: {len(packages)}")
    else:
        print("  ❌ No packages found")
    
    # ========================================================================
    # 3. STANDALONE PROCEDURES
    # ========================================================================
    print_header("⚙️  STANDALONE PROCEDURES")
    
    cur.execute("""
        SELECT object_name, status, created, last_ddl_time
        FROM user_objects
        WHERE object_type = 'PROCEDURE'
        ORDER BY object_name
    """)
    procedures = cur.fetchall()
    
    if procedures:
        for proc_name, status, created, last_ddl in procedures:
            status_icon = "✓" if status == "VALID" else "⚠️"
            print(f"\n  {status_icon} {proc_name} ({status})")
            print(f"     Created: {created}, Last Modified: {last_ddl}")
            
            # Get parameters
            cur.execute("""
                SELECT argument_name, data_type, in_out, position, data_level
                FROM user_arguments
                WHERE object_name = :proc
                  AND subprogram_name IS NULL
                ORDER BY position
            """, {"proc": proc_name})
            
            params = cur.fetchall()
            if params:
                print(f"     Parameters ({len(params)}):")
                for arg_name, data_type, in_out, position, data_level in params:
                    if arg_name:
                        print(f"       {position}. {arg_name} {in_out} {data_type}")
        
        print(f"\n✅ Total Procedures: {len(procedures)}")
    else:
        print("  ❌ No standalone procedures found")
    
    # ========================================================================
    # 4. STANDALONE FUNCTIONS
    # ========================================================================
    print_header("🔧 STANDALONE FUNCTIONS")
    
    cur.execute("""
        SELECT object_name, status, created, last_ddl_time
        FROM user_objects
        WHERE object_type = 'FUNCTION'
        ORDER BY object_name
    """)
    functions = cur.fetchall()
    
    if functions:
        for func_name, status, created, last_ddl in functions:
            status_icon = "✓" if status == "VALID" else "⚠️"
            print(f"\n  {status_icon} {func_name} ({status})")
            print(f"     Created: {created}, Last Modified: {last_ddl}")
            
            # Get return type and parameters
            cur.execute("""
                SELECT argument_name, data_type, in_out, position
                FROM user_arguments
                WHERE object_name = :func
                  AND subprogram_name IS NULL
                ORDER BY position
            """, {"func": func_name})
            
            params = cur.fetchall()
            if params:
                # First is return type
                return_type = params[0][1] if params[0][0] is None else None
                if return_type:
                    print(f"     Returns: {return_type}")
                
                # Rest are parameters
                func_params = [p for p in params if p[0] is not None]
                if func_params:
                    print(f"     Parameters ({len(func_params)}):")
                    for arg_name, data_type, in_out, position in func_params:
                        print(f"       {position}. {arg_name} {in_out} {data_type}")
        
        print(f"\n✅ Total Functions: {len(functions)}")
    else:
        print("  ❌ No standalone functions found")
    
    # ========================================================================
    # 5. TRIGGERS (ALL TYPES)
    # ========================================================================
    print_header("🎯 TRIGGERS")
    
    cur.execute("""
        SELECT trigger_name, trigger_type, triggering_event, table_name, 
               status, when_clause, description
        FROM user_triggers
        ORDER BY table_name, trigger_name
    """)
    triggers = cur.fetchall()
    
    if triggers:
        current_table = None
        for trig_name, trig_type, event, table_name, status, when_clause, description in triggers:
            if current_table != table_name:
                if current_table is not None:
                    print()
                print(f"\n  On Table/View: {table_name or '(SCHEMA LEVEL)'}")
                current_table = table_name
            
            status_icon = "✓" if status == "ENABLED" else "⚠️"
            print(f"    {status_icon} {trig_name} ({status})")
            print(f"       Type: {trig_type}")
            print(f"       Event: {event}")
            if when_clause:
                print(f"       When: {when_clause}")
        
        print(f"\n✅ Total Triggers: {len(triggers)}")
    else:
        print("  ❌ No triggers found")
    
    # ========================================================================
    # 6. SEQUENCES
    # ========================================================================
    print_header("🔢 SEQUENCES")
    
    cur.execute("""
        SELECT sequence_name, min_value, max_value, increment_by, 
               last_number, cache_size, cycle_flag, order_flag
        FROM user_sequences
        ORDER BY sequence_name
    """)
    sequences = cur.fetchall()
    
    if sequences:
        for seq_name, min_val, max_val, increment, last_num, cache, cycle, order_flag in sequences:
            print(f"\n  📈 {seq_name}")
            print(f"     Current Value: {last_num}")
            print(f"     Increment By:  {increment}")
            print(f"     Min Value:     {min_val}")
            print(f"     Max Value:     {max_val}")
            print(f"     Cache Size:    {cache}")
            print(f"     Cycle:         {cycle}")
            print(f"     Order:         {order_flag}")
        
        print(f"\n✅ Total Sequences: {len(sequences)}")
    else:
        print("  ❌ No sequences found")
    
    # ========================================================================
    # 7. VIEWS
    # ========================================================================
    print_header("👁️  VIEWS")
    
    cur.execute("""
        SELECT view_name, text_length, text
        FROM user_views
        ORDER BY view_name
    """)
    views = cur.fetchall()
    
    if views:
        for view_name, text_len, text in views:
            print(f"\n  📋 {view_name}")
            print(f"     SQL Length: {text_len} characters")
            
            # Get columns
            cur.execute("""
                SELECT column_name, data_type
                FROM user_tab_columns
                WHERE table_name = :vname
                ORDER BY column_id
            """, {"vname": view_name})
            
            view_cols = cur.fetchall()
            print(f"     Columns ({len(view_cols)}):")
            for col_name, data_type in view_cols[:10]:  # Show first 10
                print(f"       • {col_name} ({data_type})")
            if len(view_cols) > 10:
                print(f"       ... and {len(view_cols) - 10} more")
            
            # Show first 200 chars of SQL
            if text:
                sql_preview = text[:200].replace('\n', ' ')
                print(f"     SQL: {sql_preview}...")
        
        print(f"\n✅ Total Views: {len(views)}")
    else:
        print("  ❌ No views found")
    
    # ========================================================================
    # 8. MATERIALIZED VIEWS
    # ========================================================================
    print_header("📊 MATERIALIZED VIEWS")
    
    cur.execute("""
        SELECT mview_name, refresh_mode, refresh_method, 
               build_mode, fast_refreshable, last_refresh_date
        FROM user_mviews
        ORDER BY mview_name
    """)
    mviews = cur.fetchall()
    
    if mviews:
        for mview_name, refresh_mode, refresh_method, build_mode, fast_refresh, last_refresh in mviews:
            print(f"\n  📊 {mview_name}")
            print(f"     Refresh Mode:   {refresh_mode}")
            print(f"     Refresh Method: {refresh_method}")
            print(f"     Build Mode:     {build_mode}")
            print(f"     Fast Refresh:   {fast_refresh}")
            print(f"     Last Refresh:   {last_refresh}")
        
        print(f"\n✅ Total Materialized Views: {len(mviews)}")
    else:
        print("  ❌ No materialized views found")
    
    # ========================================================================
    # 9. ALL INDEXES
    # ========================================================================
    print_header("📇 INDEXES")
    
    cur.execute("""
        SELECT index_name, index_type, table_name, uniqueness, 
               status, blevel, leaf_blocks, distinct_keys
        FROM user_indexes
        WHERE index_name NOT LIKE 'SYS_%'
        ORDER BY table_name, index_name
    """)
    indexes = cur.fetchall()
    
    if indexes:
        current_table = None
        for idx_name, idx_type, tbl_name, uniqueness, status, blevel, leaf_blocks, distinct_keys in indexes:
            if current_table != tbl_name:
                if current_table is not None:
                    print()
                print(f"\n  On Table: {tbl_name}")
                current_table = tbl_name
            
            unique_flag = "UNIQUE" if uniqueness == "UNIQUE" else "NON-UNIQUE"
            print(f"    📊 {idx_name}")
            print(f"       Type: {idx_type}, {unique_flag}, Status: {status}")
            print(f"       BLevel: {blevel}, Leaf Blocks: {leaf_blocks}, Distinct Keys: {distinct_keys}")
            
            # Get indexed columns
            cur.execute("""
                SELECT column_name, column_position, descend
                FROM user_ind_columns
                WHERE index_name = :idx
                ORDER BY column_position
            """, {"idx": idx_name})
            
            idx_cols = cur.fetchall()
            if idx_cols:
                cols_str = ', '.join([f"{col}{'↓' if desc=='DESC' else '↑'}" for col, pos, desc in idx_cols])
                print(f"       Columns: {cols_str}")
        
        print(f"\n✅ Total Indexes: {len(indexes)}")
    else:
        print("  ❌ No custom indexes found")
    
    # ========================================================================
    # 10. CONSTRAINTS (ALL TYPES)
    # ========================================================================
    print_header("🔒 CONSTRAINTS")
    
    # Primary Keys
    print_subheader("🔑 Primary Keys")
    cur.execute("""
        SELECT c.constraint_name, c.table_name, cc.column_name
        FROM user_constraints c
        JOIN user_cons_columns cc ON c.constraint_name = cc.constraint_name
        WHERE c.constraint_type = 'P'
        ORDER BY c.table_name, cc.position
    """)
    pks = cur.fetchall()
    
    if pks:
        current_pk = None
        for pk_name, table_name, col_name in pks:
            if pk_name != current_pk:
                if current_pk:
                    print()
                print(f"  {table_name}: {pk_name}")
                current_pk = pk_name
            print(f"    • {col_name}")
        print(f"\n✅ Total Primary Keys: {len(set([pk[0] for pk in pks]))}")
    else:
        print("  ❌ No primary keys found")
    
    # Foreign Keys
    print_subheader("🔗 Foreign Keys")
    cur.execute("""
        SELECT c.constraint_name, c.table_name, cc.column_name,
               rc.table_name AS ref_table, rcc.column_name AS ref_column,
               c.delete_rule
        FROM user_constraints c
        JOIN user_cons_columns cc ON c.constraint_name = cc.constraint_name
        JOIN user_constraints rc ON c.r_constraint_name = rc.constraint_name
        JOIN user_cons_columns rcc ON rc.constraint_name = rcc.constraint_name
        WHERE c.constraint_type = 'R'
        ORDER BY c.table_name, c.constraint_name, cc.position
    """)
    fks = cur.fetchall()
    
    if fks:
        current_fk = None
        for fk_name, table_name, col_name, ref_table, ref_col, delete_rule in fks:
            if fk_name != current_fk:
                if current_fk:
                    print()
                print(f"  {table_name}: {fk_name}")
                print(f"    → References {ref_table}({ref_col})")
                print(f"    Delete Rule: {delete_rule}")
                current_fk = fk_name
        print(f"\n✅ Total Foreign Keys: {len(set([fk[0] for fk in fks]))}")
    else:
        print("  ❌ No foreign keys found")
    
    # Unique Constraints
    print_subheader("🎯 Unique Constraints")
    cur.execute("""
        SELECT c.constraint_name, c.table_name, cc.column_name
        FROM user_constraints c
        JOIN user_cons_columns cc ON c.constraint_name = cc.constraint_name
        WHERE c.constraint_type = 'U'
        ORDER BY c.table_name, cc.position
    """)
    uks = cur.fetchall()
    
    if uks:
        current_uk = None
        for uk_name, table_name, col_name in uks:
            if uk_name != current_uk:
                if current_uk:
                    print()
                print(f"  {table_name}: {uk_name}")
                current_uk = uk_name
            print(f"    • {col_name}")
        print(f"\n✅ Total Unique Constraints: {len(set([uk[0] for uk in uks]))}")
    else:
        print("  ❌ No unique constraints found")
    
    # Check Constraints
    print_subheader("✓ Check Constraints")
    cur.execute("""
        SELECT constraint_name, table_name, search_condition
        FROM user_constraints
        WHERE constraint_type = 'C'
          AND constraint_name NOT LIKE 'SYS_%'
        ORDER BY table_name, constraint_name
    """)
    cks = cur.fetchall()
    
    if cks:
        for ck_name, table_name, search_condition in cks:
            condition_preview = str(search_condition)[:100] if search_condition else "N/A"
            print(f"  {table_name}: {ck_name}")
            print(f"    Condition: {condition_preview}")
        print(f"\n✅ Total Check Constraints: {len(cks)}")
    else:
        print("  ❌ No check constraints found")
    
    # ========================================================================
    # 11. SYNONYMS
    # ========================================================================
    print_header("🔗 SYNONYMS")
    
    cur.execute("""
        SELECT synonym_name, table_owner, table_name, db_link
        FROM user_synonyms
        ORDER BY synonym_name
    """)
    synonyms = cur.fetchall()
    
    if synonyms:
        for syn_name, owner, table_name, db_link in synonyms:
            link_str = f"@{db_link}" if db_link else ""
            print(f"  {syn_name} → {owner}.{table_name}{link_str}")
        print(f"\n✅ Total Synonyms: {len(synonyms)}")
    else:
        print("  ❌ No synonyms found")
    
    # ========================================================================
    # 12. OBJECT TYPES
    # ========================================================================
    print_header("📐 OBJECT TYPES")
    
    cur.execute("""
        SELECT object_name, status, created, last_ddl_time
        FROM user_objects
        WHERE object_type = 'TYPE'
        ORDER BY object_name
    """)
    types = cur.fetchall()
    
    if types:
        for type_name, status, created, last_ddl in types:
            status_icon = "✓" if status == "VALID" else "⚠️"
            print(f"\n  {status_icon} {type_name} ({status})")
            print(f"     Created: {created}, Last Modified: {last_ddl}")
            
            # Get type attributes
            cur.execute("""
                SELECT attr_name, attr_type_name, length, precision, scale
                FROM user_type_attrs
                WHERE type_name = :tname
                ORDER BY attr_no
            """, {"tname": type_name})
            
            attrs = cur.fetchall()
            if attrs:
                print(f"     Attributes ({len(attrs)}):")
                for attr_name, attr_type, length, precision, scale in attrs:
                    print(f"       • {attr_name} {attr_type}")
        
        print(f"\n✅ Total Object Types: {len(types)}")
    else:
        print("  ❌ No object types found")
    
    # ========================================================================
    # 13. DATABASE LINKS
    # ========================================================================
    print_header("🌐 DATABASE LINKS")
    
    cur.execute("""
        SELECT db_link, username, host, created
        FROM user_db_links
        ORDER BY db_link
    """)
    db_links = cur.fetchall()
    
    if db_links:
        for link_name, username, host, created in db_links:
            print(f"\n  🔗 {link_name}")
            print(f"     User: {username}")
            print(f"     Host: {host}")
            print(f"     Created: {created}")
        print(f"\n✅ Total Database Links: {len(db_links)}")
    else:
        print("  ❌ No database links found")
    
    # ========================================================================
    # 14. SCHEDULED JOBS
    # ========================================================================
    print_header("⏰ SCHEDULED JOBS")
    
    try:
        cur.execute("""
            SELECT job_name, job_type, job_action, state, 
                   enabled, next_run_date, last_start_date
            FROM user_scheduler_jobs
            ORDER BY job_name
        """)
        jobs = cur.fetchall()
        
        if jobs:
            for job_name, job_type, action, state, enabled, next_run, last_start in jobs:
                enabled_icon = "✓" if enabled == "TRUE" else "✗"
                print(f"\n  {enabled_icon} {job_name} ({state})")
                print(f"     Type: {job_type}")
                print(f"     Action: {action[:100]}...")
                print(f"     Next Run: {next_run}")
                print(f"     Last Run: {last_start}")
            print(f"\n✅ Total Scheduled Jobs: {len(jobs)}")
        else:
            print("  ❌ No scheduled jobs found")
    except:
        print("  ⚠️  Unable to query scheduled jobs (may not have permissions)")
    
    # ========================================================================
    # 15. INVALID OBJECTS
    # ========================================================================
    print_header("⚠️  INVALID OBJECTS")
    
    cur.execute("""
        SELECT object_type, object_name, status, last_ddl_time
        FROM user_objects
        WHERE status != 'VALID'
        ORDER BY object_type, object_name
    """)
    invalid_objs = cur.fetchall()
    
    if invalid_objs:
        print("\n  🚨 WARNING: Found invalid objects that need attention!\n")
        current_type = None
        for obj_type, obj_name, status, last_ddl in invalid_objs:
            if obj_type != current_type:
                if current_type:
                    print()
                print(f"  {obj_type}:")
                current_type = obj_type
            print(f"    ⚠️  {obj_name} ({status}) - Last DDL: {last_ddl}")
        print(f"\n⚠️  Total Invalid Objects: {len(invalid_objs)}")
    else:
        print("\n  ✅ All objects are valid!")
    
    # ========================================================================
    # 16. OBJECT SIZES
    # ========================================================================
    print_header("💾 OBJECT SIZES")
    
    cur.execute("""
        SELECT segment_name, segment_type, SUM(bytes) AS total_bytes
        FROM user_segments
        GROUP BY segment_name, segment_type
        ORDER BY SUM(bytes) DESC
    """)
    segments = cur.fetchall()
    
    if segments:
        print("\n  Top 10 Largest Objects:\n")
        for seg_name, seg_type, total_bytes in segments[:10]:
            size_str = format_bytes(total_bytes)
            print(f"    {seg_name:30s} {seg_type:15s} {size_str:>12s}")
        
        total_size = sum([s[2] for s in segments])
        print(f"\n  📊 Total Schema Size: {format_bytes(total_size)}")
    else:
        print("  ❌ No segment information available")
    
    # ========================================================================
    # FINAL SUMMARY
    # ========================================================================
    print_header("📊 COMPLETE SCHEMA SUMMARY")
    
    # Count all object types
    cur.execute("""
        SELECT object_type, COUNT(*) AS cnt, 
               SUM(CASE WHEN status = 'VALID' THEN 1 ELSE 0 END) AS valid_cnt
        FROM user_objects
        GROUP BY object_type
        ORDER BY object_type
    """)
    obj_counts = cur.fetchall()
    
    print("\n  Object Type Breakdown:")
    print("  " + "-"*60)
    print(f"  {'Type':<25s} {'Total':>10s} {'Valid':>10s} {'Invalid':>10s}")
    print("  " + "-"*60)
    
    total_objects = 0
    total_valid = 0
    for obj_type, count, valid_count in obj_counts:
        invalid_count = count - valid_count
        total_objects += count
        total_valid += valid_count
        print(f"  {obj_type:<25s} {count:>10d} {valid_count:>10d} {invalid_count:>10d}")
    
    print("  " + "-"*60)
    print(f"  {'TOTAL':<25s} {total_objects:>10d} {total_valid:>10d} {total_objects - total_valid:>10d}")
    
    # Data summary
    print("\n  Data Summary:")
    print("  " + "-"*60)
    
    total_rows = 0
    for table_name, num_rows, blocks, avg_row_len, last_analyzed in tables:
        try:
            cur.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cur.fetchone()[0]
            total_rows += count
        except:
            pass
    
    print(f"  Total Tables:           {len(tables)}")
    print(f"  Total Rows (approx):    {total_rows:,}")
    print(f"  Total Schema Size:      {format_bytes(total_size) if segments else 'N/A'}")
    
    # Close connection
    cur.close()
    conn.close()
    
    print("\n" + "="*80)
    print("✅ COMPLETE SCHEMA INSPECTION FINISHED")
    print("="*80)
    print(f"\nInspection completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())