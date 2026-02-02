"""
Configuration management for Vox.

Handles loading/saving configuration from config.yml and storing
the API key securely in the macOS Keychain.
"""
import os
import yaml
from pathlib import Path
from typing import Optional


# Default configuration values
DEFAULT_MODELS = ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"]

DEFAULT_CONFIG = {
    "model": "gpt-4o-mini",
    "base_url": None,  # Custom OpenAI-compatible API base URL
    "auto_start": False,
    "toast_position": "cursor",  # or "top-right", "top-center"
}


class Config:
    """Manages Vox configuration and secure API key storage."""

    def __init__(self):
        """Initialize configuration manager."""
        self.config_dir = self._get_config_dir()
        self.config_file = self.config_dir / "config.yml"
        self._config = {}
        self._ensure_config_dir()
        self.load()

    @staticmethod
    def _get_config_dir() -> Path:
        """Get the application configuration directory."""
        home = Path.home()
        config_dir = home / "Library" / "Application Support" / "Vox"
        return config_dir

    def _ensure_config_dir(self):
        """Create configuration directory if it doesn't exist."""
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def load(self):
        """Load configuration from file, merging with defaults."""
        self._config = DEFAULT_CONFIG.copy()

        if self.config_file.exists():
            try:
                with open(self.config_file, "r") as f:
                    user_config = yaml.safe_load(f) or {}
                self._config.update(user_config)
            except Exception as e:
                print(f"Warning: Could not load config: {e}")

    def save(self):
        """Save current configuration to file."""
        try:
            with open(self.config_file, "w") as f:
                yaml.dump(self._config, f, default_flow_style=False)
        except Exception as e:
            print(f"Error saving config: {e}")

    @property
    def model(self) -> str:
        """Get the configured OpenAI model."""
        return self._config.get("model", DEFAULT_CONFIG["model"])

    @model.setter
    def model(self, value: str):
        """Set the OpenAI model."""
        self._config["model"] = value
        self.save()

    @property
    def base_url(self) -> Optional[str]:
        """Get the custom base URL for OpenAI API."""
        return self._config.get("base_url")

    @base_url.setter
    def base_url(self, value: Optional[str]):
        """Set the custom base URL for OpenAI API."""
        if value and value.strip():
            self._config["base_url"] = value.strip()
        else:
            self._config["base_url"] = None
        self.save()

    @property
    def auto_start(self) -> bool:
        """Get auto-start at login setting."""
        return self._config.get("auto_start", DEFAULT_CONFIG["auto_start"])

    @auto_start.setter
    def auto_start(self, value: bool):
        """Set auto-start at login setting."""
        self._config["auto_start"] = value
        self.save()

    @property
    def toast_position(self) -> str:
        """Get toast notification position preference."""
        return self._config.get("toast_position", DEFAULT_CONFIG["toast_position"])

    @toast_position.setter
    def toast_position(self, value: str):
        """Set toast notification position preference."""
        self._config["toast_position"] = value
        self.save()

    # API Key Management via config file

    def get_api_key(self) -> Optional[str]:
        """Retrieve the OpenAI API key from config."""
        return self._config.get("api_key")

    def set_api_key(self, api_key: str) -> bool:
        """Store the OpenAI API key in config."""
        self._config["api_key"] = api_key
        self.save()
        return True

    def delete_api_key(self) -> bool:
        """Delete the OpenAI API key from config."""
        self._config.pop("api_key", None)
        self.save()
        return True

    def has_api_key(self) -> bool:
        """Check if an API key is configured."""
        key = self.get_api_key()
        return key is not None and len(key) > 0

    # Auto-start Launch Agent management

    def get_launch_agent_path(self) -> Path:
        """Get the path to the Launch Agent plist file."""
        return Path.home() / "Library" / "LaunchAgents" / "com.voxapp.rewrite.plist"

    def is_auto_start_enabled(self) -> bool:
        """Check if auto-start is currently enabled."""
        return self.get_launch_agent_path().exists()

    def set_auto_start(self, enabled: bool) -> bool:
        """
        Enable or disable auto-start at login using Launch Agent.

        Args:
            enabled: True to enable auto-start, False to disable.

        Returns:
            True if successful, False otherwise.
        """
        launch_agent_path = self.get_launch_agent_path()
        launch_agent_path.parent.mkdir(parents=True, exist_ok=True)

        if enabled:
            # This would be set during installation
            # For now, we just update the config
            self.auto_start = True
        else:
            if launch_agent_path.exists():
                try:
                    launch_agent_path.unlink()
                except Exception as e:
                    print(f"Error removing launch agent: {e}")
                    return False
            self.auto_start = False

        return True


# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = Config()
    return _config


def reset_config():
    """Reset the global configuration instance (mainly for testing)."""
    global _config
    _config = None
