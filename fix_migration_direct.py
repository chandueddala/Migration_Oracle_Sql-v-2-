import os

path = r"c:\Users\Chandu Eddala\Desktop\oracle-sqlserver-migration-v2-FINAL\utils\migration_engine.py"
print(f"Reading from {path}")

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

target = "sqlserver_conn = SQLServerConnector(sqlserver_creds)"
replacement = """sqlserver_conn = SQLServerConnector(sqlserver_creds)
        
        # Connect to databases
        if not oracle_conn.connect():
            raise Exception("Failed to connect to Oracle database")
        if not sqlserver_conn.connect():
            raise Exception("Failed to connect to SQL Server database")"""

if target in content:
    if "oracle_conn.connect()" in content:
        print("Fix already present!")
    else:
        new_content = content.replace(target, replacement)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("File updated successfully")
else:
    print("Target string not found!")
