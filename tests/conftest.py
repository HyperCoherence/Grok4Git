"""
Pytest configuration and fixtures for Grok4Git tests.
"""

import os
import pytest
from unittest.mock import patch


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Set up test environment variables to prevent interactive prompts."""
    test_env = {
        "XAI_API_KEY": "test_xai_key",
        "GITHUB_TOKEN": "test_github_token",
        "GITHUB_USERNAME": "test_user",
        "MODEL_NAME": "grok-4-test",
        "LOG_LEVEL": "WARNING",  # Reduce log noise during tests
        "TESTING": "true",
    }
    
    with patch.dict(os.environ, test_env):
        # Mock file existence to skip interactive .env setup
        with patch("grok4git.config.os.path.exists") as mock_exists:
            mock_exists.return_value = True
            # Mock load_dotenv to prevent loading actual .env files
            with patch("grok4git.config.load_dotenv"):
                yield


@pytest.fixture
def clean_environment():
    """Fixture to provide a clean environment for tests that need it."""
    with patch.dict(os.environ, {}, clear=True):
        yield 