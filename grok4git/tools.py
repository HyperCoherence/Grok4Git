"""
Tool definitions and implementations for Grok4Git.

This module maintains backward compatibility by re-exporting tools from
the new services-based structure. All tool implementations have been
moved to domain-specific service modules in the services package.

DEPRECATED: This module is kept for backward compatibility. New code should
import from grok4git.services or grok4git.tools directly.
"""

# Import all tool functions from services (backward compatibility)
from .services import (
    list_github_repos,
    search_github_repos,
    get_bulk_codebase_overview,
    get_bulk_file_content,
    get_file_content,
    create_pull_request,
    list_repo_branches,
    list_directory_contents,
    get_repo_info,
    manage_issues,
    recursive_list_directory,
    get_commit_history,
    delete_file,
    get_commit_details,
    get_commit_diff,
    compare_commits,
    create_repository,
    merge_pull_request,
    add_issue_comment,
    review_pull_request,
    approve_pull_request,
    request_pr_changes,
    iterate_pull_request,
)

# Tool function mapping (functions imported from services above)
TOOL_FUNCTIONS = {
    "list_github_repos": list_github_repos,
    "search_github_repos": search_github_repos,
    "get_bulk_codebase_overview": get_bulk_codebase_overview,
    "get_bulk_file_content": get_bulk_file_content,
    "get_file_content": get_file_content,
    "create_pull_request": create_pull_request,
    "list_repo_branches": list_repo_branches,
    "list_directory_contents": list_directory_contents,
    "get_repo_info": get_repo_info,
    "manage_issues": manage_issues,
    "recursive_list_directory": recursive_list_directory,
    "get_commit_history": get_commit_history,
    "delete_file": delete_file,
    "get_commit_details": get_commit_details,
    "get_commit_diff": get_commit_diff,
    "compare_commits": compare_commits,
    "create_repository": create_repository,
    "merge_pull_request": merge_pull_request,
    "add_issue_comment": add_issue_comment,
    "review_pull_request": review_pull_request,
    "approve_pull_request": approve_pull_request,
    "request_pr_changes": request_pr_changes,
    "iterate_pull_request": iterate_pull_request,
}

__all__ = ["TOOLS", "TOOL_FUNCTIONS"]

# Keep TOOLS definition here for backward compatibility
# TODO: Move to tools/registry.py in future refactoring
# Tool definitions for the AI
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_github_repos",
            "description": "List the authenticated user's GitHub repositories with optional filtering by type (all, public, private, forks, sources, member). Returns repository full names in 'owner/repo' format. Use this to discover available repositories before performing operations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": ["all", "public", "private", "forks", "sources", "member"],
                        "description": "Type of repositories to list: 'all' (default), 'public', 'private', 'forks', 'sources', or 'member'",
                        "default": "all",
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_github_repos",
            "description": "Search for code across the authenticated user's GitHub repositories using GitHub's code search API. Searches file contents, not just filenames. Returns matching files with code snippets. Useful for finding where specific code patterns, functions, or keywords are used across repositories.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "Search query string (e.g., 'function authenticate', 'class User', 'import requests')"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_bulk_codebase_overview",
            "description": "Get an intelligent overview of a codebase by automatically discovering and reading important files (README, config files, main source files) in a structured format. Automatically identifies key files like package.json, requirements.txt, setup.py, main entry points, and documentation. Returns structured output with file separators. Best for understanding new repositories quickly without manual file exploration. Use this as the first step when analyzing an unfamiliar repository.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Repository name in format 'owner/repo', e.g., 'microsoft/vscode'",
                    },
                    "branch": {
                        "type": "string",
                        "description": "Branch name (optional, defaults to repository's default branch)",
                    },
                    "max_files": {
                        "type": "integer",
                        "description": "Maximum number of files to read (default: 20). Increase for larger codebases.",
                        "default": 20,
                    },
                },
                "required": ["repo"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_bulk_file_content",
            "description": "Get the content of multiple specific files in a GitHub repository as a single structured blob. BEHAVIOR: More efficient than reading files individually and provides better context about codebase structure. Files larger than 1MB are automatically skipped with notes. Returns structured output with file separators. IMPORTANT: Use this for reading multiple related files at once - much faster than individual calls.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Repository name in format 'owner/repo', e.g., 'microsoft/vscode'",
                    },
                    "paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of file paths to read relative to repository root, e.g., ['src/main.py', 'README.md', 'package.json']",
                    },
                    "branch": {
                        "type": "string",
                        "description": "Branch name (optional, defaults to repository's default branch)",
                    },
                },
                "required": ["repo", "paths"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_file_content",
            "description": "Get the content of a single file in a GitHub repository. BEHAVIOR: Returns the complete file content as a string. For files larger than 1MB, returns a summary with first/last lines. Binary files return an error. IMPORTANT: This reads the file at the specified branch/commit - use 'branch' parameter for non-default branches.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Repository name in format 'owner/repo', e.g., 'microsoft/vscode'",
                    },
                    "path": {
                        "type": "string",
                        "description": "File path relative to repository root, e.g., 'src/main.py' or 'README.md'",
                    },
                    "branch": {
                        "type": "string",
                        "description": "Branch name (optional, defaults to repository's default branch)",
                    },
                },
                "required": ["repo", "path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_pull_request",
            "description": "Create a pull request with file changes. WORKFLOW: (1) Creates new branch, (2) Commits all files to that branch, (3) Optional peer review by second AI agent, (4) Opens PR from new branch to base branch. AUTOMATICALLY HANDLES: Empty repositories (creates files on new branch), nested directory creation (via GitHub Tree API), and comprehensive error recovery. PEER REVIEW: When enabled, a second AI agent reviews the PR before GitHub submission for improved code quality. IMPORTANT: Branch name must be unique and use only letters, numbers, hyphens, underscores. Max file size 1MB each. BEHAVIOR: Uses GitHub Tree API with base_tree parameter - this preserves ALL existing files and only modifies/adds the specified files. Does NOT delete existing files unless explicitly specified.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Repository name in format 'owner/repo', e.g., 'octocat/Hello-World'",
                    },
                    "title": {
                        "type": "string",
                        "description": "Pull request title - should be descriptive and concise",
                    },
                    "body": {
                        "type": "string",
                        "description": "Pull request description - explain what changes are being made and why",
                    },
                    "new_branch": {
                        "type": "string",
                        "description": "New branch name - MUST be unique, use format like 'feature/description' or 'fix/issue-name'. Only letters, numbers, hyphens, underscores allowed",
                    },
                    "files": {
                        "type": "array",
                        "description": "Array of files to create/update. Each file will be committed to the new branch. IMPORTANT: Only files specified here will be modified - existing files are preserved unless explicitly included. Example: [{'file_path': 'src/main.py', 'new_content': 'print(\"hello\")'}]",
                        "items": {
                            "type": "object",
                            "properties": {
                                "file_path": {
                                    "type": "string",
                                    "description": "File path relative to repository root, e.g., 'src/utils.py' or 'README.md'",
                                },
                                "new_content": {
                                    "type": "string",
                                    "description": "Complete file content as string. For code files, include proper formatting/indentation",
                                },
                            },
                            "required": ["file_path", "new_content"],
                        },
                    },
                    "commit_message": {
                        "type": "string",
                        "description": "Commit message for the changes, e.g., 'feat: add new utility functions' or 'fix: resolve authentication issue'",
                    },
                    "base_branch": {
                        "type": "string",
                        "description": "Target branch for PR (defaults to repo's default branch like 'main' or 'master')",
                        "default": None,
                    },
                    "enable_peer_review": {
                        "type": "boolean",
                        "description": "Enable peer review by second AI agent before GitHub submission (defaults to config setting). When enabled, a second AI agent with tool access reviews the PR for quality, security, and best practices.",
                        "default": None,
                    },
                    "user_request_context": {
                        "type": "string",
                        "description": "Original user request for context in peer review (optional but recommended for better reviews)",
                        "default": None,
                    },
                },
                "required": ["repo", "title", "body", "new_branch", "files", "commit_message"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_repo_branches",
            "description": "List all branches in a repository. Returns branch names. Useful for understanding repository structure, identifying feature branches, checking for stale branches, and ensuring branch name uniqueness before creating new branches. Essential for branch management and PR creation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Repository name in format 'owner/repo', e.g., 'microsoft/vscode'",
                    }
                },
                "required": ["repo"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_directory_contents",
            "description": "List files and subdirectories in a specified path within a repository. Returns file and directory names with types. Use this to explore repository structure, navigate directories, and identify files before reading them. More efficient than recursive_list_directory for specific paths.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Repository name in format 'owner/repo', e.g., 'microsoft/vscode'",
                    },
                    "path": {
                        "type": "string",
                        "description": "Directory path relative to repository root (default: empty string for root directory)",
                        "default": "",
                    },
                    "branch": {
                        "type": "string",
                        "description": "Branch name (optional, defaults to repository's default branch)",
                        "default": None,
                    },
                },
                "required": ["repo"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_repo_info",
            "description": "Get comprehensive repository metadata including stars, forks, open issues count, default branch, primary language, creation/update dates, and repository URL. Use this to quickly assess repository status, popularity, and basic health metrics. Essential first step for repository analysis.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Repository name in format 'owner/repo', e.g., 'microsoft/vscode'",
                    }
                },
                "required": ["repo"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "manage_issues",
            "description": "Manage issues in a repository. Use action='list' to retrieve all open issues with numbers and titles (returns JSON array). Use action='create' with title (required) and optional body/labels to create a new issue (returns issue URL). Essential for tracking bugs, feature requests, and repository maintenance tasks.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Repository name in format 'owner/repo', e.g., 'microsoft/vscode'",
                    },
                    "action": {
                        "type": "string",
                        "enum": ["list", "create"],
                        "description": "Action to perform: 'list' to retrieve open issues, 'create' to create a new issue",
                    },
                    "title": {"type": "string", "description": "Issue title (required for 'create' action)"},
                    "body": {
                        "type": "string",
                        "description": "Issue description/body (optional, for 'create' action)",
                        "default": "",
                    },
                    "labels": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Labels to apply to the issue (optional, for 'create' action)",
                        "default": [],
                    },
                },
                "required": ["repo", "action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "recursive_list_directory",
            "description": "Recursively list all files and subdirectories in a repository starting from a path (defaults to root). Returns complete directory tree structure. NOTE: For large repositories, this may be slow. Consider using list_directory_contents for specific paths instead. Useful for getting full repository structure when needed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Repository name in format 'owner/repo', e.g., 'microsoft/vscode'",
                    },
                    "path": {
                        "type": "string",
                        "description": "Starting directory path relative to repository root (default: empty string for root)",
                        "default": "",
                    },
                    "branch": {
                        "type": "string",
                        "description": "Branch name (optional, defaults to repository's default branch)",
                        "default": None,
                    },
                },
                "required": ["repo"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_commit_history",
            "description": "Get commit history for a specific branch (defaults to repository's default branch). Returns commit messages, authors, dates, and SHAs. Use max_commits to limit results. Essential for understanding recent changes, activity patterns, and finding specific commits for detailed analysis. Use this before get_commit_details or get_commit_diff to identify commits of interest.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Repository name in format 'owner/repo', e.g., 'microsoft/vscode'",
                    },
                    "branch": {
                        "type": "string",
                        "description": "Branch name (optional, defaults to repository's default branch)",
                        "default": None,
                    },
                    "max_commits": {
                        "type": "integer",
                        "description": "Maximum number of commits to return (default: 10). Increase for longer history.",
                        "default": 10,
                    },
                },
                "required": ["repo"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_file",
            "description": "Delete a file from a GitHub repository. WARNING: This is a destructive operation that requires user confirmation. The file will be permanently removed from the repository. Use get_file_content first to verify the file exists.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Repository name in format 'owner/repo', e.g., 'octocat/Hello-World'",
                    },
                    "path": {
                        "type": "string",
                        "description": "Exact file path relative to repository root, e.g., 'src/old_file.py' or 'docs/deprecated.md'",
                    },
                    "commit_message": {
                        "type": "string",
                        "description": "Descriptive commit message for the deletion, e.g., 'remove deprecated utility functions'",
                        "default": "Delete file",
                    },
                    "branch": {
                        "type": "string",
                        "description": "Branch to delete from (defaults to repository's default branch)",
                        "default": None,
                    },
                },
                "required": ["repo", "path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_commit_details",
            "description": "Get detailed information about a specific commit including files changed, additions, deletions, and statistics. Returns commit metadata (SHA, message, author, date) and file-level change details with status (added/modified/deleted). Use this for commit analysis, code review, and understanding what a commit actually changed. Essential for understanding commit impact. TIP: Use get_commit_history first to find commit SHAs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Repository name in format 'owner/repo', e.g., 'octocat/Hello-World'",
                    },
                    "commit_sha": {
                        "type": "string",
                        "description": "Full commit SHA hash (40 characters) or short SHA (7+ characters). TIP: Use get_commit_history first to find the commit SHA, e.g., 'a1b2c3d4e5f6' or 'a1b2c3d'",
                    },
                },
                "required": ["repo", "commit_sha"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_commit_diff",
            "description": "Get the diff/patch for a specific commit showing exact code changes (additions/deletions). Perfect for peer review and understanding what actually changed. Returns unified diff format showing line-by-line changes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Repository name in format 'owner/repo', e.g., 'octocat/Hello-World'",
                    },
                    "commit_sha": {
                        "type": "string",
                        "description": "Full commit SHA hash (40 characters) or short SHA (7+ characters). TIP: Use get_commit_history first to find the commit SHA",
                    },
                },
                "required": ["repo", "commit_sha"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_commits",
            "description": "Compare two commits (base and head) to show file changes, additions, deletions, and statistics. Returns structured diff information showing what changed between the commits. Useful for understanding the impact of changes, reviewing feature development, and analyzing differences between versions. Use base_sha for the older commit and head_sha for the newer commit.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Repository name in format 'owner/repo', e.g., 'microsoft/vscode'",
                    },
                    "base_sha": {"type": "string", "description": "Base commit SHA (older commit) - the starting point for comparison"},
                    "head_sha": {"type": "string", "description": "Head commit SHA (newer commit) - the ending point for comparison"},
                },
                "required": ["repo", "base_sha", "head_sha"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_repository",
            "description": "Create a new GitHub repository. NOTE: This operation requires user confirmation. Repository will be created under the authenticated user's account and automatically initialized with a README file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Repository name - must be unique under your account. Use descriptive names like 'my-awesome-project' or 'data-analysis-tool'",
                    },
                    "description": {
                        "type": "string",
                        "description": "Repository description - briefly explain what this repository is for",
                        "default": "",
                    },
                    "private": {
                        "type": "boolean",
                        "description": "Repository visibility: true for private (only you can see), false for public (everyone can see)",
                        "default": False,
                    },
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "review_pull_request",
            "description": "Review a pull request using the peer review agent before GitHub submission.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Repository name in format 'owner/repo'",
                    },
                    "title": {
                        "type": "string",
                        "description": "Pull request title",
                    },
                    "body": {
                        "type": "string",
                        "description": "Pull request description",
                    },
                    "files": {
                        "type": "array",
                        "description": "List of files with their content",
                        "items": {
                            "type": "object",
                            "properties": {
                                "file_path": {"type": "string"},
                                "new_content": {"type": "string"},
                            },
                            "required": ["file_path", "new_content"],
                        },
                    },
                    "commit_message": {
                        "type": "string",
                        "description": "Commit message",
                    },
                    "branch_name": {
                        "type": "string",
                        "description": "Branch name for the PR",
                    },
                    "base_branch": {
                        "type": "string",
                        "description": "Base branch (optional)",
                        "default": None,
                    },
                },
                "required": ["repo", "title", "body", "files", "commit_message", "branch_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "approve_pull_request",
            "description": "Approve and submit a pull request to GitHub after peer review approval.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Repository name in format 'owner/repo'",
                    },
                    "title": {
                        "type": "string",
                        "description": "Pull request title",
                    },
                    "body": {
                        "type": "string",
                        "description": "Pull request description",
                    },
                    "files": {
                        "type": "array",
                        "description": "List of files with their content",
                        "items": {
                            "type": "object",
                            "properties": {
                                "file_path": {"type": "string"},
                                "new_content": {"type": "string"},
                            },
                            "required": ["file_path", "new_content"],
                        },
                    },
                    "commit_message": {
                        "type": "string",
                        "description": "Commit message",
                    },
                    "branch_name": {
                        "type": "string",
                        "description": "Branch name for the PR",
                    },
                    "base_branch": {
                        "type": "string",
                        "description": "Base branch (optional)",
                        "default": None,
                    },
                },
                "required": ["repo", "title", "body", "files", "commit_message", "branch_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "request_pr_changes",
            "description": "Request changes for a pull request based on peer review feedback.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Repository name in format 'owner/repo'",
                    },
                    "title": {
                        "type": "string",
                        "description": "Pull request title",
                    },
                    "feedback": {
                        "type": "string",
                        "description": "Peer review feedback",
                    },
                    "suggestions": {
                        "type": "array",
                        "description": "List of specific suggestions",
                        "items": {"type": "string"},
                    },
                    "current_iteration": {
                        "type": "integer",
                        "description": "Current review iteration number",
                        "default": 1,
                    },
                },
                "required": ["repo", "title", "feedback", "suggestions"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "iterate_pull_request",
            "description": "Create an improved version of a pull request based on peer review feedback. Use this after receiving feedback from peer review to implement suggestions and resubmit the PR.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Repository name in format 'owner/repo'",
                    },
                    "title": {
                        "type": "string",
                        "description": "Pull request title (can be updated based on feedback)",
                    },
                    "body": {
                        "type": "string",
                        "description": "Pull request description (can be updated based on feedback)",
                    },
                    "files": {
                        "type": "array",
                        "description": "Updated list of files with improvements based on peer review feedback",
                        "items": {
                            "type": "object",
                            "properties": {
                                "file_path": {"type": "string"},
                                "new_content": {"type": "string"},
                            },
                            "required": ["file_path", "new_content"],
                        },
                    },
                    "commit_message": {
                        "type": "string",
                        "description": "Updated commit message reflecting the changes made",
                    },
                    "branch_name": {
                        "type": "string",
                        "description": "New branch name for the iteration (should be different from previous attempts)",
                    },
                    "base_branch": {
                        "type": "string",
                        "description": "Base branch (optional)",
                        "default": None,
                    },
                    "feedback_context": {
                        "type": "string",
                        "description": "Previous peer review feedback being addressed (optional)",
                        "default": None,
                    },
                },
                "required": ["repo", "title", "body", "files", "commit_message", "branch_name"],
            },
        },
    },
]
