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
    KEYRING_SERVICE_NAME,
    KEYRING_API_KEY_ITEM,
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

    def test_default_config_values(self):
        """Test DEFAULT_CONFIG has correct default values."""
        assert DEFAULT_CONFIG["model"] == "gpt-4o-mini"
        assert DEFAULT_CONFIG["base_url"] is None
        assert DEFAULT_CONFIG["auto_start"] is False
        assert DEFAULT_CONFIG["toast_position"] == "cursor"

    def test_keyring_constants(self):
        """Test keyring constants are correctly defined."""
        assert KEYRING_SERVICE_NAME == "com.voxapp.rewrite"
        assert KEYRING_API_KEY_ITEM == "openai_api_key"


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


class TestConfigApiKey:
    """Tests for API key management via keychain."""

    @pytest.fixture
    def temp_config(self):
        """Create a config instance for keychain tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("vox.config.Path.home", return_value=Path(tmpdir)):
                reset_config()
                config = Config()
                yield config

    def test_get_api_key_when_not_set(self, temp_config):
        """Test getting API key when none is stored."""
        with patch("vox.config.keyring.get_password", return_value=None):
            assert temp_config.get_api_key() is None

    def test_get_api_key_when_set(self, temp_config):
        """Test getting API key when one is stored."""
        with patch("vox.config.keyring.get_password", return_value="sk-test123"):
            assert temp_config.get_api_key() == "sk-test123"

    def test_set_api_key(self, temp_config):
        """Test setting API key."""
        with patch("vox.config.keyring.set_password") as mock_set:
            result = temp_config.set_api_key("sk-newkey")
            assert result is True
            mock_set.assert_called_once_with(
                KEYRING_SERVICE_NAME, KEYRING_API_KEY_ITEM, "sk-newkey"
            )

    def test_set_api_key_failure(self, temp_config):
        """Test setting API key when keyring fails."""
        with patch("vox.config.keyring.set_password", side_effect=Exception("Failed")):
            result = temp_config.set_api_key("sk-newkey")
            assert result is False

    def test_delete_api_key(self, temp_config):
        """Test deleting API key."""
        with patch("vox.config.keyring.delete_password") as mock_delete:
            result = temp_config.delete_api_key()
            assert result is True
            mock_delete.assert_called_once_with(KEYRING_SERVICE_NAME, KEYRING_API_KEY_ITEM)

    def test_delete_api_key_failure(self, temp_config):
        """Test deleting API key when keyring fails."""
        with patch("vox.config.keyring.delete_password", side_effect=Exception("Failed")):
            result = temp_config.delete_api_key()
            assert result is False

    def test_has_api_key_true(self, temp_config):
        """Test has_api_key returns True when key exists."""
        with patch("vox.config.keyring.get_password", return_value="sk-test"):
            assert temp_config.has_api_key() is True

    def test_has_api_key_false(self, temp_config):
        """Test has_api_key returns False when key doesn't exist."""
        with patch("vox.config.keyring.get_password", return_value=None):
            assert temp_config.has_api_key() is False


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
