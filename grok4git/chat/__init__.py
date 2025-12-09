"""
Chat interface components for Grok4Git.

This package contains the refactored chat interface with separated concerns:
- ai_client: AI client management and message handling
- command_handlers: Slash command execution
- ui: User interface components (display, prompts, formatters)
- interface: Main chat interface orchestration
"""

from .interface import GrokChat

__all__ = ["GrokChat"]

