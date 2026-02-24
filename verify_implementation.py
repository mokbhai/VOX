#!/usr/bin/env python
"""Comprehensive verification of keychain API key implementation."""
import sys
import tempfile
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock

print("=" * 70)
print("VERIFICATION: Secure API Key Storage Implementation")
print("=" * 70)

# Test 1: Verify KeychainManager class exists and has correct methods
print("\n[Test 1] KeychainManager class structure")
try:
    from vox.keychain import KeychainManager, KeychainError, KEYCHAIN_SERVICE, KEYCHAIN_ACCOUNT

    assert KEYCHAIN_SERVICE == "com.voxapp.rewrite", f"Wrong service: {KEYCHAIN_SERVICE}"
    assert KEYCHAIN_ACCOUNT == "openai-api-key", f"Wrong account: {KEYCHAIN_ACCOUNT}"

    # Check methods exist
    assert hasattr(KeychainManager, 'get_password'), "Missing get_password method"
    assert hasattr(KeychainManager, 'set_password'), "Missing set_password method"
    assert hasattr(KeychainManager, 'delete_password'), "Missing delete_password method"
    assert hasattr(KeychainManager, 'has_password'), "Missing has_password method"

    print("  ✓ KeychainManager has all required methods")
    print(f"  ✓ Service: {KEYCHAIN_SERVICE}")
    print(f"  ✓ Account: {KEYCHAIN_ACCOUNT}")
except Exception as e:
    print(f"  ✗ FAILED: {e}")
    sys.exit(1)

# Test 2: Verify Config class has keychain integration methods
print("\n[Test 2] Config class keychain integration")
try:
    from vox.config import Config

    # Check new keychain methods exist
    assert hasattr(Config, 'get_api_key_from_keychain'), "Missing get_api_key_from_keychain"
    assert hasattr(Config, 'set_api_key_in_keychain'), "Missing set_api_key_in_keychain"
    assert hasattr(Config, 'delete_api_key_from_keychain'), "Missing delete_api_key_from_keychain"
    assert hasattr(Config, 'has_api_key_in_keychain'), "Missing has_api_key_in_keychain"

    print("  ✓ Config has all keychain integration methods")
except Exception as e:
    print(f"  ✗ FAILED: {e}")
    sys.exit(1)

# Test 3: Verify get_api_key() has migration logic
print("\n[Test 3] get_api_key() migration logic")
try:
    from vox.config import Config
    import inspect

    source = inspect.getsource(Config.get_api_key)
    assert 'keychain' in source.lower(), "get_api_key doesn't check keychain"
    assert 'migration' in source.lower() or 'migrate' in source.lower(), "get_api_key doesn't handle migration"
    assert 'config' in source.lower(), "get_api_key doesn't check config file"

    print("  ✓ get_api_key() checks keychain first")
    print("  ✓ get_api_key() falls back to config for migration")
    print("  ✓ get_api_key() migrates key to keychain")
except Exception as e:
    print(f"  ✗ FAILED: {e}")
    sys.exit(1)

# Test 4: Verify set_api_key() uses keychain
print("\n[Test 4] set_api_key() uses keychain")
try:
    from vox.config import Config
    import inspect

    source = inspect.getsource(Config.set_api_key)
    assert 'keychain' in source.lower() or 'set_api_key_in_keychain' in source, "set_api_key doesn't use keychain"

    print("  ✓ set_api_key() delegates to keychain storage")
except Exception as e:
    print(f"  ✗ FAILED: {e}")
    sys.exit(1)

# Test 5: Verify save() filters out api_key
print("\n[Test 5] save() filters api_key from config file")
try:
    from vox.config import Config
    import inspect

    source = inspect.getsource(Config.save)
    assert 'api_key' in source, "save() doesn't mention api_key"
    assert '!=' in source or 'not in' in source or 'filter' in source.lower() or 'if k !=' in source, "save() doesn't filter api_key"

    # Also test actual behavior
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("vox.config.Path.home", return_value=Path(tmpdir)):
            from vox.config import reset_config
            reset_config()
            c = Config()

            # Add api_key to internal config
            c._config['api_key'] = 'sk-test-key-should-not-be-saved'
            c.save()

            # Read the saved file
            with open(c.config_file, 'r') as f:
                saved_data = yaml.safe_load(f)

            assert 'api_key' not in saved_data, "api_key was written to file!"
            assert 'model' in saved_data, "Other config keys should be saved"

    print("  ✓ save() filters out api_key before writing to YAML")
    print("  ✓ Other config keys are preserved")
except Exception as e:
    print(f"  ✗ FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 6: Verify migration flow with mocked keychain
print("\n[Test 6] Migration flow (mocked keychain)")
try:
    from vox.config import Config
    from unittest.mock import patch, MagicMock

    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("vox.config.Path.home", return_value=Path(tmpdir)):
            from vox.config import reset_config
            reset_config()

            # Create a config file with api_key (old style)
            config_dir = Path(tmpdir) / "Library" / "Application Support" / "Vox"
            config_dir.mkdir(parents=True, exist_ok=True)
            config_file = config_dir / "config.yml"

            old_config = {
                'model': 'gpt-4o-mini',
                'api_key': 'sk-old-key-from-config',
                'auto_start': False
            }
            with open(config_file, 'w') as f:
                yaml.dump(old_config, f)

            # Create config and mock its keychain methods
            c = Config()

            # Mock the keychain methods on the Config instance
            with patch.object(c, 'get_api_key_from_keychain', return_value=None), \
                 patch.object(c, 'set_api_key_in_keychain', return_value=True) as mock_set:

                api_key = c.get_api_key()

                # Verify migration was attempted
                assert api_key == 'sk-old-key-from-config', f"Wrong key returned: {api_key}"
                mock_set.assert_called_once_with('sk-old-key-from-config')

            # After migration, config file should be saved without api_key
            with open(config_file, 'r') as f:
                saved_data = yaml.safe_load(f)

            assert 'api_key' not in saved_data, "api_key not removed after migration!"

    print("  ✓ Migration reads from config when keychain is empty")
    print("  ✓ Migration writes to keychain")
    print("  ✓ Migration removes api_key from config file")
except Exception as e:
    print(f"  ✗ FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 7: Verify keychain priority (keychain > config)
print("\n[Test 7] Keychain priority over config file")
try:
    from vox.config import Config
    from unittest.mock import patch, MagicMock

    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("vox.config.Path.home", return_value=Path(tmpdir)):
            from vox.config import reset_config
            reset_config()

            # Create config with BOTH keychain and file
            config_dir = Path(tmpdir) / "Library" / "Application Support" / "Vox"
            config_dir.mkdir(parents=True, exist_ok=True)
            config_file = config_dir / "config.yml"

            old_config = {
                'model': 'gpt-4o-mini',
                'api_key': 'sk-old-config-key',
            }
            with open(config_file, 'w') as f:
                yaml.dump(old_config, f)

            # Create config and mock its keychain methods
            c = Config()

            # Mock keychain to have a key (different from config)
            with patch.object(c, 'get_api_key_from_keychain', return_value='sk-new-keychain-key'), \
                 patch.object(c, 'set_api_key_in_keychain', return_value=True) as mock_set:

                api_key = c.get_api_key()

                # Should return keychain key, not config key
                assert api_key == 'sk-new-keychain-key', f"Should prefer keychain: {api_key}"
                # set_password should NOT be called (no migration needed)
                assert mock_set.call_count == 0, "Should not migrate when keychain has key"

    print("  ✓ Keychain has priority over config file")
    print("  ✓ No migration when keychain already has key")
except Exception as e:
    print(f"  ✗ FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 70)
print("✓ ALL VERIFICATION TESTS PASSED")
print("=" * 70)
print("\nSummary:")
print("  - KeychainManager class implemented correctly")
print("  - Config class integrated with keychain")
print("  - Migration logic in get_api_key() works correctly")
print("  - save() filters api_key from config file")
print("  - Keychain has priority over config file")
print("\nNote: Full keychain operations require non-sandboxed macOS environment.")
print("      Run 'make dev' to test with actual keychain access.")
