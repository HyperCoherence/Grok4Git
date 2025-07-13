"""
Grok4Git - AI-powered GitHub repository management tool.

This package provides a command-line interface for interacting with GitHub repositories
using natural language through Grok AI.
"""

try:
    # Try to get version from setuptools-scm
    from importlib.metadata import version

    __version__ = version("grok4git")
except ImportError:
    # Fallback for older Python versions
    try:
        from importlib_metadata import version

        __version__ = version("grok4git")
    except ImportError:
        # Final fallback if package not installed
        __version__ = "1.0.0"
__author__ = "Oliver Baumgart"
__description__ = "AI-powered GitHub repository management tool"

# Main modules
from . import config
from . import github_api
from . import tools
from . import chat

__all__ = ["config", "github_api", "tools", "chat"]
