"""
File service for GitHub file operations.
"""

import base64
import json
import re
from typing import List, Dict, Optional, Tuple

from .base import BaseService


class FileService(BaseService):
    """Service for file-related GitHub operations."""

    def get_file_content(self, repo: str, path: str, branch: Optional[str] = None) -> str:
        """
        Get the content of a file in a GitHub repository.

        Args:
            repo: Repository name in format 'owner/repo'
            path: File path
            branch: Branch name (defaults to repository's default branch)

        Returns:
            File content as string
        """
        self._validate_repo_name(repo)
        
        if branch is None:
            branch = self.api.get_default_branch(repo)

        url = f"{self.config.github_api_base_url}/repos/{repo}/contents/{path}"
        response = self._make_request(
            "GET", url, operation_name=f"get file content: {repo}/{path}", params={"ref": branch}
        )
        data = response.json()

        # Check if it's a directory
        if isinstance(data, list):
            raise ValueError(f"'{path}' is a directory, not a file")

        # Check file size
        file_size = data.get("size", 0)
        max_size_bytes = self.config.max_file_size_mb * 1024 * 1024

        if file_size > max_size_bytes:
            self.logger.info(f"File {path} is large ({file_size} bytes), providing summary")
            return self._get_large_file_summary(repo, path, branch, file_size)

        # Check if content is available
        if "content" not in data:
            raise ValueError(f"File content not available for '{path}'")

        # Decode base64 content
        content = data["content"]
        try:
            decoded_content = base64.b64decode(content).decode("utf-8")
            return decoded_content
        except UnicodeDecodeError:
            raise ValueError("File appears to be binary. Content cannot be decoded as UTF-8.")

    def get_bulk_file_content(
        self, repo: str, paths: List[str], branch: Optional[str] = None
    ) -> str:
        """
        Get the content of multiple files in a GitHub repository as a single structured blob.

        Args:
            repo: Repository name in format 'owner/repo'
            paths: List of file paths to read
            branch: Branch name (defaults to repository's default branch)

        Returns:
            Structured blob containing all file contents with separators
        """
        self._validate_repo_name(repo)
        
        if branch is None:
            branch = self.api.get_default_branch(repo)

        max_size_bytes = self.config.max_file_size_mb * 1024 * 1024
        successful_files: List[Tuple[str, str]] = []
        skipped_files: List[str] = []
        error_files: List[str] = []

        # Process each file
        for path in paths:
            try:
                url = f"{self.config.github_api_base_url}/repos/{repo}/contents/{path}"
                response = self._make_request(
                    "GET", url, operation_name=f"get bulk file: {repo}/{path}", params={"ref": branch}
                )
                data = response.json()

                # Check if it's a directory
                if isinstance(data, list):
                    error_files.append(f"{path} (directory)")
                    continue

                # Check file size
                file_size = data.get("size", 0)
                if file_size > max_size_bytes:
                    size_mb = file_size / (1024 * 1024)
                    skipped_files.append(f"{path} ({size_mb:.1f}MB)")
                    continue

                # Check if content is available
                if "content" not in data:
                    error_files.append(f"{path} (content not available)")
                    continue

                # Decode base64 content
                content = data["content"]
                try:
                    decoded_content = base64.b64decode(content).decode("utf-8")
                    successful_files.append((path, decoded_content))
                except (UnicodeDecodeError, base64.binascii.Error):
                    error_files.append(f"{path} (binary/decode error)")
                    continue

            except Exception as e:
                error_files.append(f"{path} (error: {str(e)})")
                continue

        # Build structured output
            result = []

            if successful_files:
                result.append(f"=== BULK FILE CONTENT: {repo} (branch: {branch}) ===\n")
                result.append(f"Successfully read {len(successful_files)} files:\n")

                for path, content in successful_files:
                    result.append(f"\n{'='*60}")
                    result.append(f"FILE: {path}")
                    result.append(f"{'='*60}")
                    result.append(content)
                    result.append(f"{'='*60}")
                    result.append(f"END OF FILE: {path}")
                    result.append(f"{'='*60}\n")

            # Add notes about skipped/error files
            if skipped_files:
                result.append(
                    f"\n📁 SKIPPED FILES (too large, max {self.config.max_file_size_mb}MB):"
                )
                for skipped in skipped_files:
                    result.append(f"  - {skipped}")
                result.append(f"\n💡 Use get_file_content() to read these files individually.\n")

            if error_files:
                result.append(f"\n❌ ERROR FILES (could not read):")
                for error in error_files:
                    result.append(f"  - {error}")
                result.append("")

            if not successful_files and not skipped_files and not error_files:
                return f"No files found in {repo} for the specified paths."

            final_result = "\n".join(result)

            self.logger.info(
                f"Bulk file read completed: {len(successful_files)} successful, "
                f"{len(skipped_files)} skipped, {len(error_files)} errors"
            )
            return final_result

    def get_bulk_codebase_overview(
        self, repo: str, branch: Optional[str] = None, max_files: int = 20
    ) -> str:
        """
        Get an overview of a codebase by reading multiple relevant files in a structured format.

        Args:
            repo: Repository name in format 'owner/repo'
            branch: Branch name (defaults to repository's default branch)
            max_files: Maximum number of files to read (default: 20)

        Returns:
            Structured blob containing overview of the codebase
        """
        self._validate_repo_name(repo)
        
        if branch is None:
            branch = self.api.get_default_branch(repo)

            # Get repository structure (use self to avoid circular dependency)
            structure_result = self.recursive_list_directory(repo, "", branch)

            # Parse the structure to find important files
            important_files = []

            # Priority files (always include if they exist)
            priority_patterns = [
                "README.md",
                "README.rst",
                "README.txt",
                "README",
                "package.json",
                "requirements.txt",
                "setup.py",
                "pyproject.toml",
                "Cargo.toml",
                "go.mod",
                "pom.xml",
                "build.gradle",
                "Dockerfile",
                "docker-compose.yml",
                ".env.example",
                "config.yml",
                "config.yaml",
                "config.json",
                "LICENSE",
                "CHANGELOG.md",
                "CONTRIBUTING.md",
            ]

            # Source file patterns (include some examples)
            source_patterns = [
                r"\.py$",
                r"\.js$",
                r"\.ts$",
                r"\.jsx$",
                r"\.tsx$",
                r"\.go$",
                r"\.rs$",
                r"\.java$",
                r"\.cpp$",
                r"\.c$",
                r"\.rb$",
                r"\.php$",
                r"\.swift$",
                r"\.kt$",
            ]

            try:
                # Parse directory structure
                files_data = json.loads(structure_result)
                all_files = []

                def extract_files(items, current_path=""):
                    for item in items:
                        if item["type"] == "file":
                            full_path = (
                                f"{current_path}/{item['name']}" if current_path else item["name"]
                            )
                            all_files.append(full_path)
                        elif item["type"] == "dir" and "children" in item:
                            new_path = (
                                f"{current_path}/{item['name']}" if current_path else item["name"]
                            )
                            extract_files(item["children"], new_path)

                extract_files(files_data)

                # Find priority files
                for pattern in priority_patterns:
                    matches = [
                        f
                        for f in all_files
                        if f.lower().endswith(pattern.lower())
                        or f.split("/")[-1].lower() == pattern.lower()
                    ]
                    important_files.extend(matches[:2])  # Max 2 of each type

                # Find some source files (avoid test files)
                source_files = []
                for pattern in source_patterns:
                    matches = [
                        f
                        for f in all_files
                        if re.search(pattern, f, re.IGNORECASE)
                        and not re.search(r"(test|spec|__pycache__|\.git)", f, re.IGNORECASE)
                    ]
                    source_files.extend(matches[:3])  # Max 3 of each type

                # Add source files, prioritizing root level and main directories
                source_files.sort(key=lambda x: (x.count("/"), len(x)))
                important_files.extend(source_files[: max_files - len(important_files)])

            except Exception as e:
                self.logger.warning(f"Error parsing repository structure: {e}")
                # Fallback to common files
                important_files = ["README.md", "package.json", "requirements.txt", "setup.py"]

            # Remove duplicates and limit to max_files
            important_files = list(dict.fromkeys(important_files))[:max_files]

            if not important_files:
                return f"No relevant files found in {repo} for codebase overview."

            # Use bulk file reader to get content
            return self.get_bulk_file_content(repo, important_files, branch)

    def list_directory_contents(
        self, repo: str, path: str = "", branch: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """
        List files and subdirectories in a specified path within a GitHub repository.

        Args:
            repo: Repository name in format 'owner/repo'
            path: Directory path (empty string for root)
            branch: Branch name (defaults to repository's default branch)

        Returns:
            List of directory contents
        """
        self._validate_repo_name(repo)
        
        if branch is None:
            branch = self.api.get_default_branch(repo)

        url = f"{self.config.github_api_base_url}/repos/{repo}/contents/{path}"
        response = self._make_request(
            "GET", url, operation_name=f"list directory: {repo}/{path}", params={"ref": branch}
        )
        data = response.json()

        if not isinstance(data, list):
            raise ValueError(f"'{path}' is not a directory")

        contents = [
            {"name": item["name"], "type": item["type"], "path": item["path"]} for item in data
        ]

        return contents

    def recursive_list_directory(
        self, repo: str, path: str = "", branch: Optional[str] = None
    ) -> str:
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

        def recurse(current_path: str) -> List[Dict[str, any]]:
            """Recursively get directory contents."""
            try:
                contents = self.list_directory_contents(repo, current_path, branch)

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
                        result.append(
                            {"name": item["name"], "type": "file", "path": item["path"]}
                        )
                return result

            except Exception as e:
                self.logger.error(f"Error in recursive listing for {current_path}: {str(e)}")
                return []

        result = recurse(path)
        return json.dumps(result)

    def delete_file(
        self, repo: str, path: str, commit_message: str = "Delete file", branch: Optional[str] = None
    ) -> str:
        """
        Delete a file in a GitHub repository.

        Args:
            repo: Repository name in format 'owner/repo'
            path: File path to delete
            commit_message: Commit message for the deletion
            branch: Branch name (defaults to repository's default branch)

        Returns:
            Success message
        """
        self._validate_repo_name(repo)
        
        if branch is None:
            branch = self.api.get_default_branch(repo)

        # Get current file SHA
        url = f"{self.config.github_api_base_url}/repos/{repo}/contents/{path}"
        try:
            response = self._make_request(
                "GET", url, operation_name=f"get file SHA: {repo}/{path}", params={"ref": branch}
            )
            file_sha = response.json()["sha"]
        except Exception as e:
            if "404" in str(e):
                raise ValueError(
                    f"File '{path}' not found in repository '{repo}' on branch '{branch}'"
                )
            else:
                raise

        # Delete the file
        delete_data = {"message": commit_message, "sha": file_sha, "branch": branch}
        try:
            self._make_request(
                "DELETE", url, operation_name=f"delete file: {repo}/{path}", data=delete_data
            )
        except Exception as e:
            if "404" in str(e):
                raise ValueError(
                    f"Unable to delete file (404). This typically indicates:\n"
                    f"  - Insufficient repository permissions (needs 'push' access)\n"
                    f"  - GitHub token authentication issue\n"
                    f"  - File may have been deleted by another process\n"
                    f"Original error: {str(e)}"
                )
            elif "409" in str(e):
                raise ValueError(
                    "File deletion conflict. The file may have been modified since you last accessed it."
                )
            else:
                raise

        return "File deleted successfully"

    def _get_large_file_summary(self, repo: str, path: str, branch: str, file_size: int) -> str:
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
            raw_content = self.api.get_file_content_raw(repo, path, branch)

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


# Convenience functions for backward compatibility
def get_file_content(repo: str, path: str, branch: Optional[str] = None) -> str:
    """Get file content (backward compatibility wrapper)."""
    service = FileService()
    try:
        return service.get_file_content(repo, path, branch)
    except ValueError as e:
        return str(e)


def get_bulk_file_content(repo: str, paths: List[str], branch: Optional[str] = None) -> str:
    """Get bulk file content (backward compatibility wrapper)."""
    service = FileService()
    try:
        return service.get_bulk_file_content(repo, paths, branch)
    except ValueError as e:
        return str(e)


def get_bulk_codebase_overview(
    repo: str, branch: Optional[str] = None, max_files: int = 20
) -> str:
    """Get codebase overview (backward compatibility wrapper)."""
    service = FileService()
    try:
        return service.get_bulk_codebase_overview(repo, branch, max_files)
    except ValueError as e:
        return str(e)


def list_directory_contents(repo: str, path: str = "", branch: Optional[str] = None) -> str:
    """List directory contents (backward compatibility wrapper)."""
    service = FileService()
    try:
        contents = service.list_directory_contents(repo, path, branch)
        return json.dumps(contents)
    except ValueError as e:
        return str(e)


def recursive_list_directory(repo: str, path: str = "", branch: Optional[str] = None) -> str:
    """Recursive list directory (backward compatibility wrapper)."""
    service = FileService()
    try:
        return service.recursive_list_directory(repo, path, branch)
    except ValueError as e:
        return str(e)


def delete_file(
    repo: str, path: str, commit_message: str = "Delete file", branch: Optional[str] = None
) -> str:
    """Delete file (backward compatibility wrapper)."""
    service = FileService()
    try:
        return service.delete_file(repo, path, commit_message, branch)
    except ValueError as e:
        return str(e)

