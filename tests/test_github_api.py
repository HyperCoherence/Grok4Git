"""
Unit tests for the github_api module.
"""

import pytest
from unittest.mock import Mock, patch
import grok4git.github_api as github_api


class TestGitHubAPI:
    """Test GitHub API utility functions."""

    def test_github_api_module_exists(self):
        """Test that github_api module can be imported."""
        # Access the global github_api instance
        api_instance = github_api.github_api
        assert hasattr(api_instance, "make_request")
        assert hasattr(api_instance, "get_paginated_results")
        assert hasattr(api_instance, "get_default_branch")

    def test_make_request_callable(self):
        """Test that make_request is callable."""
        api_instance = github_api.github_api
        assert callable(api_instance.make_request)

    def test_get_paginated_results_callable(self):
        """Test that get_paginated_results is callable."""
        api_instance = github_api.github_api
        assert callable(api_instance.get_paginated_results)

    def test_get_default_branch_callable(self):
        """Test that get_default_branch is callable."""
        api_instance = github_api.github_api
        assert callable(api_instance.get_default_branch)

    @patch("grok4git.github_api.requests.Session")
    def test_session_creation(self, mock_session_class):
        """Test that session is created properly."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # Import should create session
        import importlib

        importlib.reload(github_api)

        # Verify session was created
        mock_session_class.assert_called()

        # Verify session has expected attributes
        api_instance = github_api.github_api
        assert hasattr(api_instance, "session")

        # Test that session headers are set properly
        mock_session.headers.update.assert_called()


if __name__ == "__main__":
    pytest.main([__file__])
