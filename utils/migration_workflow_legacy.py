"""
Main migration workflow engine with dynamic shared memory
"""

import json
import logging
from datetime import datetime
from typing import Dict, List

from config import OUTPUT_DIR, CostTracker
from database import (
    collect_credentials,
    validate_credentials,
    discover_oracle_schema,
    discover_oracle_tables,
    get_oracle_code,
    get_oracle_table_ddl,
    oracle_connection,
    sqlserver_connection
)
from ai_converter import (
    convert_code,
    convert_table_ddl,
    reflect_code,
    try_deploy_with_repair,
    claude_sonnet
)
from shared_memory import get_shared_memory, ensure_schema_exists, fix_schema_references

logger = logging.getLogger(__name__)


def migrate_table_data(oracle_creds: Dict, sqlserver_creds: Dict, table_name: str, 
                      batch_size: int = 1000) -> Dict:
    """
    Migrate data from Oracle to SQL Server with dynamic shared memory
    Automatically handles identity columns and learns from errors
    """
    shared_memory = get_shared_memory()
    
    try:
        print(f"    ðŸ“Š Migrating data for table: {table_name}")
        
        with oracle_connection(oracle_creds) as oracle_conn:
            oracle_cursor = oracle_conn.cursor()
            
            # Get column information
            oracle_cursor.execute(f"""
                SELECT column_name, data_type, data_length, nullable
                FROM user_tab_columns 
                WHERE table_name = :tname 
                ORDER BY column_id
            """, [table_name.upper()])
            
            column_info = []
            columns = []
            for row in oracle_cursor.fetchall():
                col_name = row[0]
                columns.append(col_name)
                column_info.append({
                    "name": col_name,
                    "type": row[1],
                    "length": row[2],
                    "nullable": row[3]
                })
                
                # Dynamically detect identity columns
                col_upper = col_name.upper()
                if (col_upper.endswith('_ID') or col_upper == 'ID' or 
                    'ID' in col_upper or col_upper.startswith('PK_')):
                    shared_memory.register_identity_column(table_name, col_name)
                    logger.info(f"Dynamically detected identity column: {table_name}.{col_name}")
            
            if not columns:
                return {"status": "error", "message": f"No columns found for {table_name}"}
            
            logger.info(f"Table {table_name} has {len(columns)} columns: {', '.join(columns)}")
            
            # Get row count
            oracle_cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            total_rows = oracle_cursor.fetchone()[0]
            
            if total_rows == 0:
                print(f"    â„¹ï¸  Table {table_name} is empty, skipping data migration")
                return {"status": "success", "rows_migrated": 0}
            
            print(f"    ðŸ“ˆ Found {total_rows} rows to migrate")
            
            # Fetch all data
            oracle_cursor.execute(f"SELECT * FROM {table_name}")
            
            with sqlserver_connection(sqlserver_creds) as sqlserver_conn:
                sqlserver_cursor = sqlserver_conn.cursor()
                
                rows_migrated = 0
                batch = []
                error_rows = []
                
                # Build INSERT statement
                placeholders = ', '.join(['?' for _ in columns])
                column_list = ', '.join([f"[{col}]" for col in columns])
                base_insert_sql = f"INSERT INTO [{table_name}] ({column_list}) VALUES ({placeholders})"
                
                # Check if table has identity columns
                has_identity = shared_memory.has_identity_columns(table_name)
                
                if has_identity:
                    identity_cols = shared_memory.get_identity_columns(table_name)
                    print(f"    ðŸ”‘ Identity columns detected: {', '.join(identity_cols)}")
                    print(f"    ðŸ”‘ Enabling IDENTITY_INSERT for {table_name}")
                    try:
                        sqlserver_cursor.execute(f"SET IDENTITY_INSERT [{table_name}] ON")
                        logger.info(f"IDENTITY_INSERT ON for {table_name}")
                    except Exception as e:
                        logger.warning(f"Could not enable IDENTITY_INSERT: {e}")
                
                # Process rows
                for row_num, row in enumerate(oracle_cursor, 1):
                    try:
                        converted_row = []
                        for value in row:
                            if value is None:
                                converted_row.append(None)
                            elif isinstance(value, bytes):
                                converted_row.append(value)
                            else:
                                converted_row.append(value)
                        
                        batch.append(tuple(converted_row))
                        
                        if len(batch) >= batch_size:
                            try:
                                sqlserver_cursor.executemany(base_insert_sql, batch)
                                sqlserver_conn.commit()
                                rows_migrated += len(batch)
                                print(f"    â³ Migrated {rows_migrated}/{total_rows} rows...")
                                batch = []
                            except Exception as batch_error:
                                logger.error(f"Batch insert failed: {batch_error}")
                                sqlserver_conn.rollback()
                                
                                # Try individual inserts
                                for individual_row in batch:
                                    try:
                                        sqlserver_cursor.execute(base_insert_sql, individual_row)
                                        sqlserver_conn.commit()
                                        rows_migrated += 1
                                    except Exception as row_error:
                                        error_rows.append({
                                            "row_number": row_num,
                                            "error": str(row_error),
                                            "data_sample": str(individual_row[:3]) + "..."
                                        })
                                        logger.error(f"Row insert failed: {row_error}")
                                batch = []
                    
                    except Exception as row_error:
                        logger.error(f"Row processing failed: {row_error}")
                        error_rows.append({
                            "row_number": row_num,
                            "error": str(row_error),
                            "data_sample": str(row[:3]) + "..."
                        })
                
                # Insert remaining rows
                if batch:
                    try:
                        sqlserver_cursor.executemany(base_insert_sql, batch)
                        sqlserver_conn.commit()
                        rows_migrated += len(batch)
                    except Exception as final_error:
                        logger.error(f"Final batch failed: {final_error}")
                        sqlserver_conn.rollback()
                        
                        for individual_row in batch:
                            try:
                                sqlserver_cursor.execute(base_insert_sql, individual_row)
                                sqlserver_conn.commit()
                                rows_migrated += 1
                            except Exception as row_error:
                                error_rows.append({
                                    "error": str(row_error),
                                    "data_sample": str(individual_row[:3]) + "..."
                                })
                
                # Disable IDENTITY_INSERT
                if has_identity:
                    try:
                        sqlserver_cursor.execute(f"SET IDENTITY_INSERT [{table_name}] OFF")
                        logger.info(f"IDENTITY_INSERT OFF for {table_name}")
                    except Exception as e:
                        logger.warning(f"Could not disable IDENTITY_INSERT: {e}")
                
                sqlserver_cursor.close()
            
            oracle_cursor.close()
        
        # Report results
        if error_rows:
            print(f"    âš ï¸  Data migration completed with errors: {rows_migrated} rows migrated, {len(error_rows)} rows failed")
            logger.warning(f"Table {table_name}: {len(error_rows)} rows failed")
            
            # Store error solution in shared memory
            if len(error_rows) > 0:
                shared_memory.store_error_solution(
                    error_rows[0]["error"],
                    {
                        "fix": "Check data types and constraints",
                        "object_type": "TABLE_DATA",
                        "context": {"table": table_name, "columns": columns}
                    }
                )
        else:
            print(f"    âœ… Data migration complete: {rows_migrated} rows migrated")
        
        logger.info(f"Successfully migrated {rows_migrated} rows for table {table_name}")
        
        return {
            "status": "success",
            "rows_migrated": rows_migrated,
            "rows_failed": len(error_rows),
            "error_details": error_rows[:10] if error_rows else []
        }
    
    except Exception as e:
        error_msg = f"Data migration failed: {str(e)}"
        print(f"    âŒ {error_msg}")
        logger.error(f"Data migration error for {table_name}: {e}", exc_info=True)
        return {"status": "error", "message": error_msg}


def get_user_selection(object_type: str, available_objects: List) -> List[str]:
    """Get user selection with dynamic options"""
    if not available_objects:
        print(f"  â„¹ï¸  No {object_type} found")
        return []
    
    count = len(available_objects)
    sample = ', '.join([obj['name'] if isinstance(obj, dict) else obj 
                       for obj in available_objects[:5]])
    more = f" (and {count - 5} more)" if count > 5 else ""
    
    print(f"\n  {object_type} ({count}): {sample}{more}")
    print(f"\n  Options for {object_type}:")
    print(f"    - Type 'all' to migrate all {count} {object_type.lower()}")
    print(f"    - Type 'none' or press Enter to skip")
    print(f"    - Type space-separated names to select specific {object_type.lower()}")
    print(f"    - Type numbers (e.g., '1 2 3') to select by position")
    
    user_input = input(f"\n  Select {object_type}: ").strip()
    
    if not user_input or user_input.lower() == 'none':
        print(f"  â­ï¸  Skipping {object_type}")
        return []
    
    if user_input.lower() == 'all':
        selected = [obj['name'] if isinstance(obj, dict) else obj 
                   for obj in available_objects]
        print(f"  âœ… Selected all {len(selected)} {object_type.lower()}")
        return selected
    
    # Check if input is numbers
    if all(part.isdigit() for part in user_input.split()):
        indices = [int(i) - 1 for i in user_input.split()]
        selected = []
        for idx in indices:
            if 0 <= idx < len(available_objects):
                obj = available_objects[idx]
                selected.append(obj['name'] if isinstance(obj, dict) else obj)
            else:
                print(f"  âš ï¸  Index {idx + 1} is out of range, skipping")
        print(f"  âœ… Selected {len(selected)} {object_type.lower()}")
        return selected
    
    # Otherwise treat as names
    selected = user_input.split()
    print(f"  âœ… Selected {len(selected)} {object_type.lower()}")
    return selected


def discover_and_create_schemas(sqlserver_creds: Dict) -> List[str]:
    """
    Dynamically discover schemas from Oracle objects and create them in SQL Server
    Returns list of schemas that were created or verified
    """
    shared_memory = get_shared_memory()
    schemas_needed = set()
    
    print("\nðŸ” Analyzing schema requirements...")
    
    # Always ensure default schemas exist
    default_schemas = ["dbo"]
    for schema in default_schemas:
        schemas_needed.add(schema)
    
    # Check shared memory for previously used schemas
    for schema_key in shared_memory.schemas.keys():
        if "." in schema_key:
            _, schema_name = schema_key.split(".", 1)
            if schema_name not in ["dbo", "sys", "guest"]:
                schemas_needed.add(schema_name)
    
    # Create/verify all needed schemas
    created_schemas = []
    for schema in schemas_needed:
        print(f"  ðŸ”§ Checking schema [{schema}]...")
        if ensure_schema_exists(schema, sqlserver_creds):
            print(f"    âœ… Schema [{schema}] ready")
            created_schemas.append(schema)
        else:
            print(f"    âš ï¸  Schema [{schema}] verification failed")
    
    return created_schemas


def run_migration():
    """Main migration with fully dynamic shared memory"""
    cost_tracker = CostTracker()
    shared_memory = get_shared_memory()
    
    migration_stats = {
        "tables": {"migrated": 0, "failed": 0, "data_rows": 0},
        "procedures": {"migrated": 0, "failed": 0},
        "functions": {"migrated": 0, "failed": 0},
        "triggers": {"migrated": 0, "failed": 0}
    }
    
    print("\n" + "="*70)
    print("ðŸš€ ORACLE TO SQL SERVER MIGRATION SYSTEM")
    print("   WITH DYNAMIC SHARED MEMORY")
    print("="*70)
    print(shared_memory.get_summary())
    print()
    
    # Collect and validate credentials
    oracle_creds, sqlserver_creds = collect_credentials()
    
    if not validate_credentials(oracle_creds, sqlserver_creds):
        print("\nâŒ Credential validation failed")
        return
    
    # Dynamically discover and create schemas
    created_schemas = discover_and_create_schemas(sqlserver_creds)
    print(f"\nâœ… Schemas ready: {', '.join(created_schemas)}")
    
    # Discover and migrate tables
    tables_to_migrate = []
    migrate_data = False
    
    print("\n" + "="*70)
    print("ðŸ“Š STEP 1: TABLE MIGRATION")
    print("="*70)
    
    try:
        tinfo = discover_oracle_tables.invoke({"credentials_json": json.dumps(oracle_creds)})
        
        if tinfo.get("status") == "success" and tinfo.get("tables"):
            tables_to_migrate = get_user_selection("Tables", tinfo["tables"])
            
            if tables_to_migrate:
                data_choice = input("\n  Do you want to migrate TABLE DATA as well? [y/N]: ").strip().lower()
                migrate_data = (data_choice == 'y')
                
                if migrate_data:
                    print("  âœ… Will migrate table structure AND data")
                else:
                    print("  â„¹ï¸  Will migrate table structure only")
    except Exception as e:
        print(f"  âš ï¸  Error discovering tables: {e}")
        logger.error(f"Table discovery error: {e}", exc_info=True)
    
    # Migrate tables
    if tables_to_migrate:
        print(f"\nðŸ§± Migrating {len(tables_to_migrate)} tables...")
        
        for idx, tname in enumerate(tables_to_migrate, 1):
            print(f"\n  [{idx}/{len(tables_to_migrate)}] ðŸ“„ Table: {tname}")
            
            try:
                # Get Oracle DDL
                print("    ðŸ“¥ Retrieving Oracle DDL...")
                ddl_result = get_oracle_table_ddl.invoke({
                    "credentials_json": json.dumps(oracle_creds),
                    "table_name": tname
                })
                
                if ddl_result.get("status") != "success":
                    print(f"    âŒ Failed to fetch DDL: {ddl_result.get('message')}")
                    migration_stats["tables"]["failed"] += 1
                    continue
                
                # Convert to SQL Server DDL
                print("    ðŸ”„ Converting to SQL Server DDL...")
                tsql = convert_table_ddl(ddl_result["ddl"], tname, cost_tracker)
                
                # Dynamically fix schema references
                tsql = fix_schema_references(tsql, target_schema="dbo")
                
                # Deploy table structure
                print("    ðŸš€ Creating table structure...")
                deploy_res = try_deploy_with_repair(
                    sqlserver_creds,
                    tsql,
                    tname,
                    "TABLE",
                    claude_sonnet,
                    cost_tracker,
                    original_oracle_code=ddl_result["ddl"]
                )
                
                if deploy_res.get("status") == "success":
                    print("    âœ… Table structure created successfully")
                    migration_stats["tables"]["migrated"] += 1
                    
                    # Store successful pattern
                    shared_memory.store_successful_pattern({
                        "name": f"table_{tname}",
                        "object_type": "TABLE",
                        "oracle_ddl": ddl_result["ddl"][:500],
                        "tsql": tsql[:500],
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    # Migrate data if requested
                    if migrate_data:
                        data_result = migrate_table_data(oracle_creds, sqlserver_creds, tname)
                        if data_result.get("status") == "success":
                            rows = data_result.get("rows_migrated", 0)
                            migration_stats["tables"]["data_rows"] += rows
                else:
                    print(f"    âŒ Failed: {deploy_res.get('message')}")
                    migration_stats["tables"]["failed"] += 1
                    
                    # Store failed pattern
                    shared_memory.store_failed_pattern({
                        "name": f"table_{tname}_failed",
                        "object_type": "TABLE",
                        "error": deploy_res.get('message', '')[:200],
                        "timestamp": datetime.now().isoformat()
                    })
            
            except Exception as e:
                print(f"    âŒ Error: {e}")
                logger.error(f"Error migrating table {tname}: {e}", exc_info=True)
                migration_stats["tables"]["failed"] += 1
    
    # Discover schema objects
    print("\n" + "="*70)
    print("ðŸ“Š STEP 2: DISCOVERING SCHEMA OBJECTS")
    print("="*70)
    
    try:
        schema = discover_oracle_schema.invoke({"credentials_json": json.dumps(oracle_creds)})
        
        if schema.get("status") != "success":
            print(f"\nâŒ Schema discovery failed: {schema.get('message')}")
            return
    except Exception as e:
        print(f"\nâŒ Error: {e}")
        logger.error(f"Schema discovery error: {e}", exc_info=True)
        return
    
    # User selection
    print("\n" + "="*70)
    print("ðŸ“Š STEP 3: SELECT OBJECTS TO MIGRATE")
    print("="*70)
    
    procs = get_user_selection("Procedures", schema.get('procedures', []))
    funcs = get_user_selection("Functions", schema.get('functions', []))
    trigs = get_user_selection("Triggers", schema.get('triggers', []))
    
    total_objects = len(procs) + len(funcs) + len(trigs)
    
    if total_objects == 0:
        print("\nâš ï¸  No schema objects selected")
    else:
        print(f"\nâœ… Total: {total_objects} objects")
        print("\n" + "="*70)
        print("ðŸ“Š STEP 4: MIGRATING SCHEMA OBJECTS")
        print("="*70)
        
        results = {"success": [], "failed": []}
        all_objects = (
            [(p, "PROCEDURE") for p in procs] +
            [(f, "FUNCTION") for f in funcs] +
            [(t, "TRIGGER") for t in trigs]
        )
        
        for idx, (obj_name, obj_type) in enumerate(all_objects, 1):
            print(f"\n  [{idx}/{total_objects}] ðŸ“„ {obj_name} ({obj_type})")
            
            try:
                code_result = get_oracle_code.invoke({
                    "credentials_json": json.dumps(oracle_creds),
                    "object_name": obj_name,
                    "object_type": obj_type
                })
                
                if code_result["status"] != "success":
                    print(f"    âŒ Failed to get code")
                    results["failed"].append(obj_name)
                    _update_stats(migration_stats, obj_type, False)
                    continue
                
                print("    ðŸ”„ Converting...")
                converted = convert_code(code_result["code"], obj_name, obj_type, cost_tracker)
                converted = fix_schema_references(converted, target_schema="dbo")
                
                print("    ðŸ” Reviewing...")
                reflection = reflect_code(code_result["code"], converted, obj_name, cost_tracker)
                
                print("    ðŸš€ Deploying...")
                deploy_result = try_deploy_with_repair(
                    sqlserver_creds,
                    converted,
                    obj_name,
                    obj_type,
                    claude_sonnet,
                    cost_tracker,
                    original_oracle_code=code_result["code"]
                )
                
                if deploy_result.get("status") == "success":
                    print("    âœ… Success")
                    results["success"].append(obj_name)
                    _update_stats(migration_stats, obj_type, True)
                    
                    shared_memory.store_successful_pattern({
                        "name": f"{obj_type}_{obj_name}",
                        "object_type": obj_type,
                        "timestamp": datetime.now().isoformat()
                    })
                else:
                    print(f"    âŒ Failed: {deploy_result.get('message')[:50]}...")
                    results["failed"].append(obj_name)
                    _update_stats(migration_stats, obj_type, False)
            
            except Exception as e:
                print(f"    âŒ Error: {e}")
                logger.error(f"Error processing {obj_name}: {e}", exc_info=True)
                results["failed"].append(obj_name)
                _update_stats(migration_stats, obj_type, False)
    
    # Summary
    print("\n" + "="*70)
    print(cost_tracker.summary())
    print(shared_memory.get_summary())
    print("ðŸ“Š MIGRATION COMPLETE")
    print("="*70)
    
    print(f"\nðŸ“Š TABLES: âœ… {migration_stats['tables']['migrated']} | âŒ {migration_stats['tables']['failed']}")
    if migrate_data:
        print(f"   ðŸ“ˆ Rows: {migration_stats['tables']['data_rows']:,}")
    
    if procs or migration_stats['procedures']['migrated'] > 0:
        print(f"âš™ï¸  PROCEDURES: âœ… {migration_stats['procedures']['migrated']} | âŒ {migration_stats['procedures']['failed']}")
    
    if funcs or migration_stats['functions']['migrated'] > 0:
        print(f"ðŸ”§ FUNCTIONS: âœ… {migration_stats['functions']['migrated']} | âŒ {migration_stats['functions']['failed']}")
    
    if trigs or migration_stats['triggers']['migrated'] > 0:
        print(f"âš¡ TRIGGERS: âœ… {migration_stats['triggers']['migrated']} | âŒ {migration_stats['triggers']['failed']}")
    
    print(f"\nðŸ“Š LangSmith: https://smith.langchain.com/")
    print("="*70 + "\n")
    
    # Save report
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = OUTPUT_DIR / f"migration_{timestamp}.json"
        
        with open(report_file, 'w') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "migration_statistics": migration_stats,
                "shared_memory_stats": shared_memory.get_statistics(),
                "cost_summary": {"total_cost_usd": cost_tracker.total}
            }, f, indent=2)
        
        print(f"ðŸ“ Report saved: {report_file}\n")
    except Exception as e:
        print(f"âš ï¸  Report save failed: {e}")


def _update_stats(stats: dict, obj_type: str, success: bool):
    """Update migration statistics"""
    type_map = {"PROCEDURE": "procedures", "FUNCTION": "functions", "TRIGGER": "triggers"}
    key = type_map.get(obj_type)
    if key:
        stats[key]["migrated" if success else "failed"] += 1