"""
Issue service for GitHub issue operations.
"""

import json
from typing import List, Dict, Optional

from .base import BaseService


class IssueService(BaseService):
    """Service for issue-related GitHub operations."""

    def list_issues(self, repo: str) -> List[Dict[str, any]]:
        """
        List open issues in a GitHub repository.

        Args:
            repo: Repository name in format 'owner/repo'

        Returns:
            List of issue dictionaries
        """
        self._validate_repo_name(repo)
        
        url = f"{self.config.github_api_base_url}/repos/{repo}/issues"
        params = {"state": "open"}

        all_issues = self._get_paginated_results(
            url, params, operation_name=f"list issues: {repo}"
        )
        issues = [{"number": issue["number"], "title": issue["title"]} for issue in all_issues]

        return issues

    def create_issue(
        self, repo: str, title: str, body: str = "", labels: List[str] = None
    ) -> str:
        """
        Create a new issue in a GitHub repository.

        Args:
            repo: Repository name in format 'owner/repo'
            title: Issue title
            body: Issue description (optional)
            labels: List of labels to apply (optional)

        Returns:
            Issue URL
        """
        self._validate_repo_name(repo)
        
        if not title:
            raise ValueError("Title required for creating an issue")

        if labels is None:
            labels = []

        url = f"{self.config.github_api_base_url}/repos/{repo}/issues"
        data = {"title": title, "body": body, "labels": labels}

        response = self._make_request(
            "POST", url, operation_name=f"create issue: {repo}", data=data
        )
        return response.json()["html_url"]

    def add_comment(self, repo: str, issue_number: int, comment: str) -> str:
        """
        Add a comment to an issue or pull request.

        Args:
            repo: Repository name in format 'owner/repo'
            issue_number: Issue or PR number
            comment: Comment text

        Returns:
            Success message
        """
        self._validate_repo_name(repo)
        
        url = f"{self.config.github_api_base_url}/repos/{repo}/issues/{issue_number}/comments"
        data = {"body": comment}

        self._make_request(
            "POST", url, operation_name=f"add comment to issue #{issue_number}: {repo}", data=data
        )
        return f"Comment added to issue #{issue_number} in {repo}."


# Convenience function for backward compatibility
def manage_issues(
    repo: str, action: str, title: Optional[str] = None, body: str = "", labels: List[str] = None
) -> str:
    """Manage issues (backward compatibility wrapper)."""
    service = IssueService()
    try:
        if action == "list":
            issues = service.list_issues(repo)
            return json.dumps(issues)
        elif action == "create":
            if not title:
                return "Error: Title required for creating an issue"
            return service.create_issue(repo, title, body, labels or [])
        else:
            return f"Error: Invalid action '{action}'. Use 'list' or 'create'"
    except ValueError as e:
        return str(e)


def add_issue_comment(repo: str, issue_number: int, comment: str) -> str:
    """Add issue comment (backward compatibility wrapper)."""
    service = IssueService()
    try:
        return service.add_comment(repo, issue_number, comment)
    except ValueError as e:
        return str(e)

