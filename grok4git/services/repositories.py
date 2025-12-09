"""
Repository service for GitHub repository operations.
"""

import json
from typing import List, Optional

from .base import BaseService


class RepositoryService(BaseService):
    """Service for repository-related GitHub operations."""

    def list_repositories(self, repo_type: str = "all") -> List[str]:
        """
        List the user's GitHub repositories.

        Args:
            repo_type: Type of repositories to list (all, public, private, forks, sources, member)

        Returns:
            List of repository full names
        """
        url = f"{self.config.github_api_base_url}/user/repos"
        params = {"type": repo_type}

        all_repos = self._get_paginated_results(
            url, params, operation_name=f"list repositories (type: {repo_type})"
        )
        repo_names = [repo["full_name"] for repo in all_repos]

        return repo_names

    def get_repository_info(self, repo: str) -> dict:
        """
        Get metadata information about a GitHub repository.

        Args:
            repo: Repository name in format 'owner/repo'

        Returns:
            Dictionary with repository information
        """
        self._validate_repo_name(repo)
        
        url = f"{self.config.github_api_base_url}/repos/{repo}"
        response = self._make_request("GET", url, operation_name=f"get repository info: {repo}")
        data = response.json()

        info = {
            "full_name": data.get("full_name"),
            "description": data.get("description"),
            "stars": data.get("stargazers_count"),
            "forks": data.get("forks_count"),
            "open_issues": data.get("open_issues_count"),
            "default_branch": data.get("default_branch"),
            "language": data.get("language"),
            "created_at": data.get("created_at"),
            "updated_at": data.get("updated_at"),
            "html_url": data.get("html_url"),
        }

        return info

    def create_repository(
        self, name: str, description: str = "", private: bool = False
    ) -> str:
        """
        Create a new GitHub repository.

        Args:
            name: Repository name
            description: Repository description (optional)
            private: Whether the repository should be private (default: False)

        Returns:
            Repository URL
        """
        url = f"{self.config.github_api_base_url}/user/repos"
        data = {
            "name": name,
            "description": description,
            "private": private,
            "auto_init": True,  # Initialize with README
        }

        response = self._make_request(
            "POST", url, operation_name=f"create repository: {name}", data=data
        )
        repo_data = response.json()

        return repo_data["html_url"]

    def list_branches(self, repo: str) -> List[str]:
        """
        List all branches in a GitHub repository.

        Args:
            repo: Repository name in format 'owner/repo'

        Returns:
            List of branch names
        """
        self._validate_repo_name(repo)
        
        url = f"{self.config.github_api_base_url}/repos/{repo}/branches"
        all_branches = self._get_paginated_results(
            url, operation_name=f"list branches: {repo}"
        )
        branch_names = [branch["name"] for branch in all_branches]

        return branch_names


# Convenience functions for backward compatibility
def list_github_repos(type: str = "all") -> str:
    """List repositories (backward compatibility wrapper)."""
    service = RepositoryService()
    try:
        repos = service.list_repositories(type)
        return json.dumps(repos)
    except ValueError as e:
        return str(e)


def get_repo_info(repo: str) -> str:
    """Get repository info (backward compatibility wrapper)."""
    service = RepositoryService()
    try:
        info = service.get_repository_info(repo)
        return json.dumps(info)
    except ValueError as e:
        return str(e)


def create_repository(name: str, description: str = "", private: bool = False) -> str:
    """Create repository (backward compatibility wrapper)."""
    service = RepositoryService()
    try:
        return service.create_repository(name, description, private)
    except ValueError as e:
        return str(e)


def list_repo_branches(repo: str) -> str:
    """List branches (backward compatibility wrapper)."""
    service = RepositoryService()
    try:
        branches = service.list_branches(repo)
        return json.dumps(branches)
    except ValueError as e:
        return str(e)

