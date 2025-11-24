"""
SQL Server Deployment Tool
LangChain tool for deploying SQL code to SQL Server
"""

import json
import logging
from typing import Dict, Any
from langchain_core.tools import tool

logger = logging.getLogger(__name__)


@tool
def deploy_to_sqlserver(credentials_json: str, sql_code: str, object_name: str) -> Dict[str, Any]:
    """
    Deploy SQL code to SQL Server database

    Args:
        credentials_json: JSON string of SQL Server credentials
        sql_code: T-SQL code to deploy
        object_name: Name of the database object

    Returns:
        dict: Deployment result with status and message
    """
    try:
        from database.sqlserver_connector import SQLServerConnector

        # Parse credentials
        credentials = json.loads(credentials_json)

        # Connect to SQL Server
        connector = SQLServerConnector(credentials)
        if not connector.connect():
            return {
                "status": "error",
                "message": "Failed to connect to SQL Server",
                "object_name": object_name
            }

        try:
            # Execute the DDL
            result = connector.execute_ddl(sql_code)

            # Add object name to result
            result["object_name"] = object_name

            if result["status"] == "success":
                logger.info(f"✅ Successfully deployed {object_name}")
            else:
                logger.error(f"❌ Failed to deploy {object_name}: {result.get('message')}")

            return result

        finally:
            connector.disconnect()

    except json.JSONDecodeError as e:
        error_msg = f"Invalid credentials JSON: {e}"
        logger.error(error_msg)
        return {
            "status": "error",
            "message": error_msg,
            "object_name": object_name
        }
    except Exception as e:
        error_msg = f"Deployment failed: {str(e)}"
        logger.error(error_msg)
        return {
            "status": "error",
            "message": error_msg,
            "object_name": object_name
        }
