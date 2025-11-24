#!/usr/bin/env python3
"""
Oracle to SQL Server Migration System v2.0 - FINAL
Production-Ready with Perfect Modular Architecture

Entry Point - Run this file to start migration

Usage:
    python main.py

Directory Structure:
    agents/          - All AI agents (orchestrator, converter, reviewer, debugger, memory)
    external_tools/  - External integrations (SSMA, web search)
    database/        - Database operations (Oracle, SQL Server connectors)
    config/          - Configuration settings
    utils/           - Utility functions and workflows
    logs/            - Runtime logs
    output/          - Migration reports
"""

import sys
import os
from pathlib import Path

# Fix Windows console encoding for Unicode characters
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Add all module directories to Python path
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

# Set PYTHONPATH environment variable
os.environ['PYTHONPATH'] = str(BASE_DIR)

# Apply hot-fixes (temporary until migration_engine.py can be edited)
try:
    import hotfix_oracle_connector
except ImportError:
    pass  # Hot-fix not available

try:
    import hotfix_connection
except ImportError:
    pass  # Hot-fix not available

import logging

def setup_logging():
    """Setup logging before imports"""
    log_dir = BASE_DIR / "logs"
    log_dir.mkdir(exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / 'migration.log', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )

# Setup logging first
setup_logging()
logger = logging.getLogger(__name__)

# Now import config
try:
    from config.config_enhanced import (
        ANTHROPIC_API_KEY,
        LANGCHAIN_API_KEY,
        USE_ORCHESTRATOR
    )
except ImportError as e:
    logger.error(f"Failed to import config: {e}")
    print(f"\n❌ Configuration import failed: {e}")
    print("Please ensure config/config_enhanced.py exists")
    sys.exit(1)


def print_banner():
    """Print system banner"""
    print("\n" + "="*70)
    print("🚀 ORACLE → SQL SERVER MIGRATION SYSTEM v2.0 FINAL")
    print("   Perfect Production Architecture")
    print("="*70)
    print("✨ Features:")
    print("  ✅ Modular agents (orchestrator, converter, reviewer, debugger)")
    print("  ✅ External tools (SSMA, web search)")
    print("  ✅ Clean database layer (Oracle, SQL Server)")
    print("  ✅ Centralized configuration")
    print("  ✅ Production-ready structure")
    print("="*70 + "\n")


def validate_environment():
    """Validate that all required components are available"""
    missing = []
    warnings = []
    
    print("🔍 Validating environment...\n")
    
    # Check API keys
    if not ANTHROPIC_API_KEY:
        missing.append("ANTHROPIC_API_KEY not set in .env file")
    else:
        print("✅ Anthropic API key configured")
    
    if not LANGCHAIN_API_KEY:
        warnings.append("LANGCHAIN_API_KEY not set - LangSmith tracing disabled")
    else:
        print("✅ LangSmith API key configured")
    
    # Check module directories
    required_dirs = ["agents", "external_tools", "database", "config", "utils"]
    for dir_name in required_dirs:
        dir_path = BASE_DIR / dir_name
        if not dir_path.exists():
            missing.append(f"{dir_name}/ directory not found")
        else:
            print(f"✅ {dir_name}/ module found")
    
    # Try importing key modules
    try:
        from agents.orchestrator_agent import MigrationOrchestrator
        print("✅ Orchestrator agent imported")
    except ImportError as e:
        missing.append(f"Orchestrator agent import failed: {e}")
    
    try:
        from database.oracle_connector import OracleConnector
        from database.sqlserver_connector import SQLServerConnector
        print("✅ Database connectors imported")
    except ImportError as e:
        missing.append(f"Database connectors import failed: {e}")
    
    try:
        from external_tools.ssma_integration import get_ssma_agent
        print("✅ SSMA integration imported")
    except ImportError as e:
        warnings.append(f"SSMA integration import: {e}")
    
    try:
        from external_tools.web_search import WebSearchHelper
        print("✅ Web search imported")
    except ImportError as e:
        warnings.append(f"Web search import: {e}")
    
    if missing:
        print("\n❌ Missing required components:")
        for item in missing:
            print(f"   - {item}")
        return False
    
    if warnings:
        print("\n⚠️  Warnings:")
        for item in warnings:
            print(f"   - {item}")
        print()
    
    return True


def main():
    """Main entry point"""
    try:
        print_banner()
        
        logger.info("="*70)
        logger.info("Starting Oracle → SQL Server Migration System v2.0 FINAL")
        logger.info("="*70)
        
        # Validate environment
        if not validate_environment():
            print("\n❌ Environment validation failed")
            print("Please run: python setup.py")
            print("Or check the error messages above")
            return 1
        
        print("\n✅ All systems operational!")
        print("="*70)
        print()
        
        # Import workflow after validation
        try:
            from utils.migration_workflow import run_migration_orchestrated
            logger.info("Starting orchestrated migration workflow")
            run_migration_orchestrated()
        except ImportError as e:
            logger.error(f"Failed to import migration workflow: {e}")
            print(f"\n❌ Migration workflow import failed: {e}")
            return 1
        
        logger.info("="*70)
        logger.info("Migration completed successfully")
        logger.info("="*70)
        print("\n" + "="*70)
        print("✅ MIGRATION COMPLETED SUCCESSFULLY!")
        print("="*70)
        print("\n📊 Check results:")
        print("   - Logs: logs/migration.log")
        print("   - Reports: output/")
        print()
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Migration interrupted by user")
        logger.warning("Migration interrupted by user")
        return 0
        
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        logger.error(f"Fatal error: {e}", exc_info=True)
        print("\n📋 Check logs/migration.log for details")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
