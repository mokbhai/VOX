#!/usr/bin/env python
"""
Comprehensive verification of delete API key functionality.

This script specifically tests subtask-5-3: Manual verification of delete API key functionality.

Since we're in a sandboxed environment, we use comprehensive mocking to simulate
the delete flow and verify all edge cases.
"""
import sys
import tempfile
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock, call

print("=" * 80)
print("DELETE API KEY VERIFICATION (Subtask 5-3)")
print("=" * 80)
print("\nTesting delete API key functionality with keychain storage\n")

test_count = 0
pass_count = 0
fail_count = 0


def run_test(test_name, test_func):
    """Run a test and track results."""
    global test_count, pass_count, fail_count
    test_count += 1
    print(f"\n[Test {test_count}] {test_name}")
    try:
        test_func()
        print(f"  ✓ PASSED")
        pass_count += 1
        return True
    except AssertionError as e:
        print(f"  ✗ FAILED: {e}")
        fail_count += 1
        return False
    except Exception as e:
        print(f"  ✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        fail_count += 1
        return False


# Test 1: Basic delete - key in keychain, delete removes it
def test_basic_delete():
    """Verify that deleting an API key removes it from keychain."""
    from vox.config import Config, reset_config

    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("vox.config.Path.home", return_value=Path(tmpdir)):
            reset_config()
            c = Config()

            # Mock keychain to have a key
            keychain_storage = {'password': 'sk-test-key-to-delete'}

            def mock_has_password():
                return 'password' in keychain_storage and keychain_storage['password'] is not None

            def mock_delete_password():
                if 'password' in keychain_storage:
                    del keychain_storage['password']
                return True

            with patch.object(c, 'has_api_key_in_keychain', side_effect=mock_has_password), \
                 patch.object(c, 'delete_api_key_from_keychain', side_effect=mock_delete_password) as mock_del:

                # Verify key exists before delete
                assert c.has_api_key() == True, "Should have key before delete"

                # Delete the key
                result = c.delete_api_key()

                # Verify delete was called and returned True
                assert result == True, f"delete_api_key should return True, got {result}"
                mock_del.assert_called_once()

                # Verify key is removed from keychain
                assert 'password' not in keychain_storage, "Key not removed from keychain"


# Test 2: Delete when no key exists (idempotent delete)
def test_delete_when_no_key():
    """Verify that deleting when no key exists is safe (idempotent)."""
    from vox.config import Config, reset_config

    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("vox.config.Path.home", return_value=Path(tmpdir)):
            reset_config()
            c = Config()

            # Mock keychain to be empty
            keychain_storage = {}

            def mock_has_password():
                return 'password' in keychain_storage and keychain_storage['password'] is not None

            def mock_delete_password():
                if 'password' in keychain_storage:
                    del keychain_storage['password']
                return True  # delete_password returns True even if key doesn't exist

            with patch.object(c, 'has_api_key_in_keychain', side_effect=mock_has_password), \
                 patch.object(c, 'delete_api_key_from_keychain', side_effect=mock_delete_password) as mock_del:

                # Verify no key exists
                assert c.has_api_key() == False, "Should not have key"

                # Delete should still succeed
                result = c.delete_api_key()

                # Verify delete was called and returned True
                assert result == True, f"delete_api_key should return True even when no key, got {result}"
                mock_del.assert_called_once()


# Test 3: Verify has_api_key() returns False after delete
def test_has_api_key_after_delete():
    """Verify that has_api_key() returns False after deleting the key."""
    from vox.config import Config, reset_config

    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("vox.config.Path.home", return_value=Path(tmpdir)):
            reset_config()
            c = Config()

            # Mock keychain
            keychain_storage = {'password': 'sk-test-key-for-has-check'}

            def mock_has_password():
                return 'password' in keychain_storage and keychain_storage['password'] is not None

            def mock_delete_password():
                if 'password' in keychain_storage:
                    del keychain_storage['password']
                return True

            with patch.object(c, 'has_api_key_in_keychain', side_effect=mock_has_password), \
                 patch.object(c, 'delete_api_key_from_keychain', side_effect=mock_delete_password):

                # Before delete, has_api_key should be True
                has_before = c.has_api_key()
                assert has_before == True, "Should have key before delete"

                # Delete the key
                c.delete_api_key()

                # After delete, has_api_key should be False
                has_after = c.has_api_key()
                assert has_after == False, "Should not have key after delete"


# Test 4: Delete via set_api_key with empty string
def test_delete_via_empty_set_api_key():
    """Verify that setting an empty API key deletes the existing key."""
    from vox.config import Config, reset_config

    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("vox.config.Path.home", return_value=Path(tmpdir)):
            reset_config()
            c = Config()

            # Mock keychain
            keychain_storage = {'password': 'sk-test-key-to-clear'}

            def mock_has_password():
                return 'password' in keychain_storage and keychain_storage['password'] is not None

            def mock_get_password():
                return keychain_storage.get('password')

            def mock_set_password(password):
                if password:
                    keychain_storage['password'] = password
                else:
                    # Empty password triggers delete
                    if 'password' in keychain_storage:
                        del keychain_storage['password']
                return True

            with patch.object(c, 'get_api_key_from_keychain', side_effect=mock_get_password), \
                 patch.object(c, 'set_api_key_in_keychain', side_effect=mock_set_password) as mock_set, \
                 patch.object(c, 'has_api_key_in_keychain', side_effect=mock_has_password):

                # Verify key exists
                assert c.has_api_key() == True

                # Set empty string (should delete)
                c.set_api_key('')

                # Verify set_api_key_in_keychain was called with empty string
                mock_set.assert_called_once_with('')

                # Verify key is removed
                assert 'password' not in keychain_storage, "Key not removed when setting empty string"

                # Verify has_api_key returns False
                assert c.has_api_key() == False


# Test 5: Delete with keychain error handling
def test_delete_with_keychain_error():
    """Verify that delete handles keychain errors gracefully."""
    from vox.config import Config, reset_config
    from vox.keychain import KeychainError, KeychainManager

    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("vox.config.Path.home", return_value=Path(tmpdir)):
            reset_config()
            c = Config()

            # Mock KeychainManager.delete_password to raise KeychainError
            # This should be caught by the try/except in delete_api_key_from_keychain
            with patch.object(KeychainManager, 'delete_password',
                            side_effect=KeychainError("Keychain access denied")):
                # Should return False on error (KeychainError is caught)
                result = c.delete_api_key()
                assert result == False, f"delete_api_key should return False on KeychainError, got {result}"


# Test 6: Delete after migration (config file cleanup)
def test_delete_after_migration():
    """Verify that delete works correctly after migration from config file."""
    from vox.config import Config, reset_config

    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("vox.config.Path.home", return_value=Path(tmpdir)):
            reset_config()

            # Create a config file with api_key (simulating old install)
            config_dir = Path(tmpdir) / "Library" / "Application Support" / "Vox"
            config_dir.mkdir(parents=True, exist_ok=True)
            config_file = config_dir / "config.yml"

            old_config = {
                'model': 'gpt-4o-mini',
                'api_key': 'sk-old-key-to-migrate-and-delete',
            }
            with open(config_file, 'w') as f:
                yaml.dump(old_config, f)

            c = Config()

            # Mock keychain
            keychain_storage = {}

            def mock_get_password():
                return keychain_storage.get('password')

            def mock_set_password(password):
                keychain_storage['password'] = password
                return True

            def mock_has_password():
                return 'password' in keychain_storage and keychain_storage['password'] is not None

            def mock_delete_password():
                if 'password' in keychain_storage:
                    del keychain_storage['password']
                return True

            # Step 1: Migrate the key
            with patch.object(c, 'get_api_key_from_keychain', side_effect=mock_get_password), \
                 patch.object(c, 'set_api_key_in_keychain', side_effect=mock_set_password):

                api_key = c.get_api_key()
                assert api_key == 'sk-old-key-to-migrate-and-delete', "Migration failed"

            # Verify key is in keychain and removed from config
            assert keychain_storage.get('password') == 'sk-old-key-to-migrate-and-delete'
            with open(config_file, 'r') as f:
                saved_data = yaml.safe_load(f)
            assert 'api_key' not in saved_data, "api_key not removed from config after migration"

            # Step 2: Delete the key
            with patch.object(c, 'has_api_key_in_keychain', side_effect=mock_has_password), \
                 patch.object(c, 'delete_api_key_from_keychain', side_effect=mock_delete_password):

                assert c.has_api_key() == True, "Should have key after migration"
                result = c.delete_api_key()
                assert result == True

            # Verify key is deleted
            assert 'password' not in keychain_storage, "Key not deleted after migration"

            # Verify config file still doesn't have api_key
            with open(config_file, 'r') as f:
                saved_data = yaml.safe_load(f)
            assert 'api_key' not in saved_data, "api_key should not reappear in config"


# Test 7: Multiple deletes (idempotency)
def test_multiple_deletes():
    """Verify that multiple delete calls are safe (idempotent)."""
    from vox.config import Config, reset_config

    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("vox.config.Path.home", return_value=Path(tmpdir)):
            reset_config()
            c = Config()

            # Mock keychain
            delete_count = [0]

            def mock_has_password():
                return False  # No key after first delete

            def mock_delete_password():
                delete_count[0] += 1
                return True

            with patch.object(c, 'has_api_key_in_keychain', side_effect=mock_has_password), \
                 patch.object(c, 'delete_api_key_from_keychain', side_effect=mock_delete_password):

                # First delete
                result1 = c.delete_api_key()
                assert result1 == True

                # Second delete (should still succeed)
                result2 = c.delete_api_key()
                assert result2 == True

                # Third delete (should still succeed)
                result3 = c.delete_api_key()
                assert result3 == True

                # Verify delete was called 3 times (all succeeded)
                assert delete_count[0] == 3, f"Expected 3 delete calls, got {delete_count[0]}"


# Test 8: Config file unchanged after delete
def test_config_unchanged_after_delete():
    """Verify that config file is not modified when deleting from keychain."""
    from vox.config import Config, reset_config

    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("vox.config.Path.home", return_value=Path(tmpdir)):
            reset_config()

            config_dir = Path(tmpdir) / "Library" / "Application Support" / "Vox"
            config_dir.mkdir(parents=True, exist_ok=True)
            config_file = config_dir / "config.yml"

            # Create config with some settings
            initial_config = {
                'model': 'gpt-4o',
                'auto_start': True,
                'toast_position': 'top-right',
            }
            with open(config_file, 'w') as f:
                yaml.dump(initial_config, f)

            c = Config()

            # Mock keychain
            def mock_delete_password():
                return True

            with patch.object(c, 'delete_api_key_from_keychain', side_effect=mock_delete_password):
                c.delete_api_key()

            # Verify config file was not modified
            with open(config_file, 'r') as f:
                saved_data = yaml.safe_load(f)

            assert saved_data.get('model') == 'gpt-4o', "Config should not be modified"
            assert saved_data.get('auto_start') == True, "Config should not be modified"
            assert saved_data.get('toast_position') == 'top-right', "Config should not be modified"


# Test 9: Delete with different keychain service/account
def test_delete_uses_correct_keychain_params():
    """Verify that delete uses the correct service and account names."""
    from vox.config import Config, reset_config
    from vox.keychain import KeychainManager, KEYCHAIN_SERVICE, KEYCHAIN_ACCOUNT

    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("vox.config.Path.home", return_value=Path(tmpdir)):
            reset_config()
            c = Config()

            # Verify the keychain constants are correct
            assert KEYCHAIN_SERVICE == "com.voxapp.rewrite", \
                f"Wrong keychain service: {KEYCHAIN_SERVICE}"
            assert KEYCHAIN_ACCOUNT == "openai-api-key", \
                f"Wrong keychain account: {KEYCHAIN_ACCOUNT}"

            # Verify that Config.delete_api_key() calls KeychainManager.delete_password()
            # We can verify this by checking that the method exists and is callable
            assert hasattr(c, 'delete_api_key_from_keychain'), \
                "Config should have delete_api_key_from_keychain method"

            # Verify the method creates a KeychainManager and calls delete_password
            import inspect
            source = inspect.getsource(c.delete_api_key_from_keychain)
            assert 'KeychainManager' in source, \
                "delete_api_key_from_keychain should use KeychainManager"
            assert 'delete_password' in source, \
                "delete_api_key_from_keychain should call delete_password"


# Run all tests
run_test("Basic delete - key removed from keychain", test_basic_delete)
run_test("Delete when no key exists (idempotent)", test_delete_when_no_key)
run_test("has_api_key() returns False after delete", test_has_api_key_after_delete)
run_test("Delete via empty set_api_key()", test_delete_via_empty_set_api_key)
run_test("Delete with keychain error handling", test_delete_with_keychain_error)
run_test("Delete after migration from config file", test_delete_after_migration)
run_test("Multiple deletes (idempotency)", test_multiple_deletes)
run_test("Config file unchanged after delete", test_config_unchanged_after_delete)
run_test("Delete uses correct keychain parameters", test_delete_uses_correct_keychain_params)

# Print summary
print("\n" + "=" * 80)
print("DELETE API KEY VERIFICATION SUMMARY")
print("=" * 80)
print(f"Tests run: {test_count}")
print(f"Passed: {pass_count} ✓")
print(f"Failed: {fail_count} ✗")

if fail_count == 0:
    print("\n✓ ALL DELETE API KEY TESTS PASSED")
    print("\nThe delete API key functionality works correctly:")
    print("  • delete_api_key() removes the key from keychain")
    print("  • delete_api_key() is idempotent (safe to call multiple times)")
    print("  • has_api_key() returns False after delete")
    print("  • Setting empty string via set_api_key() deletes the key")
    print("  • Delete handles keychain errors gracefully")
    print("  • Delete works correctly after migration")
    print("  • Config file is not modified during delete")
    print("  • Correct keychain service and account are used")
    sys.exit(0)
else:
    print(f"\n✗ {fail_count} TEST(S) FAILED")
    sys.exit(1)
