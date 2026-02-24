"""
macOS Keychain storage for secure credential management.

Provides KeychainManager class for securely storing and retrieving
API keys using the macOS Keychain via the security command-line tool.
"""
import subprocess
from typing import Optional


# Keychain constants
KEYCHAIN_SERVICE = "com.voxapp.rewrite"
KEYCHAIN_ACCOUNT = "openai-api-key"


class KeychainError(Exception):
    """Base exception for keychain errors."""
    pass


class KeychainManager:
    """Manages secure storage of API keys in macOS Keychain.

    Uses the macOS 'security' command-line tool to interact with
    the Keychain, avoiding the need for PyObjC Security framework bindings.
    """

    def __init__(self):
        """Initialize the keychain manager."""
        self._service = KEYCHAIN_SERVICE
        self._account = KEYCHAIN_ACCOUNT

    def get_password(self) -> Optional[str]:
        """Retrieve the API key from keychain.

        Returns:
            The API key string if found, None otherwise.

        Raises:
            KeychainError: If keychain access fails for reasons other
                than item not found.
        """
        cmd = [
            "security",
            "find-generic-password",
            "-s", self._service,
            "-a", self._account,
            "-w",  # Output password only to stdout
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
            )

            # Exit code 44 indicates item not found (expected for new installs)
            if result.returncode == 44:
                return None

            # Exit code 0 means success
            if result.returncode == 0:
                password = result.stdout.strip()
                # security -w outputs password with a trailing newline
                # and may wrap it in quotes if it contains special chars
                if password.startswith('"') and password.endswith('"'):
                    password = password[1:-1]
                return password if password else None

            # Other exit codes indicate errors
            if result.stderr:
                error_msg = result.stderr.strip()
                # Item not found errors are OK
                if "could not be found" in error_msg.lower():
                    return None
                raise KeychainError(f"Keychain error: {error_msg}")

            raise KeychainError(
                f"Unknown keychain error (exit code {result.returncode})"
            )

        except FileNotFoundError:
            raise KeychainError("security command not found - this should not happen on macOS")
        except subprocess.TimeoutExpired:
            raise KeychainError("Keychain access timed out")

    def set_password(self, password: str) -> bool:
        """Store the API key in keychain.

        Args:
            password: The API key string to store.

        Returns:
            True if successful, False otherwise.

        Raises:
            KeychainError: If keychain storage fails.
        """
        if not password:
            # Empty password - treat as delete
            return self.delete_password()

        # First, try to delete any existing password
        self.delete_password()

        cmd = [
            "security",
            "add-generic-password",
            "-s", self._service,
            "-a", self._account,
            "-w", password,
            "-U",  # Update if exists (redundant since we delete first, but safe)
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
            )

            # Exit code 0 means success
            if result.returncode == 0:
                return True

            # Check for errors
            if result.stderr:
                error_msg = result.stderr.strip()
                raise KeychainError(f"Failed to store in keychain: {error_msg}")

            raise KeychainError(
                f"Unknown keychain error (exit code {result.returncode})"
            )

        except FileNotFoundError:
            raise KeychainError("security command not found - this should not happen on macOS")
        except subprocess.TimeoutExpired:
            raise KeychainError("Keychain access timed out")

    def delete_password(self) -> bool:
        """Delete the API key from keychain.

        Returns:
            True if successful or if item didn't exist, False otherwise.

        Raises:
            KeychainError: If keychain deletion fails for reasons other
                than item not found.
        """
        cmd = [
            "security",
            "delete-generic-password",
            "-s", self._service,
            "-a", self._account,
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
            )

            # Exit code 44 indicates item not found (OK for delete operation)
            if result.returncode == 44:
                return True

            # Exit code 0 means successful deletion
            if result.returncode == 0:
                return True

            # Check for errors
            if result.stderr:
                error_msg = result.stderr.strip()
                # Item not found errors are OK
                if "could not be found" in error_msg.lower():
                    return True
                raise KeychainError(f"Failed to delete from keychain: {error_msg}")

            raise KeychainError(
                f"Unknown keychain error (exit code {result.returncode})"
            )

        except FileNotFoundError:
            raise KeychainError("security command not found - this should not happen on macOS")
        except subprocess.TimeoutExpired:
            raise KeychainError("Keychain access timed out")

    def has_password(self) -> bool:
        """Check if an API key exists in keychain.

        Returns:
            True if a password exists, False otherwise.
        """
        try:
            password = self.get_password()
            return password is not None and len(password) > 0
        except KeychainError:
            return False
