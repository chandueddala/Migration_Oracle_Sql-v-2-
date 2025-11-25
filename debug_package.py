"""
Debug script to inspect PKG_LOAN_PROCESSOR package structure
"""
import sys
import re
sys.path.insert(0, r'c:\Users\Chandu Eddala\Desktop\oracle-sqlserver-migration-v2-FINAL')

from database.oracle_connector import OracleConnector
from agents.credential_agent import CredentialAgent

def main():
    # Get credentials
    print("Getting credentials...")
    credential_agent = CredentialAgent()
    oracle_creds, sqlserver_creds = credential_agent.run()

    # Connect to Oracle
    oracle_conn = OracleConnector(oracle_creds)
    if not oracle_conn.connect():
        print("❌ Failed to connect to Oracle")
        return

    # Fetch package code
    code = oracle_conn.fetch_package_code('PKG_LOAN_PROCESSOR')
    oracle_conn.disconnect()

    if not code:
        print("❌ No package code retrieved")
        return

    print("=" * 80)
    print(f"PACKAGE CODE LENGTH: {len(code)} characters")
    print("=" * 80)

    # Show first 3000 chars
    print("\n📄 FIRST 3000 CHARACTERS:")
    print("-" * 80)
    print(code[:3000])
    print("-" * 80)

    # Show last 1000 chars
    print("\n📄 LAST 1000 CHARACTERS:")
    print("-" * 80)
    print(code[-1000:])
    print("-" * 80)

    # Check for PROCEDURE keywords
    print("\n🔍 SEARCHING FOR PROCEDURES:")
    print("-" * 80)
    proc_matches = re.findall(r'PROCEDURE\s+([\w$#]+)', code, re.IGNORECASE)
    print(f"Found {len(proc_matches)} PROCEDURE declarations:")
    for proc in proc_matches:
        print(f"  - {proc}")
    print("-" * 80)

    # Check for FUNCTION keywords
    print("\n🔍 SEARCHING FOR FUNCTIONS:")
    print("-" * 80)
    func_matches = re.findall(r'FUNCTION\s+([\w$#]+)', code, re.IGNORECASE)
    print(f"Found {len(func_matches)} FUNCTION declarations:")
    for func in func_matches:
        print(f"  - {func}")
    print("-" * 80)

    # Check for PACKAGE BODY
    print("\n🔍 CHECKING STRUCTURE:")
    print("-" * 80)
    has_spec = bool(re.search(r'CREATE\s+(?:OR\s+REPLACE\s+)?PACKAGE\s+(?!BODY)', code, re.IGNORECASE))
    has_body = bool(re.search(r'CREATE\s+(?:OR\s+REPLACE\s+)?PACKAGE\s+BODY', code, re.IGNORECASE))
    print(f"Has PACKAGE SPECIFICATION: {has_spec}")
    print(f"Has PACKAGE BODY: {has_body}")
    print("-" * 80)

    # Try the parsing
    print("\n🔧 TESTING PARSER:")
    print("-" * 80)
    try:
        from utils.package_decomposer_enhanced import DynamicPackageParser
        parser = DynamicPackageParser()

        # Test normalization
        normalized = parser._normalize_code(code)
        print(f"Normalized code length: {len(normalized)}")

        # Test package name extraction
        package_name = parser._extract_package_name(normalized)
        print(f"Extracted package name: {package_name}")

        # Test spec/body separation
        spec, body = parser._separate_spec_and_body(normalized)
        print(f"Spec length: {len(spec)} chars")
        print(f"Body length: {len(body)} chars")

        # Show spec content pattern match
        if spec:
            content_pattern = r'PACKAGE\s+[\w$#]+\s+(?:IS|AS)(.*?)END\s+[\w$#]*'
            content_match = re.search(content_pattern, spec, re.IGNORECASE | re.DOTALL)
            if content_match:
                spec_content = content_match.group(1)
                print(f"\n📋 SPEC CONTENT LENGTH: {len(spec_content)}")
                print("First 500 chars of spec content:")
                print(spec_content[:500])
            else:
                print("❌ Could not extract spec content")

        # Show body content pattern match
        if body:
            content_pattern = r'PACKAGE\s+BODY\s+[\w$#]+\s+(?:IS|AS)(.*?)(?:BEGIN|END\s+[\w$#]*\s*;?\s*$)'
            content_match = re.search(content_pattern, body, re.IGNORECASE | re.DOTALL)
            if content_match:
                body_content = content_match.group(1)
                print(f"\n📋 BODY CONTENT LENGTH: {len(body_content)}")
                print("First 1000 chars of body content:")
                print(body_content[:1000])
            else:
                print("❌ Could not extract body content")
                # Try alternative pattern
                print("\n🔄 Trying alternative body pattern...")
                print("Looking for PACKAGE BODY pattern:")
                alt_match = re.search(r'PACKAGE\s+BODY.*?(?:IS|AS)', body, re.IGNORECASE | re.DOTALL)
                if alt_match:
                    print("Found PACKAGE BODY header:", alt_match.group(0)[:100])

        # Full parse attempt
        print("\n🚀 FULL PARSE ATTEMPT:")
        structure = parser.parse_package(code)
        print(f"Procedures found: {len(structure.procedures)}")
        print(f"Functions found: {len(structure.functions)}")
        print(f"Total members: {len(structure.members)}")

    except Exception as e:
        print(f"❌ Parser error: {e}")
        import traceback
        traceback.print_exc()

    print("-" * 80)

if __name__ == "__main__":
    main()
