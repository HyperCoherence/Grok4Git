"""
GitHub service layer for Grok4Git.

This package contains domain-specific service modules for GitHub operations.
Each service module handles operations for a specific domain (repositories, files, PRs, etc.).
"""

from .repositories import RepositoryService
from .files import FileService
from .pull_requests import PullRequestService
from .issues import IssueService
from .commits import CommitService
from .search import SearchService

__all__ = [
    "RepositoryService",
    "FileService",
    "PullRequestService",
    "IssueService",
    "CommitService",
    "SearchService",
]

# Backward compatibility - export convenience functions
from .repositories import (
    list_github_repos,
    get_repo_info,
    create_repository,
    list_repo_branches,
)
from .files import (
    get_file_content,
    get_bulk_file_content,
    get_bulk_codebase_overview,
    list_directory_contents,
    recursive_list_directory,
    delete_file,
)
from .pull_requests import (
    create_pull_request,
    merge_pull_request,
    review_pull_request,
    approve_pull_request,
    request_pr_changes,
    iterate_pull_request,
)
from .issues import manage_issues, add_issue_comment
from .commits import (
    get_commit_history,
    get_commit_details,
    get_commit_diff,
    compare_commits,
)
from .search import search_github_repos

