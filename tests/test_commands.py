"""
Unit tests for the commands module.
"""

import pytest
from grok4git.commands import (
    Command,
    CommandCategory,
    CommandRegistry,
    CommandParser,
    CommandConverter,
    command_registry,
    command_parser,
    command_converter,
)


class TestCommand:
    """Test the Command dataclass."""

    def test_command_creation(self):
        """Test creating a command."""
        cmd = Command(
            name="test",
            description="Test command",
            category=CommandCategory.SYSTEM,
            usage="/test",
            examples=["/test example"],
        )

        assert cmd.name == "test"
        assert cmd.description == "Test command"
        assert cmd.category == CommandCategory.SYSTEM
        assert cmd.usage == "/test"
        assert cmd.examples == ["/test example"]
        assert cmd.aliases == []  # Should be empty by default

    def test_command_with_aliases(self):
        """Test creating a command with aliases."""
        cmd = Command(
            name="test",
            description="Test command",
            category=CommandCategory.SYSTEM,
            usage="/test",
            examples=["/test example"],
            aliases=["t", "testing"],
        )

        assert cmd.aliases == ["t", "testing"]


class TestCommandRegistry:
    """Test the CommandRegistry class."""

    def test_registry_initialization(self):
        """Test that registry initializes with commands."""
        registry = CommandRegistry()
        assert len(registry.commands) > 0

    def test_get_command_by_name(self):
        """Test getting a command by name."""
        registry = CommandRegistry()
        cmd = registry.get_command("repos")

        assert cmd is not None
        assert cmd.name == "repos"

    def test_get_command_by_alias(self):
        """Test getting a command by alias."""
        registry = CommandRegistry()
        cmd = registry.get_command("repositories")

        assert cmd is not None
        assert cmd.name == "repos"  # Should return the main command

    def test_get_nonexistent_command(self):
        """Test getting a command that doesn't exist."""
        registry = CommandRegistry()
        cmd = registry.get_command("nonexistent")

        assert cmd is None

    def test_case_insensitive_lookup(self):
        """Test that command lookup is case insensitive."""
        registry = CommandRegistry()
        cmd1 = registry.get_command("REPOS")
        cmd2 = registry.get_command("repos")

        assert cmd1 is not None
        assert cmd2 is not None
        assert cmd1 == cmd2

    def test_get_commands_by_category(self):
        """Test getting commands organized by category."""
        registry = CommandRegistry()
        categorized = registry.get_commands_by_category()

        assert isinstance(categorized, dict)
        assert CommandCategory.REPO in categorized
        assert CommandCategory.FILE in categorized
        assert CommandCategory.SYSTEM in categorized

        # Check that repos command is in REPO category
        repo_commands = categorized[CommandCategory.REPO]
        repo_names = [cmd.name for cmd in repo_commands]
        assert "repos" in repo_names

    def test_find_similar_commands(self):
        """Test finding similar commands."""
        registry = CommandRegistry()
        similar = registry.find_similar_commands("rep")

        assert isinstance(similar, list)
        assert len(similar) <= 5  # Should return max 5
        assert "repo" in similar or "repos" in similar


class TestCommandParser:
    """Test the CommandParser class."""

    def test_parse_slash_command(self):
        """Test parsing a valid slash command."""
        is_cmd, name, args = CommandParser.parse_command("/repos private")

        assert is_cmd is True
        assert name == "repos"
        assert args == ["private"]

    def test_parse_non_slash_input(self):
        """Test parsing non-slash input."""
        is_cmd, name, args = CommandParser.parse_command("list my repositories")

        assert is_cmd is False
        assert name is None
        assert args == []

    def test_parse_empty_slash(self):
        """Test parsing just a slash."""
        is_cmd, name, args = CommandParser.parse_command("/")

        assert is_cmd is False
        assert name is None
        assert args == []

    def test_parse_command_with_multiple_args(self):
        """Test parsing a command with multiple arguments."""
        is_cmd, name, args = CommandParser.parse_command("/read microsoft/vscode README.md")

        assert is_cmd is True
        assert name == "read"
        assert args == ["microsoft/vscode", "README.md"]

    def test_parse_command_no_args(self):
        """Test parsing a command with no arguments."""
        is_cmd, name, args = CommandParser.parse_command("/help")

        assert is_cmd is True
        assert name == "help"
        assert args == []


class TestCommandConverter:
    """Test the CommandConverter class."""

    def test_convert_repos_command(self):
        """Test converting repos command."""
        # Create a mock repos command
        cmd = Command(
            name="repos",
            description="List repositories",
            category=CommandCategory.REPO,
            usage="/repos",
            examples=["/repos"],
        )

        result = CommandConverter.convert_to_natural_language(cmd, [])
        assert result == "List my all repositories"

        result = CommandConverter.convert_to_natural_language(cmd, ["private"])
        assert result == "List my private repositories"

    def test_convert_read_command(self):
        """Test converting read command."""
        cmd = Command(
            name="read",
            description="Read file",
            category=CommandCategory.FILE,
            usage="/read",
            examples=["/read"],
        )

        result = CommandConverter.convert_to_natural_language(
            cmd, ["microsoft/vscode", "README.md"]
        )
        assert result == "Show me the contents of README.md in repository microsoft/vscode"

        # Test insufficient args
        result = CommandConverter.convert_to_natural_language(cmd, ["repo"])
        assert result is None

    def test_convert_unknown_command(self):
        """Test converting an unknown command."""
        cmd = Command(
            name="unknown",
            description="Unknown command",
            category=CommandCategory.SYSTEM,
            usage="/unknown",
            examples=["/unknown"],
        )

        result = CommandConverter.convert_to_natural_language(cmd, [])
        assert result is None


class TestGlobalInstances:
    """Test the global instances."""

    def test_global_registry_exists(self):
        """Test that global command registry exists."""
        assert command_registry is not None
        assert isinstance(command_registry, CommandRegistry)

    def test_global_parser_exists(self):
        """Test that global command parser exists."""
        assert command_parser is not None
        assert isinstance(command_parser, CommandParser)

    def test_global_converter_exists(self):
        """Test that global command converter exists."""
        assert command_converter is not None
        assert isinstance(command_converter, CommandConverter)

    def test_global_instances_work(self):
        """Test that global instances function correctly."""
        # Test parser
        is_cmd, name, args = command_parser.parse_command("/test")
        assert is_cmd is True
        assert name == "test"

        # Test registry
        cmd = command_registry.get_command("repos")
        assert cmd is not None

        # Test converter
        if cmd:
            result = command_converter.convert_to_natural_language(cmd, ["private"])
            assert result is not None


if __name__ == "__main__":
    pytest.main([__file__])
