"""
Automatic Cleanup Utility
Drops existing tables before migration
"""

import sys
import pyodbc
from typing import List


def cleanup_tables(server: str, database: str, username: str, password: str, tables: List[str]):
    """
    Drop tables from SQL Server

    Args:
        server: SQL Server hostname
        database: Database name
        username: SQL username
        password: SQL password
        tables: List of table names to drop
    """
    print("\n" + "="*70)
    print("AUTOMATIC CLEANUP UTILITY")
    print("="*70)

    # Build connection string
    conn_str = (
        f"DRIVER={{ODBC Driver 18 for SQL Server}};"
        f"SERVER={server};"
        f"DATABASE={database};"
        f"UID={username};"
        f"PWD={password};"
        f"TrustServerCertificate=yes;"
    )

    try:
        print(f"\n🔗 Connecting to SQL Server...")
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        print(f"   ✅ Connected to {server}/{database}")

        print(f"\n🗑️  Dropping {len(tables)} tables...")

        for table in tables:
            try:
                # Drop table
                drop_sql = f"DROP TABLE IF EXISTS [{table}]"
                cursor.execute(drop_sql)
                conn.commit()
                print(f"   ✅ Dropped: {table}")

            except Exception as e:
                print(f"   ⚠️  Could not drop {table}: {str(e)[:100]}")

        cursor.close()
        conn.close()

        print(f"\n✅ Cleanup complete!")
        print(f"   You can now run: python main.py")

    except Exception as e:
        print(f"\n❌ Cleanup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    print("\n" + "="*70)
    print("SQL SERVER CLEANUP UTILITY")
    print("="*70)
    print("\nThis will DROP the following tables:")
    print("  • LOANS")
    print("  • LOAN_AUDIT")
    print("  • LOAN_PAYMENTS")
    print("  • LOAN_SCHEDULE")
    print("  • STG_LOAN_APPS")

    confirm = input("\n⚠️  Confirm cleanup? (yes/no): ").strip().lower()

    if confirm != 'yes':
        print("❌ Cleanup cancelled")
        sys.exit(0)

    # Get credentials
    print("\n📊 SQL Server Credentials:")
    server = input("  Server (default: localhost): ").strip() or "localhost"
    database = input("  Database (default: master): ").strip() or "master"
    username = input("  Username: ").strip()
    password = input("  Password: ").strip()

    # Tables to drop
    tables = [
        "LOANS",
        "LOAN_AUDIT",
        "LOAN_PAYMENTS",
        "LOAN_SCHEDULE",
        "STG_LOAN_APPS"
    ]

    # Run cleanup
    cleanup_tables(server, database, username, password, tables)
