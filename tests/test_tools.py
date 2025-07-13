"""
Unit tests for the tools module.
"""

import pytest
import json
from unittest.mock import Mock, patch
from grok4git.tools import (
    list_github_repos,
    get_repo_info,
    get_file_content,
    create_pull_request,
    list_repo_branches,
    manage_issues,
)


class TestGitHubTools:
    """Test GitHub tool functions."""

    def test_list_github_repos_callable(self):
        """Test that list_github_repos is callable."""
        assert callable(list_github_repos)

    def test_get_repo_info_callable(self):
        """Test that get_repo_info is callable."""
        assert callable(get_repo_info)

    def test_get_file_content_callable(self):
        """Test that get_file_content is callable."""
        assert callable(get_file_content)

    def test_create_pull_request_callable(self):
        """Test that create_pull_request is callable."""
        assert callable(create_pull_request)

    @patch("grok4git.tools.github_api")
    def test_list_github_repos_success(self, mock_api):
        """Test successful repository listing."""
        # Mock successful API response
        mock_api.get_paginated_results.return_value = [
            {"full_name": "user/repo1", "private": False},
            {"full_name": "user/repo2", "private": True},
        ]

        result = list_github_repos()
        parsed_result = json.loads(result)

        assert isinstance(parsed_result, list)
        assert len(parsed_result) == 2
        assert "user/repo1" in parsed_result
        assert "user/repo2" in parsed_result

    @patch("grok4git.tools.github_api")
    def test_get_repo_info_success(self, mock_api):
        """Test successful repository info retrieval."""
        # Mock successful API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "full_name": "user/test-repo",
            "description": "Test repository",
            "stargazers_count": 42,
            "forks_count": 7,
            "open_issues_count": 3,
            "default_branch": "main",
            "language": "Python",
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-12-01T00:00:00Z",
            "html_url": "https://github.com/user/test-repo",
        }
        mock_api.make_request.return_value = mock_response

        result = get_repo_info("user/test-repo")
        parsed_result = json.loads(result)

        assert parsed_result["full_name"] == "user/test-repo"
        assert parsed_result["stars"] == 42
        assert parsed_result["forks"] == 7
        assert parsed_result["language"] == "Python"

    @patch("grok4git.tools.github_api")
    def test_get_file_content_success(self, mock_api):
        """Test successful file content retrieval."""
        # Mock successful API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "content": "aGVsbG8gd29ybGQ=",  # base64 encoded "hello world"
            "encoding": "base64",
        }
        mock_api.make_request.return_value = mock_response

        result = get_file_content("user/test-repo", "README.md")

        assert "hello world" in result

    @patch("grok4git.tools.github_api")
    def test_list_repo_branches_success(self, mock_api):
        """Test successful branch listing."""
        # Mock successful API response
        mock_api.get_paginated_results.return_value = [
            {"name": "main"},
            {"name": "develop"},
            {"name": "feature/test"},
        ]

        result = list_repo_branches("user/test-repo")
        parsed_result = json.loads(result)

        assert isinstance(parsed_result, list)
        assert len(parsed_result) == 3
        assert "main" in parsed_result
        assert "develop" in parsed_result
        assert "feature/test" in parsed_result

    @patch("grok4git.tools.github_api")
    def test_manage_issues_list_success(self, mock_api):
        """Test successful issue listing."""
        # Mock successful API response
        mock_api.get_paginated_results.return_value = [
            {"number": 1, "title": "Bug report"},
            {"number": 2, "title": "Feature request"},
        ]

        result = manage_issues("user/test-repo", "list")
        parsed_result = json.loads(result)

        assert isinstance(parsed_result, list)
        assert len(parsed_result) == 2
        assert parsed_result[0]["number"] == 1
        assert parsed_result[0]["title"] == "Bug report"

    @patch("grok4git.tools.github_api")
    def test_manage_issues_create_success(self, mock_api):
        """Test successful issue creation."""
        # Mock successful API response
        mock_response = Mock()
        mock_response.json.return_value = {"html_url": "https://github.com/user/test-repo/issues/3"}
        mock_api.make_request.return_value = mock_response

        result = manage_issues("user/test-repo", "create", "Test Issue", "Test body")

        assert result == "https://github.com/user/test-repo/issues/3"

    def test_create_pull_request_empty_files(self):
        """Test create_pull_request with empty files list."""
        result = create_pull_request(
            "user/test-repo", "Test PR", "Test description", "test-branch", [], "Test commit"
        )

        assert "Error" in result
        assert "non-empty list" in result

    def test_manage_issues_invalid_action(self):
        """Test manage_issues with invalid action."""
        result = manage_issues("user/test-repo", "invalid_action")

        assert "Error" in result
        assert "Invalid action" in result

    def test_manage_issues_create_no_title(self):
        """Test manage_issues create without title."""
        result = manage_issues("user/test-repo", "create")

        assert "Error" in result
        assert "Title required" in result


class TestErrorHandling:
    """Test error handling in GitHub tools."""

    @patch("grok4git.tools.github_api")
    def test_api_error_handling(self, mock_api):
        """Test API error handling."""
        mock_api.get_paginated_results.side_effect = Exception("API Error")

        result = list_github_repos()

        assert "Error" in result
        assert "API Error" in result

    @patch("grok4git.tools.github_api")
    def test_404_error_handling(self, mock_api):
        """Test 404 error handling."""
        mock_api.make_request.side_effect = Exception("404 Not Found")

        result = get_repo_info("user/nonexistent-repo")

        assert "Error" in result


if __name__ == "__main__":
    pytest.main([__file__])
