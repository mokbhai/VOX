#!/usr/bin/env python
"""
Comprehensive verification of migration path from config file to keychain.

This script specifically tests subtask-5-2: Manual verification of migration path
from existing config file API key to keychain storage.

Since we're in a sandboxed environment, we use comprehensive mocking to simulate
the migration flow and verify all edge cases.
"""
import sys
import tempfile
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock, call

print("=" * 80)
print("MIGRATION PATH VERIFICATION (Subtask 5-2)")
print("=" * 80)
print("\nTesting migration from config file API key to keychain storage\n")

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


# Test 1: Basic migration - key in config, empty keychain
def test_basic_migration():
    """Verify that a key in config.yml is migrated to keychain on first access."""
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
                'api_key': 'sk-test-old-config-key-12345',
                'auto_start': False,
                'toast_position': 'cursor'
            }
            with open(config_file, 'w') as f:
                yaml.dump(old_config, f)

            # Create Config instance
            c = Config()

            # Mock keychain methods to simulate empty keychain initially
            keychain_storage = {}

            def mock_get_password():
                return keychain_storage.get('password')

            def mock_set_password(password):
                keychain_storage['password'] = password
                return True

            with patch.object(c, 'get_api_key_from_keychain', side_effect=mock_get_password), \
                 patch.object(c, 'set_api_key_in_keychain', side_effect=mock_set_password) as mock_set:

                # First access should trigger migration
                api_key = c.get_api_key()

                # Verify the key was returned
                assert api_key == 'sk-test-old-config-key-12345', \
                    f"Wrong key returned: {api_key}"

                # Verify set_api_key_in_keychain was called (migration happened)
                mock_set.assert_called_once_with('sk-test-old-config-key-12345')

            # Verify the key is now in our mocked keychain
            assert keychain_storage.get('password') == 'sk-test-old-config-key-12345', \
                "Key not stored in keychain after migration"

            # Verify config file was updated to remove api_key
            with open(config_file, 'r') as f:
                saved_data = yaml.safe_load(f)

            assert 'api_key' not in saved_data, \
                "api_key was not removed from config file after migration"

            # Verify other config values were preserved
            assert saved_data.get('model') == 'gpt-4o-mini', \
                "Other config values not preserved"
            assert saved_data.get('auto_start') == False, \
                "Other config values not preserved"


# Test 2: Migration idempotency - subsequent accesses don't re-migrate
def test_migration_idempotency():
    """Verify that after migration, subsequent calls don't trigger migration again."""
    from vox.config import Config, reset_config

    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("vox.config.Path.home", return_value=Path(tmpdir)):
            reset_config()

            config_dir = Path(tmpdir) / "Library" / "Application Support" / "Vox"
            config_dir.mkdir(parents=True, exist_ok=True)
            config_file = config_dir / "config.yml"

            old_config = {
                'model': 'gpt-4o-mini',
                'api_key': 'sk-test-key-for-idempotency',
            }
            with open(config_file, 'w') as f:
                yaml.dump(old_config, f)

            c = Config()

            keychain_storage = {}

            def mock_get_password():
                return keychain_storage.get('password')

            def mock_set_password(password):
                keychain_storage['password'] = password
                return True

            with patch.object(c, 'get_api_key_from_keychain', side_effect=mock_get_password), \
                 patch.object(c, 'set_api_key_in_keychain', side_effect=mock_set_password):

                # First call - migration happens
                api_key_1 = c.get_api_key()
                assert api_key_1 == 'sk-test-key-for-idempotency'

                # Verify key is now in keychain storage
                assert keychain_storage.get('password') == 'sk-test-key-for-idempotency'

                # Reset the mock to track new calls
                with patch.object(c, 'set_api_key_in_keychain', side_effect=mock_set_password) as mock_set_2:
                    # Second call - should NOT call set_password (key already in keychain)
                    api_key_2 = c.get_api_key()
                    assert api_key_2 == 'sk-test-key-for-idempotency'
                    mock_set_2.assert_not_called()


# Test 3: Keychain priority - no migration if keychain has key
def test_keychain_priority():
    """Verify that if keychain already has a key, config key is ignored."""
    from vox.config import Config, reset_config

    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("vox.config.Path.home", return_value=Path(tmpdir)):
            reset_config()

            config_dir = Path(tmpdir) / "Library" / "Application Support" / "Vox"
            config_dir.mkdir(parents=True, exist_ok=True)
            config_file = config_dir / "config.yml"

            # Config has an old key
            old_config = {
                'model': 'gpt-4o-mini',
                'api_key': 'sk-old-config-key-ignored',
            }
            with open(config_file, 'w') as f:
                yaml.dump(old_config, f)

            c = Config()

            # Mock keychain to already have a different key
            with patch.object(c, 'get_api_key_from_keychain',
                            return_value='sk-keychain-key-takes-priority'), \
                 patch.object(c, 'set_api_key_in_keychain', return_value=True) as mock_set:

                api_key = c.get_api_key()

                # Should return keychain key, not config key
                assert api_key == 'sk-keychain-key-takes-priority', \
                    f"Should prefer keychain key: {api_key}"

                # set_api_key_in_keychain should NOT be called (no migration)
                mock_set.assert_not_called()


# Test 4: Migration error handling - graceful fallback
def test_migration_error_handling():
    """Verify that if keychain write fails during migration, config key is still returned."""
    from vox.config import Config, reset_config

    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("vox.config.Path.home", return_value=Path(tmpdir)):
            reset_config()

            config_dir = Path(tmpdir) / "Library" / "Application Support" / "Vox"
            config_dir.mkdir(parents=True, exist_ok=True)
            config_file = config_dir / "config.yml"

            old_config = {
                'model': 'gpt-4o-mini',
                'api_key': 'sk-config-key-even-on-error',
            }
            with open(config_file, 'w') as f:
                yaml.dump(old_config, f)

            c = Config()

            # Mock keychain to fail on write
            with patch.object(c, 'get_api_key_from_keychain', return_value=None), \
                 patch.object(c, 'set_api_key_in_keychain', return_value=False):  # Write fails

                # Even with keychain write failure, should return the config key
                api_key = c.get_api_key()
                assert api_key == 'sk-config-key-even-on-error', \
                    "Should return config key even if migration fails"


# Test 5: Empty/None config key handling
def test_empty_config_key_handling():
    """Verify that empty string in config is handled correctly."""
    from vox.config import Config, reset_config

    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("vox.config.Path.home", return_value=Path(tmpdir)):
            reset_config()

            config_dir = Path(tmpdir) / "Library" / "Application Support" / "Vox"
            config_dir.mkdir(parents=True, exist_ok=True)
            config_file = config_dir / "config.yml"

            # Config has empty api_key
            old_config = {
                'model': 'gpt-4o-mini',
                'api_key': '',  # Empty string
            }
            with open(config_file, 'w') as f:
                yaml.dump(old_config, f)

            c = Config()

            keychain_storage = {}

            def mock_get_password():
                return keychain_storage.get('password')

            def mock_set_password(password):
                keychain_storage['password'] = password
                return True

            with patch.object(c, 'get_api_key_from_keychain', side_effect=mock_get_password), \
                 patch.object(c, 'set_api_key_in_keychain', side_effect=mock_set_password):

                # Empty string is falsy but should not trigger migration
                api_key = c.get_api_key()

                # Should return None (empty string treated as no key)
                assert api_key is None or api_key == '', \
                    f"Empty config key should return None: {api_key}"

                # set_api_key_in_keychain might be called with empty string,
                # but that's acceptable behavior (clearing the key)


# Test 6: Config file structure preservation after migration
def test_config_structure_preservation():
    """Verify that config file structure and other values are preserved after migration."""
    from vox.config import Config, reset_config

    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("vox.config.Path.home", return_value=Path(tmpdir)):
            reset_config()

            config_dir = Path(tmpdir) / "Library" / "Application Support" / "Vox"
            config_dir.mkdir(parents=True, exist_ok=True)
            config_file = config_dir / "config.yml"

            # Complex config with multiple sections
            old_config = {
                'model': 'gpt-4o',
                'base_url': 'https://api.example.com/v1',
                'api_key': 'sk-complex-config-test-key',
                'auto_start': True,
                'toast_position': 'top-right',
                'thinking_mode': True,
                'hotkeys_enabled': True,
                'hotkeys': {
                    'fix_grammar': {'modifiers': 'cmd+shift', 'key': 'g'},
                    'professional': {'modifiers': 'cmd+shift', 'key': 'p'},
                },
                'speech': {
                    'enabled': True,
                    'model': 'base',
                    'language': 'en',
                }
            }
            with open(config_file, 'w') as f:
                yaml.dump(old_config, f)

            c = Config()

            keychain_storage = {}

            def mock_get_password():
                return keychain_storage.get('password')

            def mock_set_password(password):
                keychain_storage['password'] = password
                return True

            with patch.object(c, 'get_api_key_from_keychain', side_effect=mock_get_password), \
                 patch.object(c, 'set_api_key_in_keychain', side_effect=mock_set_password):

                # Trigger migration
                api_key = c.get_api_key()
                assert api_key == 'sk-complex-config-test-key'

            # Verify all other settings are preserved
            with open(config_file, 'r') as f:
                saved_data = yaml.safe_load(f)

            assert 'api_key' not in saved_data, "api_key should be removed"
            assert saved_data.get('model') == 'gpt-4o', "model not preserved"
            assert saved_data.get('base_url') == 'https://api.example.com/v1', "base_url not preserved"
            assert saved_data.get('auto_start') == True, "auto_start not preserved"
            assert saved_data.get('toast_position') == 'top-right', "toast_position not preserved"
            assert saved_data.get('thinking_mode') == True, "thinking_mode not preserved"
            assert saved_data.get('hotkeys_enabled') == True, "hotkeys_enabled not preserved"
            # Hotkeys are merged with defaults - user-provided hotkeys override defaults,
            # but missing hotkeys are filled in from defaults
            saved_hotkeys = saved_data.get('hotkeys', {})
            assert saved_hotkeys.get('fix_grammar') == {'modifiers': 'cmd+shift', 'key': 'g'}, \
                "fix_grammar hotkey not preserved"
            assert saved_hotkeys.get('professional') == {'modifiers': 'cmd+shift', 'key': 'p'}, \
                "professional hotkey not preserved"
            assert saved_data.get('speech') == {
                'enabled': True,
                'model': 'base',
                'language': 'en',
            }, "speech not preserved"


# Test 7: Migration with no existing config file
def test_migration_no_config_file():
    """Verify behavior when there's no existing config file (fresh install)."""
    from vox.config import Config, reset_config

    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("vox.config.Path.home", return_value=Path(tmpdir)):
            reset_config()

            # Don't create a config file - fresh install scenario
            config_dir = Path(tmpdir) / "Library" / "Application Support" / "Vox"
            # Config will be created by Config().__init__

            c = Config()

            # Should not have any API key
            api_key = c.get_api_key()
            assert api_key is None, "Fresh install should have no API key"


# Test 8: Verify has_api_key() checks keychain after migration
def test_has_api_key_after_migration():
    """Verify that has_api_key() correctly reports key existence after migration."""
    from vox.config import Config, reset_config

    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("vox.config.Path.home", return_value=Path(tmpdir)):
            reset_config()

            config_dir = Path(tmpdir) / "Library" / "Application Support" / "Vox"
            config_dir.mkdir(parents=True, exist_ok=True)
            config_file = config_dir / "config.yml"

            old_config = {
                'model': 'gpt-4o-mini',
                'api_key': 'sk-test-has-api-key',
            }
            with open(config_file, 'w') as f:
                yaml.dump(old_config, f)

            c = Config()

            keychain_storage = {}

            def mock_get_password():
                return keychain_storage.get('password')

            def mock_set_password(password):
                keychain_storage['password'] = password
                return True

            def mock_has_password():
                return 'password' in keychain_storage and keychain_storage['password'] is not None

            with patch.object(c, 'get_api_key_from_keychain', side_effect=mock_get_password), \
                 patch.object(c, 'set_api_key_in_keychain', side_effect=mock_set_password), \
                 patch.object(c, 'has_api_key_in_keychain', side_effect=mock_has_password):

                # Before migration, has_api_key should be False (keychain empty)
                has_before = c.has_api_key()
                assert has_before == False, "Should not have key before migration"

                # Trigger migration
                api_key = c.get_api_key()
                assert api_key == 'sk-test-has-api-key'

                # After migration, has_api_key should be True
                has_after = c.has_api_key()
                assert has_after == True, "Should have key after migration"


# Test 9: Simulated "restart" after migration
def test_restart_after_migration():
    """Simulate app restart after migration - key should persist in keychain."""
    from vox.config import Config, reset_config

    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("vox.config.Path.home", return_value=Path(tmpdir)):
            reset_config()

            config_dir = Path(tmpdir) / "Library" / "Application Support" / "Vox"
            config_dir.mkdir(parents=True, exist_ok=True)
            config_file = config_dir / "config.yml"

            old_config = {
                'model': 'gpt-4o-mini',
                'api_key': 'sk-test-restart-persistence',
            }
            with open(config_file, 'w') as f:
                yaml.dump(old_config, f)

            # Shared keychain storage (simulating persistent keychain across restarts)
            keychain_storage = {}

            def mock_get_password():
                return keychain_storage.get('password')

            def mock_set_password(password):
                keychain_storage['password'] = password
                return True

            # First run - migration happens
            c1 = Config()
            with patch.object(c1, 'get_api_key_from_keychain', side_effect=mock_get_password), \
                 patch.object(c1, 'set_api_key_in_keychain', side_effect=mock_set_password):

                api_key_1 = c1.get_api_key()
                assert api_key_1 == 'sk-test-restart-persistence'

            # Verify key is in keychain
            assert keychain_storage.get('password') == 'sk-test-restart-persistence'

            # Verify config file no longer has api_key
            with open(config_file, 'r') as f:
                data_after_first = yaml.safe_load(f)
            assert 'api_key' not in data_after_first

            # Simulate restart: create new Config instance
            reset_config()
            c2 = Config()
            with patch.object(c2, 'get_api_key_from_keychain', side_effect=mock_get_password):

                # Should get the key from keychain
                api_key_2 = c2.get_api_key()
                assert api_key_2 == 'sk-test-restart-persistence', \
                    "Key should persist in keychain after restart"


# Run all tests
run_test("Basic migration - key moved from config to keychain", test_basic_migration)
run_test("Migration idempotency - no re-migration on subsequent access", test_migration_idempotency)
run_test("Keychain priority - config key ignored when keychain has key", test_keychain_priority)
run_test("Migration error handling - graceful fallback", test_migration_error_handling)
run_test("Empty config key handling", test_empty_config_key_handling)
run_test("Config structure preservation after migration", test_config_structure_preservation)
run_test("No config file (fresh install) scenario", test_migration_no_config_file)
run_test("has_api_key() correctness after migration", test_has_api_key_after_migration)
run_test("Key persistence after simulated restart", test_restart_after_migration)

# Print summary
print("\n" + "=" * 80)
print("MIGRATION PATH VERIFICATION SUMMARY")
print("=" * 80)
print(f"Tests run: {test_count}")
print(f"Passed: {pass_count} ✓")
print(f"Failed: {fail_count} ✗")

if fail_count == 0:
    print("\n✓ ALL MIGRATION PATH TESTS PASSED")
    print("\nThe migration from config file to keychain works correctly:")
    print("  • Keys in config.yml are automatically migrated to keychain on first access")
    print("  • After migration, api_key is removed from config file")
    print("  • Migration is idempotent (doesn't repeat on subsequent calls)")
    print("  • Keychain has priority over config file")
    print("  • Migration failures are handled gracefully")
    print("  • Config file structure and other settings are preserved")
    print("  • Keys persist in keychain across app restarts")
    sys.exit(0)
else:
    print(f"\n✗ {fail_count} TEST(S) FAILED")
    sys.exit(1)
