"""
Migrate only the PKG_LOAN_PROCESSOR package to test the fixed parser
"""

import sys
import logging
from config.config_enhanced import CostTracker
from agents.credential_agent import CredentialAgent
from agents.orchestrator_agent import MigrationOrchestrator

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def main():
    print("="*70)
    print(" PACKAGE MIGRATION TEST - PKG_LOAN_PROCESSOR")
    print("="*70)

    # Step 1: Get credentials
    print("\n[STEP 1] Getting credentials...")
    credential_agent = CredentialAgent()
    oracle_creds, sqlserver_creds = credential_agent.run()

    # Step 2: Initialize orchestrator
    print("\n[STEP 2] Initializing migration orchestrator...")
    cost_tracker = CostTracker()
    orchestrator = MigrationOrchestrator(oracle_creds, sqlserver_creds, cost_tracker)

    # Step 3: Migrate package
    print("\n[STEP 3] Migrating PKG_LOAN_PROCESSOR...")
    print("-"*70)

    result = orchestrator.orchestrate('PKG_LOAN_PROCESSOR', 'PACKAGE')

    # Step 4: Show results
    print("\n" + "="*70)
    print(" MIGRATION RESULT")
    print("="*70)

    print(f"\nObject: {result['object_name']}")
    print(f"Type: {result['object_type']}")
    print(f"Status: {result['status']}")

    if result['status'] == 'success':
        print("\nSUCCESS! Package migrated successfully!")

        # Show what was migrated
        if 'decomposition' in result:
            decomp = result['decomposition']
            print(f"\nDecomposed into:")
            print(f"  - Procedures: {decomp.get('total_procedures', 0)}")
            print(f"  - Functions: {decomp.get('total_functions', 0)}")

            if 'members' in decomp:
                print(f"\nMigrated members:")
                for member in decomp['members']:
                    status = member.get('status', 'unknown')
                    print(f"  - {member['type']}: {member['name']} [{status}]")
    else:
        print("\nFAILED!")
        if 'error' in result:
            print(f"Error: {result['error']}")

    # Cost
    print(f"\n{cost_tracker}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nMigration cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        print(f"\nERROR: {e}")
        sys.exit(1)
