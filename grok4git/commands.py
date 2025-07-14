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
            # System/Client Control Commands
            Command(
                name="help",
                description="Show help information",
                category=CommandCategory.SYSTEM,
                usage="/help [command]",
                examples=["/help", "/help model"],
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
            Command(
                name="peer-review-toggle",
                description="Enable or disable peer review for pull requests",
                category=CommandCategory.SYSTEM,
                usage="/peer-review-toggle [enable|disable]",
                examples=["/peer-review-toggle enable", "/peer-review-toggle disable", "/peer-review-toggle"],
                aliases=["peer-toggle", "pr-review-toggle"],
            ),
            Command(
                name="peer-review-status",
                description="Show current peer review configuration",
                category=CommandCategory.SYSTEM,
                usage="/peer-review-status",
                examples=["/peer-review-status"],
                aliases=["peer-status", "pr-review-status"],
            ),
            # Convenience Commands
            Command(
                name="repos",
                description="Quick list of your repositories",
                category=CommandCategory.REPO,
                usage="/repos [type]",
                examples=["/repos", "/repos private", "/repos public"],
                aliases=["repositories"],
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
        categorized: Dict[CommandCategory, List[Command]] = {}
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
        # Note: Most client control commands are handled directly in chat.py
        # Only commands that need AI processing are converted here
        
        if cmd.name == "peer-review-toggle":
            if not args:
                return "Show current peer review status and toggle settings"
            
            action = args[0].lower()
            if action in ["enable", "on", "true"]:
                return "Enable peer review for pull requests"
            elif action in ["disable", "off", "false"]:
                return "Disable peer review for pull requests"
            else:
                return "Show current peer review status and toggle settings"

        elif cmd.name == "peer-review-status":
            return "Show current peer review configuration and settings"

        return None


# Global instances for easy access
command_registry = CommandRegistry()
command_parser = CommandParser()
command_converter = CommandConverter()
