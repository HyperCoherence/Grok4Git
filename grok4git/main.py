#!/usr/bin/env python3
"""
Grok4Git - AI-powered GitHub repository management tool.

This is the main entry point for the Grok4Git application, providing
a command-line interface for interacting with GitHub repositories
using natural language through Grok AI.
"""

import argparse
import logging
import sys

from .config import config
from .chat import GrokChat
from .github_api import github_api

logger = logging.getLogger(__name__)


def setup_argument_parser() -> argparse.ArgumentParser:
    """Set up command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Grok4Git - AI-powered GitHub repository management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    # Start interactive chat
  %(prog)s --log-level DEBUG  # Enable debug logging
  %(prog)s --model grok-4     # Use specific model
  %(prog)s --version          # Show version information

Environment Variables:
  XAI_API_KEY      - Your xAI API key (required)
  GITHUB_TOKEN     - Your GitHub personal access token (required)
  GITHUB_USERNAME  - Your GitHub username (required)
  MODEL_NAME       - AI model to use (default: grok-4-0709)
  LOG_LEVEL        - Logging level (default: INFO)

For more information, visit: https://github.com/HyperCoherence/Grok4Git
        """,
    )

    parser.add_argument("--version", action="version", version="Grok4Git v1.0.0")

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default=config.log_level,
        help="Set logging level (default: %(default)s)",
    )

    parser.add_argument(
        "--model", default=config.model_name, help="AI model to use (default: %(default)s)"
    )

    parser.add_argument("--no-color", action="store_true", help="Disable colored output")

    parser.add_argument("--config-test", action="store_true", help="Test configuration and exit")

    return parser


def test_configuration() -> bool:
    """Test configuration and connectivity."""
    try:
        from rich.console import Console
        from rich.table import Table

        console = Console()

        # Test basic configuration
        console.print("[bold cyan]Testing Configuration...[/bold cyan]")

        table = Table(title="Configuration Status")
        table.add_column("Setting", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Value", style="yellow")

        # Check required environment variables
        table.add_row(
            "xAI API Key",
            "✓ Set" if config.xai_api_key else "✗ Missing",
            "***" if config.xai_api_key else "Not set",
        )
        table.add_row(
            "GitHub Token",
            "✓ Set" if config.github_token else "✗ Missing",
            "***" if config.github_token else "Not set",
        )
        table.add_row(
            "GitHub Username",
            "✓ Set" if config.github_username else "✗ Missing",
            config.github_username or "Not set",
        )
        table.add_row("Model Name", "✓ Set", config.model_name)
        table.add_row("Log Level", "✓ Set", config.log_level)

        console.print(table)

        if not all([config.xai_api_key, config.github_token, config.github_username]):
            console.print(
                "[red]❌ Configuration incomplete. Please check your environment variables.[/red]"
            )
            return False

        # Test GitHub API connectivity
        console.print("\n[bold cyan]Testing GitHub API Connection...[/bold cyan]")
        try:
            # Make a simple API call to test connectivity
            url = f"{config.github_api_base_url}/user"
            response = github_api.make_request("GET", url)
            user_data = response.json()

            console.print("[green]✓ GitHub API connection successful[/green]")
            console.print(f"[green]✓ Authenticated as: {user_data.get('login', 'Unknown')}[/green]")

        except Exception as e:
            console.print(f"[red]❌ GitHub API connection failed: {str(e)}[/red]")
            return False

        # Test xAI API connectivity
        console.print("\n[bold cyan]Testing xAI API Connection...[/bold cyan]")
        try:
            from openai import OpenAI

            client = OpenAI(base_url=config.xai_base_url, api_key=config.xai_api_key)

            # Make a simple API call to test connectivity
            response = client.chat.completions.create(
                model=config.model_name,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=10,
            )

            console.print("[green]✓ xAI API connection successful[/green]")
            console.print(f"[green]✓ Using model: {config.model_name}[/green]")

        except Exception as e:
            console.print(f"[red]❌ xAI API connection failed: {str(e)}[/red]")
            return False

        console.print(
            "\n[bold green]🎉 All tests passed! Configuration is working correctly.[/bold green]"
        )
        return True

    except Exception as e:
        print(f"Configuration test failed: {str(e)}")
        return False


def main():
    """Main entry point for the application."""
    parser = setup_argument_parser()
    args = parser.parse_args()

    # Update configuration based on arguments
    if args.log_level:
        import os

        os.environ["LOG_LEVEL"] = args.log_level
        config.setup_logging()

    if args.model:
        import os

        os.environ["MODEL_NAME"] = args.model

    # Handle no-color option
    if args.no_color:
        import os

        os.environ["NO_COLOR"] = "1"

    logger.info(f"Starting Grok4Git with model: {config.model_name}")
    logger.info(f"Log level: {config.log_level}")

    try:
        # Test configuration if requested
        if args.config_test:
            success = test_configuration()
            sys.exit(0 if success else 1)

        # Start the chat interface
        chat = GrokChat()
        chat.run()

    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
        print("\nGoodbye! 👋")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Application error: {str(e)}")
        print(f"Error: {str(e)}")
        sys.exit(1)
    finally:
        # Cleanup
        try:
            github_api.close()
            logger.info("Application shutdown complete")
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")


if __name__ == "__main__":
    main()
