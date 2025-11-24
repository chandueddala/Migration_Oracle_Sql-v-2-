"""
User Prompt Utilities
Handles user interaction with timeout and defaults
"""
import sys
import select
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def prompt_with_timeout(
    question: str,
    options: list,
    timeout: int = 30,
    default: str = None
) -> str:
    """
    Prompt user with timeout and default fallback

    Args:
        question: Question to ask the user
        options: List of valid options (e.g., ['drop', 'skip', 'append'])
        timeout: Timeout in seconds (default: 30)
        default: Default option if timeout or no response

    Returns:
        User's choice or default
    """
    # Format options display
    options_str = "/".join([opt.upper() if opt == default else opt for opt in options])

    print(f"\n⚠️  {question}")
    print(f"   Options: {options_str}")
    print(f"   (Auto-select '{default}' in {timeout} seconds if no response)")
    print(f"   Your choice: ", end='', flush=True)

    try:
        # Windows doesn't support select on stdin, use simpler approach
        if sys.platform == 'win32':
            # Use input with a simple message
            import threading

            user_input = [None]
            timeout_occurred = [False]

            def get_input():
                try:
                    user_input[0] = input().strip().lower()
                except:
                    pass

            input_thread = threading.Thread(target=get_input)
            input_thread.daemon = True
            input_thread.start()
            input_thread.join(timeout)

            if input_thread.is_alive():
                # Timeout occurred
                timeout_occurred[0] = True
                print(f"\n   ⏱️  Timeout - using default: '{default}'")
                logger.info(f"User prompt timeout - using default: {default}")
                return default

            choice = user_input[0]
            if not choice:
                print(f"   ℹ️  No input - using default: '{default}'")
                logger.info(f"No user input - using default: {default}")
                return default

        else:
            # Unix-like systems can use select
            ready, _, _ = select.select([sys.stdin], [], [], timeout)

            if ready:
                choice = sys.stdin.readline().strip().lower()
            else:
                print(f"\n   ⏱️  Timeout - using default: '{default}'")
                logger.info(f"User prompt timeout - using default: {default}")
                return default

        # Validate choice
        if choice in options:
            logger.info(f"User selected: {choice}")
            return choice
        else:
            print(f"   ⚠️  Invalid choice '{choice}' - using default: '{default}'")
            logger.warning(f"Invalid choice '{choice}' - using default: {default}")
            return default

    except Exception as e:
        logger.error(f"Error in user prompt: {e}")
        print(f"\n   ⚠️  Error - using default: '{default}'")
        return default


def prompt_existing_object(
    object_name: str,
    object_type: str,
    timeout: int = 30
) -> str:
    """
    Prompt user about existing database object

    Args:
        object_name: Name of the object (e.g., 'LOANS')
        object_type: Type of object (e.g., 'TABLE', 'PROCEDURE')
        timeout: Timeout in seconds

    Returns:
        User's choice: 'drop', 'skip', or 'append' (for tables only)
    """
    if object_type.upper() == "TABLE":
        question = f"{object_type} '{object_name}' already exists in SQL Server. What would you like to do?"
        options = ['drop', 'skip', 'append']
        default = 'append'

        print("\n" + "=" * 70)
        print(f"   DROP   - Drop existing table and recreate (data will be lost)")
        print(f"   SKIP   - Skip this table (no changes)")
        print(f"   APPEND - Keep existing table and add new data (recommended)")
        print("=" * 70)

    else:
        question = f"{object_type} '{object_name}' already exists in SQL Server. What would you like to do?"
        options = ['drop', 'skip']
        default = 'drop'

        print("\n" + "=" * 70)
        print(f"   DROP - Drop existing {object_type.lower()} and recreate")
        print(f"   SKIP - Skip this {object_type.lower()} (no changes)")
        print("=" * 70)

    return prompt_with_timeout(question, options, timeout, default)


def confirm_action(
    action: str,
    details: str = "",
    timeout: int = 15,
    default: bool = True
) -> bool:
    """
    Ask user to confirm an action

    Args:
        action: Action to confirm (e.g., "Drop all existing tables")
        details: Additional details
        timeout: Timeout in seconds
        default: Default response (True = yes, False = no)

    Returns:
        True if user confirms, False otherwise
    """
    default_str = "y" if default else "n"

    question = f"{action}"
    if details:
        question += f"\n   {details}"

    print(f"\n⚠️  {question}")
    print(f"   Continue? [Y/n] (default: {'Yes' if default else 'No'})")
    print(f"   (Auto-select '{'Yes' if default else 'No'}' in {timeout} seconds)")
    print(f"   Your choice: ", end='', flush=True)

    try:
        if sys.platform == 'win32':
            import threading

            user_input = [None]

            def get_input():
                try:
                    user_input[0] = input().strip().lower()
                except:
                    pass

            input_thread = threading.Thread(target=get_input)
            input_thread.daemon = True
            input_thread.start()
            input_thread.join(timeout)

            if input_thread.is_alive():
                print(f"\n   ⏱️  Timeout - using default: {'Yes' if default else 'No'}")
                return default

            choice = user_input[0]
            if not choice:
                return default

            return choice in ['y', 'yes']

        else:
            ready, _, _ = select.select([sys.stdin], [], [], timeout)

            if ready:
                choice = sys.stdin.readline().strip().lower()
                return choice in ['y', 'yes']
            else:
                print(f"\n   ⏱️  Timeout - using default: {'Yes' if default else 'No'}")
                return default

    except Exception as e:
        logger.error(f"Error in confirmation prompt: {e}")
        return default
