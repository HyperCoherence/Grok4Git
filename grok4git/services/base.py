"""
Base service class for GitHub operations.

This module provides a base class that all service classes inherit from,
providing common functionality like error handling, logging, and API requests.
"""

import logging
from typing import Any, Dict, Optional, Callable

from ..config import config
from ..github_api import github_api

logger = logging.getLogger(__name__)


class BaseService:
    """Base class for all GitHub service classes."""
    
    def __init__(self, api_client=None, config_obj=None):
        """
        Initialize base service.
        
        Args:
            api_client: GitHub API client instance (defaults to global github_api)
            config_obj: Configuration object (defaults to global config)
        """
        self.api = api_client or github_api
        self.config = config_obj or config
        self.logger = logging.getLogger(self.__class__.__module__)
    
    def _make_request(
        self,
        method: str,
        url: str,
        operation_name: str,
        **kwargs
    ) -> Any:
        """
        Make a GitHub API request with error handling and logging.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            url: API endpoint URL
            operation_name: Human-readable name for the operation (for logging)
            **kwargs: Additional arguments passed to make_request
            
        Returns:
            Response object from the API
            
        Raises:
            ValueError: If the request fails
        """
        self._log_operation(operation_name, {"method": method, "url": url})
        
        try:
            response = self.api.make_request(method, url, **kwargs)
            self.logger.debug(f"{operation_name} completed successfully")
            return response
        except Exception as e:
            error_context = {
                "method": method,
                "url": url,
                "operation": operation_name
            }
            self._handle_error(e, error_context)
            raise
    
    def _handle_error(self, error: Exception, context: Dict[str, Any]) -> None:
        """
        Handle errors with consistent logging and formatting.
        
        Args:
            error: The exception that occurred
            context: Additional context about the operation
        """
        operation = context.get("operation", "Unknown operation")
        method = context.get("method", "Unknown")
        url = context.get("url", "Unknown")
        
        error_msg = f"Error in {operation}: {str(error)}"
        self.logger.error(f"{error_msg} (Method: {method}, URL: {url})")
        
        # Log additional context if available
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(f"Error context: {context}")
    
    def _log_operation(self, operation: str, details: Dict[str, Any]) -> None:
        """
        Log an operation with details.
        
        Args:
            operation: Name of the operation
            details: Additional details about the operation
        """
        self.logger.info(f"Executing: {operation}")
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(f"Operation details: {details}")
    
    def _get_paginated_results(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        operation_name: Optional[str] = None,
        max_pages: int = 100
    ) -> list:
        """
        Get paginated results from GitHub API.
        
        Args:
            url: API endpoint URL
            params: Query parameters
            operation_name: Human-readable name for the operation (for logging)
            
        Returns:
            List of all results from paginated API calls
        """
        if operation_name:
            self._log_operation(operation_name, {"url": url, "params": params})
        
        try:
            results = self.api.get_paginated_results(url, params, max_pages=max_pages)
            if operation_name:
                self.logger.info(f"{operation_name} completed: {len(results)} items")
            return results
        except Exception as e:
            error_context = {
                "url": url,
                "params": params,
                "operation": operation_name or "paginated request"
            }
            self._handle_error(e, error_context)
            raise
    
    def _format_error_message(
        self,
        operation: str,
        error: Exception,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Format a consistent error message.
        
        Args:
            operation: Name of the operation that failed
            error: The exception that occurred
            additional_context: Optional additional context
            
        Returns:
            Formatted error message string
        """
        error_msg = f"Error {operation}: {str(error)}"
        
        if additional_context:
            context_parts = [f"{k}={v}" for k, v in additional_context.items()]
            error_msg += f" ({', '.join(context_parts)})"
        
        return error_msg
    
    def _validate_repo_name(self, repo: str) -> None:
        """
        Validate repository name format (owner/repo).
        
        Args:
            repo: Repository name to validate
            
        Raises:
            ValueError: If repository name format is invalid
        """
        if not repo or "/" not in repo:
            raise ValueError(
                f"Invalid repository name format: '{repo}'. "
                "Expected format: 'owner/repo' (e.g., 'microsoft/vscode')"
            )
        
        parts = repo.split("/")
        if len(parts) != 2 or not all(parts):
            raise ValueError(
                f"Invalid repository name format: '{repo}'. "
                "Expected format: 'owner/repo'"
            )
    
    def _validate_branch_name(self, branch: str) -> None:
        """
        Validate branch name format.
        
        Args:
            branch: Branch name to validate
            
        Raises:
            ValueError: If branch name is invalid
        """
        if not branch or not branch.strip():
            raise ValueError("Branch name cannot be empty")
        
        # GitHub branch name restrictions
        invalid_chars = ["~", "^", ":", "?", "*", "[", "\\", "..", "@", "{", "}"]
        for char in invalid_chars:
            if char in branch:
                raise ValueError(
                    f"Invalid branch name: '{branch}'. "
                    f"Cannot contain '{char}'"
                )

