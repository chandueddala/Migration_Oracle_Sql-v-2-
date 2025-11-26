#!/usr/bin/env python3
"""
DYNAMIC ORACLE OBJECT SUMMARY (AUTO-CREDENTIAL VERSION)
=======================================================

Automatically prints:
- Tables
- Sequences
- Functions
- Procedures
- Packages
- Triggers
- Views
- Types
- Synonyms

Credentials are pre-set for:
docker run -d --name oracle_free -p 1521:1521 -p 5500:5500 \
  -e ORACLE_PASSWORD=oracle \
  -e APP_USER=app \
  -e APP_USER_PASSWORD=app \
  gvenzl/oracle-free:23-slim
"""

import oracledb

# ======================================================
# 🔥 AUTO-CONNECT CREDENTIALS (NO NEED TO TYPE ANYTHING)
# ======================================================
USER = "app"
PASSWORD = "app"
DSN = "localhost:1521/FREEPDB1"


def fetch_list(cur, sql):
    cur.execute(sql)
    return [r[0] for r in cur.fetchall()]


def print_section(title, names):
    print(f"\n{title}: {len(names)}")
    if names:
        for n in names:
            print(f"   - {n}")


def main():
    print("============================================")
    print("  ORACLE SCHEMA SUMMARY (AUTO-CONNECT)")
    print("============================================")
    print(f"Connecting as user: {USER}")
    print(f"DSN: {DSN}")

    # Connect automatically
    conn = oracledb.connect(user=USER, password=PASSWORD, dsn=DSN)
    cur = conn.cursor()
    print("\nConnected ✓")

    # --------------------------------------------
    # Tables
    # --------------------------------------------
    tables = fetch_list(cur, "SELECT table_name FROM user_tables ORDER BY table_name")
    print_section("Tables", tables)

    # --------------------------------------------
    # Sequences
    # --------------------------------------------
    sequences = fetch_list(cur, "SELECT sequence_name FROM user_sequences ORDER BY sequence_name")
    print_section("Sequences", sequences)

    # --------------------------------------------
    # Standalone Functions
    # --------------------------------------------
    functions = fetch_list(cur, """
        SELECT object_name FROM user_objects
        WHERE object_type = 'FUNCTION'
        ORDER BY object_name
    """)
    print_section("Functions", functions)

    # --------------------------------------------
    # Standalone Procedures
    # --------------------------------------------
    procedures = fetch_list(cur, """
        SELECT object_name FROM user_objects
        WHERE object_type = 'PROCEDURE'
        ORDER BY object_name
    """)
    print_section("Procedures", procedures)

    # --------------------------------------------
    # Packages
    # --------------------------------------------
    packages = fetch_list(cur, """
        SELECT object_name FROM user_objects
        WHERE object_type = 'PACKAGE'
        ORDER BY object_name
    """)
    print_section("Packages", packages)

    # --------------------------------------------
    # Triggers
    # --------------------------------------------
    triggers = fetch_list(cur, """
        SELECT trigger_name FROM user_triggers ORDER BY trigger_name
    """)
    print_section("Triggers", triggers)

    # --------------------------------------------
    # Views
    # --------------------------------------------
    views = fetch_list(cur, """
        SELECT view_name FROM user_views ORDER BY view_name
    """)
    print_section("Views", views)

    # --------------------------------------------
    # Object Types
    # --------------------------------------------
    obj_types = fetch_list(cur, """
        SELECT object_name FROM user_objects
        WHERE object_type = 'TYPE'
        ORDER BY object_name
    """)
    print_section("Object Types", obj_types)

    # --------------------------------------------
    # Synonyms
    # --------------------------------------------
    synonyms = fetch_list(cur, """
        SELECT synonym_name FROM user_synonyms ORDER BY synonym_name
    """)
    print_section("Synonyms", synonyms)

    # --------------------------------------------
    # TOTAL OBJECT COUNT
    # --------------------------------------------
    total = len(tables) + len(sequences) + len(functions) + len(procedures) + \
            len(packages) + len(triggers) + len(views) + len(obj_types) + len(synonyms)

    print("\n============================================")
    print(f" TOTAL OBJECTS FOUND: {total}")
    print("============================================")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
