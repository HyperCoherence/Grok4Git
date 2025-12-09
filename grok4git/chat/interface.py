"""
Main chat interface for Grok4Git.

This module orchestrates all chat components to provide the main chat interface.
"""

import logging
from typing import Dict, Any

from rich.console import Console
from rich.prompt import Confirm
from rich.panel import Panel

from .ai_client import AIClient
from .command_handlers import CommandHandler
from .ui.display import DisplayManager
from .ui.prompts import PromptManager
from ..commands import command_parser

logger = logging.getLogger(__name__)


class GrokChat:
    """Enhanced chat interface for Grok4Git with slash commands."""
    
    def __init__(self):
        """Initialize the chat interface."""
        self.console = Console()
        
        # Initialize UI components
        self.display = DisplayManager(self.console)
        
        # Initialize AI client (will be set up after display manager)
        self.ai_client = AIClient(
            console=self.console,
            display_manager=self.display,
            confirm_callback=self._confirm_destructive_operation
        )
        
        # Initialize prompt manager with context calculator
        self.prompt = PromptManager(
            console=self.console,
            calculate_context_usage=self.ai_client.calculate_context_usage
        )
        
        # Initialize command handler
        self.command_handler = CommandHandler(
            console=self.console,
            display_manager=self.display,
            prompt_manager=self.prompt,
            context_calculator=self.ai_client.calculate_context_usage,
            setup_system_message_callback=self.ai_client._setup_system_message
        )
        
        logger.info("Grok chat interface initialized")
    
    def _confirm_destructive_operation(
        self, function_name: str, function_args: Dict[str, Any]
    ) -> bool:
        """
        Ask user to confirm destructive operations.
        
        Args:
            function_name: Name of the function
            function_args: Arguments passed to the function
            
        Returns:
            True if confirmed, False otherwise
        """
        if function_name == "delete_file":
            repo = function_args.get("repo", "unknown")
            path = function_args.get("path", "unknown")

            self.console.print(
                Panel(
                    f"[bold red]⚠️  DESTRUCTIVE OPERATION[/bold red]\n\n"
                    f"[yellow]You are about to delete:[/yellow]\n"
                    f"[red]📁 Repository: {repo}[/red]\n"
                    f"[red]📄 File: {path}[/red]\n\n"
                    f"[yellow]⚠️  This action cannot be undone.[/yellow]",
                    title="[bold red]Confirmation Required[/bold red]",
                    border_style="red",
                )
            )

            return Confirm.ask(
                "Are you sure you want to proceed?", default=False, console=self.console
            )

        elif function_name == "create_repository":
            name = function_args.get("name", "unknown")
            private = function_args.get("private", False)

            self.console.print(
                Panel(
                    f"[bold yellow]📦 REPOSITORY CREATION[/bold yellow]\n\n"
                    f"[cyan]Creating new repository:[/cyan]\n"
                    f"[cyan]📁 Name: {name}[/cyan]\n"
                    f"[cyan]🔒 Visibility: {'Private' if private else 'Public'}[/cyan]",
                    title="[bold yellow]Confirmation[/bold yellow]",
                    border_style="yellow",
                )
            )

            return Confirm.ask(
                "Do you want to create this repository?", default=True, console=self.console
            )

        return True
    
    def run(self) -> None:
        """Run the main chat loop."""
        self.display.show_welcome()

        while True:
            try:
                user_input = self.prompt.get_user_input()

                if not user_input:
                    continue

                # Check if it's a slash command
                is_command, command_name, args = command_parser.parse_command(user_input)

                if is_command:
                    # Handle slash command
                    if command_name == "clear":
                        # Clear messages in AI client
                        self.ai_client.clear_messages()
                    
                    if self.command_handler.execute(command_name, args, self.ai_client.messages):
                        break  # Exit if command returned True
                else:
                    # Handle natural language input
                    # Display user message in conversation
                    self.display.show_user_message(user_input)
                    self.ai_client.send_message(user_input)

            except KeyboardInterrupt:
                self.console.print("\n[yellow]Session interrupted by user[/yellow]")
                break
            except Exception as e:
                error_msg = f"Unexpected error in chat loop: {str(e)}"
                logger.error(error_msg)
                suggestion = "Try: Continue chatting, use `/clear` to reset, or `/exit` to quit"
                self.display.show_error(error_msg, suggestion=suggestion)


def main():
    """Main entry point for the chat interface."""
    try:
        chat = GrokChat()
        chat.run()
    except Exception as e:
        console = Console()
        console.print(f"[red]❌ Failed to start chat interface: {str(e)}[/red]")
        logger.error(f"Failed to start chat interface: {str(e)}")


if __name__ == "__main__":
    main()

