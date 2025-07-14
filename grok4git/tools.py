"""
Tool definitions and implementations for Grok4Git.

This module contains all the GitHub integration tools that can be used
by the AI assistant to perform various GitHub operations.
"""

import base64
import json
import logging
import urllib.parse
from typing import Dict, List, Any, Optional

from .config import config
from .github_api import github_api
from .peer_review import create_peer_review_context, PeerReviewOrchestrator, PeerReviewResult

logger = logging.getLogger(__name__)
# Set tools logger to WARNING level by default to reduce clutter unless in debug mode
if config.log_level != "DEBUG":
    logger.setLevel(logging.WARNING)


def list_github_repos(type: str = "all") -> str:
    """
    List the user's GitHub repositories.

    Args:
        type: Type of repositories to list (all, public, private, forks, sources, member)

    Returns:
        JSON string of repository names
    """
    logger.info(f"Listing GitHub repositories of type: {type}")

    try:
        url = f"{config.github_api_base_url}/user/repos"
        params = {"type": type}

        all_repos = github_api.get_paginated_results(url, params)
        repo_names = [repo["full_name"] for repo in all_repos]

        logger.info(f"Found {len(repo_names)} repositories")
        return json.dumps(repo_names)

    except Exception as e:
        error_msg = f"Error listing repositories: {str(e)}"
        logger.error(error_msg)
        return error_msg


def search_github_repos(query: str) -> str:
    """
    Search for code in the user's GitHub repositories.

    Args:
        query: Search query string

    Returns:
        JSON string of search results
    """
    logger.info(f"Searching repositories for: {query}")

    try:
        encoded_query = urllib.parse.quote(f"{query} user:{config.github_username}")
        url = f"{config.github_api_base_url}/search/code"
        params = {"q": encoded_query}

        all_items = github_api.get_paginated_results(url, params, max_pages=10)

        logger.info(f"Found {len(all_items)} search results")
        return json.dumps(all_items)

    except Exception as e:
        error_msg = f"Error searching repositories: {str(e)}"
        logger.error(error_msg)
        return error_msg


def get_file_content(repo: str, path: str, branch: Optional[str] = None) -> str:
    """
    Get the content of a file in a GitHub repository.

    Args:
        repo: Repository name in format 'owner/repo'
        path: File path
        branch: Branch name (defaults to repository's default branch)

    Returns:
        File content as string or error message
    """
    logger.info(f"Getting file content: {repo}/{path} on branch {branch}")

    try:
        if branch is None:
            branch = github_api.get_default_branch(repo)

        url = f"{config.github_api_base_url}/repos/{repo}/contents/{path}"
        response = github_api.make_request("GET", url, params={"ref": branch})
        data = response.json()

        # Check if it's a directory
        if isinstance(data, list):
            return f"Error: '{path}' is a directory, not a file"

        # Check file size
        file_size = data.get("size", 0)
        max_size_bytes = config.max_file_size_mb * 1024 * 1024

        if file_size > max_size_bytes:
            logger.info(f"File {path} is large ({file_size} bytes), providing summary")
            return _get_large_file_summary(repo, path, branch, file_size)

        # Check if content is available
        if "content" not in data:
            return f"Error: File content not available for '{path}'"

        # Decode base64 content
        content = data["content"]
        try:
            decoded_content = base64.b64decode(content).decode("utf-8")
            logger.info(f"Successfully retrieved file content: {len(decoded_content)} characters")
            return decoded_content

        except UnicodeDecodeError:
            return "Error: File appears to be binary. Content cannot be decoded as UTF-8."

    except Exception as e:
        error_msg = f"Error getting file content: {str(e)}"
        logger.error(error_msg)
        return error_msg


def _get_large_file_summary(repo: str, path: str, branch: str, file_size: int) -> str:
    """
    Get a summary of a large file instead of full content.

    Args:
        repo: Repository name
        path: File path
        branch: Branch name
        file_size: Size of the file in bytes

    Returns:
        Summary of the file
    """
    try:
        # Get raw content in chunks
        raw_content = github_api.get_file_content_raw(repo, path, branch)

        # Get first and last few lines for context
        lines = raw_content.split("\n")
        total_lines = len(lines)

        # Show first 50 and last 20 lines
        first_lines = lines[:50]
        last_lines = lines[-20:] if total_lines > 70 else []

        # Create summary
        summary = f"📄 **Large File Summary: {path}**\n\n"
        summary += f"**File Size:** {file_size:,} bytes\n"
        summary += f"**Total Lines:** {total_lines:,}\n"
        summary += f"**File Type:** {path.split('.')[-1] if '.' in path else 'Unknown'}\n\n"

        summary += "**First 50 lines:**\n```\n"
        summary += "\n".join(first_lines)
        summary += "\n```\n\n"

        if last_lines and total_lines > 70:
            summary += f"**... ({total_lines - 70:,} lines omitted) ...**\n\n"
            summary += "**Last 20 lines:**\n```\n"
            summary += "\n".join(last_lines)
            summary += "\n```\n\n"

        summary += "💡 **Tip:** For specific sections, ask me to search for patterns or functions within this file."

        return summary

    except Exception as e:
        return f"Error getting large file summary: {str(e)}. File size: {file_size:,} bytes"


def _create_files_in_empty_repo(repo: str, files: List[Dict[str, str]], branch: str) -> str:
    """
    Create files in an empty repository using the Contents API.

    Args:
        repo: Repository name in format 'owner/repo'
        files: List of files to create
        branch: Branch name to create files in

    Returns:
        Success message or error message
    """
    logger.info(f"Creating files in empty repository {repo}")

    try:
        # Create files one by one using Contents API
        for file_change in files:
            file_path = file_change["file_path"]
            content = file_change["new_content"]

            # Encode content as base64
            encoded_content = base64.b64encode(content.encode("utf-8")).decode("utf-8")

            url = f"{config.github_api_base_url}/repos/{repo}/contents/{file_path}"
            data = {"message": f"Create {file_path}", "content": encoded_content, "branch": branch}

            github_api.make_request("PUT", url, data=data)
            logger.info(f"Created file: {file_path}")

        return "Files created successfully in empty repository"

    except Exception as e:
        error_msg = f"Error creating files in empty repository: {str(e)}"
        logger.error(error_msg)
        return error_msg


def create_pull_request(
    repo: str,
    title: str,
    body: str,
    new_branch: str,
    files: List[Dict[str, str]],
    commit_message: str,
    base_branch: Optional[str] = None,
    enable_peer_review: Optional[bool] = None,
) -> str:
    """
    Create a pull request in a GitHub repository with changes to multiple files.

    Args:
        repo: Repository name in format 'owner/repo'
        title: Pull request title
        body: Pull request description
        new_branch: Name of the new branch to create
        files: List of files to update/create with their content
        commit_message: Commit message for the changes
        base_branch: Base branch (defaults to repository's default branch)
        enable_peer_review: Enable peer review (defaults to config setting)

    Returns:
        URL of the created pull request or error message
    """
    logger.info(f"Creating pull request in {repo}: {title}")

    try:
        if not files or not isinstance(files, list) or len(files) == 0:
            return "Error: 'files' must be a non-empty list"

        # Determine if peer review should be enabled
        if enable_peer_review is None:
            enable_peer_review = config.pr_peer_review_enabled
        
        # If peer review is enabled, create context and orchestrate review
        if enable_peer_review:
            logger.info("Peer review enabled - initiating peer review process")
            
            try:
                # Create peer review context
                review_context = create_peer_review_context(
                    repo=repo,
                    title=title,
                    body=body,
                    files=files,
                    commit_message=commit_message,
                    branch_name=new_branch,
                    base_branch=base_branch
                )
                
                # Orchestrate peer review
                orchestrator = PeerReviewOrchestrator()
                review_result = orchestrator.orchestrate_review(review_context)
                
                if not review_result.should_proceed:
                    # Return feedback to main agent for iteration
                    return review_result.to_agent_message()
                
                logger.info("Peer review completed successfully - proceeding with GitHub submission")
                
            except Exception as e:
                logger.error(f"Peer review system failed: {str(e)}")
                
                # Fallback: Ask user whether to proceed without peer review
                from rich.console import Console
                from rich.prompt import Prompt
                
                console = Console()
                console.print(f"[red]❌ Peer review system failed: {str(e)}[/red]")
                
                choice = Prompt.ask(
                    "Would you like to proceed with PR creation without peer review?",
                    choices=["y", "n"],
                    default="y"
                )
                
                if choice != "y":
                    return "Pull request creation cancelled due to peer review failure"
                
                logger.info("Proceeding with PR creation without peer review after failure")
                console.print("[yellow]⚠️  Proceeding without peer review due to system failure[/yellow]")
        else:
            logger.info("Peer review disabled - proceeding directly with GitHub submission")

        # Validate repository access and permissions upfront
        try:
            repo_url = f"{config.github_api_base_url}/repos/{repo}"
            repo_response = github_api.make_request("GET", repo_url)
            repo_data = repo_response.json()
            permissions = repo_data.get("permissions", {})

            if not permissions.get("push", False):
                return (
                    f"Error: Insufficient permissions for repository '{repo}'.\n"
                    f"Your GitHub token needs 'push' access to create pull requests.\n"
                    f"Current permissions: {permissions}"
                )
        except Exception as e:
            if "404" in str(e):
                return (
                    f"Error: Repository '{repo}' not found or not accessible.\n"
                    f"Please check:\n"
                    f"  - Repository name is correct\n"
                    f"  - GitHub token has access to this repository\n"
                    f"  - Repository exists and is not private (if using public token)"
                )
            else:
                logger.warning(f"Could not validate repository permissions: {e}")

        if base_branch is None:
            base_branch = github_api.get_default_branch(repo)

        # Get base commit SHA
        ref_url = f"{config.github_api_base_url}/repos/{repo}/git/ref/heads/{base_branch}"
        try:
            response = github_api.make_request("GET", ref_url)
            base_commit_sha = response.json()["object"]["sha"]
        except Exception as e:
            if "404" in str(e):
                # Repository is likely empty - use Contents API to create files directly on new branch
                logger.info(
                    f"Repository {repo} appears to be empty, creating files on new branch {new_branch}"
                )

                # Create files using Contents API directly on the new branch
                create_result = _create_files_in_empty_repo(repo, files, new_branch)
                if "Error" in create_result:
                    return create_result

                # Create pull request (base branch should be empty, new branch has files)
                pr_url = f"{config.github_api_base_url}/repos/{repo}/pulls"
                pr_data = {"title": title, "body": body, "head": new_branch, "base": base_branch}

                try:
                    response = github_api.make_request("POST", pr_url, data=pr_data)
                    pr_html_url = response.json()["html_url"]
                    logger.info(f"Pull request created successfully: {pr_html_url}")
                    return str(pr_html_url)
                except Exception as e4:
                    return f"Error creating pull request: {str(e4)}"
            else:
                raise

        # Get base tree SHA
        commit_url = f"{config.github_api_base_url}/repos/{repo}/git/commits/{base_commit_sha}"
        try:
            response = github_api.make_request("GET", commit_url)
            base_tree_sha = response.json()["tree"]["sha"]
        except Exception as e:
            if "404" in str(e):
                return (
                    f"Error: Unable to get commit tree (404).\n"
                    f"This typically indicates:\n"
                    f"  - Commit SHA '{base_commit_sha}' is invalid\n"
                    f"  - Repository access permissions issue\n"
                    f"Original error: {str(e)}"
                )
            else:
                raise

        # Prepare tree data - GitHub automatically creates directory structure
        tree = []
        for file_change in files:
            tree.append(
                {
                    "path": file_change["file_path"],
                    "mode": "100644",
                    "type": "blob",
                    "content": file_change["new_content"],
                }
            )

        # Create new tree
        tree_url = f"{config.github_api_base_url}/repos/{repo}/git/trees"
        tree_data = {"base_tree": base_tree_sha, "tree": tree}

        try:
            response = github_api.make_request("POST", tree_url, data=tree_data)
            new_tree_sha = response.json()["sha"]
        except Exception as e:
            if "404" in str(e):
                return (
                    f"Error: Unable to create git tree (404). This typically indicates:\n"
                    f"  - Insufficient repository permissions (needs 'push' access)\n"
                    f"  - GitHub token may be expired or invalid\n"
                    f"  - Repository may be private and token lacks access\n"
                    f"  - Temporary GitHub API authentication issue\n"
                    f"  - Invalid base_tree SHA (repository may be empty)\n"
                    f"Note: GitHub automatically creates directory structure for nested file paths.\n"
                    f"Files being created: {[f['file_path'] for f in files]}\n"
                    f"Original error: {str(e)}"
                )
            else:
                raise

        # Create new commit
        commit_url = f"{config.github_api_base_url}/repos/{repo}/git/commits"
        commit_data = {
            "message": commit_message,
            "tree": new_tree_sha,
            "parents": [base_commit_sha],
        }

        try:
            response = github_api.make_request("POST", commit_url, data=commit_data)
            new_commit_sha = response.json()["sha"]
        except Exception as e:
            if "404" in str(e):
                return (
                    f"Error: Unable to create commit (404). This typically indicates:\n"
                    f"  - Authentication/permission issue with repository\n"
                    f"  - GitHub token lacks 'contents:write' permission\n"
                    f"Original error: {str(e)}"
                )
            else:
                raise

        # Create new branch
        branch_url = f"{config.github_api_base_url}/repos/{repo}/git/refs"
        branch_data = {"ref": f"refs/heads/{new_branch}", "sha": new_commit_sha}

        try:
            github_api.make_request("POST", branch_url, data=branch_data)
        except Exception as e:
            if "404" in str(e):
                return (
                    f"Error: Unable to create branch '{new_branch}' (404). This typically indicates:\n"
                    f"  - Insufficient repository permissions\n"
                    f"  - Authentication issue with GitHub token\n"
                    f"Original error: {str(e)}"
                )
            elif "422" in str(e):
                return f"Error: Branch '{new_branch}' already exists. Please use a different branch name."
            else:
                raise

        # Create pull request
        pr_url = f"{config.github_api_base_url}/repos/{repo}/pulls"
        pr_data = {"title": title, "body": body, "head": new_branch, "base": base_branch}

        try:
            response = github_api.make_request("POST", pr_url, data=pr_data)
            pr_html_url = response.json()["html_url"]
            logger.info(f"Pull request created successfully: {pr_html_url}")
            return str(pr_html_url)
        except Exception as e:
            if "404" in str(e):
                return (
                    f"Error: Unable to create pull request (404). This typically indicates:\n"
                    f"  - Insufficient repository permissions\n"
                    f"  - Repository may not allow pull requests\n"
                    f"  - Authentication issue with GitHub token\n"
                    f"Original error: {str(e)}"
                )
            elif "422" in str(e):
                return f"Error: Pull request validation failed. Branch '{new_branch}' may have no changes or already has a PR."
            else:
                raise

    except Exception as e:
        error_msg = f"Error creating pull request: {str(e)}"
        logger.error(error_msg)
        return error_msg


def list_repo_branches(repo: str) -> str:
    """
    List all branches in a GitHub repository.

    Args:
        repo: Repository name in format 'owner/repo'

    Returns:
        JSON string of branch names
    """
    logger.info(f"Listing branches for repository: {repo}")

    try:
        url = f"{config.github_api_base_url}/repos/{repo}/branches"
        all_branches = github_api.get_paginated_results(url)
        branch_names = [branch["name"] for branch in all_branches]

        logger.info(f"Found {len(branch_names)} branches")
        return json.dumps(branch_names)

    except Exception as e:
        error_msg = f"Error listing branches: {str(e)}"
        logger.error(error_msg)
        return error_msg


def list_directory_contents(repo: str, path: str = "", branch: Optional[str] = None) -> str:
    """
    List files and subdirectories in a specified path within a GitHub repository.

    Args:
        repo: Repository name in format 'owner/repo'
        path: Directory path (empty string for root)
        branch: Branch name (defaults to repository's default branch)

    Returns:
        JSON string of directory contents
    """
    logger.info(f"Listing directory contents: {repo}/{path} on branch {branch}")

    try:
        if branch is None:
            branch = github_api.get_default_branch(repo)

        url = f"{config.github_api_base_url}/repos/{repo}/contents/{path}"
        response = github_api.make_request("GET", url, params={"ref": branch})
        data = response.json()

        if not isinstance(data, list):
            return f"Error: '{path}' is not a directory"

        contents = [
            {"name": item["name"], "type": item["type"], "path": item["path"]} for item in data
        ]

        logger.info(f"Found {len(contents)} items in directory")
        return json.dumps(contents)

    except Exception as e:
        error_msg = f"Error listing directory contents: {str(e)}"
        logger.error(error_msg)
        return error_msg


def get_repo_info(repo: str) -> str:
    """
    Get metadata information about a GitHub repository.

    Args:
        repo: Repository name in format 'owner/repo'

    Returns:
        JSON string of repository information
    """
    logger.info(f"Getting repository information: {repo}")

    try:
        url = f"{config.github_api_base_url}/repos/{repo}"
        response = github_api.make_request("GET", url)
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

        logger.info("Retrieved repository information successfully")
        return json.dumps(info)

    except Exception as e:
        error_msg = f"Error getting repository info: {str(e)}"
        logger.error(error_msg)
        return error_msg


def manage_issues(
    repo: str, action: str, title: Optional[str] = None, body: str = "", labels: List[str] = []
) -> str:
    """
    List open issues or create a new issue in a GitHub repository.

    Args:
        repo: Repository name in format 'owner/repo'
        action: Action to perform ('list' or 'create')
        title: Issue title (required for 'create' action)
        body: Issue description (optional for 'create' action)
        labels: List of labels to apply (optional for 'create' action)

    Returns:
        JSON string of issues or URL of created issue
    """
    logger.info(f"Managing issues in {repo}: action={action}")

    try:
        if action == "list":
            url = f"{config.github_api_base_url}/repos/{repo}/issues"
            params = {"state": "open"}

            all_issues = github_api.get_paginated_results(url, params)
            issues = [{"number": issue["number"], "title": issue["title"]} for issue in all_issues]

            logger.info(f"Found {len(issues)} open issues")
            return json.dumps(issues)

        elif action == "create":
            if not title:
                return "Error: Title required for creating an issue"

            url = f"{config.github_api_base_url}/repos/{repo}/issues"
            data = {"title": title, "body": body, "labels": labels}

            response = github_api.make_request("POST", url, data=data)
            issue_url = response.json()["html_url"]

            logger.info(f"Issue created successfully: {issue_url}")
            return str(issue_url)

        else:
            return f"Error: Invalid action '{action}'. Use 'list' or 'create'"

    except Exception as e:
        error_msg = f"Error managing issues: {str(e)}"
        logger.error(error_msg)
        return error_msg


def recursive_list_directory(repo: str, path: str = "", branch: Optional[str] = None) -> str:
    """
    Recursively list all files and subdirectories in a GitHub repository.

    Args:
        repo: Repository name in format 'owner/repo'
        path: Starting directory path (empty string for root)
        branch: Branch name (defaults to repository's default branch)

    Returns:
        JSON string of recursive directory structure
    """
    logger.info(f"Recursively listing directory: {repo}/{path} on branch {branch}")

    def recurse(current_path: str) -> List[Dict[str, Any]]:
        """Recursively get directory contents."""
        try:
            contents_json = list_directory_contents(repo, current_path, branch)
            contents = json.loads(contents_json)

            result = []
            for item in contents:
                if item["type"] == "dir":
                    result.append(
                        {
                            "name": item["name"],
                            "type": "dir",
                            "path": item["path"],
                            "contents": recurse(item["path"]),
                        }
                    )
                else:
                    result.append({"name": item["name"], "type": "file", "path": item["path"]})
            return result

        except Exception as e:
            logger.error(f"Error in recursive listing for {current_path}: {str(e)}")
            return []

    try:
        result = recurse(path)
        logger.info("Recursive listing completed successfully")
        return json.dumps(result)

    except Exception as e:
        error_msg = f"Error in recursive directory listing: {str(e)}"
        logger.error(error_msg)
        return error_msg


def get_commit_history(repo: str, branch: Optional[str] = None, max_commits: int = 10) -> str:
    """
    Get the commit history for a branch in a GitHub repository.

    Args:
        repo: Repository name in format 'owner/repo'
        branch: Branch name (defaults to repository's default branch)
        max_commits: Maximum number of commits to return

    Returns:
        JSON string of commit history
    """
    logger.info(f"Getting commit history for {repo} on branch {branch}")

    try:
        if branch is None:
            branch = github_api.get_default_branch(repo)

        url = f"{config.github_api_base_url}/repos/{repo}/commits"
        params = {"sha": branch, "per_page": max_commits}

        response = github_api.make_request("GET", url, params=params)
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

        logger.info(f"Retrieved {len(commits)} commits")
        return json.dumps(commits)

    except Exception as e:
        error_msg = f"Error getting commit history: {str(e)}"
        logger.error(error_msg)
        return error_msg


def delete_file(
    repo: str, path: str, commit_message: str = "Delete file", branch: Optional[str] = None
) -> str:
    """
    Delete a file in a GitHub repository.

    Args:
        repo: Repository name in format 'owner/repo'
        path: File path to delete
        commit_message: Commit message for the deletion
        branch: Branch name (defaults to repository's default branch)

    Returns:
        Success message or error message
    """
    logger.info(f"Deleting file: {repo}/{path} on branch {branch}")

    try:
        if branch is None:
            branch = github_api.get_default_branch(repo)

        # Get current file SHA
        url = f"{config.github_api_base_url}/repos/{repo}/contents/{path}"
        try:
            response = github_api.make_request("GET", url, params={"ref": branch})
            file_sha = response.json()["sha"]
        except Exception as e:
            if "404" in str(e):
                return f"Error: File '{path}' not found in repository '{repo}' on branch '{branch}'"
            else:
                raise

        # Delete the file
        delete_data = {"message": commit_message, "sha": file_sha, "branch": branch}
        try:
            github_api.make_request("DELETE", url, data=delete_data)
        except Exception as e:
            if "404" in str(e):
                return (
                    f"Error: Unable to delete file (404). This typically indicates:\n"
                    f"  - Insufficient repository permissions (needs 'push' access)\n"
                    f"  - GitHub token authentication issue\n"
                    f"  - File may have been deleted by another process\n"
                    f"Original error: {str(e)}"
                )
            elif "409" in str(e):
                return "Error: File deletion conflict. The file may have been modified since you last accessed it."
            else:
                raise

        logger.info(f"File deleted successfully: {path}")
        return "File deleted successfully"

    except Exception as e:
        error_msg = f"Error deleting file: {str(e)}"
        logger.error(error_msg)
        return error_msg


def get_commit_details(repo: str, commit_sha: str) -> str:
    """
    Get detailed information about a specific commit.

    Args:
        repo: Repository name in format 'owner/repo'
        commit_sha: Commit SHA hash

    Returns:
        JSON string with commit details including files changed, additions, deletions
    """
    logger.info(f"Getting commit details for {repo}: {commit_sha}")

    try:
        url = f"{config.github_api_base_url}/repos/{repo}/commits/{commit_sha}"
        response = github_api.make_request("GET", url)
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

        logger.info(f"Retrieved commit details: {len(details['files'])} files changed")
        return json.dumps(details)

    except Exception as e:
        error_msg = f"Error getting commit details: {str(e)}"
        logger.error(error_msg)
        return error_msg


def get_commit_diff(repo: str, commit_sha: str) -> str:
    """
    Get the diff/patch for a specific commit.

    Args:
        repo: Repository name in format 'owner/repo'
        commit_sha: Commit SHA hash

    Returns:
        String containing the full diff patch
    """
    logger.info(f"Getting commit diff for {repo}: {commit_sha}")

    try:
        url = f"{config.github_api_base_url}/repos/{repo}/commits/{commit_sha}"
        headers = {"Accept": "application/vnd.github.v3.diff"}

        # Get the diff by requesting with diff accept header
        diff_response = github_api.session.get(
            url, headers={**github_api.session.headers, **headers}
        )
        diff_response.raise_for_status()

        diff_content = diff_response.text
        logger.info(f"Retrieved diff content: {len(diff_content)} characters")
        return diff_content

    except Exception as e:
        error_msg = f"Error getting commit diff: {str(e)}"
        logger.error(error_msg)
        return error_msg


def compare_commits(repo: str, base_sha: str, head_sha: str) -> str:
    """
    Compare two commits and show the differences.

    Args:
        repo: Repository name in format 'owner/repo'
        base_sha: Base commit SHA (older commit)
        head_sha: Head commit SHA (newer commit)

    Returns:
        JSON string with comparison details
    """
    logger.info(f"Comparing commits in {repo}: {base_sha}...{head_sha}")

    try:
        url = f"{config.github_api_base_url}/repos/{repo}/compare/{base_sha}...{head_sha}"
        response = github_api.make_request("GET", url)
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

        logger.info(
            f"Comparison complete: {comparison['total_commits']} commits, {len(comparison['files'])} files"
        )
        return json.dumps(comparison)

    except Exception as e:
        error_msg = f"Error comparing commits: {str(e)}"
        logger.error(error_msg)
        return error_msg


def create_repository(name: str, description: str = "", private: bool = False) -> str:
    """
    Create a new GitHub repository.

    Args:
        name: Repository name
        description: Repository description (optional)
        private: Whether the repository should be private (default: False)

    Returns:
        Repository URL or error message
    """
    logger.info(f"Creating repository: {name} (private: {private})")

    try:
        url = f"{config.github_api_base_url}/user/repos"
        data = {
            "name": name,
            "description": description,
            "private": private,
            "auto_init": True,  # Initialize with README
        }

        response = github_api.make_request("POST", url, data=data)
        repo_data = response.json()

        repo_url = repo_data["html_url"]
        logger.info(f"Repository created successfully: {repo_url}")
        return str(repo_url)

    except Exception as e:
        error_msg = f"Error creating repository: {str(e)}"
        logger.error(error_msg)
        return error_msg


def merge_pull_request(repo: str, pr_number: int, merge_method: str = "merge") -> str:
    """Merge a pull request."""
    url = f"{config.github_api_base_url}/repos/{repo}/pulls/{pr_number}/merge"
    data = {"merge_method": merge_method}
    github_api.make_request("PUT", url, data=data)
    return f"Pull request #{pr_number} merged successfully in {repo}."


def add_issue_comment(repo: str, issue_number: int, comment: str) -> str:
    """Add a comment to an issue or pull request."""
    url = f"{config.github_api_base_url}/repos/{repo}/issues/{issue_number}/comments"
    data = {"body": comment}
    github_api.make_request("POST", url, data=data)
    return f"Comment added to issue #{issue_number} in {repo}."


def review_pull_request(
    repo: str,
    title: str,
    body: str,
    files: List[Dict[str, str]],
    commit_message: str,
    branch_name: str,
    base_branch: Optional[str] = None,
) -> str:
    """
    Review a pull request using the peer review agent.
    
    Args:
        repo: Repository name in format 'owner/repo'
        title: Pull request title
        body: Pull request description
        files: List of files with their content
        commit_message: Commit message
        branch_name: Branch name for the PR
        base_branch: Base branch (optional)
    
    Returns:
        JSON string with review results
    """
    logger.info(f"Starting peer review for PR: {title} in {repo}")
    
    try:
        # Create review context
        review_context = create_peer_review_context(
            repo=repo,
            title=title,
            body=body,
            files=files,
            commit_message=commit_message,
            branch_name=branch_name,
            base_branch=base_branch
        )
        
        # Initialize peer review agent
        from .peer_review import PeerReviewAgent
        peer_agent = PeerReviewAgent()
        
        # Perform review
        decision, feedback, suggestions = peer_agent.review_pull_request(review_context)
        
        # Format response
        review_result = {
            "decision": decision.value,
            "feedback": feedback,
            "suggestions": suggestions,
            "repo": repo,
            "title": title,
            "branch_name": branch_name
        }
        
        logger.info(f"Peer review completed with decision: {decision.value}")
        return json.dumps(review_result)
        
    except Exception as e:
        error_msg = f"Error during peer review: {str(e)}"
        logger.error(error_msg)
        return json.dumps({"error": error_msg})


def approve_pull_request(
    repo: str,
    title: str,
    body: str,
    files: List[Dict[str, str]],
    commit_message: str,
    branch_name: str,
    base_branch: Optional[str] = None,
) -> str:
    """
    Approve and submit a pull request to GitHub after peer review.
    
    Args:
        repo: Repository name in format 'owner/repo'
        title: Pull request title
        body: Pull request description
        files: List of files with their content
        commit_message: Commit message
        branch_name: Branch name for the PR
        base_branch: Base branch (optional)
    
    Returns:
        URL of the created pull request or error message
    """
    logger.info(f"Approving and submitting PR: {title} in {repo}")
    
    try:
        # Call create_pull_request with peer review disabled to avoid recursion
        result = create_pull_request(
            repo=repo,
            title=title,
            body=body,
            new_branch=branch_name,
            files=files,
            commit_message=commit_message,
            base_branch=base_branch,
            enable_peer_review=False  # Disable peer review since we're already in review process
        )
        
        logger.info(f"PR approved and submitted: {result}")
        return result
        
    except Exception as e:
        error_msg = f"Error submitting approved PR: {str(e)}"
        logger.error(error_msg)
        return error_msg


def request_pr_changes(
    repo: str,
    title: str,
    feedback: str,
    suggestions: List[str],
    current_iteration: int = 1,
) -> str:
    """
    Request changes for a pull request based on peer review feedback.
    
    Args:
        repo: Repository name in format 'owner/repo'
        title: Pull request title
        feedback: Peer review feedback
        suggestions: List of specific suggestions
        current_iteration: Current review iteration number
    
    Returns:
        Formatted feedback for the original agent
    """
    logger.info(f"Requesting changes for PR: {title} in {repo}")
    
    try:
        # Format the change request
        change_request = {
            "action": "request_changes",
            "repo": repo,
            "title": title,
            "feedback": feedback,
            "suggestions": suggestions,
            "iteration": current_iteration,
            "message": (
                f"Peer review feedback for PR '{title}' in {repo}:\n\n"
                f"**Feedback:** {feedback}\n\n"
                f"**Suggestions:**\n"
                + "\n".join(f"- {suggestion}" for suggestion in suggestions)
            )
        }
        
        logger.info(f"Change request created for iteration {current_iteration}")
        return json.dumps(change_request)
        
    except Exception as e:
        error_msg = f"Error creating change request: {str(e)}"
        logger.error(error_msg)
        return json.dumps({"error": error_msg})


def iterate_pull_request(
    repo: str,
    title: str,
    body: str,
    files: List[Dict[str, str]],
    commit_message: str,
    branch_name: str,
    base_branch: Optional[str] = None,
    feedback_context: Optional[str] = None,
) -> str:
    """
    Create an improved version of a pull request based on peer review feedback.
    This is used by the main agent to iterate on PRs after receiving feedback.
    
    Args:
        repo: Repository name in format 'owner/repo'
        title: Pull request title (can be updated)
        body: Pull request description (can be updated)
        files: Updated list of files with improvements
        commit_message: Updated commit message
        branch_name: New branch name for the iteration
        base_branch: Base branch (optional)
        feedback_context: Previous peer review feedback (optional)
    
    Returns:
        Result of the improved pull request creation
    """
    logger.info(f"Iterating on PR: {title} in {repo}")
    
    try:
        # Add feedback context to the PR description if provided
        if feedback_context:
            body = f"{body}\n\n---\n**Peer Review Iteration:**\nAddressed feedback: {feedback_context}"
        
        # Create the improved pull request with peer review enabled
        result = create_pull_request(
            repo=repo,
            title=title,
            body=body,
            new_branch=branch_name,
            files=files,
            commit_message=commit_message,
            base_branch=base_branch,
            enable_peer_review=True  # Always enable peer review for iterations
        )
        
        logger.info(f"PR iteration completed: {result}")
        return result
        
    except Exception as e:
        error_msg = f"Error iterating on PR: {str(e)}"
        logger.error(error_msg)
        return error_msg


# Tool definitions for the AI
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_github_repos",
            "description": "List the user's GitHub repositories.",
            "parameters": {
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": ["all", "public", "private", "forks", "sources", "member"],
                        "description": "Type of repositories to list",
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
            "description": "Search for code in the user's GitHub repositories.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "Search query"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_file_content",
            "description": "Get the content of a file in a GitHub repository.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Repository name, e.g., username/repo",
                    },
                    "path": {"type": "string", "description": "File path"},
                    "branch": {
                        "type": "string",
                        "description": "Branch name, defaults to repo's default branch",
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
            "name": "create_pull_request",
            "description": "Create a pull request with file changes. WORKFLOW: (1) Creates new branch, (2) Commits all files to that branch, (3) Optional peer review by second AI agent, (4) Opens PR from new branch to base branch. AUTOMATICALLY HANDLES: Empty repositories (creates files on new branch), nested directory creation (via GitHub Tree API), and comprehensive error recovery. PEER REVIEW: When enabled, a second AI agent reviews the PR before GitHub submission for improved code quality. IMPORTANT: Branch name must be unique and use only letters, numbers, hyphens, underscores. Max file size 1MB each.",
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
                        "description": "Array of files to create/update. Each file will be committed to the new branch. Example: [{'file_path': 'src/main.py', 'new_content': 'print(\"hello\")'}]",
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
                        "description": "Enable peer review by second AI agent before GitHub submission (defaults to config setting)",
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
            "description": "List all branches in a GitHub repository.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Repository name, e.g., username/repo",
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
            "description": "List files and subdirectories in a specified path within a GitHub repository.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Repository name, e.g., username/repo",
                    },
                    "path": {
                        "type": "string",
                        "description": "Directory path, default root",
                        "default": "",
                    },
                    "branch": {
                        "type": "string",
                        "description": "Branch name, defaults to repo's default",
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
            "description": "Get metadata information about a GitHub repository.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Repository name, e.g., username/repo",
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
            "description": "List open issues or create a new issue in a GitHub repository.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Repository name, e.g., username/repo",
                    },
                    "action": {
                        "type": "string",
                        "enum": ["list", "create"],
                        "description": "Action to perform",
                    },
                    "title": {"type": "string", "description": "Issue title (for create)"},
                    "body": {
                        "type": "string",
                        "description": "Issue body (for create)",
                        "default": "",
                    },
                    "labels": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Labels for the issue (for create)",
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
            "description": "Recursively list all files and subdirectories in a GitHub repository.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Repository name, e.g., username/repo",
                    },
                    "path": {
                        "type": "string",
                        "description": "Starting directory path, default root",
                        "default": "",
                    },
                    "branch": {
                        "type": "string",
                        "description": "Branch name, defaults to repo's default",
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
            "description": "Get the commit history for a branch in a GitHub repository.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Repository name, e.g., username/repo",
                    },
                    "branch": {
                        "type": "string",
                        "description": "Branch name, defaults to repo's default",
                        "default": None,
                    },
                    "max_commits": {
                        "type": "integer",
                        "description": "Maximum number of commits to return, default 10",
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
            "description": "Get detailed information about a specific commit including files changed, additions, deletions, and statistics. Use this for commit analysis and code review. Returns JSON with commit metadata and file change details.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Repository name in format 'owner/repo', e.g., 'octocat/Hello-World'",
                    },
                    "commit_sha": {
                        "type": "string",
                        "description": "Full commit SHA hash (40 characters) or short SHA (7+ characters), e.g., 'a1b2c3d4e5f6' or 'a1b2c3d'",
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
            "description": "Compare two commits and show the differences between them.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Repository name, e.g., username/repo",
                    },
                    "base_sha": {"type": "string", "description": "Base commit SHA (older commit)"},
                    "head_sha": {"type": "string", "description": "Head commit SHA (newer commit)"},
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


# Tool function mapping
TOOL_FUNCTIONS = {
    "list_github_repos": list_github_repos,
    "search_github_repos": search_github_repos,
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
