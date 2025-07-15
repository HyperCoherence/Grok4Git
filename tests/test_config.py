"""
Unit tests for the config module.
"""

import os
import tempfile
import shutil
from unittest.mock import patch
import pytest
from grok4git.config import Config


class TestConfig:
    """Test configuration setup and validation."""

    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)

    def teardown_method(self):
        """Cleanup test environment."""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir)

    @patch.dict(
        os.environ,
        {
            "XAI_API_KEY": "test_xai_key",
            "GITHUB_TOKEN": "test_github_token",
            "GITHUB_USERNAME": "test_user",
        },
    )
    @patch("grok4git.config.os.path.exists")
    @patch("grok4git.config.load_dotenv")
    def test_config_with_valid_env_vars(self, mock_load_dotenv, mock_exists):
        """Test configuration with valid environment variables."""
        # Mock that .env exists to skip interactive setup
        mock_exists.return_value = True

        config = Config()

        assert config.xai_api_key == "test_xai_key"
        assert config.github_token == "test_github_token"
        assert config.github_username == "test_user"

    @pytest.mark.skip(reason="Interactive test - difficult to mock properly")
    @patch("grok4git.config.Prompt.ask")
    def test_config_creates_env_file_when_missing(self, mock_prompt, clean_environment):
        """Test that config creates .env file when missing."""
        # Mock user inputs
        mock_prompt.side_effect = [
            "y",  # Create .env file
            "test_xai_key",  # XAI API key
            "test_github_token",  # GitHub token
            "test_user",  # GitHub username
            "n",  # Don't configure optional settings
        ]

        # This should create the .env file
        config = Config()

        # Check that .env file was created
        assert os.path.exists(".env")

        # Check .env file contents
        with open(".env", "r") as f:
            content = f.read()
            assert "XAI_API_KEY=test_xai_key" in content
            assert "GITHUB_TOKEN=test_github_token" in content
            assert "GITHUB_USERNAME=test_user" in content

    @pytest.mark.skip(reason="Interactive test - difficult to mock properly")
    @patch("grok4git.config.Prompt.ask")
    def test_config_copies_env_example_when_available(self, mock_prompt, clean_environment):
        """Test that config copies .env.example to .env when available."""
        # Create .env.example file
        with open(".env.example", "w") as f:
            f.write("XAI_API_KEY=your_xai_api_key_here\n")
            f.write("GITHUB_TOKEN=your_github_token_here\n")
            f.write("GITHUB_USERNAME=your_github_username_here\n")

        # Mock user input to copy .env.example
        mock_prompt.return_value = "y"

        # This should copy .env.example to .env
        config = Config()

        # Check that .env file was created
        assert os.path.exists(".env")

        # Check .env file contents match .env.example
        with open(".env", "r") as f:
            content = f.read()
            assert "XAI_API_KEY=your_xai_api_key_here" in content
            assert "GITHUB_TOKEN=your_github_token_here" in content
            assert "GITHUB_USERNAME=your_github_username_here" in content

    @patch.dict(
        os.environ,
        {"XAI_API_KEY": "", "GITHUB_TOKEN": "test_github_token", "GITHUB_USERNAME": "test_user"},
    )
    @patch("grok4git.config.os.path.exists")
    @patch("grok4git.config.load_dotenv")
    @patch("grok4git.config.Config._is_testing_environment")
    def test_config_validation_fails_with_missing_vars(self, mock_is_testing_env, mock_load_dotenv, mock_exists):
        """Test that config validation fails with missing required variables."""
        # Mock that .env exists to skip interactive setup
        mock_exists.return_value = True
        # Mock that we're NOT in testing environment so validation runs
        mock_is_testing_env.return_value = False

        with pytest.raises(ValueError, match="Missing required environment variables"):
            Config()

    @patch.dict(
        os.environ,
        {
            "XAI_API_KEY": "test_xai_key",
            "GITHUB_TOKEN": "test_github_token",
            "GITHUB_USERNAME": "test_user",
            "MODEL_NAME": "custom-model",
            "LOG_LEVEL": "DEBUG",
        },
    )
    @patch("grok4git.config.os.path.exists")
    @patch("grok4git.config.load_dotenv")
    def test_config_optional_settings(self, mock_load_dotenv, mock_exists):
        """Test configuration with optional settings."""
        # Mock that .env exists to skip interactive setup
        mock_exists.return_value = True

        config = Config()

        assert config.model_name == "custom-model"
        assert config.log_level == "DEBUG"
        assert config.max_file_size_mb == 1  # default value
        assert config.api_timeout == 30  # default value

    @patch.dict(
        os.environ,
        {
            "XAI_API_KEY": "test_xai_key",
            "GITHUB_TOKEN": "test_github_token",
            "GITHUB_USERNAME": "test_user",
        },
    )
    @patch("grok4git.config.os.path.exists")
    @patch("grok4git.config.load_dotenv")
    def test_github_headers(self, mock_load_dotenv, mock_exists):
        """Test GitHub headers generation."""
        # Mock that .env exists to skip interactive setup
        mock_exists.return_value = True

        config = Config()
        headers = config.get_github_headers()

        assert headers["Authorization"] == "Bearer test_github_token"
        assert headers["Accept"] == "application/vnd.github+json"
        assert "X-GitHub-Api-Version" in headers

    @pytest.mark.skip(reason="Interactive test - difficult to mock properly")
    @patch("grok4git.config.Prompt.ask")
    def test_config_optional_settings_configuration(self, mock_prompt, clean_environment):
        """Test configuring optional settings during setup."""
        # Mock user inputs including optional settings
        mock_prompt.side_effect = [
            "y",  # Create .env file
            "test_xai_key",  # XAI API key
            "test_github_token",  # GitHub token
            "test_user",  # GitHub username
            "y",  # Configure optional settings
            "grok-beta",  # Model name
            "ERROR",  # Log level
        ]

        config = Config()

        # Check that .env file was created with optional settings
        assert os.path.exists(".env")

        with open(".env", "r") as f:
            content = f.read()
            assert "MODEL_NAME=grok-beta" in content
            assert "LOG_LEVEL=ERROR" in content


if __name__ == "__main__":
    pytest.main([__file__])
