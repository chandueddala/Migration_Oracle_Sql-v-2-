"""
Simple debug script to inspect PKG_LOAN_PROCESSOR package structure
Run this to see what's in the package and why parsing fails
"""
import sys
import re
import os

# Set up environment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ['PYTHONIOENCODING'] = 'utf-8'

from database.oracle_connector import OracleConnector

def main():
    # Use environment variables or .env file for credentials
    oracle_creds = {
        'host': os.getenv('ORACLE_HOST'),
        'port': os.getenv('ORACLE_PORT', '1521'),
        'service_name': os.getenv('ORACLE_SERVICE_NAME'),
        'username': os.getenv('ORACLE_USERNAME'),
        'password': os.getenv('ORACLE_PASSWORD')
    }

    print("Connecting to Oracle...")
    oracle_conn = OracleConnector(oracle_creds)
    if not oracle_conn.connect():
        print("ERROR: Failed to connect to Oracle")
        print("Make sure .env file has Oracle credentials")
        return

    # Fetch package code
    print("Fetching PKG_LOAN_PROCESSOR...")
    code = oracle_conn.fetch_package_code('PKG_LOAN_PROCESSOR')
    oracle_conn.disconnect()

    if not code:
        print("ERROR: No package code retrieved")
        return

    print("=" * 80)
    print(f"PACKAGE CODE LENGTH: {len(code)} characters")
    print("=" * 80)

    # Show first 2000 chars
    print("\n[FIRST 2000 CHARS]")
    print("-" * 80)
    print(code[:2000])
    print("-" * 80)

    # Show last 1000 chars
    print("\n[LAST 1000 CHARS]")
    print("-" * 80)
    print(code[-1000:])
    print("-" * 80)

    # Check for PROCEDURE keywords
    print("\n[SEARCHING FOR PROCEDURES]")
    proc_matches = re.findall(r'PROCEDURE\s+([\w$#]+)', code, re.IGNORECASE)
    print(f"Found {len(proc_matches)} PROCEDURE declarations:")
    for i, proc in enumerate(proc_matches, 1):
        print(f"  {i}. {proc}")

    # Check for FUNCTION keywords
    print("\n[SEARCHING FOR FUNCTIONS]")
    func_matches = re.findall(r'FUNCTION\s+([\w$#]+)', code, re.IGNORECASE)
    print(f"Found {len(func_matches)} FUNCTION declarations:")
    for i, func in enumerate(func_matches, 1):
        print(f"  {i}. {func}")

    # Check structure
    print("\n[CHECKING STRUCTURE]")
    has_spec = bool(re.search(r'CREATE\s+(?:OR\s+REPLACE\s+)?PACKAGE\s+(?!BODY)', code, re.IGNORECASE))
    has_body = bool(re.search(r'CREATE\s+(?:OR\s+REPLACE\s+)?PACKAGE\s+BODY', code, re.IGNORECASE))
    print(f"Has PACKAGE SPECIFICATION: {has_spec}")
    print(f"Has PACKAGE BODY: {has_body}")

    # Save to file for manual inspection
    output_file = "PKG_LOAN_PROCESSOR_raw.sql"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(code)
    print(f"\nPackage code saved to: {output_file}")

    # Try the parser
    print("\n" + "=" * 80)
    print("[TESTING ENHANCED PARSER]")
    print("=" * 80)
    try:
        from utils.package_decomposer_enhanced import DynamicPackageParser
        parser = DynamicPackageParser()

        # Test spec/body separation
        spec, body = parser._separate_spec_and_body(code)
        print(f"\nSpec length: {len(spec)} chars")
        print(f"Body length: {len(body)} chars")

        if spec:
            print("\n[SPEC - First 500 chars]")
            print(spec[:500])

        if body:
            print("\n[BODY - First 1000 chars]")
            print(body[:1000])

        # Full parse
        print("\n[FULL PARSE RESULT]")
        structure = parser.parse_package(code)
        print(f"Package name: {structure.package_name}")
        print(f"Procedures found: {len(structure.procedures)}")
        print(f"Functions found: {len(structure.functions)}")
        print(f"Total members: {len(structure.members)}")

        if structure.members:
            print("\nMembers:")
            for m in structure.members:
                print(f"  - {m.member_type.value}: {m.name}")
        else:
            print("\nWARNING: No members found! Parser failed to extract procedures/functions.")
            print("Check the regex patterns in package_decomposer_enhanced.py")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
