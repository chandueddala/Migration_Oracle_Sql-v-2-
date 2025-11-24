"""
Test Script for Credential Agent

This script tests the credential validation agent independently
to verify the retry logic and error handling.

Usage:
    python test_credential_agent.py
"""

import sys
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config.config_enhanced import setup_logging
from agents.credential_agent import CredentialAgent

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


def main():
    """Test the credential agent"""
    print("\n" + "="*70)
    print("CREDENTIAL AGENT TEST")
    print("="*70)
    print("\nThis test will:")
    print("  1. Collect database credentials from you")
    print("  2. Validate connections to Oracle and SQL Server")
    print("  3. Retry up to 5 times if validation fails")
    print("  4. Provide intelligent feedback based on errors")
    print("\nNOTE: No credentials are sent to LLMs - validation is local only")
    print("="*70)

    # Initialize credential agent
    agent = CredentialAgent()

    # Run the agent
    oracle_creds, sqlserver_creds = agent.run()

    # Display results
    print("\n" + "="*70)
    print("TEST RESULTS")
    print("="*70)

    if oracle_creds and sqlserver_creds:
        print("\n✅ CREDENTIAL VALIDATION SUCCESSFUL")
        print("\nOracle Connection:")
        print(f"  Host: {oracle_creds.get('host')}")
        print(f"  Port: {oracle_creds.get('port')}")
        print(f"  Service: {oracle_creds.get('service_name')}")
        print(f"  User: {oracle_creds.get('user')}")

        print("\nSQL Server Connection:")
        print(f"  Server: {sqlserver_creds.get('server')}")
        print(f"  Database: {sqlserver_creds.get('database')}")
        print(f"  User: {sqlserver_creds.get('user')}")

        print("\n🎉 All database connections validated successfully!")
        print("You can now run the full migration with these credentials.")
        return 0
    else:
        print("\n❌ CREDENTIAL VALIDATION FAILED")
        print("\nPossible reasons:")
        print("  1. Incorrect username or password")
        print("  2. Database server is not running")
        print("  3. Network connectivity issues")
        print("  4. Firewall blocking connections")
        print("  5. Service name or database name is incorrect")

        print("\nPlease verify your database credentials and try again.")
        logger.error("Credential validation test failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
