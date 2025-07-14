"""
Chat interface for Grok4Git.

This module provides the interactive chat interface between the user and Grok,
with enhanced terminal formatting, slash commands, and user experience improvements.
"""

import json
import logging
import os
from typing import List, Dict, Any, Optional

from openai import OpenAI
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.status import Status

from .config import config
from .tools import TOOLS, TOOL_FUNCTIONS
from .commands import command_registry, command_parser, command_converter

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.formatted_text import HTML

logger = logging.getLogger(__name__)


class SlashCommandCompleter(Completer):
    def __init__(self, commands):
        self.commands = commands

    def get_completions(self, document, complete_event):
        word = document.get_word_before_cursor()
        if document.text.startswith("/"):
            for cmd in self.commands:
                if cmd.startswith(word):
                    yield Completion(cmd, start_position=-len(word))


class GrokChat:
    """Enhanced chat interface for Grok4Git with slash commands."""

    # TODO: Implement handling for large files via streaming or summaries
    # TODO: Add support for dynamic model switching

    def __init__(self):
        """Initialize the chat interface."""
        self.console = Console()
        
        # Suppress httpx logging to keep output clean
        logging.getLogger("httpx").setLevel(logging.WARNING)
        
        self.client = OpenAI(
            base_url=config.xai_base_url, 
            api_key=config.xai_api_key
            # No timeout for AI requests - users can manually abort with Ctrl+C
        )
        self.messages: List[Dict[str, Any]] = []
        self._setup_system_message()
        logger.info("Grok chat interface initialized")

    def _setup_system_message(self) -> None:
        """Setup the initial system message for the AI."""
        system_message = {
            "role": "system",
            "content": (
                "You are Grok, an AI assistant from xAI specialized in software development and GitHub operations. "
                "You have access to comprehensive GitHub integration tools that allow you to interact with repositories, "
                "manage files, create pull requests, handle issues, analyze commits, and perform various GitHub operations. "
                "Use these tools to help users with their GitHub workflows and repository management tasks. "
                "Be coherent and provide clear explanations of what you're doing.\n\n"
                "RESPONSE GUIDELINES:\n"
                "- Always explain what you're about to do before executing operations\n"
                "- Provide context and reasoning for your actions\n"
                "- Use formatting to make responses visually appealing\n"
                "- When showing code or file content, use proper formatting\n"
                "- Offer suggestions and best practices when relevant\n"
                "- If an operation fails, explain why and suggest alternatives\n\n"
                "TOOL USAGE GUIDELINES:\n"
                "- For code review: Use get_commit_history to find commits, then get_commit_details and get_commit_diff to analyze changes\n"
                "- For PRs: Branch names must be unique and descriptive (e.g., 'feature/add-logging' or 'fix/auth-bug')\n"
                "- File paths should be relative to repo root (e.g., 'src/main.py' not '/src/main.py')\n"
                "- Repository names must be in 'owner/repo' format\n"
                "- Always explain what you're doing before using destructive operations\n\n"
                "PEER REVIEW FEEDBACK HANDLING:\n"
                "- When creating pull requests, you may receive peer review feedback from a second AI agent\n"
                "- If you receive feedback with 'action: request_changes', analyze the suggestions carefully\n"
                "- Implement the requested changes by modifying your code/files accordingly\n"
                "- After making changes, create a new pull request with the improvements\n"
                "- The peer review process is iterative - continue improving until approval is received\n"
                "- Always acknowledge and address specific feedback points in your responses"
            ),
        }
        self.messages.append(system_message)

    def _display_welcome(self) -> None:
        """Display welcome message and instructions."""
        welcome_text = """
# Welcome to Grok4Git! 🚀

### 💬 **Natural Language** (Primary Interface)
Just type your request in plain English for GitHub operations:
- "Show me the README for microsoft/vscode"
- "Create a new repository called my-project"
- "List recent commits in my-repo"
- "Create a pull request for my feature"

### ⚡ **Slash Commands** (Client Control)
Use `/command` for controlling the CLI client:
- `/help` - Show help
- `/clear` - Clear chat history
- `/exit` - Exit application
- `/model <name>` - Switch AI model
- `/repos` - Quick list of your repositories
- `/peer-review-toggle` - Enable/disable peer review
- `/peer-review-status` - Show peer review settings

### 🎯 **What I Can Do**
- Repository management and analysis
- File operations and content reading
- Commit review and diff analysis
- Pull request creation and management
- **Peer review system** - Second AI agent reviews PRs before submission
- Issue tracking and creation
- Branch operations and history

### 🔄 **How It Works**
- **Natural language** → AI Agent → GitHub operations
- **Slash commands** → Direct client control (no AI needed)

### ⚡ **Pro Tips**
- **Ctrl+C** to interrupt long-running requests
- Use natural language for GitHub operations
- Use slash commands only for client control
- Try `/help` to see all available commands

**Quick Start**: Ask me "List my repositories" or try `/repos` for a quick list!
        """

        self.console.print(
            Panel(
                Markdown(welcome_text),
                title="[bold cyan]Grok4Git[/bold cyan]",
                subtitle="[dim]AI-Powered GitHub Assistant[/dim]",
                border_style="cyan",
                padding=(1, 2),
            )
        )

    def _display_command_help(self, command_name: Optional[str] = None) -> None:
        """Display help for commands."""
        if command_name:
            cmd = command_registry.get_command(command_name)
            if cmd:
                self._display_single_command_help(cmd)
            else:
                similar = command_registry.find_similar_commands(command_name)
                self.console.print(f"[red]Unknown command: [bold]/{command_name}[/bold][/red]")
                if similar:
                    self.console.print(
                        f"[yellow]Did you mean: [bold]{', '.join(similar)}[/bold]?[/yellow]"
                    )
        else:
            self._display_all_commands_help()

    def _display_single_command_help(self, cmd) -> None:
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

    def _display_all_commands_help(self) -> None:
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

    def _execute_slash_command(self, command_name: str, args: List[str]) -> bool:
        """
        Execute a slash command.

        Returns:
            True if the session should end, False otherwise
        """
        cmd = command_registry.get_command(command_name)

        if not cmd:
            similar = command_registry.find_similar_commands(command_name)
            self.console.print(f"[red]Unknown command: [bold]/{command_name}[/bold][/red]")
            if similar:
                self.console.print(
                    f"[yellow]Did you mean: [bold]{', '.join(similar)}[/bold]?[/yellow]"
                )
            return False

        # Handle client control commands directly
        if cmd.name == "help":
            help_cmd = args[0] if args else None
            self._display_command_help(help_cmd)
            return False

        elif cmd.name == "clear":
            self.messages = []
            self._setup_system_message()
            self.console.clear()
            self.console.print("[green]✅ Conversation history cleared[/green]")
            return False

        elif cmd.name == "exit":
            self.console.print("[yellow]👋 Goodbye![/yellow]")
            return True

        elif cmd.name == "model":
            if not args:
                self.console.print(f"[red]Model name required[/red]")
                self.console.print(f"[yellow]Usage: [bold]{cmd.usage}[/bold][/yellow]")
                return False
            
            old_model = config.model_name
            config.model_name = args[0]
            self.console.print(f"[green]✅ Model switched from [bold]{old_model}[/bold] to [bold]{config.model_name}[/bold][/green]")
            return False

        elif cmd.name == "repos":
            self._execute_repos_command(args)
            return False

        elif cmd.name == "peer-review-toggle":
            self._execute_peer_review_toggle(args)
            return False

        elif cmd.name == "peer-review-status":
            self._execute_peer_review_status()
            return False

        # Unknown command (shouldn't happen due to registry check above)
        self.console.print(f"[red]Unknown command: [bold]/{command_name}[/bold][/red]")
        return False

    def _execute_repos_command(self, args: List[str]) -> None:
        """Execute /repos command directly without AI."""
        from .tools import TOOL_FUNCTIONS
        
        try:
            # Determine repository type
            repo_type = args[0] if args else "all"
            
            # Direct call to GitHub API
            with Status(f"[cyan]📁 Fetching {repo_type} repositories...", console=self.console):
                result = TOOL_FUNCTIONS["list_github_repos"](type=repo_type)
            
            # Display result directly
            self.console.print("[bold green]📁 Your Repositories:[/bold green]")
            self.console.print(result)
            
        except Exception as e:
            self.console.print(f"[red]❌ Error fetching repositories: {str(e)}[/red]")

    def _execute_peer_review_status(self) -> None:
        """Execute /peer-review-status command directly."""
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
            self.console.print(f"[red]❌ Error reading peer review status: {str(e)}[/red]")

    def _execute_peer_review_toggle(self, args: List[str]) -> None:
        """Execute /peer-review-toggle command directly."""
        try:
            current_status = config.pr_peer_review_enabled
            
            if not args:
                # Toggle current state
                new_status = not current_status
                action = "enabled" if new_status else "disabled"
                self.console.print(f"[yellow]🔄 Toggling peer review from {('enabled' if current_status else 'disabled')} to {action}[/yellow]")
            else:
                # Set specific state
                arg = args[0].lower()
                if arg in ["enable", "on", "true"]:
                    new_status = True
                    action = "enabled"
                elif arg in ["disable", "off", "false"]:
                    new_status = False
                    action = "disabled"
                else:
                    self.console.print(f"[red]❌ Invalid argument: {args[0]}[/red]")
                    self.console.print("[yellow]Usage: /peer-review-toggle [enable|disable][/yellow]")
                    return
            
            # Update .env file
            self._update_env_variable("ENABLE_PR_PEER_REVIEW", str(new_status).lower())
            
            # Reload config
            from dotenv import load_dotenv
            load_dotenv(override=True)
            
            # Confirm the change
            emoji = "🟢" if new_status else "🔴"
            self.console.print(f"[green]✅ Peer review {action} {emoji}[/green]")
            
        except Exception as e:
            self.console.print(f"[red]❌ Error toggling peer review: {str(e)}[/red]")

    def _update_env_variable(self, key: str, value: str) -> None:
        """Update a single environment variable in .env file."""
        env_file = ".env"
        
        # Read current .env file
        env_lines = []
        if os.path.exists(env_file):
            with open(env_file, "r") as f:
                env_lines = f.readlines()
        
        # Update or add the key
        key_found = False
        for i, line in enumerate(env_lines):
            if line.strip().startswith(f"{key}="):
                env_lines[i] = f"{key}={value}\n"
                key_found = True
                break
        
        # Add the key if not found
        if not key_found:
            env_lines.append(f"{key}={value}\n")
        
        # Write back to .env file
        with open(env_file, "w") as f:
            f.writelines(env_lines)

    def _get_user_input(self) -> str:
        """Get user input with rich prompt and command auto-completion."""
        try:
            session: PromptSession = PromptSession(
                completer=SlashCommandCompleter(list(command_registry.commands.keys()))
            )
            user_input = session.prompt(HTML("<ansicyan><b>You</b></ansicyan>: "))
            return user_input.strip()
        except (KeyboardInterrupt, EOFError):
            self.console.print("\n[yellow]Session ended by user[/yellow]")
            return "/exit"

    def _display_response(self, content: str) -> None:
        """Display AI response with rich formatting."""
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
            self.console.print(
                "[bold green]🤖 Grok:[/bold green] [yellow]No response content[/yellow]"
            )

    def _execute_tool(self, tool_call) -> str:
        """Execute a tool function call."""
        function_name = tool_call.function.name

        try:
            function_args = json.loads(tool_call.function.arguments)
        except json.JSONDecodeError as e:
            error_msg = f"Error parsing tool arguments: {str(e)}"
            logger.error(error_msg)
            return error_msg

        if function_name not in TOOL_FUNCTIONS:
            error_msg = f"Unknown function: {function_name}"
            logger.error(error_msg)
            return error_msg

        # Check if this is a destructive operation that requires confirmation
        if function_name in ["delete_file", "create_repository"]:
            if not self._confirm_destructive_operation(function_name, function_args):
                return "Operation cancelled by user"

        try:
            # Create status message with consistent alignment
            # Pad function name to consistent width for better alignment
            padded_function_name = f"{function_name}".ljust(25)
            status_msg = f"[cyan]⚡ Executing {padded_function_name} ->"
            
            with Status(status_msg, console=self.console) as status:
                function_to_call = TOOL_FUNCTIONS.get(function_name)
                if function_to_call is None:
                    return f"Error: Unknown function {function_name}"
                if callable(function_to_call):
                    result = function_to_call(**function_args)
                else:
                    return f"Error: {function_name} is not callable"

                # Extract meaningful info from result for compact display
                result_summary = self._extract_tool_result_summary(function_name, result, function_args)
                
                # Update status with result and checkmark (this shows briefly)
                status.update(f"[cyan]⚡ Executing {padded_function_name} -> {result_summary} ✅")
                
                # Brief pause to show the result
                import time
                time.sleep(0.3)

            # Print the final line to make it persistent (after status context ends)
            self.console.print(f"[cyan]⚡ Executing {padded_function_name} -> {result_summary} ✅")

            # Only log detailed info in debug mode
            if logger.isEnabledFor(logging.DEBUG):
                logger.info(f"Tool {function_name} executed successfully")
                logger.debug(f"Tool result: {result}")

            return str(result)

        except Exception as e:
            error_msg = f"Error executing {function_name}: {str(e)}"
            logger.error(error_msg)
            return error_msg

    def _extract_tool_result_summary(self, function_name: str, result: str, args: dict) -> str:
        """Extract a concise summary from tool execution results."""
        try:
            # Handle different tool types
            if function_name == "list_github_repos":
                # Extract repository count
                import json
                try:
                    repos = json.loads(result)
                    return f"Found {len(repos)} repositories"
                except:
                    return "Listed repositories"
            
            elif function_name == "get_repo_info":
                # Extract repo name
                repo = args.get("repo", "repository")
                return f"Got info for {repo}"
            
            elif function_name == "recursive_list_directory":
                # Extract directory and file count
                repo = args.get("repo", "")
                path = args.get("path", "")
                try:
                    import json
                    items = json.loads(result)
                    return f"Listed {len(items)} items in {repo}/{path}"
                except:
                    return f"Listed directory {repo}/{path}"
            
            elif function_name == "get_commit_history":
                # Extract commit count
                repo = args.get("repo", "repository")
                try:
                    import json
                    commits = json.loads(result)
                    return f"Got {len(commits)} commits from {repo}"
                except:
                    return f"Got commit history for {repo}"
            
            elif function_name == "manage_issues":
                # Extract issue info
                repo = args.get("repo", "repository")
                action = args.get("action", "managed")
                if action == "list":
                    try:
                        import json
                        issues = json.loads(result)
                        return f"Found {len(issues)} issues in {repo}"
                    except:
                        return f"Listed issues in {repo}"
                else:
                    return f"Issue {action}d in {repo}"
            
            elif function_name == "get_file_content":
                # Extract file info
                repo = args.get("repo", "")
                path = args.get("path", "file")
                return f"Read {repo}/{path}"
            
            elif function_name == "create_pull_request":
                # Extract PR info
                repo = args.get("repo", "repository")
                return f"Created PR in {repo}"
            
            elif function_name == "search_repositories":
                # Extract search results
                query = args.get("query", "")
                try:
                    import json
                    results = json.loads(result)
                    return f"Found {len(results)} repos for '{query}'"
                except:
                    return f"Searched for '{query}'"
            
            else:
                # Generic fallback
                return "Completed"
                
        except Exception as e:
            logger.debug(f"Error extracting tool summary: {e}")
            return "Completed"

    def _confirm_destructive_operation(
        self, function_name: str, function_args: Dict[str, Any]
    ) -> bool:
        """Ask user to confirm destructive operations."""
        from rich.prompt import Confirm

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

    def _process_ai_response(self) -> None:
        """Process AI response and handle tool calls."""
        try:
            with Status("[cyan]🤔 Thinking...", console=self.console):
                response = self.client.chat.completions.create(  # type: ignore
                    model=config.model_name, 
                    messages=self.messages, 
                    tools=TOOLS, 
                    tool_choice="auto"
                )

            response_message = response.choices[0].message
            self.messages.append(response_message)

            # Handle tool calls
            if response_message.tool_calls:
                for tool_call in response_message.tool_calls:
                    result = self._execute_tool(tool_call)
                    self.messages.append(
                        {"role": "tool", "content": result, "tool_call_id": tool_call.id}
                    )

                # Get final response after tool execution
                self._process_ai_response()
            else:
                # Display final response
                content = response_message.content
                if content:
                    self._display_response(content)
                else:
                    self.console.print("[yellow]No response content received[/yellow]")

        except KeyboardInterrupt:
            self.console.print("\n[yellow]⚠️  Request interrupted by user[/yellow]")
            self.console.print("[dim]💡 Tip: You can always interrupt long-running requests with Ctrl+C[/dim]")
            logger.info("AI request interrupted by user")
        except Exception as e:
            error_msg = f"Error processing AI response: {str(e)}"
            logger.error(error_msg)
            self.console.print(f"[red]❌ Error: {error_msg}[/red]")
            self.console.print("[dim]💡 Tip: You can interrupt requests with Ctrl+C and try again[/dim]")

    def run(self) -> None:
        """Run the main chat loop."""
        self._display_welcome()

        while True:
            try:
                user_input = self._get_user_input()

                if not user_input:
                    continue

                # Check if it's a slash command
                is_command, command_name, args = command_parser.parse_command(user_input)

                if is_command:
                    # Handle slash command
                    if self._execute_slash_command(command_name, args):
                        break  # Exit if command returned True
                else:
                    # Handle natural language input
                    self.messages.append({"role": "user", "content": user_input})
                    self._process_ai_response()

            except KeyboardInterrupt:
                self.console.print("\n[yellow]Session interrupted by user[/yellow]")
                break
            except Exception as e:
                error_msg = f"Unexpected error in chat loop: {str(e)}"
                logger.error(error_msg)
                self.console.print(f"[red]❌ Error: {error_msg}[/red]")
                self.console.print(
                    "[yellow]You can continue chatting or type '/exit' to quit[/yellow]"
                )


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
