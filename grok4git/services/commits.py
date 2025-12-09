"""
Commit service for GitHub commit operations.
"""

import json
from typing import Dict, List, Any

from .base import BaseService


class CommitService(BaseService):
    """Service for commit-related GitHub operations."""

    def get_commit_history(
        self, repo: str, branch: str = None, max_commits: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get the commit history for a branch in a GitHub repository.

        Args:
            repo: Repository name in format 'owner/repo'
            branch: Branch name (defaults to repository's default branch)
            max_commits: Maximum number of commits to return

        Returns:
            List of commit dictionaries
        """
        self._validate_repo_name(repo)
        
        if branch is None:
            branch = self.api.get_default_branch(repo)

        url = f"{self.config.github_api_base_url}/repos/{repo}/commits"
        params = {"sha": branch, "per_page": max_commits}

        response = self._make_request(
            "GET", url, operation_name=f"get commit history: {repo}", params=params
        )
        commits_data = response.json()

        commits = [
            {
                "sha": commit["sha"],
                "message": commit["commit"]["message"],
                "author": commit["commit"]["author"]["name"],
                "date": commit["commit"]["author"]["date"],
            }
            for commit in commits_data
        ]

        return commits

    def get_commit_details(self, repo: str, commit_sha: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific commit.

        Args:
            repo: Repository name in format 'owner/repo'
            commit_sha: Commit SHA hash

        Returns:
            Dictionary with commit details
        """
        self._validate_repo_name(repo)
        
        url = f"{self.config.github_api_base_url}/repos/{repo}/commits/{commit_sha}"
        response = self._make_request(
            "GET", url, operation_name=f"get commit details: {repo}/{commit_sha}"
        )
        commit_data = response.json()

        # Extract key information
        details = {
            "sha": commit_data["sha"],
            "message": commit_data["commit"]["message"],
            "author": {
                "name": commit_data["commit"]["author"]["name"],
                "email": commit_data["commit"]["author"]["email"],
                "date": commit_data["commit"]["author"]["date"],
            },
            "committer": {
                "name": commit_data["commit"]["committer"]["name"],
                "email": commit_data["commit"]["committer"]["email"],
                "date": commit_data["commit"]["committer"]["date"],
            },
            "stats": commit_data["stats"],
            "files": [
                {
                    "filename": file["filename"],
                    "status": file["status"],
                    "additions": file["additions"],
                    "deletions": file["deletions"],
                    "changes": file["changes"],
                }
                for file in commit_data["files"]
            ],
            "url": commit_data["html_url"],
        }

        return details

    def get_commit_diff(self, repo: str, commit_sha: str) -> str:
        """
        Get the diff/patch for a specific commit.

        Args:
            repo: Repository name in format 'owner/repo'
            commit_sha: Commit SHA hash

        Returns:
            String containing the full diff patch
        """
        self._validate_repo_name(repo)
        
        url = f"{self.config.github_api_base_url}/repos/{repo}/commits/{commit_sha}"
        headers = {"Accept": "application/vnd.github.v3.diff"}

        # Get the diff by requesting with diff accept header
        diff_response = self.api.session.get(
            url, headers={**self.api.session.headers, **headers}
        )
        diff_response.raise_for_status()

        return diff_response.text

    def compare_commits(self, repo: str, base_sha: str, head_sha: str) -> Dict[str, Any]:
        """
        Compare two commits and show the differences.

        Args:
            repo: Repository name in format 'owner/repo'
            base_sha: Base commit SHA (older commit)
            head_sha: Head commit SHA (newer commit)

        Returns:
            Dictionary with comparison details
        """
        self._validate_repo_name(repo)
        
        url = f"{self.config.github_api_base_url}/repos/{repo}/compare/{base_sha}...{head_sha}"
        response = self._make_request(
            "GET", url, operation_name=f"compare commits: {repo}"
        )
        comparison_data = response.json()

        # Extract key comparison information
        comparison = {
            "base_commit": {
                "sha": comparison_data["base_commit"]["sha"],
                "message": comparison_data["base_commit"]["commit"]["message"],
            },
            "head_commit": {
                "sha": comparison_data["head_commit"]["sha"],
                "message": comparison_data["head_commit"]["commit"]["message"],
            },
            "status": comparison_data["status"],
            "ahead_by": comparison_data["ahead_by"],
            "behind_by": comparison_data["behind_by"],
            "total_commits": comparison_data["total_commits"],
            "files": [
                {
                    "filename": file["filename"],
                    "status": file["status"],
                    "additions": file["additions"],
                    "deletions": file["deletions"],
                    "changes": file["changes"],
                }
                for file in comparison_data["files"]
            ],
            "url": comparison_data["html_url"],
        }

        return comparison


# Convenience functions for backward compatibility
def get_commit_history(repo: str, branch: str = None, max_commits: int = 10) -> str:
    """Get commit history (backward compatibility wrapper)."""
    service = CommitService()
    try:
        commits = service.get_commit_history(repo, branch, max_commits)
        return json.dumps(commits)
    except ValueError as e:
        return str(e)


def get_commit_details(repo: str, commit_sha: str) -> str:
    """Get commit details (backward compatibility wrapper)."""
    service = CommitService()
    try:
        details = service.get_commit_details(repo, commit_sha)
        return json.dumps(details)
    except ValueError as e:
        return str(e)


def get_commit_diff(repo: str, commit_sha: str) -> str:
    """Get commit diff (backward compatibility wrapper)."""
    service = CommitService()
    try:
        return service.get_commit_diff(repo, commit_sha)
    except ValueError as e:
        return str(e)


def compare_commits(repo: str, base_sha: str, head_sha: str) -> str:
    """Compare commits (backward compatibility wrapper)."""
    service = CommitService()
    try:
        comparison = service.compare_commits(repo, base_sha, head_sha)
        return json.dumps(comparison)
    except ValueError as e:
        return str(e)

