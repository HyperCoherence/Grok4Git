"""
AI client for managing OpenAI interactions and message history.
"""

import json
import logging
import time
from typing import List, Dict, Any, Tuple, Callable, Optional

from openai import OpenAI
from rich.console import Console
from rich.status import Status

from ..config import config
from ..tools import TOOLS, TOOL_FUNCTIONS
from .ui.formatters import format_tool_result
from .ui.display import DisplayManager

logger = logging.getLogger(__name__)


class AIClient:
    """Manages AI client interactions, message history, and tool execution."""
    
    def __init__(self, console: Console, display_manager: DisplayManager, confirm_callback: Callable):
        """
        Initialize AI client.
        
        Args:
            console: Rich console instance
            display_manager: DisplayManager instance for showing responses
            confirm_callback: Callback function for confirming destructive operations
        """
        self.console = console
        self.display = display_manager
        self.confirm_callback = confirm_callback
        
        # Suppress httpx logging to keep output clean
        logging.getLogger("httpx").setLevel(logging.WARNING)
        
        self.client = OpenAI(
            base_url=config.xai_base_url,
            api_key=config.xai_api_key
        )
        self.messages: List[Dict[str, Any]] = []
        self._setup_system_message()
        logger.info("AI client initialized")
    
    def _setup_system_message(self) -> None:
        """Setup the initial system message for the AI."""
        system_message = {
            "role": "system",
            "content": (
                "Your primary function is to provide coherent, systematic analysis and assistance with repository management.\n\n"
                
                "CORE PROCESS FRAMEWORK:\n"
                "When engaging with any repository or development task, follow this unified process:\n\n"
                
                "1. UNDERSTAND\n"
                "   • Analyze the request to identify the core objective\n"
                "   • Determine what information is needed to provide a complete response\n"
                "   • For new repositories: Use get_bulk_codebase_overview() for comprehensive understanding\n"
                "   • For specific areas: Use targeted tools (get_file_content, list_directory_contents)\n\n"
                
                "2. ANALYZE\n"
                "   • Synthesize gathered information into coherent patterns\n"
                "   • Identify relationships between files, components, and architectural decisions\n"
                "   • Assess current state against requested objectives\n"
                "   • Consider implications and dependencies\n\n"
                
                "3. PLAN\n"
                "   • Design the minimal viable approach to achieve the objective\n"
                "   • Sequence operations logically with clear dependencies\n"
                "   • Anticipate potential issues and prepare contingencies\n"
                "   • Explain your approach before execution\n\n"
                
                "4. EXECUTE\n"
                "   • Perform operations in logical sequence\n"
                "   • Use efficient batch operations (get_bulk_file_content) over individual calls\n"
                "   • Maintain context awareness throughout execution\n"
                "   • Provide status updates for complex operations\n\n"
                
                "5. SYNTHESIZE\n"
                "   • Always provide meaningful responses that close the interaction loop\n"
                "   • Summarize what was accomplished and its significance\n"
                "   • Offer relevant insights, patterns, or recommendations\n"
                "   • Connect results back to the original objective\n\n"
                
                "RESPONSE COHERENCE REQUIREMENTS:\n"
                "• Every response must emerge from unified analysis, not fragmented execution\n"
                "• Maintain consistent logical flow from understanding through synthesis\n"
                "• Never send empty responses - always acknowledge and summarize\n"
                "• Use clear formatting to enhance comprehension\n"
                "• Provide context for actions and explain reasoning\n\n"
                
                "TECHNICAL EXECUTION STANDARDS:\n"
                "• Repository format: 'owner/repo' (e.g., 'microsoft/vscode')\n"
                "• File paths: relative to repo root (e.g., 'src/main.py')\n"
                "• Branch names: descriptive and unique (e.g., 'feature/auth-system')\n"
                "• Bulk operations: preferred over individual file reads for efficiency\n"
                "• Error handling: explain failures and provide actionable alternatives\n\n"
                
                "SPECIALIZED WORKFLOWS:\n"
                "• Code Review: get_commit_history → get_commit_details → get_commit_diff → analysis\n"
                "• Pull Requests: may receive peer review feedback requiring iterative improvement\n"
                "• New Repositories: start with get_bulk_codebase_overview for comprehensive context\n"
                "• File Operations: batch with get_bulk_file_content when reading multiple files\n\n"
                
                "PEER REVIEW INTEGRATION:\n"
                "When creating pull requests, a second AI agent may provide review feedback. "
                "Address all feedback systematically, implement requested changes, and iterate until approval. "
                "Always acknowledge specific feedback points in your responses.\n\n"
                
                "Your goal is to provide coherent, systematic assistance that demonstrates deep understanding "
                "of both the immediate request and its broader context within the development workflow."
            ),
        }
        self.messages.append(system_message)
    
    def send_message(self, user_input: str) -> None:
        """
        Send a user message and process AI response.
        
        Args:
            user_input: User's input message
        """
        self.messages.append({"role": "user", "content": user_input})
        self._process_ai_response()
    
    def _process_ai_response(self) -> None:
        """Process AI response and handle tool calls."""
        self._process_ai_response_with_recovery()
    
    def _process_ai_response_with_recovery(self, recovery_attempt: int = 0) -> None:
        """Process AI response with auto-recovery for empty responses."""
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
                total_tools = len(response_message.tool_calls)
                for idx, tool_call in enumerate(response_message.tool_calls, 1):
                    # Show progress for multiple tool calls
                    if total_tools > 1:
                        progress_msg = f"[dim]⚡[/dim] [cyan]{tool_call.function.name}[/cyan]... [{idx}/{total_tools}]"
                        with Status(progress_msg, console=self.console):
                            result = self._execute_tool(tool_call)
                    else:
                        result = self._execute_tool(tool_call)
                    
                    self.messages.append(
                        {"role": "tool", "content": result, "tool_call_id": tool_call.id}
                    )

                # Get final response after tool execution
                self._process_ai_response_with_recovery(recovery_attempt)
            else:
                # Display final response
                content = response_message.content
                if content and content.strip():
                    self.display.show_response(content)
                else:
                    # Handle empty response with auto-recovery
                    self._handle_empty_response(recovery_attempt)

        except KeyboardInterrupt:
            self.console.print("\n[yellow]⚠️  Request interrupted by user[/yellow]")
            self.console.print("[dim]💡 Tip: You can always interrupt long-running requests with Ctrl+C[/dim]")
            logger.info("AI request interrupted by user")
        except Exception as e:
            error_msg = f"Error processing AI response: {str(e)}"
            logger.error(error_msg)
            suggestion = "Try: Interrupt with Ctrl+C and rephrase your request, or use `/clear` to reset context"
            self.display.show_error(error_msg, suggestion=suggestion)
    
    def _execute_tool(self, tool_call) -> str:
        """
        Execute a tool function call.
        
        Args:
            tool_call: Tool call object from OpenAI API
            
        Returns:
            Tool execution result as string
        """
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
            if not self.confirm_callback(function_name, function_args):
                return "Operation cancelled by user"

        try:
            # Show compact status message
            status_msg = f"[dim]⚡[/dim] [cyan]{function_name}[/cyan]..."
            
            with Status(status_msg, console=self.console) as status:
                function_to_call = TOOL_FUNCTIONS.get(function_name)
                if function_to_call is None:
                    return f"Error: Unknown function {function_name}"
                if callable(function_to_call):
                    result = function_to_call(**function_args)
                else:
                    return f"Error: {function_name} is not callable"

                # Extract meaningful info from result for compact display
                result_summary = format_tool_result(function_name, result, function_args)
                
                # Update status with result
                status.update(f"[dim]⚡[/dim] [cyan]{function_name}[/cyan] → {result_summary}")

            # Print the final line to make it persistent (compact format)
            self.console.print(f"[dim]⚡[/dim] [cyan]{function_name}[/cyan] → {result_summary} [green]✅[/green]")

            # Only log detailed info in debug mode
            if logger.isEnabledFor(logging.DEBUG):
                logger.info(f"Tool {function_name} executed successfully")
                logger.debug(f"Tool result: {result}")

            return str(result)

        except Exception as e:
            error_msg = f"Error executing {function_name}: {str(e)}"
            logger.error(error_msg)
            return error_msg
    
    def _handle_empty_response(self, recovery_attempt: int) -> None:
        """Handle empty responses with auto-recovery or fallback."""
        if not config.auto_recover_empty_responses:
            # Auto-recovery disabled, show original error message
            self.display.show_warning("No response content received")
            return

        if recovery_attempt >= config.max_recovery_attempts:
            # Max attempts reached, show enhanced error message
            self.display.show_warning("No response content received after recovery attempts")
            self.console.print("[dim]💡 Try rephrasing your request or use '/clear' to reset context[/dim]")
            logger.warning(f"Failed to recover from empty response after {recovery_attempt} attempts")
            return

        # Attempt auto-recovery
        logger.info(f"Attempting auto-recovery for empty response (attempt {recovery_attempt + 1}/{config.max_recovery_attempts})")
        
        # Remove the empty response message
        if self.messages and self.messages[-1].get("role") == "assistant":
            self.messages.pop()

        # Analyze recent context for recovery message
        recovery_context = self._build_recovery_context()
        
        # Add recovery prompt
        recovery_message = {
            "role": "user",
            "content": (
                f"You didn't provide any response to my previous message. {recovery_context}"
                f"Please provide a meaningful response addressing my request. "
                f"If you performed any actions, summarize what was accomplished. "
                f"If you need clarification, ask specific questions."
            )
        }
        self.messages.append(recovery_message)

        # Show recovery status to user
        status_text = f"[cyan]🔄 Auto-recovering from empty response (attempt {recovery_attempt + 1}/{config.max_recovery_attempts})..."
        with Status(status_text, console=self.console):
            time.sleep(0.5)  # Brief pause to show status

        # Retry with recovery context
        self._process_ai_response_with_recovery(recovery_attempt + 1)
    
    def _build_recovery_context(self) -> str:
        """Build context information for recovery attempts."""
        context_parts = []
        
        # Check for recent tool calls
        recent_tool_calls = []
        for msg in reversed(self.messages[-5:]):  # Check last 5 messages
            if msg.get("role") == "assistant" and msg.get("tool_calls"):
                for tool_call in msg["tool_calls"]:
                    recent_tool_calls.append(tool_call.function.name)
        
        if recent_tool_calls:
            tools_text = ", ".join(set(recent_tool_calls))
            context_parts.append(f"You just executed these tools: {tools_text}.")
        
        # Check for user's original request
        user_messages = [msg for msg in self.messages if msg.get("role") == "user"]
        if user_messages:
            last_user_msg = user_messages[-1].get("content", "")
            # Exclude recovery messages
            if not last_user_msg.startswith("You didn't provide any response"):
                context_parts.append(
                    f"My original request was: '{last_user_msg[:100]}{'...' if len(last_user_msg) > 100 else ''}'"
                )
        
        return " ".join(context_parts) + " " if context_parts else ""
    
    def calculate_context_usage(self) -> Tuple[int, int, float]:
        """
        Calculate current context usage.
        
        Returns:
            Tuple of (used_tokens, total_tokens, usage_percentage)
        """
        total_tokens = 0
        
        # Count tokens in all messages
        for message in self.messages:
            content = ""
            
            try:
                # Handle both dict and ChatCompletionMessage objects
                if isinstance(message, dict):
                    content = message.get("content", "")
                else:
                    # ChatCompletionMessage object - handle various attributes
                    content = getattr(message, "content", "") or ""
                
                # Ensure content is a string
                if content is not None:
                    total_tokens += self._estimate_token_count(str(content))
                    
            except Exception as e:
                # Skip problematic messages but log for debugging
                logger.debug(f"Error processing message for token count: {e}")
                continue
        
        # Get context window size for current model
        context_window = self._get_context_window_size(config.model_name)
        
        # Ensure we don't divide by zero
        if context_window <= 0:
            context_window = 131072  # Default fallback
        
        # Calculate percentage used
        usage_percentage = (total_tokens / context_window) * 100
        
        return total_tokens, context_window, usage_percentage
    
    def _estimate_token_count(self, text: str) -> int:
        """
        Estimate token count for a given text.
        
        Args:
            text: Text to estimate tokens for
            
        Returns:
            Estimated token count
        """
        # Rough estimation: 1 token ≈ 4 characters for most text
        return len(text) // 4
    
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
    
    def clear_messages(self) -> None:
        """Clear all messages and reset system message."""
        self.messages.clear()
        self._setup_system_message()

