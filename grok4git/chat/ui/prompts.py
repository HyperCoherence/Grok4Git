"""
Prompt manager for chat interface user input.
"""

import logging
import random
from typing import Callable, Tuple

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.formatted_text import HTML

from ...commands import command_registry

logger = logging.getLogger(__name__)


class SlashCommandCompleter(Completer):
    """Completer for slash commands."""
    
    def __init__(self, commands):
        """
        Initialize command completer.
        
        Args:
            commands: List of command names
        """
        self.commands = commands

    def get_completions(self, document, complete_event):
        """Get command completions."""
        word = document.get_word_before_cursor()
        if document.text.startswith("/"):
            for cmd in self.commands:
                if cmd.startswith(word):
                    yield Completion(cmd, start_position=-len(word))


class PromptManager:
    """Manages user input prompts and context status."""
    
    def __init__(self, console, calculate_context_usage: Callable[[], Tuple[int, int, float]]):
        """
        Initialize prompt manager.
        
        Args:
            console: Rich console instance
            calculate_context_usage: Function that returns (used, total, percentage) tuple
        """
        self.console = console
        self.calculate_context_usage = calculate_context_usage
        self._session = None
    
    def get_user_input(self) -> str:
        """
        Get user input with rich prompt and command auto-completion.
        
        Returns:
            User input string, or "/exit" if interrupted
        """
        try:
            # Show context status bar (non-intrusive, only when needed)
            self._show_context_status_bar()
            
            # Show contextual hints occasionally (first few inputs)
            self._show_contextual_hint()
            
            # Create clean prompt without inline context status
            prompt_html = "<ansicyan><b>You</b></ansicyan>: "
            
            if self._session is None:
                self._session = PromptSession(
                    completer=SlashCommandCompleter(list(command_registry.commands.keys()))
                )
            
            user_input = self._session.prompt(HTML(prompt_html))
            return user_input.strip()
        except (KeyboardInterrupt, EOFError):
            self.console.print("\n[yellow]Session ended by user[/yellow]")
            return "/exit"
    
    def _show_contextual_hint(self) -> None:
        """Show contextual hints to help users discover features."""
        # Show hints only occasionally (not every time)
        if random.random() > 0.1:  # 10% chance to show hint
            return
        
        hints = [
            "[dim]💡 Tip: Press Tab for command completion, or use [/dim][bold]/help[/bold][dim] for all commands[/dim]",
            "[dim]💡 Tip: Use [/dim][bold]/repos[/bold][dim] to quickly list your repositories[/dim]",
            "[dim]💡 Tip: Use [/dim][bold]/history[/bold][dim] to view recent conversation[/dim]",
            "[dim]💡 Tip: Use [/dim][bold]/clear[/bold][dim] if context gets full[/dim]",
        ]
        
        # Show a random hint
        hint = random.choice(hints)
        self.console.print(hint)
    
    def _show_context_status_bar(self) -> None:
        """Show context status bar only when needed (non-intrusive)."""
        try:
            used_tokens, total_tokens, usage_percentage = self.calculate_context_usage()
            remaining_percentage = 100 - usage_percentage
            
            # Only show warnings when context is getting low
            if usage_percentage > 95:  # Critical
                self.console.print(
                    f"[red]🚨 Context: {usage_percentage:.0f}% full - Use [bold]/clear[/bold] to reset[/red]"
                )
            elif usage_percentage > 80:  # Warning
                # Show compact status bar
                if used_tokens < 1000:
                    token_display = f"{used_tokens}"
                else:
                    token_display = f"{used_tokens/1000:.1f}K"
                total_display = f"{total_tokens//1000}K"
                self.console.print(
                    f"[yellow]⚠️  Context: {usage_percentage:.0f}% ({token_display}/{total_display}) - Consider [bold]/clear[/bold][/yellow]"
                )
            # Don't show anything when context is healthy (>20% remaining)
            
        except Exception as e:
            logger.debug(f"Error showing context status: {e}")
    
    def _get_context_status_plain(self) -> str:
        """
        Get a plain text version of context status for prompt integration.
        
        Returns:
            Plain text context status string
        """
        try:
            used_tokens, total_tokens, usage_percentage = self.calculate_context_usage()
            remaining_percentage = 100 - usage_percentage
            
            # Choose emoji based on usage
            if remaining_percentage > 70:
                emoji = "🟢"
            elif remaining_percentage > 40:
                emoji = "🟡"
            elif remaining_percentage > 20:
                emoji = "🟠"
            else:
                emoji = "🔴"
            
            # Format the display with token count for more detail
            if used_tokens < 1000:
                token_display = f"{used_tokens}"
            else:
                token_display = f"{used_tokens/1000:.1f}K"
            
            total_display = f"{total_tokens//1000}K"
            
            return f"{emoji} {remaining_percentage:.0f}% Context Left ({token_display}/{total_display}) "
            
        except Exception as e:
            logger.debug(f"Error calculating context usage: {e}")
            return ""

