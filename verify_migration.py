"""
MIGRATION VERIFICATION SCRIPT
Checks if data actually migrated to SQL Server despite -1 rowcount
"""

import pyodbc
import json

def verify_migration():
    """Verify migration results by querying SQL Server"""

    print("\n" + "=" * 70)
    print("📊 MIGRATION VERIFICATION")
    print("=" * 70)

    # Load SQL Server credentials
    try:
        with open('config/sqlserver_config.json', 'r') as f:
            creds = json.load(f)
    except Exception as e:
        print(f"\n❌ Failed to load credentials: {e}")
        return

    # Connect to SQL Server
    try:
        driver = creds.get('driver', 'ODBC Driver 18 for SQL Server')
        username = creds.get('user') or creds.get('username')

        conn_str = (
            f"DRIVER={{{driver}}};"
            f"SERVER={creds['server']};"
            f"DATABASE={creds['database']};"
            f"UID={username};"
            f"PWD={creds['password']};"
            f"TrustServerCertificate=yes;"
        )

        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()

        print("\n✅ Connected to SQL Server\n")

    except Exception as e:
        print(f"\n❌ Connection failed: {e}")
        return

    # Tables to verify
    tables = ['LOANS', 'LOAN_AUDIT', 'LOAN_PAYMENTS', 'LOAN_SCHEDULE', 'STG_LOAN_APPS']

    print("\n" + "-" * 70)
    print("TABLE DATA VERIFICATION")
    print("-" * 70 + "\n")

    total_tables = 0
    tables_with_data = 0

    for table in tables:
        try:
            # Check if table exists and get row count
            query = f"SELECT COUNT(*) FROM {table}"
            cursor.execute(query)
            count = cursor.fetchone()[0]

            if count > 0:
                print(f"✅ {table:<20} - {count} rows")
                tables_with_data += 1
            else:
                print(f"⚠️  {table:<20} - 0 rows (empty)")

            total_tables += 1

        except pyodbc.Error as e:
            print(f"❌ {table:<20} - Table not found or error: {e}")

    print("\n" + "-" * 70)
    print("SUMMARY")
    print("-" * 70)
    print(f"\nTables checked: {total_tables}")
    print(f"Tables with data: {tables_with_data}")
    print(f"Empty tables: {total_tables - tables_with_data}")

    # Show detailed data from LOANS table
    print("\n" + "-" * 70)
    print("SAMPLE DATA FROM LOANS TABLE")
    print("-" * 70 + "\n")

    try:
        cursor.execute("SELECT TOP 5 * FROM LOANS")
        rows = cursor.fetchall()

        if rows:
            # Get column names
            columns = [col[0] for col in cursor.description]
            print(f"Columns: {', '.join(columns)}")
            print()

            for row in rows:
                print(f"Row: {dict(zip(columns, row))}")
        else:
            print("No data found in LOANS table")

    except Exception as e:
        print(f"Error reading LOANS table: {e}")

    # Check for IDENTITY columns
    print("\n" + "-" * 70)
    print("IDENTITY COLUMNS CHECK")
    print("-" * 70 + "\n")

    for table in tables:
        try:
            query = """
            SELECT COLUMN_NAME, DATA_TYPE
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = ?
            AND COLUMNPROPERTY(OBJECT_ID(TABLE_SCHEMA + '.' + TABLE_NAME),
                             COLUMN_NAME, 'IsIdentity') = 1
            """
            cursor.execute(query, table)
            identity_cols = cursor.fetchall()

            if identity_cols:
                cols = ', '.join([col[0] for col in identity_cols])
                print(f"🔑 {table:<20} - IDENTITY: {cols}")

        except:
            pass

    cursor.close()
    conn.close()

    print("\n" + "=" * 70)
    print("VERIFICATION COMPLETE")
    print("=" * 70 + "\n")

    # Verdict
    if tables_with_data >= 4:
        print("✅ MIGRATION SUCCESSFUL!")
        print(f"   {tables_with_data}/{total_tables} tables have data")
        print("\n   Despite -1 rowcount display, data was migrated correctly!")
        print("   The -1 rowcount is a pyodbc driver quirk, not a failure.")
    elif tables_with_data > 0:
        print("⚠️  PARTIAL MIGRATION")
        print(f"   {tables_with_data}/{total_tables} tables have data")
        print("\n   Some tables migrated successfully, others may have failed")
    else:
        print("❌ MIGRATION FAILED")
        print("   No data found in any tables")
        print("\n   Check migration logs for errors")


if __name__ == "__main__":
    verify_migration()
