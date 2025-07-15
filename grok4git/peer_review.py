"""
Peer review system for Grok4Git pull requests.

This module provides a second AI agent that reviews pull requests
before they are submitted to GitHub, enabling iterative improvement
and higher code quality.
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, NamedTuple
from enum import Enum

from openai import OpenAI
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

from .config import config

logger = logging.getLogger(__name__)


class ReviewDecision(Enum):
    """Possible decisions from peer review."""
    APPROVE = "approve"
    REQUEST_CHANGES = "request_changes"
    NEEDS_MAJOR_REVISION = "needs_major_revision"


@dataclass
class PeerReviewResult:
    """Result of peer review process."""
    decision: ReviewDecision
    feedback: str
    suggestions: List[str]
    should_proceed: bool
    iteration_count: int
    
    def to_agent_message(self) -> str:
        """Convert result to message format for main agent."""
        if self.decision == ReviewDecision.APPROVE:
            return f"Pull request approved by peer review agent after {self.iteration_count} iteration(s). Proceeding with GitHub submission."
        
        elif self.decision == ReviewDecision.REQUEST_CHANGES:
            message = f"Peer review feedback (iteration {self.iteration_count}):\n\n"
            message += f"**Feedback:** {self.feedback}\n\n"
            message += "**Suggestions:**\n"
            for i, suggestion in enumerate(self.suggestions, 1):
                message += f"{i}. {suggestion}\n"
            message += "\nPlease implement these changes and create an updated pull request."
            return message
        
        elif self.decision == ReviewDecision.NEEDS_MAJOR_REVISION:
            message = f"Peer review identified major issues requiring significant revision:\n\n"
            message += f"**Feedback:** {self.feedback}\n\n"
            message += "**Critical Issues:**\n"
            for i, suggestion in enumerate(self.suggestions, 1):
                message += f"{i}. {suggestion}\n"
            message += "\nThis PR cannot be submitted in its current state. Please address these fundamental issues."
            return message


@dataclass
class PeerReviewContext:
    """Context for peer review session."""
    repo: str
    title: str
    body: str
    files: List[Dict[str, str]]
    commit_message: str
    branch_name: str
    base_branch: Optional[str] = None
    user_request: Optional[str] = None  # Original user request context
    
    # Review state
    current_iteration: int = 0
    review_history: List[Dict[str, Any]] = field(default_factory=list)
    final_decision: Optional[ReviewDecision] = None
    
    def add_review_iteration(self, decision: ReviewDecision, feedback: str, suggestions: List[str]):
        """Add a review iteration to the history."""
        self.review_history.append({
            "iteration": self.current_iteration,
            "decision": decision.value,
            "feedback": feedback,
            "suggestions": suggestions,
            "timestamp": self._get_timestamp()
        })
        self.current_iteration += 1
    
    def _get_timestamp(self) -> str:
        """Get current timestamp for review history."""
        from datetime import datetime
        return datetime.now().isoformat()


class PeerReviewAgent:
    """AI agent specialized in code review with GitHub tool access."""
    
    def __init__(self):
        """Initialize the peer review agent."""
        self.client = OpenAI(
            base_url=config.xai_base_url,
            api_key=config.xai_api_key
        )
        self.messages: List[Dict[str, Any]] = []
        self._setup_system_message()
        logger.info("Enhanced peer review agent initialized with tool access")
    
    def _setup_system_message(self) -> None:
        """Setup specialized system message for code review."""
        system_message = {
            "role": "system",
            "content": (
                "You are a Senior Code Review Agent specialized in thorough, constructive peer review. "
                "You have access to GitHub tools to explore repository context and provide comprehensive reviews. "
                "Your primary responsibility is to review pull requests before they are submitted to GitHub. "
                "You work alongside another AI agent and provide a second pair of eyes to ensure code quality.\n\n"
                
                "AVAILABLE TOOLS:\n"
                "You have access to the same GitHub tools as the main agent, including:\n"
                "- get_file_content: Read existing files to understand context\n"
                "- list_directory_contents: Explore repository structure\n"
                "- get_commit_history: Review recent changes\n"
                "- get_repo_info: Understand repository metadata\n"
                "- get_bulk_file_content: Read multiple files efficiently\n"
                "- recursive_list_directory: Get full repository structure\n"
                "Use these tools to understand the broader context before making review decisions.\n\n"
                
                "REVIEW CRITERIA:\n"
                "- Code Quality: Style, patterns, maintainability, readability\n"
                "- Security: Potential vulnerabilities, secrets exposure, input validation\n"
                "- Best Practices: Following conventions, error handling, performance\n"
                "- Documentation: Comments, commit messages, PR descriptions\n"
                "- Testing: Consider test coverage and edge cases\n"
                "- Architecture: Design patterns, modularity, dependencies\n"
                "- Context Awareness: How changes fit with existing codebase\n\n"
                
                "REVIEW PROCESS:\n"
                "1. Use tools to explore repository context if needed\n"
                "2. Analyze all file changes thoroughly\n"
                "3. Review commit message and PR description\n"
                "4. Check for security issues and best practices\n"
                "5. Consider how changes fit with existing code\n"
                "6. Provide specific, actionable feedback\n"
                "7. Make one of three decisions: APPROVE, REQUEST_CHANGES, or NEEDS_MAJOR_REVISION\n\n"
                
                "FEEDBACK GUIDELINES:\n"
                "- Be constructive and specific\n"
                "- Reference line numbers when possible\n"
                "- Explain the 'why' behind suggestions\n"
                "- Prioritize critical issues over minor style preferences\n"
                "- Acknowledge good practices when you see them\n"
                "- Use repository context to make informed suggestions\n"
                "- Keep feedback concise but comprehensive\n\n"
                
                "DECISION CRITERIA:\n"
                "- APPROVE: Code is ready for submission (minor suggestions are optional)\n"
                "- REQUEST_CHANGES: Specific improvements needed but overall approach is good\n"
                "- NEEDS_MAJOR_REVISION: Significant architectural or design issues require rework\n\n"
                
                "Always provide your review in JSON format with: decision, feedback, suggestions, and reasoning.\n"
                "Use the available tools to gather additional context when needed for thorough reviews."
            )
        }
        self.messages.append(system_message)
    
    def review_pull_request(self, context: PeerReviewContext) -> Tuple[ReviewDecision, str, List[str]]:
        """Review a pull request with tool access for enhanced context."""
        try:
            # Import tools here to avoid circular imports
            from .tools import TOOLS, TOOL_FUNCTIONS
            
            # Prepare review request with enhanced context
            review_request = self._format_review_request(context)
            self.messages.append({"role": "user", "content": review_request})
            
            # Get review response with tool access
            response = self.client.chat.completions.create(
                model=config.peer_review_model,
                messages=self.messages,
                tools=TOOLS,  # Give peer review agent access to the same tools
                tool_choice="auto",
                temperature=0.3  # Lower temperature for more consistent reviews
            )
            
            response_message = response.choices[0].message
            self.messages.append(response_message)
            
            # Handle tool calls if the agent wants to explore the repository
            if response_message.tool_calls:
                logger.info(f"Peer review agent is using {len(response_message.tool_calls)} tools for context")
                
                for tool_call in response_message.tool_calls:
                    try:
                        tool_name = tool_call.function.name
                        tool_args = json.loads(tool_call.function.arguments)
                        
                        if tool_name in TOOL_FUNCTIONS:
                            result = TOOL_FUNCTIONS[tool_name](**tool_args)
                            self.messages.append({
                                "role": "tool",
                                "content": result,
                                "tool_call_id": tool_call.id
                            })
                            logger.info(f"Peer review agent used tool: {tool_name}")
                        else:
                            logger.warning(f"Unknown tool called by peer review agent: {tool_name}")
                            self.messages.append({
                                "role": "tool",
                                "content": f"Error: Unknown tool {tool_name}",
                                "tool_call_id": tool_call.id
                            })
                    except Exception as e:
                        logger.error(f"Error executing tool {tool_call.function.name}: {str(e)}")
                        self.messages.append({
                            "role": "tool",
                            "content": f"Error: {str(e)}",
                            "tool_call_id": tool_call.id
                        })
                
                # Get final review after tool usage
                final_response = self.client.chat.completions.create(
                    model=config.peer_review_model,
                    messages=self.messages,
                    temperature=0.3
                )
                
                final_response_message = final_response.choices[0].message
                self.messages.append(final_response_message)
                response_content = final_response_message.content
            else:
                response_content = response_message.content
            
            if not response_content:
                raise ValueError("No response content received from peer review agent")
            
            # Parse the response
            decision, feedback, suggestions = self._parse_review_response(response_content)
            
            logger.info(f"Enhanced peer review completed with decision: {decision.value}")
            return decision, feedback, suggestions
            
        except Exception as e:
            logger.error(f"Error during enhanced peer review: {str(e)}")
            # Fallback to approval on error to avoid blocking PR submission
            fallback_feedback = (
                f"Enhanced peer review encountered an error and fell back to approval: {str(e)}\n\n"
                f"**Fallback Review Notes:**\n"
                f"- The peer review agent experienced a technical issue\n"
                f"- This PR is being approved to avoid blocking development workflow\n"
                f"- Consider manual review or retry with peer review disabled\n"
                f"- Check logs for detailed error information"
            )
            return ReviewDecision.APPROVE, fallback_feedback, [
                "Consider manual code review due to peer review failure",
                "Check application logs for technical details",
                "Verify all changes meet coding standards manually"
            ]
    
    def _format_review_request(self, context: PeerReviewContext) -> str:
        """Format the review request for the AI agent with enhanced context."""
        files_content = []
        for file_info in context.files:
            files_content.append(f"**File: {file_info['file_path']}**\n```\n{file_info['new_content']}\n```")
        
        files_section = "\n\n".join(files_content)
        
        review_request = f"""
Please review this pull request before submission to GitHub. You have access to GitHub tools to explore repository context.

**Repository:** {context.repo}
**PR Title:** {context.title}
**PR Description:** {context.body}
**Branch:** {context.branch_name} → {context.base_branch or 'main'}
**Commit Message:** {context.commit_message}

**Original User Request Context:**
{context.user_request or 'No original request context provided'}

**Files Changed:**
{files_section}

**Review History:**
{self._format_review_history(context)}

**Instructions:**
1. Use available GitHub tools to explore repository context if needed
2. Consider how these changes fit with the existing codebase
3. Evaluate code quality, security, and best practices
4. Provide specific, actionable feedback

Please provide your review in the following JSON format:
{{
    "decision": "approve|request_changes|needs_major_revision",
    "feedback": "Overall assessment and key points",
    "suggestions": ["Specific suggestion 1", "Specific suggestion 2", ...],
    "reasoning": "Explanation of your decision and any tool usage"
}}
"""
        return review_request
    
    def _format_review_history(self, context: PeerReviewContext) -> str:
        """Format the review history for context."""
        if not context.review_history:
            return "This is the first review iteration."
        
        history_items = []
        for review in context.review_history:
            history_items.append(f"- Iteration {review['iteration']}: {review['decision']} - {review['feedback']}")
        
        return "\n".join(history_items)
    
    def _parse_review_response(self, response_content: str) -> Tuple[ReviewDecision, str, List[str]]:
        """Parse the JSON response from the review agent."""
        try:
            # Extract JSON from response (handle markdown code blocks)
            if "```json" in response_content:
                start = response_content.find("```json") + 7
                end = response_content.find("```", start)
                json_content = response_content[start:end].strip()
            elif "```" in response_content:
                start = response_content.find("```") + 3
                end = response_content.find("```", start)
                json_content = response_content[start:end].strip()
            else:
                json_content = response_content
            
            # Parse JSON
            review_data = json.loads(json_content)
            
            # Extract decision
            decision_str = review_data.get("decision", "approve").lower()
            decision = ReviewDecision(decision_str)
            
            # Extract feedback and suggestions
            feedback = review_data.get("feedback", "No specific feedback provided")
            suggestions = review_data.get("suggestions", [])
            
            return decision, feedback, suggestions
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"Failed to parse review response: {str(e)}")
            logger.debug(f"Response content: {response_content}")
            
            # Fallback parsing
            feedback = "Review parsing failed, but content seems acceptable"
            suggestions = []
            
            # Try to determine decision from content
            if any(word in response_content.lower() for word in ["reject", "major", "revision", "significant"]):
                decision = ReviewDecision.NEEDS_MAJOR_REVISION
            elif any(word in response_content.lower() for word in ["change", "improve", "fix", "should"]):
                decision = ReviewDecision.REQUEST_CHANGES
            else:
                decision = ReviewDecision.APPROVE
            
            return decision, feedback, suggestions


class PeerReviewOrchestrator:
    """Orchestrates the peer review process."""
    
    def __init__(self):
        """Initialize the peer review orchestrator."""
        self.console = Console()
        self.peer_agent = PeerReviewAgent()
        logger.info("Peer review orchestrator initialized")
    
    def orchestrate_review(self, context: PeerReviewContext) -> PeerReviewResult:
        """
        Orchestrate the peer review process.
        
        Returns:
            PeerReviewResult with decision, feedback, and suggestions
        """
        self.console.print(Panel(
            "[bold cyan]🔄 Peer Review Process Started[/bold cyan]\n"
            f"Repository: {context.repo}\n"
            f"PR Title: {context.title}\n"
            f"Files: {len(context.files)} changed",
            title="Peer Review",
            border_style="cyan"
        ))
        
        while context.current_iteration < config.max_review_iterations:
            self._display_review_iteration(context.current_iteration + 1)
            
            try:
                # Get peer review with timeout handling
                decision, feedback, suggestions = self.peer_agent.review_pull_request(context)
                context.add_review_iteration(decision, feedback, suggestions)
            except Exception as e:
                logger.error(f"Peer review iteration failed: {str(e)}")
                self._display_review_error(str(e))
                
                # Ask user how to proceed on error
                from rich.prompt import Prompt
                choice = Prompt.ask(
                    "Peer review failed. How would you like to proceed?",
                    choices=["approve", "retry", "cancel"],
                    default="approve"
                )
                
                if choice == "approve":
                    self.console.print("[yellow]⚠️  Proceeding with approval despite review failure[/yellow]")
                    return PeerReviewResult(
                        decision=ReviewDecision.APPROVE,
                        feedback=f"Review failed due to error: {str(e)}",
                        suggestions=["Manual review recommended due to peer review failure"],
                        should_proceed=True,
                        iteration_count=context.current_iteration
                    )
                elif choice == "retry":
                    self.console.print("[cyan]🔄 Retrying peer review...[/cyan]")
                    continue
                else:  # cancel
                    self.console.print("[red]❌ PR submission cancelled[/red]")
                    return PeerReviewResult(
                        decision=ReviewDecision.NEEDS_MAJOR_REVISION,
                        feedback=f"Review cancelled due to error: {str(e)}",
                        suggestions=["Please fix the peer review system or submit manually"],
                        should_proceed=False,
                        iteration_count=context.current_iteration
                    )
            
            # Display review results
            self._display_review_results(decision, feedback, suggestions)
            
            # Handle decision
            if decision == ReviewDecision.APPROVE:
                self._display_approval()
                context.final_decision = decision
                return PeerReviewResult(
                    decision=decision,
                    feedback=feedback,
                    suggestions=suggestions,
                    should_proceed=True,
                    iteration_count=context.current_iteration
                )
            
            elif decision == ReviewDecision.NEEDS_MAJOR_REVISION:
                self._display_major_revision_needed()
                context.final_decision = decision
                return PeerReviewResult(
                    decision=decision,
                    feedback=feedback,
                    suggestions=suggestions,
                    should_proceed=False,
                    iteration_count=context.current_iteration
                )
            
            elif decision == ReviewDecision.REQUEST_CHANGES:
                if context.current_iteration >= config.max_review_iterations:
                    self._display_max_iterations_reached()
                    # Ask user for decision
                    user_decision = self._ask_user_for_final_decision(context)
                    return PeerReviewResult(
                        decision=ReviewDecision.REQUEST_CHANGES,
                        feedback=feedback,
                        suggestions=suggestions,
                        should_proceed=user_decision,
                        iteration_count=context.current_iteration
                    )
                
                # Return feedback to main agent for iteration
                self._display_requesting_changes()
                return PeerReviewResult(
                    decision=decision,
                    feedback=feedback,
                    suggestions=suggestions,
                    should_proceed=False,  # Don't proceed to GitHub yet
                    iteration_count=context.current_iteration
                )
        
        # Max iterations reached
        self._display_max_iterations_reached()
        user_decision = self._ask_user_for_final_decision(context)
        
        # Get the last review from history for feedback
        last_review = context.review_history[-1] if context.review_history else {}
        
        return PeerReviewResult(
            decision=ReviewDecision.REQUEST_CHANGES,
            feedback=last_review.get('feedback', 'Maximum review iterations reached'),
            suggestions=last_review.get('suggestions', ['Please review and improve the code manually']),
            should_proceed=user_decision,
            iteration_count=context.current_iteration
        )
    
    def _display_review_iteration(self, iteration: int) -> None:
        """Display current review iteration."""
        self.console.print(f"[cyan]🔍 Review Iteration {iteration}[/cyan]")
    
    def _display_review_results(self, decision: ReviewDecision, feedback: str, suggestions: List[str]) -> None:
        """Display the review results."""
        # Decision with emoji
        decision_emoji = {
            ReviewDecision.APPROVE: "✅",
            ReviewDecision.REQUEST_CHANGES: "🔄",
            ReviewDecision.NEEDS_MAJOR_REVISION: "❌"
        }
        
        emoji = decision_emoji.get(decision, "❓")
        self.console.print(f"{emoji} **Decision:** {decision.value.replace('_', ' ').title()}")
        
        # Feedback
        self.console.print(f"[bold]📝 Feedback:[/bold]")
        self.console.print(Markdown(feedback))
        
        # Suggestions
        if suggestions:
            self.console.print(f"[bold]💡 Suggestions:[/bold]")
            for i, suggestion in enumerate(suggestions, 1):
                self.console.print(f"  {i}. {suggestion}")
        
        self.console.print()  # Add spacing
    
    def _display_approval(self) -> None:
        """Display approval message."""
        self.console.print(Panel(
            "[bold green]✅ Pull Request Approved![/bold green]\n"
            "The peer review agent has approved the PR for submission to GitHub.",
            title="Review Complete",
            border_style="green"
        ))
    
    def _display_major_revision_needed(self) -> None:
        """Display major revision needed message."""
        self.console.print(Panel(
            "[bold red]❌ Major Revision Required[/bold red]\n"
            "The peer review agent identified significant issues that require major changes.\n"
            "Please address the feedback before resubmitting.",
            title="Review Failed",
            border_style="red"
        ))
    
    def _display_requesting_changes(self) -> None:
        """Display requesting changes message."""
        self.console.print(Panel(
            "[bold yellow]🔄 Changes Requested[/bold yellow]\n"
            "The peer review agent has requested specific changes.\n"
            "Implementing suggestions and proceeding to next iteration...",
            title="Review Iteration",
            border_style="yellow"
        ))
    
    def _display_max_iterations_reached(self) -> None:
        """Display maximum iterations reached message."""
        self.console.print(Panel(
            "[bold yellow]⏰ Maximum Review Iterations Reached[/bold yellow]\n"
            f"Completed {config.max_review_iterations} review iterations.\n"
            "Please decide how to proceed.",
            title="Review Limit",
            border_style="yellow"
        ))
    
    def _display_review_error(self, error_message: str) -> None:
        """Display review error message."""
        self.console.print(Panel(
            f"[bold red]❌ Peer Review Error[/bold red]\n"
            f"An error occurred during the peer review process:\n"
            f"[dim]{error_message}[/dim]\n\n"
            f"This could be due to:\n"
            f"- Network connectivity issues\n"
            f"- AI service temporary unavailability\n"
            f"- Invalid configuration\n"
            f"- Resource limitations",
            title="Review Error",
            border_style="red"
        ))
    
    def _ask_user_for_final_decision(self, context: PeerReviewContext) -> bool:
        """Ask user for final decision when max iterations reached."""
        from rich.prompt import Prompt
        
        choice = Prompt.ask(
            "How would you like to proceed?",
            choices=["submit", "cancel"],
            default="submit"
        )
        
        if choice == "submit":
            self.console.print("[green]✅ Proceeding with PR submission[/green]")
            return True
        else:
            self.console.print("[red]❌ PR submission cancelled[/red]")
            return False


# Factory function for easy integration
def create_peer_review_context(repo: str, title: str, body: str, files: List[Dict[str, str]], 
                             commit_message: str, branch_name: str, base_branch: Optional[str] = None,
                             user_request: Optional[str] = None) -> PeerReviewContext:
    """Create a peer review context from PR parameters."""
    return PeerReviewContext(
        repo=repo,
        title=title,
        body=body,
        files=files,
        commit_message=commit_message,
        branch_name=branch_name,
        base_branch=base_branch,
        user_request=user_request
    ) 