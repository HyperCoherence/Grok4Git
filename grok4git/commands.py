"""
Command system for Grok4Git slash commands.

This module provides the command registry, parsing, and conversion logic
for the Cursor-style slash command system.
"""

import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class CommandCategory(Enum):
    """Categories for organizing commands."""

    REPO = "🏗️  Repository"
    FILE = "📁 File Operations"
    COMMIT = "📊 Commit Analysis"
    PULL = "🔄 Pull Requests"
    ISSUE = "🎯 Issues"
    SYSTEM = "⚙️  System"


@dataclass
class Command:
    """Represents a slash command."""

    name: str
    description: str
    category: CommandCategory
    usage: str
    examples: List[str]
    aliases: List[str] = None

    def __post_init__(self):
        if self.aliases is None:
            self.aliases = []


class CommandRegistry:
    """Registry for all available slash commands."""

    def __init__(self):
        self.commands: Dict[str, Command] = {}
        self._register_commands()

    def _register_commands(self):
        """Register all available commands."""
        commands = [
            # Repository Commands
            Command(
                name="repos",
                description="List all your repositories",
                category=CommandCategory.REPO,
                usage="/repos [type]",
                examples=["/repos", "/repos private", "/repos public"],
                aliases=["repositories", "list-repos"],
            ),
            Command(
                name="repo",
                description="Get detailed information about a repository",
                category=CommandCategory.REPO,
                usage="/repo <owner/repo>",
                examples=["/repo microsoft/vscode", "/repo my-username/my-project"],
                aliases=["info", "repository"],
            ),
            Command(
                name="search",
                description="Search repositories by keyword",
                category=CommandCategory.REPO,
                usage="/search <query>",
                examples=["/search python api", "/search machine learning"],
                aliases=["find", "search-repos"],
            ),
            Command(
                name="create",
                description="Create a new repository",
                category=CommandCategory.REPO,
                usage="/create <name> [description] [--private]",
                examples=["/create my-new-project", "/create my-app 'A cool app' --private"],
                aliases=["new", "create-repo"],
            ),
            # File Operations
            Command(
                name="read",
                description="Read file contents",
                category=CommandCategory.FILE,
                usage="/read <owner/repo> <file-path>",
                examples=["/read microsoft/vscode README.md", "/read my-user/my-app src/main.py"],
                aliases=["cat", "file", "show"],
            ),
            Command(
                name="ls",
                description="List directory contents",
                category=CommandCategory.FILE,
                usage="/ls <owner/repo> [path]",
                examples=["/ls microsoft/vscode", "/ls my-user/my-app src/"],
                aliases=["list", "dir", "tree"],
            ),
            Command(
                name="delete",
                description="Delete a file (requires confirmation)",
                category=CommandCategory.FILE,
                usage="/delete <owner/repo> <file-path>",
                examples=["/delete my-user/my-app old-file.txt"],
                aliases=["rm", "remove"],
            ),
            # Commit Analysis
            Command(
                name="commits",
                description="Show recent commit history",
                category=CommandCategory.COMMIT,
                usage="/commits <owner/repo> [branch] [count]",
                examples=["/commits microsoft/vscode", "/commits my-user/my-app main 5"],
                aliases=["history", "log"],
            ),
            Command(
                name="commit",
                description="Show detailed commit information",
                category=CommandCategory.COMMIT,
                usage="/commit <owner/repo> <commit-sha>",
                examples=["/commit microsoft/vscode abc123def", "/commit my-user/my-app 1a2b3c4d"],
                aliases=["show", "details"],
            ),
            Command(
                name="diff",
                description="Show commit diff/changes",
                category=CommandCategory.COMMIT,
                usage="/diff <owner/repo> <commit-sha>",
                examples=["/diff microsoft/vscode abc123def", "/diff my-user/my-app 1a2b3c4d"],
                aliases=["changes", "patch"],
            ),
            Command(
                name="compare",
                description="Compare two commits",
                category=CommandCategory.COMMIT,
                usage="/compare <owner/repo> <commit1> <commit2>",
                examples=["/compare microsoft/vscode abc123 def456"],
                aliases=["comp", "versus"],
            ),
            # Pull Requests
            Command(
                name="pr",
                description="Create a pull request",
                category=CommandCategory.PULL,
                usage="/pr <owner/repo> <title> <description>",
                examples=["/pr my-user/my-app 'Add new feature' 'This PR adds...'"],
                aliases=["pull-request", "create-pr"],
            ),
            Command(
                name="branches",
                description="List all branches",
                category=CommandCategory.PULL,
                usage="/branches <owner/repo>",
                examples=["/branches microsoft/vscode", "/branches my-user/my-app"],
                aliases=["branch", "list-branches"],
            ),
            Command(
                name="merge",
                description="Merge a pull request",
                category=CommandCategory.PULL,
                usage="/merge <owner/repo> <pr_number> [merge_method]",
                examples=["/merge my-user/my-app 42", "/merge my-user/my-app 42 squash"],
                aliases=["merge-pr"],
            ),
            # Issues
            Command(
                name="issues",
                description="List open issues",
                category=CommandCategory.ISSUE,
                usage="/issues <owner/repo>",
                examples=["/issues microsoft/vscode", "/issues my-user/my-app"],
                aliases=["bugs", "list-issues"],
            ),
            Command(
                name="issue",
                description="Create a new issue",
                category=CommandCategory.ISSUE,
                usage="/issue <owner/repo> <title> [description]",
                examples=["/issue my-user/my-app 'Bug report' 'Found a bug...'"],
                aliases=["bug", "create-issue"],
            ),
            Command(
                name="comment",
                description="Add a comment to an issue or PR",
                category=CommandCategory.ISSUE,
                usage="/comment <owner/repo> <issue_number> <comment>",
                examples=["/comment my-user/my-app 42 'Thanks for the fix!'"],
                aliases=["add-comment"],
            ),
            # System Commands
            Command(
                name="help",
                description="Show help information",
                category=CommandCategory.SYSTEM,
                usage="/help [command]",
                examples=["/help", "/help repos", "/help pr"],
                aliases=["h", "?"],
            ),
            Command(
                name="clear",
                description="Clear conversation history",
                category=CommandCategory.SYSTEM,
                usage="/clear",
                examples=["/clear"],
                aliases=["cls", "reset"],
            ),
            Command(
                name="exit",
                description="Exit the application",
                category=CommandCategory.SYSTEM,
                usage="/exit",
                examples=["/exit"],
                aliases=["quit", "bye"],
            ),
            Command(
                name="model",
                description="Switch AI model",
                category=CommandCategory.SYSTEM,
                usage="/model <model_name>",
                examples=["/model grok-4", "/model grok-4-0709"],
                aliases=["switch-model"],
            ),
        ]

        for cmd in commands:
            self.commands[cmd.name] = cmd
            for alias in cmd.aliases:
                self.commands[alias] = cmd

    def get_command(self, name: str) -> Optional[Command]:
        """Get a command by name or alias."""
        return self.commands.get(name.lower())

    def get_commands_by_category(self) -> Dict[CommandCategory, List[Command]]:
        """Get all commands organized by category."""
        categorized = {}
        seen = set()

        for cmd in self.commands.values():
            if cmd.name in seen:
                continue
            seen.add(cmd.name)

            if cmd.category not in categorized:
                categorized[cmd.category] = []
            categorized[cmd.category].append(cmd)

        return categorized

    def find_similar_commands(self, name: str) -> List[str]:
        """Find similar command names for suggestions."""
        name_lower = name.lower()
        similar = []

        for cmd_name in self.commands.keys():
            if name_lower in cmd_name or cmd_name.startswith(name_lower):
                similar.append(cmd_name)

        return sorted(similar)[:5]  # Return top 5 matches


class CommandParser:
    """Parser for slash commands."""

    @staticmethod
    def parse_command(user_input: str) -> Tuple[bool, Optional[str], List[str]]:
        """
        Parse user input to check if it's a slash command.

        Args:
            user_input: The user's input string

        Returns:
            (is_command, command_name, args)
        """
        if not user_input.startswith("/"):
            return False, None, []

        # Remove the leading slash and split
        parts = user_input[1:].split()
        if not parts:
            return False, None, []

        command_name = parts[0]
        args = parts[1:]

        return True, command_name, args


class CommandConverter:
    """Converts slash commands to natural language for AI processing."""

    @staticmethod
    def convert_to_natural_language(cmd: Command, args: List[str]) -> Optional[str]:
        """Convert a slash command to natural language for the AI."""
        if cmd.name == "repos":
            repo_type = args[0] if args else "all"
            return f"List my {repo_type} repositories"

        elif cmd.name == "repo":
            if not args:
                return None
            return f"Show detailed information about the repository {args[0]}"

        elif cmd.name == "search":
            if not args:
                return None
            query = " ".join(args)
            return f"Search for repositories matching: {query}"

        elif cmd.name == "create":
            if not args:
                return None
            name = args[0]
            description = ""
            private = False

            # Parse arguments
            remaining_args = args[1:]
            if remaining_args:
                if "--private" in remaining_args:
                    private = True
                    remaining_args = [arg for arg in remaining_args if arg != "--private"]
                if remaining_args:
                    description = " ".join(remaining_args).strip("'\"")

            cmd_text = f"Create a new repository named '{name}'"
            if description:
                cmd_text += f" with description '{description}'"
            if private:
                cmd_text += " (make it private)"

            return cmd_text

        elif cmd.name == "read":
            if len(args) < 2:
                return None
            repo = args[0]
            file_path = args[1]
            return f"Show me the contents of {file_path} in repository {repo}"

        elif cmd.name == "ls":
            if not args:
                return None
            repo = args[0]
            path = args[1] if len(args) > 1 else ""
            if path:
                return f"List the contents of directory {path} in repository {repo}"
            else:
                return f"List the contents of repository {repo}"

        elif cmd.name == "delete":
            if len(args) < 2:
                return None
            repo = args[0]
            file_path = args[1]
            return f"Delete the file {file_path} from repository {repo}"

        elif cmd.name == "commits":
            if not args:
                return None
            repo = args[0]
            branch = args[1] if len(args) > 1 else None
            count = args[2] if len(args) > 2 else "10"

            cmd_text = f"Show the last {count} commits in repository {repo}"
            if branch:
                cmd_text += f" on branch {branch}"

            return cmd_text

        elif cmd.name == "commit":
            if len(args) < 2:
                return None
            repo = args[0]
            commit_sha = args[1]
            return f"Show detailed information about commit {commit_sha} in repository {repo}"

        elif cmd.name == "diff":
            if len(args) < 2:
                return None
            repo = args[0]
            commit_sha = args[1]
            return f"Show the diff/changes for commit {commit_sha} in repository {repo}"

        elif cmd.name == "compare":
            if len(args) < 3:
                return None
            repo = args[0]
            commit1 = args[1]
            commit2 = args[2]
            return f"Compare commits {commit1} and {commit2} in repository {repo}"

        elif cmd.name == "pr":
            if len(args) < 2:
                return None
            repo = args[0]
            title = args[1]
            description = (
                " ".join(args[2:]) if len(args) > 2 else "Pull request created via Grok4Git"
            )
            return f"Create a pull request in repository {repo} with title '{title}' and description '{description}'"

        elif cmd.name == "branches":
            if not args:
                return None
            repo = args[0]
            return f"List all branches in repository {repo}"

        elif cmd.name == "issues":
            if not args:
                return None
            repo = args[0]
            return f"List all open issues in repository {repo}"

        elif cmd.name == "issue":
            if len(args) < 2:
                return None
            repo = args[0]
            title = args[1]
            description = " ".join(args[2:]) if len(args) > 2 else ""

            cmd_text = f"Create a new issue in repository {repo} with title '{title}'"
            if description:
                cmd_text += f" and description '{description}'"

            return cmd_text

        elif cmd.name == "merge":
            if len(args) < 2:
                return None
            repo = args[0]
            pr_number = args[1]
            merge_method = args[2] if len(args) > 2 else "merge"
            return (
                f"Merge pull request #{pr_number} in repository {repo} using {merge_method} method"
            )

        elif cmd.name == "comment":
            if len(args) < 3:
                return None
            repo = args[0]
            issue_number = args[1]
            comment = " ".join(args[2:])
            return f"Add comment '{comment}' to issue #{issue_number} in repository {repo}"

        return None


# Global instances for easy access
command_registry = CommandRegistry()
command_parser = CommandParser()
command_converter = CommandConverter()
