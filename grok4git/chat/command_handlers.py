"""
Command handlers for slash commands in Grok4Git chat interface.
"""

import logging
import os
from typing import List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Confirm

from ..config import config
from ..tools import TOOL_FUNCTIONS

logger = logging.getLogger(__name__)


class CommandHandler:
    """Handles execution of slash commands."""
    
    def __init__(self, console: Console, display_manager, prompt_manager, context_calculator, setup_system_message_callback):
        """
        Initialize command handler.
        
        Args:
            console: Rich console instance
            display_manager: DisplayManager instance
            prompt_manager: PromptManager instance
            context_calculator: Function to calculate context usage
        """
        self.console = console
        self.display = display_manager
        self.prompt = prompt_manager
        self.calculate_context_usage = context_calculator
        self.setup_system_message = setup_system_message_callback
    
    def execute(self, command_name: str, args: List[str], messages_list) -> bool:
        """
        Execute a slash command.
        
        Args:
            command_name: Name of the command
            args: Command arguments
            messages_list: Reference to messages list (for clear command)
            
        Returns:
            True if the session should end, False otherwise
        """
        from ..commands import command_registry
        
        cmd = command_registry.get_command(command_name)
        
        if not cmd:
            similar = command_registry.find_similar_commands(command_name)
            self.console.print(f"[red]Unknown command: [bold]/{command_name}[/bold][/red]")
            if similar:
                self.console.print(
                    f"[yellow]Did you mean: [bold]{', '.join(similar)}[/bold]?[/yellow]"
                )
            return False
        
        # Handle client control commands
        if cmd.name == "help":
            help_cmd = args[0] if args else None
            self.display.show_help(help_cmd)
            return False
        
        elif cmd.name == "clear":
            messages_list.clear()
            # Re-add system message (callback will be provided by interface)
            if self.setup_system_message:
                self.setup_system_message()
            self.console.clear()
            self.display.show_success("Conversation history cleared")
            return False
        
        elif cmd.name == "exit":
            self.console.print("[yellow]👋 Goodbye![/yellow]")
            return True
        
        elif cmd.name == "model":
            return self._handle_model(args)
        
        elif cmd.name == "repos":
            self._handle_repos(args)
            return False
        
        elif cmd.name == "peer-review-toggle":
            self._handle_peer_review_toggle(args)
            return False
        
        elif cmd.name == "peer-review-status":
            self._handle_peer_review_status()
            return False
        
        elif cmd.name == "auto-recovery-toggle":
            self._handle_auto_recovery_toggle(args)
            return False
        
        elif cmd.name == "auto-recovery-status":
            self._handle_auto_recovery_status()
            return False
        
        elif cmd.name == "history":
            self._handle_history(args, messages_list)
            return False
        
        # Unknown command (shouldn't happen due to registry check above)
        self.console.print(f"[red]Unknown command: [bold]/{command_name}[/bold][/red]")
        return False
    
    def _handle_model(self, args: List[str]) -> bool:
        """Handle /model command."""
        if not args:
            self.console.print("[red]Model name required[/red]")
            from ..commands import command_registry
            cmd = command_registry.get_command("model")
            if cmd:
                self.console.print(f"[yellow]Usage: [bold]{cmd.usage}[/bold][/yellow]")
            return False
        
        old_model = config.model_name
        old_context_size = self._get_context_window_size(old_model)
        new_model = args[0]
        new_context_size = self._get_context_window_size(new_model)
        
        # Update the environment variable and reload config
        self._update_env_variable("MODEL_NAME", new_model)
        from dotenv import load_dotenv
        load_dotenv(override=True)
        
        self.console.print(
            f"[green]✅ Model switched from [bold]{old_model}[/bold] to [bold]{new_model}[/bold][/green]"
        )
        
        # Show context window change if different
        if old_context_size != new_context_size:
            old_size_display = f"{old_context_size//1000}K"
            new_size_display = f"{new_context_size//1000}K"
            self.console.print(
                f"[blue]🔄 Context window: {old_size_display} → {new_size_display} tokens[/blue]"
            )
        
        return False
    
    def _handle_repos(self, args: List[str]) -> None:
        """Handle /repos command."""
        try:
            # Determine repository type
            repo_type = args[0] if args else "all"
            
            # Direct call to GitHub API
            from rich.status import Status
            with Status(f"[cyan]📁 Fetching {repo_type} repositories...", console=self.console):
                result = TOOL_FUNCTIONS["list_github_repos"](type=repo_type)
            
            # Display result directly
            self.console.print("[bold green]📁 Your Repositories:[/bold green]")
            self.console.print(result)
            
        except Exception as e:
            self.console.print(f"[red]❌ Error fetching repositories: {str(e)}[/red]")
    
    def _handle_peer_review_status(self) -> None:
        """Handle /peer-review-status command."""
        try:
            status_text = f"""
## 🔍 Peer Review Configuration

**Status:** {'🟢 ENABLED' if config.pr_peer_review_enabled else '🔴 DISABLED'}

**Settings:**
- Model: `{config.peer_review_model}`
- Max Iterations: `{config.max_review_iterations}`
- Environment Variable: `ENABLE_PR_PEER_REVIEW={str(config.pr_peer_review_enabled).lower()}`

**Usage:**
- Use `/peer-review-toggle enable` to enable peer review
- Use `/peer-review-toggle disable` to disable peer review
- Use `/peer-review-toggle` to toggle current state
            """

            self.console.print(
                Panel(
                    Markdown(status_text),
                    title="[bold cyan]Peer Review Status[/bold cyan]",
                    border_style="cyan",
                    padding=(1, 2),
                )
            )
        except Exception as e:
            self.console.print(f"[red]❌ Error getting peer review status: {str(e)}[/red]")
    
    def _handle_peer_review_toggle(self, args: List[str]) -> None:
        """Handle /peer-review-toggle command."""
        try:
            current_state = config.pr_peer_review_enabled
            
            if args:
                arg = args[0].lower()
                if arg in ["enable", "on", "true", "1"]:
                    new_state = True
                elif arg in ["disable", "off", "false", "0"]:
                    new_state = False
                else:
                    self.console.print(
                        f"[red]Invalid argument: {arg}. Use 'enable' or 'disable'[/red]"
                    )
                    return
            else:
                # Toggle current state
                new_state = not current_state
            
            # Update environment variable
            self._update_env_variable("ENABLE_PR_PEER_REVIEW", str(new_state).lower())
            from dotenv import load_dotenv
            load_dotenv(override=True)
            
            status_emoji = "🟢" if new_state else "🔴"
            status_text = "ENABLED" if new_state else "DISABLED"
            
            self.console.print(
                f"[green]✅ Peer review {status_text.lower()} {status_emoji}[/green]"
            )
            
        except Exception as e:
            self.console.print(f"[red]❌ Error toggling peer review: {str(e)}[/red]")
    
    def _handle_auto_recovery_status(self) -> None:
        """Handle /auto-recovery-status command."""
        try:
            status_text = f"""
## 🔄 Auto-Recovery Configuration

**Status:** {'🟢 ENABLED' if config.auto_recover_empty_responses else '🔴 DISABLED'}

**Settings:**
- Max Recovery Attempts: `{config.max_recovery_attempts}`
- Environment Variable: `AUTO_RECOVER_EMPTY_RESPONSES={str(config.auto_recover_empty_responses).lower()}`

**Usage:**
- Use `/auto-recovery-toggle enable` to enable auto-recovery
- Use `/auto-recovery-toggle disable` to disable auto-recovery
- Use `/auto-recovery-toggle` to toggle current state

**What it does:**
When enabled, if the AI returns an empty response, the system will automatically
attempt to recover by providing context and asking for a proper response.
            """

            self.console.print(
                Panel(
                    Markdown(status_text),
                    title="[bold cyan]Auto-Recovery Status[/bold cyan]",
                    border_style="cyan",
                    padding=(1, 2),
                )
            )
        except Exception as e:
            self.console.print(f"[red]❌ Error getting auto-recovery status: {str(e)}[/red]")
    
    def _handle_auto_recovery_toggle(self, args: List[str]) -> None:
        """Handle /auto-recovery-toggle command."""
        try:
            current_state = config.auto_recover_empty_responses
            
            if args:
                arg = args[0].lower()
                if arg in ["enable", "on", "true", "1"]:
                    new_state = True
                elif arg in ["disable", "off", "false", "0"]:
                    new_state = False
                else:
                    self.console.print(
                        f"[red]Invalid argument: {arg}. Use 'enable' or 'disable'[/red]"
                    )
                    return
            else:
                # Toggle current state
                new_state = not current_state
            
            # Update environment variable
            self._update_env_variable("AUTO_RECOVER_EMPTY_RESPONSES", str(new_state).lower())
            from dotenv import load_dotenv
            load_dotenv(override=True)
            
            status_emoji = "🟢" if new_state else "🔴"
            status_text = "ENABLED" if new_state else "DISABLED"
            
            self.console.print(
                f"[green]✅ Auto-recovery {status_text.lower()} {status_emoji}[/green]"
            )
            
        except Exception as e:
            self.console.print(f"[red]❌ Error toggling auto-recovery: {str(e)}[/red]")
    
    def _update_env_variable(self, key: str, value: str) -> None:
        """
        Update an environment variable in the .env file.
        
        Args:
            key: Environment variable name
            value: New value
        """
        env_file = ".env"
        
        try:
            # Read existing .env file
            env_vars = {}
            if os.path.exists(env_file):
                with open(env_file, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            env_vars[k.strip()] = v.strip()
            
            # Update the variable
            env_vars[key] = value
            
            # Write back to .env file
            with open(env_file, "w") as f:
                for k, v in env_vars.items():
                    f.write(f"{k}={v}\n")
            
            # Also update in current environment
            os.environ[key] = value
            
        except Exception as e:
            logger.warning(f"Could not update .env file: {e}")
            # Fallback: just update environment variable
            os.environ[key] = value
    
    def _handle_history(self, args: List[str], messages_list) -> None:
        """Handle /history command."""
        try:
            max_exchanges = int(args[0]) if args and args[0].isdigit() else 5
            self.display.show_conversation_history(messages_list, max_exchanges=max_exchanges)
        except Exception as e:
            self.console.print(f"[red]❌ Error showing history: {str(e)}[/red]")
    
    def _get_context_window_size(self, model_name: str) -> int:
        """
        Get the context window size for a given model.
        
        Args:
            model_name: Name of the model
            
        Returns:
            Context window size in tokens
        """
        # Model context window sizes (in tokens)
        model_limits = {
            "grok-4": 131072,  # 128K tokens
            "grok-4-0709": 131072,  # 128K tokens
            "grok-beta": 131072,  # 128K tokens
            "grok-vision-beta": 131072,  # 128K tokens
        }
        
        # Default to 128K if model not found
        return model_limits.get(model_name, 131072)

