"""
HOT-FIX: Add fetch_table_data alias to OracleConnector
This monkey-patches the OracleConnector class to add the missing method
"""
import sys
from database.oracle_connector import OracleConnector

# Add alias for backward compatibility
if not hasattr(OracleConnector, 'fetch_table_data'):
    OracleConnector.fetch_table_data = OracleConnector.get_table_data
    print("✅ Hot-fix applied: Added fetch_table_data alias to OracleConnector")
else:
    print("ℹ️  Hot-fix not needed: fetch_table_data already exists")
