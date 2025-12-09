"""
Display manager for chat interface UI.
"""

import logging
from typing import Optional

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from ...commands import command_registry

logger = logging.getLogger(__name__)


class DisplayManager:
    """Manages display of UI elements in the chat interface."""
    
    def __init__(self, console: Console):
        """
        Initialize display manager.
        
        Args:
            console: Rich console instance for output
        """
        self.console = console
    
    def show_welcome(self) -> None:
        """Display streamlined welcome message."""
        welcome_text = """
# Welcome to Grok4Git! 🚀

**AI-Powered GitHub Assistant** - Manage repositories with natural language.

**Quick Start:**
- Ask: "List my repositories" or use `/repos`
- Try: "Show me the README for microsoft/vscode"
- Commands: `/help` for all commands, `/clear` to reset context

**Tip:** Use `/help` for detailed documentation or press Tab for command completion.
        """

        self.console.print(
            Panel(
                Markdown(welcome_text),
                title="[bold cyan]Grok4Git[/bold cyan]",
                border_style="cyan",
                padding=(1, 2),
            )
        )
    
    def show_help(self, command_name: Optional[str] = None) -> None:
        """
        Display help for commands.
        
        Args:
            command_name: Optional command name for specific help
        """
        if command_name:
            cmd = command_registry.get_command(command_name)
            if cmd:
                self._show_single_command_help(cmd)
            else:
                similar = command_registry.find_similar_commands(command_name)
                self.console.print(f"[red]Unknown command: [bold]/{command_name}[/bold][/red]")
                if similar:
                    self.console.print(
                        f"[yellow]Did you mean: [bold]{', '.join(similar)}[/bold]?[/yellow]"
                    )
        else:
            self._show_all_commands_help()
    
    def _show_single_command_help(self, cmd) -> None:
        """Display help for a single command."""
        panel_content = f"""
## [bold cyan]/{cmd.name}[/bold cyan]

{cmd.description}

**Usage:** `{cmd.usage}`

**Examples:**
{chr(10).join(f'  • `{example}`' for example in cmd.examples)}
        """

        if cmd.aliases:
            panel_content += f"\n**Aliases:** {', '.join(f'`/{alias}`' for alias in cmd.aliases)}"

        self.console.print(
            Panel(
                Markdown(panel_content),
                title="[bold green]Command Help[/bold green]",
                border_style="green",
                padding=(1, 2),
            )
        )
    
    def _show_all_commands_help(self) -> None:
        """Display help for all commands organized by category."""
        commands_by_category = command_registry.get_commands_by_category()

        help_content = "# Available Commands\n\n"

        for category, commands in commands_by_category.items():
            help_content += f"## {category.value}\n\n"

            for cmd in commands:
                aliases_str = f" (aliases: {', '.join(cmd.aliases)})" if cmd.aliases else ""
                help_content += f"- **`/{cmd.name}`** - {cmd.description}{aliases_str}\n"

            help_content += "\n"

        help_content += """
## Usage Guidelines
- **Slash commands** are for client control only
- **Natural language** is for GitHub operations
- Use `/help <command>` for detailed help on a specific command
- Commands are case-insensitive and support aliases

## Examples
```
# Client Control (slash commands)
/repos                          # Quick list of repositories
/model grok-4                   # Switch AI model
/peer-review-toggle enable      # Enable peer review
/clear                          # Clear chat history

# GitHub Operations (natural language)
"Show me the README for microsoft/vscode"
"Create a new repository called my-project"
"List recent commits in my-repo"
"Create a pull request for my feature"
```
        """

        self.console.print(
            Panel(
                Markdown(help_content),
                title="[bold green]Command Reference[/bold green]",
                border_style="green",
                padding=(1, 2),
            )
        )
    
    def show_user_message(self, message: str) -> None:
        """
        Display user message in conversation.
        
        Args:
            message: User's input message
        """
        self.console.print(f"[bold cyan]You:[/bold cyan] {message}")
        self.console.print()  # Add blank line for spacing
    
    def show_response(self, content: str) -> None:
        """
        Display AI response with rich formatting.
        
        Args:
            content: Response content to display
        """
        if content:
            # Display the Grok header
            self.console.print("[bold green]🤖 Grok:[/bold green]")
            self.console.print()  # Add blank line for spacing
            
            # Try to render as markdown if it looks like markdown
            if any(marker in content for marker in ["#", "*", "`", "```", "-"]):
                try:
                    self.console.print(Markdown(content))
                except Exception:
                    # Fall back to plain text if markdown parsing fails
                    self.console.print(content)
            else:
                self.console.print(content)
                
            self.console.print()  # Add blank line after response
        else:
            # This case should now be handled by auto-recovery in AI client
            # But keeping as fallback for direct calls
            self.console.print(
                "[bold green]🤖 Grok:[/bold green] [yellow]No response content[/yellow]"
            )
    
    def show_conversation_history(self, messages: list, max_exchanges: int = 5) -> None:
        """
        Display recent conversation history.
        
        Args:
            messages: List of message dictionaries
            max_exchanges: Maximum number of exchanges to show
        """
        if not messages:
            self.console.print("[dim]No conversation history[/dim]")
            return
        
        # Filter out system messages and count user/assistant exchanges
        exchanges = []
        current_exchange = None
        
        for msg in messages:
            role = msg.get("role") if isinstance(msg, dict) else getattr(msg, "role", None)
            content = msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", "")
            
            if role == "user":
                if current_exchange:
                    exchanges.append(current_exchange)
                current_exchange = {"user": content, "assistant": None}
            elif role == "assistant" and current_exchange:
                current_exchange["assistant"] = content
        
        if current_exchange:
            exchanges.append(current_exchange)
        
        # Show only recent exchanges
        recent_exchanges = exchanges[-max_exchanges:] if len(exchanges) > max_exchanges else exchanges
        
        if not recent_exchanges:
            self.console.print("[dim]No conversation history to display[/dim]")
            return
        
        self.console.print("\n[bold]Recent Conversation:[/bold]")
        self.console.print("[dim]" + "─" * 60 + "[/dim]")
        
        for exchange in recent_exchanges:
            if exchange.get("user"):
                self.console.print(f"[cyan]You:[/cyan] {exchange['user'][:100]}{'...' if len(exchange['user']) > 100 else ''}")
            if exchange.get("assistant"):
                assistant_preview = exchange['assistant'][:150] if exchange['assistant'] else ""
                self.console.print(f"[green]Grok:[/green] {assistant_preview}{'...' if len(exchange.get('assistant', '')) > 150 else ''}")
            self.console.print("[dim]" + "─" * 60 + "[/dim]")
        
        self.console.print()
    
    def show_status(self, message: str) -> None:
        """
        Display a status message.
        
        Args:
            message: Status message to display
        """
        self.console.print(f"[cyan]{message}[/cyan]")
    
    def show_error(self, message: str, suggestion: str = None) -> None:
        """
        Display an error message with actionable suggestions.
        
        Args:
            message: Error message to display
            suggestion: Optional suggestion for how to fix the error
        """
        self.console.print(f"[red]❌ {message}[/red]")
        if suggestion:
            self.console.print(f"[dim]💡 {suggestion}[/dim]")
        else:
            # Default suggestions based on common errors
            if "context" in message.lower() or "token" in message.lower():
                self.console.print("[dim]💡 Try: Use [bold]/clear[/bold] to reset context[/dim]")
            elif "import" in message.lower() or "module" in message.lower():
                self.console.print("[dim]💡 Try: Restart the application or check your installation[/dim]")
            elif "api" in message.lower() or "network" in message.lower():
                self.console.print("[dim]💡 Try: Check your internet connection and API credentials[/dim]")
    
    def show_success(self, message: str) -> None:
        """
        Display a success message.
        
        Args:
            message: Success message to display
        """
        self.console.print(f"[green]✅ {message}[/green]")
    
    def show_warning(self, message: str) -> None:
        """
        Display a warning message.
        
        Args:
            message: Warning message to display
        """
        self.console.print(f"[yellow]⚠️  {message}[/yellow]")

