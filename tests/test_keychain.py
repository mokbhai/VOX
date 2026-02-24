"""Tests for the keychain module."""
import pytest
from unittest.mock import patch, MagicMock
from vox.keychain import (
    KeychainManager,
    KeychainError,
    KEYCHAIN_SERVICE,
    KEYCHAIN_ACCOUNT,
)


class TestKeychainConstants:
    """Tests for keychain module constants."""

    def test_keychain_service(self):
        """Test KEYCHAIN_SERVICE has expected value."""
        assert KEYCHAIN_SERVICE == "com.voxapp.rewrite"

    def test_keychain_account(self):
        """Test KEYCHAIN_ACCOUNT has expected value."""
        assert KEYCHAIN_ACCOUNT == "openai-api-key"


class TestKeychainError:
    """Tests for KeychainError exception."""

    def test_keychain_error_is_exception(self):
        """Test KeychainError inherits from Exception."""
        assert issubclass(KeychainError, Exception)

    def test_keychain_error_can_be_raised(self):
        """Test KeychainError can be raised and caught."""
        with pytest.raises(KeychainError):
            raise KeychainError("test error")

    def test_keychain_error_message(self):
        """Test KeychainError preserves error message."""
        error_msg = "Keychain access failed"
        try:
            raise KeychainError(error_msg)
        except KeychainError as e:
            assert str(e) == error_msg


class TestKeychainManagerInit:
    """Tests for KeychainManager initialization."""

    def test_init_default_values(self):
        """Test KeychainManager initializes with correct defaults."""
        manager = KeychainManager()
        assert manager._service == KEYCHAIN_SERVICE
        assert manager._account == KEYCHAIN_ACCOUNT

    def test_init_service_account_constants(self):
        """Test service and account match module constants."""
        manager = KeychainManager()
        assert manager._service == "com.voxapp.rewrite"
        assert manager._account == "openai-api-key"


class TestKeychainManagerGetPassword:
    """Tests for KeychainManager.get_password method."""

    @pytest.fixture
    def manager(self):
        """Create a KeychainManager instance for testing."""
        return KeychainManager()

    def test_get_password_success(self, manager):
        """Test successful password retrieval."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "sk-test-api-key-12345\n"

        with patch("subprocess.run", return_value=mock_result):
            password = manager.get_password()
            assert password == "sk-test-api-key-12345"

    def test_get_password_with_quotes(self, manager):
        """Test password retrieval when keychain wraps password in quotes."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '"sk-test-key-with-special-chars"\n'

        with patch("subprocess.run", return_value=mock_result):
            password = manager.get_password()
            assert password == "sk-test-key-with-special-chars"

    def test_get_password_not_found_exit_code_44(self, manager):
        """Test get_password returns None when exit code is 44 (not found)."""
        mock_result = MagicMock()
        mock_result.returncode = 44
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result):
            password = manager.get_password()
            assert password is None

    def test_get_password_not_found_stderr_message(self, manager):
        """Test get_password returns None when stderr indicates not found."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "security: SecKeychainSearchCopyNext: The specified item could not be found in the keychain"

        with patch("subprocess.run", return_value=mock_result):
            password = manager.get_password()
            assert password is None

    def test_get_password_empty_response(self, manager):
        """Test get_password returns None when password is empty."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "   \n"

        with patch("subprocess.run", return_value=mock_result):
            password = manager.get_password()
            assert password is None

    def test_get_password_unknown_error(self, manager):
        """Test get_password raises KeychainError on unknown error."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "security: SecKeychainSearchCopyNext: Access denied"

        with patch("subprocess.run", return_value=mock_result):
            with pytest.raises(KeychainError) as exc_info:
                manager.get_password()
            assert "Keychain error" in str(exc_info.value)

    def test_get_password_unknown_error_no_stderr(self, manager):
        """Test get_password raises KeychainError with exit code when no stderr."""
        mock_result = MagicMock()
        mock_result.returncode = 2
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result):
            with pytest.raises(KeychainError) as exc_info:
                manager.get_password()
            assert "Unknown keychain error" in str(exc_info.value)
            assert "exit code 2" in str(exc_info.value)

    def test_get_password_security_not_found(self, manager):
        """Test get_password raises KeychainError when security command not found."""
        with patch("subprocess.run", side_effect=FileNotFoundError):
            with pytest.raises(KeychainError) as exc_info:
                manager.get_password()
            assert "security command not found" in str(exc_info.value)

    def test_get_password_timeout(self, manager):
        """Test get_password raises KeychainError on timeout."""
        import subprocess
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("security", 30)):
            with pytest.raises(KeychainError) as exc_info:
                manager.get_password()
            assert "timed out" in str(exc_info.value)

    def test_get_password_command_args(self, manager):
        """Test get_password calls security with correct arguments."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "test-key\n"

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            manager.get_password()

            call_args = mock_run.call_args
            cmd = call_args[0][0]
            assert cmd[0] == "security"
            assert cmd[1] == "find-generic-password"
            assert "-s" in cmd
            assert "-a" in cmd
            assert "-w" in cmd
            assert KEYCHAIN_SERVICE in cmd
            assert KEYCHAIN_ACCOUNT in cmd


class TestKeychainManagerSetPassword:
    """Tests for KeychainManager.set_password method."""

    @pytest.fixture
    def manager(self):
        """Create a KeychainManager instance for testing."""
        return KeychainManager()

    def test_set_password_success(self, manager):
        """Test successful password storage."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result):
            result = manager.set_password("sk-new-api-key")
            assert result is True

    def test_set_password_empty_string_deletes(self, manager):
        """Test set_password with empty string calls delete."""
        with patch.object(manager, "delete_password", return_value=True) as mock_delete:
            result = manager.set_password("")
            assert result is True
            mock_delete.assert_called_once()

    def test_set_password_whitespace_only_deletes(self, manager):
        """Test set_password with whitespace only is not treated as empty."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result):
            # Whitespace-only password is stored as-is (only empty string triggers delete)
            result = manager.set_password("   ")
            assert result is True

    def test_set_password_deletes_existing_first(self, manager):
        """Test set_password deletes existing password before adding new one."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result):
            with patch.object(manager, "delete_password", return_value=True) as mock_delete:
                manager.set_password("sk-test-key")
                mock_delete.assert_called_once()

    def test_set_password_command_args(self, manager):
        """Test set_password calls security with correct arguments."""
        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            with patch.object(manager, "delete_password", return_value=True):
                manager.set_password("sk-test-key")

                # Check the add command
                calls = mock_run.call_args_list
                add_call = [c for c in calls if "add-generic-password" in c[0][0]][0]
                cmd = add_call[0][0]
                assert cmd[0] == "security"
                assert cmd[1] == "add-generic-password"
                assert "-s" in cmd
                assert "-a" in cmd
                assert "-w" in cmd
                assert "-U" in cmd
                assert "sk-test-key" in cmd

    def test_set_password_stderr_error(self, manager):
        """Test set_password raises KeychainError on stderr error."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "security: SecKeychainItemCreate: Access denied"

        with patch("subprocess.run", return_value=mock_result):
            with patch.object(manager, "delete_password", return_value=True):
                with pytest.raises(KeychainError) as exc_info:
                    manager.set_password("sk-test-key")
                assert "Failed to store in keychain" in str(exc_info.value)

    def test_set_password_unknown_error(self, manager):
        """Test set_password raises KeychainError on unknown error."""
        mock_result = MagicMock()
        mock_result.returncode = 2
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result):
            with patch.object(manager, "delete_password", return_value=True):
                with pytest.raises(KeychainError) as exc_info:
                    manager.set_password("sk-test-key")
                assert "Unknown keychain error" in str(exc_info.value)

    def test_set_password_security_not_found(self, manager):
        """Test set_password raises KeychainError when security command not found."""
        with patch.object(manager, "delete_password", return_value=True):
            with patch("subprocess.run", side_effect=FileNotFoundError):
                with pytest.raises(KeychainError) as exc_info:
                    manager.set_password("sk-test-key")
                assert "security command not found" in str(exc_info.value)

    def test_set_password_timeout(self, manager):
        """Test set_password raises KeychainError on timeout."""
        import subprocess
        with patch.object(manager, "delete_password", return_value=True):
            with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("security", 30)):
                with pytest.raises(KeychainError) as exc_info:
                    manager.set_password("sk-test-key")
                assert "timed out" in str(exc_info.value)


class TestKeychainManagerDeletePassword:
    """Tests for KeychainManager.delete_password method."""

    @pytest.fixture
    def manager(self):
        """Create a KeychainManager instance for testing."""
        return KeychainManager()

    def test_delete_password_success(self, manager):
        """Test successful password deletion."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result):
            result = manager.delete_password()
            assert result is True

    def test_delete_password_not_found_exit_code_44(self, manager):
        """Test delete_password returns True when exit code is 44 (not found)."""
        mock_result = MagicMock()
        mock_result.returncode = 44
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result):
            result = manager.delete_password()
            assert result is True

    def test_delete_password_not_found_stderr_message(self, manager):
        """Test delete_password returns True when stderr indicates not found."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "security: SecKeychainItemDelete: The specified item could not be found in the keychain"

        with patch("subprocess.run", return_value=mock_result):
            result = manager.delete_password()
            assert result is True

    def test_delete_password_stderr_error(self, manager):
        """Test delete_password raises KeychainError on stderr error."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "security: SecKeychainItemDelete: Access denied"

        with patch("subprocess.run", return_value=mock_result):
            with pytest.raises(KeychainError) as exc_info:
                manager.delete_password()
            assert "Failed to delete from keychain" in str(exc_info.value)

    def test_delete_password_unknown_error(self, manager):
        """Test delete_password raises KeychainError on unknown error."""
        mock_result = MagicMock()
        mock_result.returncode = 2
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result):
            with pytest.raises(KeychainError) as exc_info:
                manager.delete_password()
            assert "Unknown keychain error" in str(exc_info.value)

    def test_delete_password_security_not_found(self, manager):
        """Test delete_password raises KeychainError when security command not found."""
        with patch("subprocess.run", side_effect=FileNotFoundError):
            with pytest.raises(KeychainError) as exc_info:
                manager.delete_password()
            assert "security command not found" in str(exc_info.value)

    def test_delete_password_timeout(self, manager):
        """Test delete_password raises KeychainError on timeout."""
        import subprocess
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("security", 30)):
            with pytest.raises(KeychainError) as exc_info:
                manager.delete_password()
            assert "timed out" in str(exc_info.value)

    def test_delete_password_command_args(self, manager):
        """Test delete_password calls security with correct arguments."""
        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            manager.delete_password()

            call_args = mock_run.call_args
            cmd = call_args[0][0]
            assert cmd[0] == "security"
            assert cmd[1] == "delete-generic-password"
            assert "-s" in cmd
            assert "-a" in cmd
            assert KEYCHAIN_SERVICE in cmd
            assert KEYCHAIN_ACCOUNT in cmd


class TestKeychainManagerHasPassword:
    """Tests for KeychainManager.has_password method."""

    @pytest.fixture
    def manager(self):
        """Create a KeychainManager instance for testing."""
        return KeychainManager()

    def test_has_password_true(self, manager):
        """Test has_password returns True when password exists."""
        with patch.object(manager, "get_password", return_value="sk-test-key"):
            assert manager.has_password() is True

    def test_has_password_false_when_none(self, manager):
        """Test has_password returns False when password is None."""
        with patch.object(manager, "get_password", return_value=None):
            assert manager.has_password() is False

    def test_has_password_false_when_empty(self, manager):
        """Test has_password returns False when password is empty string."""
        with patch.object(manager, "get_password", return_value=""):
            assert manager.has_password() is False

    def test_has_password_on_keychain_error(self, manager):
        """Test has_password returns False on KeychainError."""
        with patch.object(manager, "get_password", side_effect=KeychainError("test error")):
            assert manager.has_password() is False

    def test_has_password_with_length_check(self, manager):
        """Test has_password checks password length."""
        # Non-empty password
        with patch.object(manager, "get_password", return_value="a"):
            assert manager.has_password() is True

        # Empty password
        with patch.object(manager, "get_password", return_value=""):
            assert manager.has_password() is False
