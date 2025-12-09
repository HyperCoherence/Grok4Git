"""
Pull request service for GitHub PR operations.
"""

import base64
import json
from typing import List, Dict, Optional

from ..peer_review import create_peer_review_context, PeerReviewOrchestrator
from .base import BaseService


class PullRequestService(BaseService):
    """Service for pull request-related GitHub operations."""

    def create_pull_request(
        self,
        repo: str,
        title: str,
        body: str,
        new_branch: str,
        files: List[Dict[str, str]],
        commit_message: str,
        base_branch: Optional[str] = None,
        enable_peer_review: Optional[bool] = None,
        user_request_context: Optional[str] = None,
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
            user_request_context: Original user request for context in peer review

        Returns:
            URL of the created pull request
        """
        logger.info(f"Creating pull request in {repo}: {title}")

        try:
            if not files or not isinstance(files, list) or len(files) == 0:
                raise ValueError("'files' must be a non-empty list")

            # Determine if peer review should be enabled
            if enable_peer_review is None:
                enable_peer_review = self.config.pr_peer_review_enabled

            # If peer review is enabled, create context and orchestrate review
            if enable_peer_review:
                logger.info("Peer review enabled - initiating peer review process")

                try:
                    # Create peer review context with user request context
                    review_context = create_peer_review_context(
                        repo=repo,
                        title=title,
                        body=body,
                        files=files,
                        commit_message=commit_message,
                        branch_name=new_branch,
                        base_branch=base_branch,
                        user_request=user_request_context,
                    )

                    # Orchestrate peer review
                    orchestrator = PeerReviewOrchestrator()
                    review_result = orchestrator.orchestrate_review(review_context)

                    if not review_result.should_proceed:
                        # Return feedback to main agent for iteration
                        return review_result.to_agent_message()

                    logger.info(
                        "Peer review completed successfully - proceeding with GitHub submission"
                    )

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
                        default="y",
                    )

                    if choice != "y":
                        raise ValueError(
                            "Pull request creation cancelled due to peer review failure"
                        )

                    logger.info(
                        "Proceeding with PR creation without peer review after failure"
                    )
                    console.print(
                        "[yellow]⚠️  Proceeding without peer review due to system failure[/yellow]"
                    )
            else:
                logger.info("Peer review disabled - proceeding directly with GitHub submission")

            # Validate repository access and permissions upfront
            self._validate_repository_permissions(repo)

            if base_branch is None:
                base_branch = self.api.get_default_branch(repo)

            # Get base commit SHA
            base_commit_sha = self._get_base_commit_sha(repo, base_branch, files, new_branch)

            # Get base tree SHA
            base_tree_sha = self._get_base_tree_sha(repo, base_commit_sha)

            # Create new tree with file changes
            new_tree_sha = self._create_tree(repo, base_tree_sha, files)

            # Create new commit
            new_commit_sha = self._create_commit(repo, commit_message, new_tree_sha, base_commit_sha)

            # Create new branch
            self._create_branch(repo, new_branch, new_commit_sha)

            # Create pull request
            pr_url = self._create_pr(repo, title, body, new_branch, base_branch)

            logger.info(f"Pull request created successfully: {pr_url}")
            return pr_url

        except Exception as e:
            error_msg = f"Error creating pull request: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg)

    def _validate_repository_permissions(self, repo: str) -> None:
        """Validate repository access and permissions."""
        try:
            repo_url = f"{self.config.github_api_base_url}/repos/{repo}"
            repo_response = self.api.make_request("GET", repo_url)
            repo_data = repo_response.json()
            permissions = repo_data.get("permissions", {})

            if not permissions.get("push", False):
                raise ValueError(
                    f"Insufficient permissions for repository '{repo}'.\n"
                    f"Your GitHub token needs 'push' access to create pull requests.\n"
                    f"Current permissions: {permissions}"
                )
        except Exception as e:
            if "404" in str(e):
                raise ValueError(
                    f"Repository '{repo}' not found or not accessible.\n"
                    f"Please check:\n"
                    f"  - Repository name is correct\n"
                    f"  - GitHub token has access to this repository\n"
                    f"  - Repository exists and is not private (if using public token)"
                )
            else:
                logger.warning(f"Could not validate repository permissions: {e}")

    def _get_base_commit_sha(
        self, repo: str, base_branch: str, files: List[Dict[str, str]], new_branch: str
    ) -> str:
        """Get base commit SHA, handling empty repositories."""
        ref_url = f"{self.config.github_api_base_url}/repos/{repo}/git/ref/heads/{base_branch}"
        try:
            response = self.api.make_request("GET", ref_url)
            return response.json()["object"]["sha"]
        except Exception as e:
            if "404" in str(e):
                # Repository is likely empty - use Contents API to create files directly on new branch
                logger.info(
                    f"Repository {repo} appears to be empty, creating files on new branch {new_branch}"
                )

                # Create files using Contents API directly on the new branch
                self._create_files_in_empty_repo(repo, files, new_branch)

                # Return empty SHA to indicate we'll create PR from new branch
                return ""
            else:
                raise

    def _get_base_tree_sha(self, repo: str, base_commit_sha: str) -> str:
        """Get base tree SHA from commit."""
        if not base_commit_sha:
            return ""  # Empty repository

        commit_url = f"{self.config.github_api_base_url}/repos/{repo}/git/commits/{base_commit_sha}"
        try:
            response = self.api.make_request("GET", commit_url)
            return response.json()["tree"]["sha"]
        except Exception as e:
            if "404" in str(e):
                raise ValueError(
                    f"Unable to get commit tree (404).\n"
                    f"This typically indicates:\n"
                    f"  - Commit SHA '{base_commit_sha}' is invalid\n"
                    f"  - Repository access permissions issue\n"
                    f"Original error: {str(e)}"
                )
            else:
                raise

    def _create_tree(self, repo: str, base_tree_sha: str, files: List[Dict[str, str]]) -> str:
        """Create a new tree with file changes."""
        tree = []
        for file_change in files:
            # Validate file path
            if not file_change.get("file_path"):
                raise ValueError("Invalid file in files array - missing 'file_path'")
            if not file_change.get("new_content"):
                raise ValueError("Invalid file in files array - missing 'new_content'")

            tree.append(
                {
                    "path": file_change["file_path"],
                    "mode": "100644",
                    "type": "blob",
                    "content": file_change["new_content"],
                }
            )

        # Create new tree
        tree_url = f"{self.config.github_api_base_url}/repos/{repo}/git/trees"
        tree_data = {"base_tree": base_tree_sha, "tree": tree} if base_tree_sha else {"tree": tree}

        # Log the tree creation for debugging
        logger.info(f"Creating tree with base_tree: {base_tree_sha}, {len(tree)} files")
        for file_item in tree:
            logger.info(f"  - {file_item['path']}")

        try:
            response = self.api.make_request("POST", tree_url, data=tree_data)
            return response.json()["sha"]
        except Exception as e:
            if "404" in str(e):
                raise ValueError(
                    f"Unable to create git tree (404). This typically indicates:\n"
                    f"  - Insufficient repository permissions (needs 'push' access)\n"
                    f"  - GitHub token may be expired or invalid\n"
                    f"  - Repository may be private and token lacks access\n"
                    f"  - Temporary GitHub API authentication issue\n"
                    f"  - Invalid base_tree SHA (repository may be empty)\n"
                    f"Note: GitHub Tree API with base_tree preserves existing files and only modifies specified files.\n"
                    f"Base tree SHA: {base_tree_sha}\n"
                    f"Files being created/updated: {[f['path'] for f in tree]}\n"
                    f"Original error: {str(e)}"
                )
            else:
                raise

    def _create_commit(
        self, repo: str, commit_message: str, new_tree_sha: str, base_commit_sha: str
    ) -> str:
        """Create a new commit."""
        commit_url = f"{self.config.github_api_base_url}/repos/{repo}/git/commits"
        commit_data = {
            "message": commit_message,
            "tree": new_tree_sha,
            "parents": [base_commit_sha] if base_commit_sha else [],
        }

        try:
            response = self.api.make_request("POST", commit_url, data=commit_data)
            return response.json()["sha"]
        except Exception as e:
            if "404" in str(e):
                raise ValueError(
                    f"Unable to create commit (404). This typically indicates:\n"
                    f"  - Authentication/permission issue with repository\n"
                    f"  - GitHub token lacks 'contents:write' permission\n"
                    f"Original error: {str(e)}"
                )
            else:
                raise

    def _create_branch(self, repo: str, new_branch: str, new_commit_sha: str) -> None:
        """Create a new branch."""
        branch_url = f"{self.config.github_api_base_url}/repos/{repo}/git/refs"
        branch_data = {"ref": f"refs/heads/{new_branch}", "sha": new_commit_sha}

        try:
            self.api.make_request("POST", branch_url, data=branch_data)
        except Exception as e:
            if "404" in str(e):
                raise ValueError(
                    f"Unable to create branch '{new_branch}' (404). This typically indicates:\n"
                    f"  - Insufficient repository permissions\n"
                    f"  - Authentication issue with GitHub token\n"
                    f"Original error: {str(e)}"
                )
            elif "422" in str(e):
                raise ValueError(
                    f"Branch '{new_branch}' already exists. Please use a different branch name."
                )
            else:
                raise

    def _create_pr(self, repo: str, title: str, body: str, new_branch: str, base_branch: str) -> str:
        """Create the pull request."""
        pr_url = f"{self.config.github_api_base_url}/repos/{repo}/pulls"
        pr_data = {"title": title, "body": body, "head": new_branch, "base": base_branch}

        try:
            response = self.api.make_request("POST", pr_url, data=pr_data)
            return response.json()["html_url"]
        except Exception as e:
            if "404" in str(e):
                raise ValueError(
                    f"Unable to create pull request (404). This typically indicates:\n"
                    f"  - Insufficient repository permissions\n"
                    f"  - Repository may not allow pull requests\n"
                    f"  - Authentication issue with GitHub token\n"
                    f"Original error: {str(e)}"
                )
            elif "422" in str(e):
                raise ValueError(
                    f"Pull request validation failed. Branch '{new_branch}' may have no changes or already has a PR."
                )
            else:
                raise

    def _create_files_in_empty_repo(
        self, repo: str, files: List[Dict[str, str]], branch: str
    ) -> None:
        """
        Create files in an empty repository using the Contents API.

        Args:
            repo: Repository name in format 'owner/repo'
            files: List of files to create
            branch: Branch name to create files in
        """
        logger.info(f"Creating files in empty repository {repo}")

        try:
            # Create files one by one using Contents API
            for file_change in files:
                file_path = file_change["file_path"]
                content = file_change["new_content"]

                # Encode content as base64
                encoded_content = base64.b64encode(content.encode("utf-8")).decode("utf-8")

                url = f"{self.config.github_api_base_url}/repos/{repo}/contents/{file_path}"
                data = {"message": f"Create {file_path}", "content": encoded_content, "branch": branch}

                self.api.make_request("PUT", url, data=data)
                logger.info(f"Created file: {file_path}")

        except Exception as e:
            error_msg = f"Error creating files in empty repository: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg)

    def merge_pull_request(self, repo: str, pr_number: int, merge_method: str = "merge") -> str:
        """
        Merge a pull request.

        Args:
            repo: Repository name in format 'owner/repo'
            pr_number: Pull request number
            merge_method: Merge method (merge, squash, rebase)

        Returns:
            Success message
        """
        logger.info(f"Merging pull request #{pr_number} in {repo}")

        try:
            url = f"{self.config.github_api_base_url}/repos/{repo}/pulls/{pr_number}/merge"
            data = {"merge_method": merge_method}

            self.api.make_request("PUT", url, data=data)
            return f"Pull request #{pr_number} merged successfully in {repo}."

        except Exception as e:
            error_msg = f"Error merging pull request: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg)


# Convenience functions for backward compatibility
def create_pull_request(
    repo: str,
    title: str,
    body: str,
    new_branch: str,
    files: List[Dict[str, str]],
    commit_message: str,
    base_branch: Optional[str] = None,
    enable_peer_review: Optional[bool] = None,
    user_request_context: Optional[str] = None,
) -> str:
    """Create pull request (backward compatibility wrapper)."""
    service = PullRequestService()
    try:
        return service.create_pull_request(
            repo,
            title,
            body,
            new_branch,
            files,
            commit_message,
            base_branch,
            enable_peer_review,
            user_request_context,
        )
    except ValueError as e:
        return str(e)


def merge_pull_request(repo: str, pr_number: int, merge_method: str = "merge") -> str:
    """Merge pull request (backward compatibility wrapper)."""
    service = PullRequestService()
    try:
        return service.merge_pull_request(repo, pr_number, merge_method)
    except ValueError as e:
        return str(e)


# Peer review related functions (kept for backward compatibility)
def review_pull_request(
    repo: str,
    title: str,
    body: str,
    files: List[Dict[str, str]],
    commit_message: str,
    branch_name: str,
    base_branch: Optional[str] = None,
) -> str:
    """Review pull request (backward compatibility wrapper)."""
    from ..peer_review import create_peer_review_context, PeerReviewAgent

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
            base_branch=base_branch,
        )

        # Initialize peer review agent
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
            "branch_name": branch_name,
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
    """Approve and submit pull request (backward compatibility wrapper)."""
    service = PullRequestService()
    try:
        return service.create_pull_request(
            repo=repo,
            title=title,
            body=body,
            new_branch=branch_name,
            files=files,
            commit_message=commit_message,
            base_branch=base_branch,
            enable_peer_review=False,  # Disable peer review since we're already in review process
        )
    except ValueError as e:
        return str(e)


def request_pr_changes(
    repo: str,
    title: str,
    feedback: str,
    suggestions: List[str],
    current_iteration: int = 1,
) -> str:
    """Request PR changes (backward compatibility wrapper)."""
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
            ),
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
    """Iterate pull request (backward compatibility wrapper)."""
    logger.info(f"Iterating on PR: {title} in {repo}")

    try:
        # Add feedback context to the PR description if provided
        if feedback_context:
            body = (
                f"{body}\n\n---\n**Peer Review Iteration:**\nAddressed feedback: {feedback_context}"
            )

        # Create the improved pull request with peer review enabled
        service = PullRequestService()
        return service.create_pull_request(
            repo=repo,
            title=title,
            body=body,
            new_branch=branch_name,
            files=files,
            commit_message=commit_message,
            base_branch=base_branch,
            enable_peer_review=True,  # Always enable peer review for iterations
        )

    except ValueError as e:
        return str(e)

