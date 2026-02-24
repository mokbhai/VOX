"""
Configuration management for Vox.

Handles loading/saving configuration from config.yml and storing
the API key securely in the macOS Keychain.
"""
import yaml
from pathlib import Path
from typing import Optional

from vox.keychain import KeychainManager, KeychainError


# Default configuration values
DEFAULT_MODELS = ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"]

DEFAULT_CONFIG = {
    "model": "gpt-4o-mini",
    "base_url": None,  # Custom OpenAI-compatible API base URL
    "auto_start": False,
    "toast_position": "cursor",  # or "top-right", "top-center"
    "thinking_mode": False,  # Enable extended thinking for rewrites
    "hotkeys_enabled": True,
    "hotkeys": {
        "fix_grammar":  {"modifiers": "cmd+shift", "key": "g"},
        "professional": {"modifiers": "cmd+shift", "key": "p"},
        "concise":      {"modifiers": "cmd+shift", "key": "c"},
        "friendly":     {"modifiers": "cmd+shift", "key": "f"},
    },
    "speech": {
        "enabled": True,
        "model": "base",
        "language": "auto",  # or "en", "es", etc.
        "hotkey": {"modifiers": "fn", "key": "f13"},
    },
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
        # Deep-copy the hotkeys dict so mutations don't affect DEFAULT_CONFIG
        self._config["hotkeys"] = {
            k: dict(v) for k, v in DEFAULT_CONFIG["hotkeys"].items()
        }

        if self.config_file.exists():
            try:
                with open(self.config_file, "r") as f:
                    user_config = yaml.safe_load(f) or {}

                # Migrate old single-hotkey format to per-mode format
                if "hotkey_key" in user_config and "hotkeys" not in user_config:
                    old_mod = user_config.pop("hotkey_modifiers", "cmd")
                    old_key = user_config.pop("hotkey_key", "d")
                    old_enabled = user_config.pop("hotkey_enabled", True)

                    user_config["hotkeys_enabled"] = old_enabled
                    user_config["hotkeys"] = {
                        k: dict(v) for k, v in DEFAULT_CONFIG["hotkeys"].items()
                    }
                    # Migrate the old single hotkey to fix_grammar
                    user_config["hotkeys"]["fix_grammar"] = {
                        "modifiers": old_mod,
                        "key": old_key,
                    }
                    # Save migrated config
                    self._config.update(user_config)
                    self.save()
                else:
                    # Clean up any leftover old keys
                    for old_key in ("hotkey_enabled", "hotkey_modifiers", "hotkey_key"):
                        user_config.pop(old_key, None)

                    # Merge hotkeys dict carefully (keep defaults for missing modes)
                    if "hotkeys" in user_config:
                        stored_hotkeys = user_config.pop("hotkeys")
                        for mode_key, hk in stored_hotkeys.items():
                            if isinstance(hk, dict):
                                self._config["hotkeys"][mode_key] = dict(hk)

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

    @property
    def thinking_mode(self) -> bool:
        """Get whether thinking mode is enabled for rewrites."""
        return self._config.get("thinking_mode", DEFAULT_CONFIG["thinking_mode"])

    @thinking_mode.setter
    def thinking_mode(self, value: bool):
        """Set whether thinking mode is enabled for rewrites."""
        self._config["thinking_mode"] = value
        self.save()

    @property
    def hotkeys_enabled(self) -> bool:
        """Get whether hot keys are enabled."""
        return self._config.get("hotkeys_enabled", DEFAULT_CONFIG["hotkeys_enabled"])

    @hotkeys_enabled.setter
    def hotkeys_enabled(self, value: bool):
        """Set whether hot keys are enabled."""
        self._config["hotkeys_enabled"] = value
        self.save()

    def get_mode_hotkey(self, mode_value: str) -> dict:
        """Get the hotkey config for a specific mode.

        Args:
            mode_value: The mode value string (e.g. "fix_grammar").

        Returns:
            Dict with "modifiers" and "key" strings.
        """
        hotkeys = self._config.get("hotkeys", DEFAULT_CONFIG["hotkeys"])
        default = DEFAULT_CONFIG["hotkeys"].get(mode_value, {"modifiers": "", "key": ""})
        return dict(hotkeys.get(mode_value, default))

    def set_mode_hotkey(self, mode_value: str, modifiers: str, key: str):
        """Set the hotkey for a specific mode.

        Args:
            mode_value: The mode value string (e.g. "fix_grammar").
            modifiers: Modifier string (e.g. "cmd+shift").
            key: Key character (e.g. "g").
        """
        if "hotkeys" not in self._config:
            self._config["hotkeys"] = {
                k: dict(v) for k, v in DEFAULT_CONFIG["hotkeys"].items()
            }
        self._config["hotkeys"][mode_value] = {
            "modifiers": modifiers,
            "key": key.lower() if key else "",
        }
        self.save()

    def get_all_hotkeys(self) -> dict:
        """Get all hotkey configs, merging defaults with stored values.

        Returns:
            Dict mapping mode_value -> {"modifiers": str, "key": str}.
        """
        defaults = {k: dict(v) for k, v in DEFAULT_CONFIG["hotkeys"].items()}
        stored = self._config.get("hotkeys", {})
        for mode_key, hk in stored.items():
            if isinstance(hk, dict):
                defaults[mode_key] = dict(hk)
        return defaults

    # Speech-to-Text Settings

    @property
    def speech_enabled(self) -> bool:
        """Get whether speech-to-text is enabled."""
        speech = self._config.get("speech", {})
        return speech.get("enabled", DEFAULT_CONFIG["speech"]["enabled"])

    @speech_enabled.setter
    def speech_enabled(self, value: bool):
        """Set whether speech-to-text is enabled."""
        if "speech" not in self._config:
            self._ensure_speech_config()
        self._config["speech"]["enabled"] = value
        self.save()

    @property
    def speech_model(self) -> str:
        """Get the speech-to-text model name."""
        speech = self._config.get("speech", {})
        return speech.get("model", DEFAULT_CONFIG["speech"]["model"])

    @speech_model.setter
    def speech_model(self, value: str):
        """Set the speech-to-text model name."""
        if "speech" not in self._config:
            self._ensure_speech_config()
        self._config["speech"]["model"] = value
        self.save()

    @property
    def speech_language(self) -> str:
        """Get the speech-to-text language code."""
        speech = self._config.get("speech", {})
        return speech.get("language", DEFAULT_CONFIG["speech"]["language"])

    @speech_language.setter
    def speech_language(self, value: str):
        """Set the speech-to-text language code."""
        if "speech" not in self._config:
            self._ensure_speech_config()
        self._config["speech"]["language"] = value
        self.save()

    def _ensure_speech_config(self):
        """Ensure speech config exists with deep-copied defaults."""
        default_speech = DEFAULT_CONFIG["speech"]
        self._config["speech"] = {
            "enabled": default_speech["enabled"],
            "model": default_speech["model"],
            "language": default_speech["language"],
            "hotkey": dict(default_speech["hotkey"]),
        }

    def get_speech_hotkey(self) -> dict:
        """Get the speech hotkey config.

        Returns:
            Dict with "modifiers" and "key" strings.
        """
        speech = self._config.get("speech", {})
        default_hotkey = DEFAULT_CONFIG["speech"]["hotkey"]
        hotkey = speech.get("hotkey", default_hotkey)
        return dict(hotkey)

    def set_speech_hotkey(self, modifiers: str, key: str):
        """Set the speech hotkey.

        Args:
            modifiers: Modifier string (e.g. "fn").
            key: Key character (e.g. "f13").
        """
        if "speech" not in self._config:
            self._ensure_speech_config()
        self._config["speech"]["hotkey"] = {
            "modifiers": modifiers,
            "key": key.lower() if key else "",
        }
        self.save()

    # API Key Management via keychain (with migration from config file)

    def get_api_key(self) -> Optional[str]:
        """Retrieve the OpenAI API key from keychain.

        Checks keychain first. If no key exists in keychain, falls back to
        config file for migration and automatically migrates the key to keychain.

        Returns:
            The API key string if found, None otherwise.
        """
        # First check keychain
        keychain_key = self.get_api_key_from_keychain()
        if keychain_key:
            return keychain_key

        # Fall back to config file for migration
        config_key = self._config.get("api_key")
        if config_key:
            # Migrate the key to keychain
            try:
                if self.set_api_key_in_keychain(config_key):
                    # Remove from config file after successful migration
                    self._config.pop("api_key", None)
                    self.save()
                    return config_key
            except Exception:
                # If migration fails, still return the key from config
                return config_key

        return None

    def set_api_key(self, api_key: str) -> bool:
        """Store the OpenAI API key in keychain."""
        return self.set_api_key_in_keychain(api_key)

    def delete_api_key(self) -> bool:
        """Delete the OpenAI API key from keychain."""
        return self.delete_api_key_from_keychain()

    def has_api_key(self) -> bool:
        """Check if an API key is configured."""
        return self.has_api_key_in_keychain()

    # API Key Management via Keychain (new secure storage)

    def get_api_key_from_keychain(self) -> Optional[str]:
        """Retrieve the OpenAI API key from keychain.

        Returns:
            The API key string if found in keychain, None otherwise.
        """
        try:
            keychain = KeychainManager()
            return keychain.get_password()
        except KeychainError:
            return None

    def set_api_key_in_keychain(self, api_key: str) -> bool:
        """Store the OpenAI API key in keychain.

        Args:
            api_key: The API key string to store.

        Returns:
            True if successful, False otherwise.
        """
        try:
            keychain = KeychainManager()
            return keychain.set_password(api_key)
        except KeychainError:
            return False

    def delete_api_key_from_keychain(self) -> bool:
        """Delete the OpenAI API key from keychain.

        Returns:
            True if successful, False otherwise.
        """
        try:
            keychain = KeychainManager()
            return keychain.delete_password()
        except KeychainError:
            return False

    def has_api_key_in_keychain(self) -> bool:
        """Check if an API key exists in keychain.

        Returns:
            True if a key exists in keychain, False otherwise.
        """
        try:
            keychain = KeychainManager()
            return keychain.has_password()
        except KeychainError:
            return False

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
