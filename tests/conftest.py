"""
Test configuration for Grok4Git tests.
"""
import os
import pytest
from unittest.mock import patch

# Set up test environment variables before any imports
os.environ.update({
    "XAI_API_KEY": "test_xai_key",
    "GITHUB_TOKEN": "test_github_token", 
    "GITHUB_USERNAME": "test_user",
    "MODEL_NAME": "grok-4-0709",
    "LOG_LEVEL": "DEBUG",
    "MAX_FILE_SIZE_MB": "1",
    "API_TIMEOUT": "30",
    "GITHUB_API_VERSION": "2022-11-28",
    "ENABLE_PR_PEER_REVIEW": "false",
    "PEER_REVIEW_MODEL": "grok-4-0709",
    "MAX_REVIEW_ITERATIONS": "3",
    "TESTING": "true"  # Flag to indicate testing environment
})

@pytest.fixture(autouse=True)
def setup_test_environment():
    """Setup test environment for all tests."""
    # Mock any interactive prompts to prevent them from running during tests
    with patch('rich.prompt.Prompt.ask') as mock_prompt, \
         patch('rich.console.Console.print') as mock_print:
        
        # Default prompt responses for testing
        mock_prompt.return_value = "n"  # Don't create .env file during tests
        
        yield
        
        # Cleanup after tests if needed
        pass

@pytest.fixture
def mock_config():
    """Provide a mock config for testing."""
    from grok4git.config import Config
    
    # Create config instance with test environment variables already set
    config = Config()
    return config 