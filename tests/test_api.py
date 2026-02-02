"""Tests for the API module."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from vox.api import (
    RewriteMode,
    DISPLAY_NAMES,
    SYSTEM_PROMPTS,
    RewriteAPI,
    RewriteError,
    APIKeyError,
    NetworkError,
    RateLimitError,
)


class TestRewriteMode:
    """Tests for RewriteMode enum."""

    def test_all_modes_exist(self):
        """Test that all expected modes are defined."""
        expected_modes = {
            RewriteMode.FIX_GRAMMAR,
            RewriteMode.PROFESSIONAL,
            RewriteMode.CONCISE,
            RewriteMode.FRIENDLY,
        }
        actual_modes = set(RewriteMode)
        assert actual_modes == expected_modes

    def test_display_names_exist(self):
        """Test that all modes have display names."""
        for mode in RewriteMode:
            assert mode in DISPLAY_NAMES
            assert isinstance(DISPLAY_NAMES[mode], str)

    def test_system_prompts_exist(self):
        """Test that all modes have system prompts."""
        for mode in RewriteMode:
            assert mode in SYSTEM_PROMPTS
            assert isinstance(SYSTEM_PROMPTS[mode], str)
            assert len(SYSTEM_PROMPTS[mode]) > 0

    def test_display_names_are_correct(self):
        """Test display names match expected values."""
        assert DISPLAY_NAMES[RewriteMode.FIX_GRAMMAR] == "Fix Grammar"
        assert DISPLAY_NAMES[RewriteMode.PROFESSIONAL] == "Professional"
        assert DISPLAY_NAMES[RewriteMode.CONCISE] == "Concise"
        assert DISPLAY_NAMES[RewriteMode.FRIENDLY] == "Friendly"


class TestRewriteAPI:
    """Tests for RewriteAPI class."""

    def test_init_default(self):
        """Test initialization with default values."""
        with patch("vox.api.OpenAI") as mock_openai:
            api = RewriteAPI("test-key")
            assert api.model == "gpt-4o-mini"
            assert api.base_url is None
            mock_openai.assert_called_once_with(api_key="test-key")

    def test_init_with_model(self):
        """Test initialization with custom model."""
        with patch("vox.api.OpenAI") as mock_openai:
            api = RewriteAPI("test-key", model="gpt-4o")
            assert api.model == "gpt-4o"

    def test_init_with_base_url(self):
        """Test initialization with custom base URL."""
        with patch("vox.api.OpenAI") as mock_openai:
            api = RewriteAPI("test-key", base_url="https://custom.api/v1")
            assert api.base_url == "https://custom.api/v1"
            mock_openai.assert_called_once_with(
                api_key="test-key", base_url="https://custom.api/v1"
            )

    def test_set_model(self):
        """Test setting model after initialization."""
        with patch("vox.api.OpenAI"):
            api = RewriteAPI("test-key")
            api.set_model("gpt-4o")
            assert api.model == "gpt-4o"

    def test_rewrite_empty_text(self):
        """Test that empty text returns as-is."""
        with patch("vox.api.OpenAI"):
            api = RewriteAPI("test-key")
            assert api.rewrite("", RewriteMode.FIX_GRAMMAR) == ""
            assert api.rewrite("   ", RewriteMode.FIX_GRAMMAR) == "   "

    def test_rewrite_success(self):
        """Test successful text rewrite."""
        with patch("vox.api.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "Corrected text."
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            api = RewriteAPI("test-key")
            result = api.rewrite("fix this", RewriteMode.FIX_GRAMMAR)

            assert result == "Corrected text."
            mock_client.chat.completions.create.assert_called_once()

    def test_rewrite_uses_correct_system_prompt(self):
        """Test that rewrite uses the correct system prompt for each mode."""
        with patch("vox.api.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "Result"
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            api = RewriteAPI("test-key")

            for mode in RewriteMode:
                api.rewrite("test", mode)
                call_args = mock_client.chat.completions.create.call_args
                messages = call_args[1]["messages"]
                assert messages[0]["role"] == "system"
                assert messages[0]["content"] == SYSTEM_PROMPTS[mode]

    def test_get_display_name(self):
        """Test get_display_name static method."""
        assert RewriteAPI.get_display_name(RewriteMode.FIX_GRAMMAR) == "Fix Grammar"
        assert RewriteAPI.get_display_name(RewriteMode.PROFESSIONAL) == "Professional"
        assert RewriteAPI.get_display_name(RewriteMode.CONCISE) == "Concise"
        assert RewriteAPI.get_display_name(RewriteMode.FRIENDLY) == "Friendly"

    def test_get_all_modes(self):
        """Test get_all_modes returns all modes with display names."""
        modes = RewriteAPI.get_all_modes()
        assert len(modes) == 4
        assert (RewriteMode.FIX_GRAMMAR, "Fix Grammar") in modes
        assert (RewriteMode.PROFESSIONAL, "Professional") in modes
        assert (RewriteMode.CONCISE, "Concise") in modes
        assert (RewriteMode.FRIENDLY, "Friendly") in modes


class TestErrorHandling:
    """Tests for error handling in RewriteAPI."""

    def test_api_key_error_invalid_code(self):
        """Test APIKeyError is raised for invalid_api_key code."""
        from openai import OpenAIError

        with patch("vox.api.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_error = OpenAIError("Invalid API key")
            mock_error.code = "invalid_api_key"
            mock_client.chat.completions.create.side_effect = mock_error
            mock_openai.return_value = mock_client

            api = RewriteAPI("test-key")
            with pytest.raises(APIKeyError):
                api.rewrite("test", RewriteMode.FIX_GRAMMAR)

    def test_api_key_error_401_code(self):
        """Test APIKeyError is raised for 401 code."""
        from openai import OpenAIError

        with patch("vox.api.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_error = OpenAIError("Unauthorized")
            mock_error.code = "401"
            mock_client.chat.completions.create.side_effect = mock_error
            mock_openai.return_value = mock_client

            api = RewriteAPI("test-key")
            with pytest.raises(APIKeyError):
                api.rewrite("test", RewriteMode.FIX_GRAMMAR)

    def test_rate_limit_error(self):
        """Test RateLimitError is raised for rate limit errors."""
        from openai import OpenAIError

        with patch("vox.api.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_error = OpenAIError("Rate limit exceeded")
            mock_error.code = "429"
            mock_client.chat.completions.create.side_effect = mock_error
            mock_openai.return_value = mock_client

            api = RewriteAPI("test-key")
            with pytest.raises(RateLimitError):
                api.rewrite("test", RewriteMode.FIX_GRAMMAR)

    def test_network_error_connection(self):
        """Test NetworkError for connection errors."""
        from openai import OpenAIError

        with patch("vox.api.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_error = OpenAIError("Connection failed")
            mock_client.chat.completions.create.side_effect = mock_error
            mock_openai.return_value = mock_client

            api = RewriteAPI("test-key")
            with pytest.raises(NetworkError):
                api.rewrite("test", RewriteMode.FIX_GRAMMAR)

    def test_authentication_error_in_message(self):
        """Test APIKeyError for authentication error in message."""
        from openai import OpenAIError

        with patch("vox.api.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_error = OpenAIError("Authentication failed")
            mock_client.chat.completions.create.side_effect = mock_error
            mock_openai.return_value = mock_client

            api = RewriteAPI("test-key")
            with pytest.raises(APIKeyError):
                api.rewrite("test", RewriteMode.FIX_GRAMMAR)
