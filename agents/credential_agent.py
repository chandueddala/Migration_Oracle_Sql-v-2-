"""
Credential Validation Agent

An intelligent agentic system that handles database credential collection,
validation, and retry logic without sending sensitive information to LLMs.

Key Features:
- Retry loop with configurable attempts (default: 5)
- Intelligent error diagnosis without exposing credentials
- User-friendly prompts based on error patterns
- Secure credential handling with no LLM exposure
"""

import logging
from typing import Dict, Optional, Tuple
from database.oracle_connector import OracleConnector
from database.sqlserver_connector import SQLServerConnector
from config.config_enhanced import MAX_CREDENTIAL_ATTEMPTS, SecurityLogger

logger = logging.getLogger(__name__)


class CredentialAgent:
    """
    Agentic system for intelligent credential validation with retry logic.

    This agent:
    1. Collects credentials from the user
    2. Validates connections without exposing credentials
    3. Provides intelligent feedback based on error patterns
    4. Retries up to MAX_CREDENTIAL_ATTEMPTS times
    5. Never sends credentials to LLMs
    """

    def __init__(self, max_attempts: int = None):
        """
        Initialize the credential agent.

        Args:
            max_attempts: Maximum number of credential retry attempts
        """
        self.max_attempts = max_attempts if max_attempts is not None else MAX_CREDENTIAL_ATTEMPTS
        self.attempt_count = 0
        logger.info(f"Credential Agent initialized (max {self.max_attempts} attempts)")

    def run(self) -> Tuple[Optional[Dict], Optional[Dict]]:
        """
        Main agent loop: collect and validate credentials with retry logic.
        Validates each database connection individually and only re-prompts for failed ones.

        Returns:
            Tuple of (oracle_credentials, sqlserver_credentials) if successful,
            (None, None) if max attempts exceeded
        """
        oracle_creds = None
        sqlserver_creds = None
        oracle_validated = False
        sqlserver_validated = False

        while self.attempt_count < self.max_attempts:
            self.attempt_count += 1

            print(f"\n{'='*70}")
            print(f"CREDENTIAL VALIDATION - Attempt {self.attempt_count}/{self.max_attempts}")
            print(f"{'='*70}")

            # Collect credentials from user (only for databases that need validation)
            if not oracle_validated:
                oracle_creds = self._collect_oracle_credentials()
                oracle_creds = self._normalize_oracle_credentials(oracle_creds)
                SecurityLogger.log_credential_usage(
                    "oracle",
                    SecurityLogger.mask_credential(oracle_creds.get('password', ''))
                )

            if not sqlserver_validated:
                sqlserver_creds = self._collect_sqlserver_credentials()
                sqlserver_creds = self._normalize_sqlserver_credentials(sqlserver_creds)
                SecurityLogger.log_credential_usage(
                    "sqlserver",
                    SecurityLogger.mask_credential(sqlserver_creds.get('password', ''))
                )

            # Validate each connection individually
            if not oracle_validated:
                oracle_result = self._validate_oracle_connection(oracle_creds)
                if oracle_result['success']:
                    oracle_validated = True
                    print("  ✅ Oracle connection successful")
                else:
                    print("  ❌ Oracle connection failed")
                    print(f"     Error Type: {oracle_result['error_type']}")
                    print(f"     {self._get_error_suggestion('oracle', oracle_result['error_type'])}")

            if not sqlserver_validated:
                sqlserver_result = self._validate_sqlserver_connection(sqlserver_creds)
                if sqlserver_result['success']:
                    sqlserver_validated = True
                    print("  ✅ SQL Server connection successful")
                else:
                    print("  ❌ SQL Server connection failed")
                    print(f"     Error Type: {sqlserver_result['error_type']}")
                    print(f"     {self._get_error_suggestion('sqlserver', sqlserver_result['error_type'])}")

            # Check if both are validated
            if oracle_validated and sqlserver_validated:
                print(f"\n✅ All credentials validated successfully!")
                logger.info(f"Credential validation succeeded on attempt {self.attempt_count}")
                return oracle_creds, sqlserver_creds

            # Provide feedback on what needs to be retried
            print(f"\n{'='*70}")
            print(f"VALIDATION SUMMARY - Attempt {self.attempt_count}/{self.max_attempts}")
            print(f"{'='*70}")
            if oracle_validated:
                print("✅ Oracle: Connected successfully")
            else:
                print("❌ Oracle: Needs valid credentials")

            if sqlserver_validated:
                print("✅ SQL Server: Connected successfully")
            else:
                print("❌ SQL Server: Needs valid credentials")

            if self.attempt_count < self.max_attempts:
                retry = input(f"\n🔄 Retry with different credentials? (y/n): ").strip().lower()
                if retry != 'y':
                    logger.info("User chose not to retry credentials")
                    return None, None

        # Max attempts exceeded
        print(f"\n❌ Maximum attempts ({self.max_attempts}) exceeded.")
        print("Please verify your credentials and try again later.")
        logger.error(f"Credential validation failed after {self.max_attempts} attempts")
        return None, None

    def _collect_credentials(self) -> Tuple[Dict, Dict]:
        """
        Collect database credentials from user input.

        Returns:
            Tuple of (oracle_credentials, sqlserver_credentials)
        """
        oracle_creds = self._collect_oracle_credentials()
        sqlserver_creds = self._collect_sqlserver_credentials()
        return oracle_creds, sqlserver_creds

    def _collect_oracle_credentials(self) -> Dict:
        """
        Collect Oracle database credentials from user input.

        Returns:
            Oracle credentials dictionary
        """
        print("\n📊 Oracle Database Credentials:")
        oracle_creds = {
            "host": input("  Host (default: localhost): ").strip() or "localhost",
            "port": input("  Port (default: 1521): ").strip() or "1521",
            "service_name": input("  Service Name: ").strip(),
            "username": input("  Username: ").strip(),
            "password": input("  Password: ").strip()
        }
        return oracle_creds

    def _collect_sqlserver_credentials(self) -> Dict:
        """
        Collect SQL Server database credentials from user input.

        Returns:
            SQL Server credentials dictionary
        """
        print("\n📊 SQL Server Database Credentials:")
        sqlserver_creds = {
            "server": input("  Server (default: localhost): ").strip() or "localhost",
            "database": input("  Database: ").strip(),
            "username": input("  Username: ").strip(),
            "password": input("  Password: ").strip()
        }
        return sqlserver_creds

    def _normalize_oracle_credentials(self, creds: Dict) -> Dict:
        """
        Normalize Oracle credentials to expected format.

        Maps 'username' -> 'user' for oracledb compatibility.

        Args:
            creds: Raw credentials dictionary

        Returns:
            Normalized credentials dictionary
        """
        normalized = creds.copy()
        if 'username' in normalized:
            normalized['user'] = normalized.pop('username')
        return normalized

    def _normalize_sqlserver_credentials(self, creds: Dict) -> Dict:
        """
        Normalize SQL Server credentials to expected format.

        Maps 'username' -> 'user' for pyodbc compatibility.

        Args:
            creds: Raw credentials dictionary

        Returns:
            Normalized credentials dictionary
        """
        normalized = creds.copy()
        if 'username' in normalized:
            normalized['user'] = normalized.pop('username')
        return normalized

    def _validate_credentials(self, oracle_creds: Dict, sqlserver_creds: Dict) -> Dict:
        """
        Validate database credentials by attempting connections.

        This method NEVER sends credentials to LLMs. All validation is done
        through direct database connection attempts.

        Args:
            oracle_creds: Oracle database credentials
            sqlserver_creds: SQL Server database credentials

        Returns:
            Dictionary with validation results:
            {
                'success': bool,
                'oracle': {'success': bool, 'error': str, 'error_type': str},
                'sqlserver': {'success': bool, 'error': str, 'error_type': str}
            }
        """
        result = {
            'success': False,
            'oracle': {'success': False, 'error': None, 'error_type': None},
            'sqlserver': {'success': False, 'error': None, 'error_type': None}
        }

        # Test Oracle connection
        print("\n🔍 Validating Oracle connection...")
        result['oracle'] = self._validate_oracle_connection(oracle_creds)

        # Test SQL Server connection
        print("\n🔍 Validating SQL Server connection...")
        result['sqlserver'] = self._validate_sqlserver_connection(sqlserver_creds)

        # Overall success if both connections succeeded
        result['success'] = result['oracle']['success'] and result['sqlserver']['success']

        return result

    def _validate_oracle_connection(self, oracle_creds: Dict) -> Dict:
        """
        Validate Oracle database connection.

        Args:
            oracle_creds: Oracle database credentials

        Returns:
            Dictionary with validation result:
            {'success': bool, 'error': str, 'error_type': str}
        """
        result = {'success': False, 'error': None, 'error_type': None}

        try:
            oracle_conn = OracleConnector(oracle_creds)
            if oracle_conn.connect():
                result['success'] = True
                oracle_conn.disconnect()
            else:
                result['error'] = "Connection failed"
                result['error_type'] = 'connection_failed'
        except KeyError as e:
            error_msg = f"Missing credential field: {str(e)}"
            result['error'] = error_msg
            result['error_type'] = 'missing_field'
            logger.error(f"Oracle credential error: {error_msg}")
        except Exception as e:
            error_msg = str(e)
            error_type = self._categorize_error(error_msg)
            result['error'] = error_msg
            result['error_type'] = error_type
            logger.error(f"Oracle connection error ({error_type}): {error_msg}")

        return result

    def _validate_sqlserver_connection(self, sqlserver_creds: Dict) -> Dict:
        """
        Validate SQL Server database connection.

        Args:
            sqlserver_creds: SQL Server database credentials

        Returns:
            Dictionary with validation result:
            {'success': bool, 'error': str, 'error_type': str}
        """
        result = {'success': False, 'error': None, 'error_type': None}

        try:
            sqlserver_conn = SQLServerConnector(sqlserver_creds)
            if sqlserver_conn.connect():
                result['success'] = True
                sqlserver_conn.disconnect()
            else:
                result['error'] = "Connection failed"
                result['error_type'] = 'connection_failed'
        except KeyError as e:
            error_msg = f"Missing credential field: {str(e)}"
            result['error'] = error_msg
            result['error_type'] = 'missing_field'
            logger.error(f"SQL Server credential error: {error_msg}")
        except Exception as e:
            error_msg = str(e)
            error_type = self._categorize_error(error_msg)
            result['error'] = error_msg
            result['error_type'] = error_type
            logger.error(f"SQL Server connection error ({error_type}): {error_msg}")

        return result

    def _categorize_error(self, error_msg: str) -> str:
        """
        Categorize error type based on error message patterns.

        NO CREDENTIALS ARE ANALYZED - only error patterns.

        Args:
            error_msg: Error message string

        Returns:
            Error category string
        """
        error_lower = error_msg.lower()

        if 'authentication' in error_lower or 'login' in error_lower:
            return 'authentication'
        elif 'password' in error_lower:
            return 'password'
        elif 'user' in error_lower or 'username' in error_lower:
            return 'username'
        elif 'host' in error_lower or 'server' in error_lower or 'network' in error_lower:
            return 'network'
        elif 'service' in error_lower or 'sid' in error_lower:
            return 'service_name'
        elif 'database' in error_lower:
            return 'database'
        elif 'port' in error_lower:
            return 'port'
        elif 'timeout' in error_lower:
            return 'timeout'
        elif 'permission' in error_lower or 'access denied' in error_lower:
            return 'permission'
        else:
            return 'unknown'

    def _provide_feedback(self, validation_result: Dict, attempt_num: int) -> None:
        """
        Provide intelligent feedback to user based on error patterns.

        NO CREDENTIALS ARE EXPOSED - only error diagnostics.

        Args:
            validation_result: Validation result dictionary
            attempt_num: Current attempt number
        """
        print(f"\n{'='*70}")
        print(f"VALIDATION FAILED - Attempt {attempt_num}/{self.max_attempts}")
        print(f"{'='*70}")

        # Oracle feedback
        if not validation_result['oracle']['success']:
            oracle_error = validation_result['oracle']
            print(f"\n❌ Oracle Connection Issues:")
            print(f"   Error Type: {oracle_error['error_type']}")
            print(f"   {self._get_error_suggestion('oracle', oracle_error['error_type'])}")

        # SQL Server feedback
        if not validation_result['sqlserver']['success']:
            sqlserver_error = validation_result['sqlserver']
            print(f"\n❌ SQL Server Connection Issues:")
            print(f"   Error Type: {sqlserver_error['error_type']}")
            print(f"   {self._get_error_suggestion('sqlserver', sqlserver_error['error_type'])}")

    def _get_error_suggestion(self, db_type: str, error_type: str) -> str:
        """
        Get user-friendly suggestion based on error type.

        Args:
            db_type: 'oracle' or 'sqlserver'
            error_type: Error category

        Returns:
            Suggestion string
        """
        suggestions = {
            'authentication': "💡 Check that your username and password are correct",
            'password': "💡 Verify your password (case-sensitive)",
            'username': "💡 Verify your username (case-sensitive)",
            'network': f"💡 Check that the {db_type} server is running and accessible",
            'service_name': "💡 Verify the Oracle service name (e.g., XEPDB1, ORCL)",
            'database': "💡 Verify the database name exists",
            'port': f"💡 Check the port number (Oracle: 1521, SQL Server: 1433)",
            'timeout': f"💡 The {db_type} server may be slow or unreachable",
            'permission': "💡 Your user account may not have sufficient permissions",
            'missing_field': "💡 Please provide all required credential fields",
            'connection_failed': f"💡 Unable to connect to {db_type} - check all connection parameters",
            'unknown': f"💡 Please review all {db_type} connection parameters"
        }

        return suggestions.get(error_type, suggestions['unknown'])


def main():
    """
    Test the credential agent independently.
    """
    print("\n" + "="*70)
    print("CREDENTIAL AGENT TEST")
    print("="*70)

    agent = CredentialAgent(max_attempts=5)
    oracle_creds, sqlserver_creds = agent.run()

    if oracle_creds and sqlserver_creds:
        print(f"\n✅ Credential validation successful!")
        print(f"   Oracle host: {oracle_creds.get('host')}")
        print(f"   SQL Server: {sqlserver_creds.get('server')}")
    else:
        print(f"\n❌ Credential validation failed")


if __name__ == "__main__":
    main()
