"""
Formatters for chat interface output.
"""

import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def format_tool_result(function_name: str, result: str, args: dict) -> str:
    """
    Extract a concise summary from tool execution results.
    
    Args:
        function_name: Name of the tool function
        result: Result string from tool execution
        args: Arguments passed to the tool
        
    Returns:
        Formatted summary string
    """
    try:
        # Handle different tool types
        if function_name == "list_github_repos":
            # Extract repository count
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
                items = json.loads(result)
                return f"Listed {len(items)} items in {repo}/{path}"
            except:
                return f"Listed directory {repo}/{path}"
        
        elif function_name == "get_commit_history":
            # Extract commit count
            repo = args.get("repo", "repository")
            try:
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
        
        elif function_name == "search_github_repos" or function_name == "search_repositories":
            # Extract search results
            query = args.get("query", "")
            try:
                results = json.loads(result)
                return f"Found {len(results)} results for '{query}'"
            except:
                return f"Searched for '{query}'"
        
        else:
            # Generic fallback
            return "Completed"
            
    except Exception as e:
        logger.debug(f"Error extracting tool summary: {e}")
        return "Completed"


def format_error(error: Exception) -> str:
    """
    Format an error exception for display.
    
    Args:
        error: Exception to format
        
    Returns:
        Formatted error message
    """
    error_type = type(error).__name__
    error_msg = str(error)
    return f"[{error_type}] {error_msg}"


def format_context_status(used: int, total: int) -> str:
    """
    Format context window status for display.
    
    Args:
        used: Number of tokens used
        total: Total context window size
        
    Returns:
        Formatted status string
    """
    usage_percentage = (used / total) * 100 if total > 0 else 0
    remaining_percentage = 100 - usage_percentage
    
    # Choose color and emoji based on usage
    if remaining_percentage > 70:
        color = "green"
        emoji = "🟢"
    elif remaining_percentage > 40:
        color = "yellow"
        emoji = "🟡"
    elif remaining_percentage > 20:
        color = "orange3"
        emoji = "🟠"
    else:
        color = "red"
        emoji = "🔴"
    
    # Format the display with token count for more detail
    if used < 1000:
        token_display = f"{used}"
    else:
        token_display = f"{used/1000:.1f}K"
    
    total_display = f"{total//1000}K"
    
    return f"[{color}]{emoji} {remaining_percentage:.0f}% Context Left[/{color}] [dim]({token_display}/{total_display})[/dim]"

