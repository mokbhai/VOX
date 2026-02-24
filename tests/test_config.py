"""Tests for the config module."""
import pytest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock
from vox.config import (
    Config,
    DEFAULT_CONFIG,
    DEFAULT_MODELS,
    get_config,
    reset_config,
)


class TestConfigConstants:
    """Tests for config module constants."""

    def test_default_models(self):
        """Test DEFAULT_MODELS contains expected models."""
        assert "gpt-4o" in DEFAULT_MODELS
        assert "gpt-4o-mini" in DEFAULT_MODELS
        assert "gpt-4-turbo" in DEFAULT_MODELS
        assert "gpt-3.5-turbo" in DEFAULT_MODELS

    def test_default_config_structure(self):
        """Test DEFAULT_CONFIG has all required keys."""
        assert "model" in DEFAULT_CONFIG
        assert "base_url" in DEFAULT_CONFIG
        assert "auto_start" in DEFAULT_CONFIG
        assert "toast_position" in DEFAULT_CONFIG
        assert "hotkeys_enabled" in DEFAULT_CONFIG
        assert "hotkeys" in DEFAULT_CONFIG

    def test_default_config_values(self):
        """Test DEFAULT_CONFIG has correct default values."""
        assert DEFAULT_CONFIG["model"] == "gpt-4o-mini"
        assert DEFAULT_CONFIG["base_url"] is None
        assert DEFAULT_CONFIG["auto_start"] is False
        assert DEFAULT_CONFIG["toast_position"] == "cursor"
        assert DEFAULT_CONFIG["thinking_mode"] is False
        assert DEFAULT_CONFIG["hotkeys_enabled"] is True

    def test_default_hotkeys_structure(self):
        """Test DEFAULT_CONFIG hotkeys has all modes."""
        hotkeys = DEFAULT_CONFIG["hotkeys"]
        assert "fix_grammar" in hotkeys
        assert "professional" in hotkeys
        assert "concise" in hotkeys
        assert "friendly" in hotkeys
        for mode_key, hk in hotkeys.items():
            assert "modifiers" in hk
            assert "key" in hk

    def test_default_hotkeys_values(self):
        """Test DEFAULT_CONFIG hotkeys have correct defaults."""
        hotkeys = DEFAULT_CONFIG["hotkeys"]
        assert hotkeys["fix_grammar"] == {"modifiers": "cmd+shift", "key": "g"}
        assert hotkeys["professional"] == {"modifiers": "cmd+shift", "key": "p"}
        assert hotkeys["concise"] == {"modifiers": "cmd+shift", "key": "c"}
        assert hotkeys["friendly"] == {"modifiers": "cmd+shift", "key": "f"}


class TestConfig:
    """Tests for Config class."""

    @pytest.fixture
    def temp_config(self):
        """Create a config instance with a temporary config directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("vox.config.Path.home", return_value=Path(tmpdir)):
                reset_config()
                config = Config()
                yield config

    def test_config_dir_path(self, temp_config):
        """Test config directory is correctly set."""
        assert temp_config.config_dir.name == "Vox"
        assert "Application Support" in str(temp_config.config_dir)

    def test_config_file_path(self, temp_config):
        """Test config file path is correctly set."""
        assert temp_config.config_file.name == "config.yml"
        assert temp_config.config_file.parent == temp_config.config_dir

    def test_load_default_values(self, temp_config):
        """Test that loading without a config file uses defaults."""
        assert temp_config.model == DEFAULT_CONFIG["model"]
        assert temp_config.base_url == DEFAULT_CONFIG["base_url"]
        assert temp_config.auto_start == DEFAULT_CONFIG["auto_start"]
        assert temp_config.toast_position == DEFAULT_CONFIG["toast_position"]

    def test_model_property(self, temp_config):
        """Test model property getter and setter."""
        assert temp_config.model == "gpt-4o-mini"
        temp_config.model = "gpt-4o"
        assert temp_config.model == "gpt-4o"

    def test_base_url_property(self, temp_config):
        """Test base_url property getter and setter."""
        assert temp_config.base_url is None

        temp_config.base_url = "https://api.example.com/v1"
        assert temp_config.base_url == "https://api.example.com/v1"

        temp_config.base_url = "  https://another.com/v1  "
        assert temp_config.base_url == "https://another.com/v1"

        temp_config.base_url = ""
        assert temp_config.base_url is None

        temp_config.base_url = "   "
        assert temp_config.base_url is None

    def test_auto_start_property(self, temp_config):
        """Test auto_start property getter and setter."""
        assert temp_config.auto_start is False
        temp_config.auto_start = True
        assert temp_config.auto_start is True

    def test_toast_position_property(self, temp_config):
        """Test toast_position property getter and setter."""
        assert temp_config.toast_position == "cursor"
        temp_config.toast_position = "top-right"
        assert temp_config.toast_position == "top-right"

    def test_save_and_load(self, temp_config):
        """Test that config is persisted to file."""
        temp_config.model = "gpt-4o"
        temp_config.auto_start = True
        temp_config.base_url = "https://custom.api"

        # Verify file was created and contains correct data
        assert temp_config.config_file.exists()
        with open(temp_config.config_file, "r") as f:
            data = yaml.safe_load(f)

        assert data["model"] == "gpt-4o"
        assert data["auto_start"] is True
        assert data["base_url"] == "https://custom.api"


class TestConfigThinkingMode:
    """Tests for thinking mode configuration."""

    @pytest.fixture
    def temp_config(self):
        """Create a config instance for thinking mode tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("vox.config.Path.home", return_value=Path(tmpdir)):
                reset_config()
                config = Config()
                yield config

    def test_thinking_mode_default(self, temp_config):
        """Test default thinking_mode value is False."""
        assert temp_config.thinking_mode is False

    def test_thinking_mode_getter_setter(self, temp_config):
        """Test thinking_mode getter and setter."""
        temp_config.thinking_mode = True
        assert temp_config.thinking_mode is True

        temp_config.thinking_mode = False
        assert temp_config.thinking_mode is False

    def test_thinking_mode_persistence(self, temp_config):
        """Test thinking_mode is persisted to file."""
        temp_config.thinking_mode = True

        # Verify file was created and contains correct data
        assert temp_config.config_file.exists()
        with open(temp_config.config_file, "r") as f:
            data = yaml.safe_load(f)

        assert data["thinking_mode"] is True

    def test_thinking_mode_load_from_file(self, temp_config):
        """Test thinking_mode is loaded from existing config file."""
        # Write config with thinking_mode enabled
        config_data = {
            "model": "gpt-4o-mini",
            "thinking_mode": True,
        }
        with open(temp_config.config_file, "w") as f:
            yaml.dump(config_data, f)

        # Reload config
        temp_config.load()

        assert temp_config.thinking_mode is True

    def test_thinking_mode_default_when_missing_in_file(self, temp_config):
        """Test thinking_mode defaults to False when not in config file."""
        # Write config without thinking_mode
        config_data = {"model": "gpt-4o-mini"}
        with open(temp_config.config_file, "w") as f:
            yaml.dump(config_data, f)

        # Reload config
        temp_config.load()

        assert temp_config.thinking_mode is False


class TestConfigApiKey:
    """Tests for API key management via keychain."""

    @pytest.fixture
    def temp_config(self):
        """Create a config instance for API key tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("vox.config.Path.home", return_value=Path(tmpdir)):
                reset_config()
                config = Config()
                yield config

    @pytest.fixture
    def mock_keychain(self):
        """Create a mock KeychainManager."""
        mock = MagicMock()
        mock.get_password.return_value = None
        mock.set_password.return_value = True
        mock.delete_password.return_value = True
        mock.has_password.return_value = False
        return mock

    def test_get_api_key_when_not_set(self, temp_config, mock_keychain):
        """Test getting API key when none is stored."""
        with patch("vox.config.KeychainManager", return_value=mock_keychain):
            assert temp_config.get_api_key() is None
            mock_keychain.get_password.assert_called_once()

    def test_get_api_key_when_set(self, temp_config, mock_keychain):
        """Test getting API key when one is stored in keychain."""
        mock_keychain.get_password.return_value = "sk-test123"
        with patch("vox.config.KeychainManager", return_value=mock_keychain):
            assert temp_config.get_api_key() == "sk-test123"
            mock_keychain.get_password.assert_called_once()

    def test_set_api_key(self, temp_config, mock_keychain):
        """Test setting API key stores in keychain."""
        with patch("vox.config.KeychainManager", return_value=mock_keychain):
            result = temp_config.set_api_key("sk-newkey")
            assert result is True
            mock_keychain.set_password.assert_called_once_with("sk-newkey")

    def test_delete_api_key(self, temp_config, mock_keychain):
        """Test deleting API key from keychain."""
        mock_keychain.has_password.return_value = True
        with patch("vox.config.KeychainManager", return_value=mock_keychain):
            temp_config.set_api_key("sk-test")
            assert temp_config.has_api_key() is True

            mock_keychain.reset_mock()
            mock_keychain.delete_password.return_value = True
            mock_keychain.has_password.return_value = False

            result = temp_config.delete_api_key()
            assert result is True
            mock_keychain.delete_password.assert_called_once()

    def test_delete_api_key_when_not_set(self, temp_config, mock_keychain):
        """Test deleting API key when none exists."""
        mock_keychain.delete_password.return_value = True
        with patch("vox.config.KeychainManager", return_value=mock_keychain):
            result = temp_config.delete_api_key()
            assert result is True  # Should succeed even if key doesn't exist
            mock_keychain.delete_password.assert_called_once()

    def test_has_api_key_true(self, temp_config, mock_keychain):
        """Test has_api_key returns True when key exists in keychain."""
        mock_keychain.has_password.return_value = True
        with patch("vox.config.KeychainManager", return_value=mock_keychain):
            assert temp_config.has_api_key() is True
            mock_keychain.has_password.assert_called_once()

    def test_has_api_key_false(self, temp_config, mock_keychain):
        """Test has_api_key returns False when key doesn't exist in keychain."""
        mock_keychain.has_password.return_value = False
        with patch("vox.config.KeychainManager", return_value=mock_keychain):
            assert temp_config.has_api_key() is False
            mock_keychain.has_password.assert_called_once()

    def test_has_api_key_empty_string(self, temp_config, mock_keychain):
        """Test has_api_key returns False for empty string (keychain deletes)."""
        # Setting empty string should store empty string (keychain handles delete internally)
        with patch("vox.config.KeychainManager", return_value=mock_keychain):
            temp_config.set_api_key("")
            # set_password is called with empty string
            mock_keychain.set_password.assert_called_once_with("")
            # has_password should return False for empty password
            mock_keychain.has_password.return_value = False
            assert temp_config.has_api_key() is False

    def test_get_api_key_migrates_from_config(self, temp_config, mock_keychain):
        """Test get_api_key migrates key from config file to keychain."""
        # Mock keychain to initially return None, then accept the migrated key
        mock_keychain.get_password.return_value = None
        mock_keychain.set_password.return_value = True

        with patch("vox.config.KeychainManager", return_value=mock_keychain):
            # Write API key to config file (old format) AFTER mocking
            config_data = {"api_key": "sk-old-config-key"}
            with open(temp_config.config_file, "w") as f:
                yaml.dump(config_data, f)

            # Reload config to pick up the file
            temp_config.load()

            # First call should migrate from config to keychain
            key = temp_config.get_api_key()
            assert key == "sk-old-config-key"
            mock_keychain.set_password.assert_called_once_with("sk-old-config-key")

            # Verify the key was removed from config file
            temp_config.load()
            assert "api_key" not in temp_config._config

    def test_get_api_key_returns_keychain_priority_over_config(self, temp_config, mock_keychain):
        """Test get_api_key returns keychain key even if config has one."""
        # Mock keychain to return a different key
        mock_keychain.get_password.return_value = "sk-keychain-key"

        with patch("vox.config.KeychainManager", return_value=mock_keychain):
            # Write API key to config file
            config_data = {"api_key": "sk-config-key"}
            with open(temp_config.config_file, "w") as f:
                yaml.dump(config_data, f)

            # Reload config to pick up the file
            temp_config.load()

            # Should return keychain key, not config key
            key = temp_config.get_api_key()
            assert key == "sk-keychain-key"
            # Should not migrate config key since keychain has one
            mock_keychain.set_password.assert_not_called()

    def test_migration_handles_keychain_errors(self, temp_config, mock_keychain):
        """Test migration handles keychain errors gracefully."""
        # Mock keychain to raise error on set
        mock_keychain.get_password.return_value = None
        mock_keychain.set_password.side_effect = Exception("Keychain error")

        with patch("vox.config.KeychainManager", return_value=mock_keychain):
            # Write API key to config file
            config_data = {"api_key": "sk-config-key"}
            with open(temp_config.config_file, "w") as f:
                yaml.dump(config_data, f)

            # Reload config to pick up the file
            temp_config.load()

            # Should still return the config key even if migration fails
            key = temp_config.get_api_key()
            assert key == "sk-config-key"


class TestConfigHotkey:
    """Tests for hot key configuration."""

    @pytest.fixture
    def temp_config(self):
        """Create a config instance for hot key tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("vox.config.Path.home", return_value=Path(tmpdir)):
                reset_config()
                config = Config()
                yield config

    def test_hotkeys_enabled_default(self, temp_config):
        """Test default hotkeys_enabled value."""
        assert temp_config.hotkeys_enabled is True

    def test_hotkeys_enabled_getter_setter(self, temp_config):
        """Test hotkeys_enabled getter and setter."""
        temp_config.hotkeys_enabled = False
        assert temp_config.hotkeys_enabled is False

        temp_config.hotkeys_enabled = True
        assert temp_config.hotkeys_enabled is True

    def test_get_mode_hotkey_defaults(self, temp_config):
        """Test get_mode_hotkey returns defaults for each mode."""
        hk = temp_config.get_mode_hotkey("fix_grammar")
        assert hk == {"modifiers": "cmd+shift", "key": "g"}

        hk = temp_config.get_mode_hotkey("professional")
        assert hk == {"modifiers": "cmd+shift", "key": "p"}

        hk = temp_config.get_mode_hotkey("concise")
        assert hk == {"modifiers": "cmd+shift", "key": "c"}

        hk = temp_config.get_mode_hotkey("friendly")
        assert hk == {"modifiers": "cmd+shift", "key": "f"}

    def test_get_mode_hotkey_unknown_mode(self, temp_config):
        """Test get_mode_hotkey returns empty for unknown mode."""
        hk = temp_config.get_mode_hotkey("nonexistent")
        assert hk == {"modifiers": "", "key": ""}

    def test_set_mode_hotkey(self, temp_config):
        """Test set_mode_hotkey updates and persists."""
        temp_config.set_mode_hotkey("fix_grammar", "option", "r")
        hk = temp_config.get_mode_hotkey("fix_grammar")
        assert hk == {"modifiers": "option", "key": "r"}

        # Other modes unchanged
        hk = temp_config.get_mode_hotkey("professional")
        assert hk == {"modifiers": "cmd+shift", "key": "p"}

    def test_set_mode_hotkey_empty_key(self, temp_config):
        """Test set_mode_hotkey with empty key (cleared shortcut)."""
        temp_config.set_mode_hotkey("concise", "cmd", "")
        hk = temp_config.get_mode_hotkey("concise")
        assert hk == {"modifiers": "cmd", "key": ""}

    def test_set_mode_hotkey_case_normalization(self, temp_config):
        """Test set_mode_hotkey normalizes key to lowercase."""
        temp_config.set_mode_hotkey("friendly", "cmd+shift", "F")
        hk = temp_config.get_mode_hotkey("friendly")
        assert hk["key"] == "f"

    def test_get_all_hotkeys(self, temp_config):
        """Test get_all_hotkeys returns all modes."""
        all_hk = temp_config.get_all_hotkeys()
        assert "fix_grammar" in all_hk
        assert "professional" in all_hk
        assert "concise" in all_hk
        assert "friendly" in all_hk
        assert all_hk["fix_grammar"] == {"modifiers": "cmd+shift", "key": "g"}

    def test_get_all_hotkeys_after_modification(self, temp_config):
        """Test get_all_hotkeys reflects modifications."""
        temp_config.set_mode_hotkey("fix_grammar", "option", "x")
        all_hk = temp_config.get_all_hotkeys()
        assert all_hk["fix_grammar"] == {"modifiers": "option", "key": "x"}
        # Others still default
        assert all_hk["professional"] == {"modifiers": "cmd+shift", "key": "p"}

    def test_hotkey_config_persisted(self, temp_config):
        """Test hot key settings are persisted across loads."""
        temp_config.hotkeys_enabled = False
        temp_config.set_mode_hotkey("fix_grammar", "option", "r")

        # Reload config
        temp_config.load()

        assert temp_config.hotkeys_enabled is False
        hk = temp_config.get_mode_hotkey("fix_grammar")
        assert hk == {"modifiers": "option", "key": "r"}

    def test_migration_from_old_format(self, temp_config):
        """Test migration from old single-hotkey format to per-mode format."""
        # Write old-format config directly
        old_config = {
            "model": "gpt-4o",
            "hotkey_enabled": True,
            "hotkey_modifiers": "option",
            "hotkey_key": "v",
        }
        with open(temp_config.config_file, "w") as f:
            yaml.dump(old_config, f)

        # Reload to trigger migration
        temp_config.load()

        # hotkeys_enabled should be migrated from hotkey_enabled
        assert temp_config.hotkeys_enabled is True

        # fix_grammar should have the old hotkey values
        hk = temp_config.get_mode_hotkey("fix_grammar")
        assert hk == {"modifiers": "option", "key": "v"}

        # Other modes should have defaults
        hk = temp_config.get_mode_hotkey("professional")
        assert hk == {"modifiers": "cmd+shift", "key": "p"}

        # Old keys should not remain in saved config
        with open(temp_config.config_file, "r") as f:
            data = yaml.safe_load(f)
        assert "hotkey_key" not in data
        assert "hotkey_modifiers" not in data
        assert "hotkey_enabled" not in data
        assert "hotkeys" in data
        assert "hotkeys_enabled" in data

    def test_migration_preserves_other_config(self, temp_config):
        """Test migration preserves non-hotkey config values."""
        old_config = {
            "model": "gpt-4o",
            "base_url": "https://custom.api",
            "hotkey_enabled": False,
            "hotkey_modifiers": "cmd",
            "hotkey_key": "d",
        }
        with open(temp_config.config_file, "w") as f:
            yaml.dump(old_config, f)

        temp_config.load()

        assert temp_config.model == "gpt-4o"
        assert temp_config.base_url == "https://custom.api"
        assert temp_config.hotkeys_enabled is False


class TestConfigAutoStart:
    """Tests for auto-start Launch Agent management."""

    @pytest.fixture
    def temp_config(self):
        """Create a config instance for auto-start tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("vox.config.Path.home", return_value=Path(tmpdir)):
                reset_config()
                config = Config()
                yield config

    def test_launch_agent_path(self, temp_config):
        """Test Launch Agent path is correct."""
        path = temp_config.get_launch_agent_path()
        assert "LaunchAgents" in str(path)
        assert path.name == "com.voxapp.rewrite.plist"

    def test_is_auto_start_enabled_false(self, temp_config):
        """Test is_auto_start_enabled returns False when no Launch Agent."""
        assert temp_config.is_auto_start_enabled() is False

    def test_is_auto_start_enabled_true(self, temp_config):
        """Test is_auto_start_enabled returns True when Launch Agent exists."""
        launch_agent_path = temp_config.get_launch_agent_path()
        launch_agent_path.parent.mkdir(parents=True, exist_ok=True)
        launch_agent_path.touch()

        assert temp_config.is_auto_start_enabled() is True

    def test_set_auto_start_enables(self, temp_config):
        """Test enabling auto-start updates config."""
        result = temp_config.set_auto_start(True)
        assert result is True
        assert temp_config.auto_start is True

    def test_set_auto_start_disables(self, temp_config):
        """Test disabling auto-start removes Launch Agent and updates config."""
        # First create a launch agent file
        launch_agent_path = temp_config.get_launch_agent_path()
        launch_agent_path.parent.mkdir(parents=True, exist_ok=True)
        launch_agent_path.touch()

        result = temp_config.set_auto_start(False)
        assert result is True
        assert temp_config.auto_start is False
        assert not launch_agent_path.exists()


class TestConfigGlobalInstance:
    """Tests for global config instance management."""

    def test_get_config_returns_singleton(self):
        """Test that get_config returns the same instance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("vox.config.Path.home", return_value=Path(tmpdir)):
                reset_config()
                config1 = get_config()
                config2 = get_config()
                assert config1 is config2

    def test_reset_config(self):
        """Test that reset_config creates a new instance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("vox.config.Path.home", return_value=Path(tmpdir)):
                reset_config()
                config1 = get_config()
                reset_config()
                config2 = get_config()
                assert config1 is not config2
