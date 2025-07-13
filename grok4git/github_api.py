"""
GitHub API helper functions and utilities for Grok4Git.

This module provides a centralized interface for interacting with the GitHub API,
including session management and common utility functions.
"""

import logging
import time
import requests
from typing import Optional, Dict, Any
from .config import config

logger = logging.getLogger(__name__)


class GitHubAPI:
    """GitHub API wrapper with session management and utility functions."""

    def __init__(self):
        """Initialize GitHub API client with session."""
        self.session = requests.Session()
        self.session.headers.update(config.get_github_headers())
        self.session.timeout = config.api_timeout
        logger.info("GitHub API client initialized")

    def get_default_branch(self, repo: str) -> str:
        """
        Get the default branch for a repository.

        Args:
            repo: Repository name in format 'owner/repo'

        Returns:
            Default branch name

        Raises:
            ValueError: If repository is not found or accessible
        """
        url = f"{config.github_api_base_url}/repos/{repo}"

        try:
            response = self.session.get(url)
            response.raise_for_status()

            default_branch = response.json().get("default_branch", "main")
            logger.debug(f"Default branch for {repo}: {default_branch}")
            return default_branch

        except requests.exceptions.RequestException as e:
            error_msg = f"Error fetching default branch for {repo}: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg)

    def make_request(
        self,
        method: str,
        url: str,
        data: Optional[Dict[Any, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        max_retries: int = 3,
    ) -> requests.Response:
        """
        Make a generic HTTP request to GitHub API with retry logic.

        Args:
            method: HTTP method (GET, POST, PATCH, DELETE, etc.)
            url: Full URL for the request
            data: JSON data for POST/PATCH requests
            params: Query parameters
            max_retries: Maximum number of retry attempts for rate limits

        Returns:
            Response object

        Raises:
            requests.exceptions.RequestException: For HTTP errors
        """
        for attempt in range(max_retries + 1):
            try:
                response = self.session.request(method=method, url=url, json=data, params=params)

                # Log rate limit information
                if "x-ratelimit-remaining" in response.headers:
                    remaining = response.headers["x-ratelimit-remaining"]
                    logger.debug(f"GitHub API rate limit remaining: {remaining}")

                    # Warn if rate limit is getting low
                    if int(remaining) < 100:
                        logger.warning(
                            f"GitHub API rate limit running low: {remaining} requests remaining"
                        )

                response.raise_for_status()
                return response

            except requests.exceptions.HTTPError as e:
                if response.status_code == 403 and "rate limit" in response.text.lower():
                    if attempt < max_retries:
                        # Calculate retry delay based on rate limit reset time
                        reset_time = int(response.headers.get("x-ratelimit-reset", 0))
                        current_time = int(time.time())
                        delay = max(1, reset_time - current_time)

                        logger.warning(
                            f"Rate limit exceeded. Retrying in {delay} seconds... (attempt {attempt + 1}/{max_retries})"
                        )
                        time.sleep(delay)
                        continue
                    else:
                        logger.error("Rate limit exceeded and max retries reached")
                        raise
                else:
                    logger.error(f"GitHub API request failed: {method} {url} - {str(e)}")
                    raise
            except requests.exceptions.RequestException as e:
                logger.error(f"GitHub API request failed: {method} {url} - {str(e)}")
                raise

    def get_paginated_results(
        self, url: str, params: Optional[Dict[str, Any]] = None, max_pages: int = 100
    ) -> list:
        """
        Get all results from a paginated GitHub API endpoint.

        Args:
            url: Base URL for the API endpoint
            params: Query parameters
            max_pages: Maximum number of pages to fetch

        Returns:
            List of all items from all pages
        """
        all_items = []
        page = 1
        per_page = 100

        if params is None:
            params = {}

        params["per_page"] = per_page

        while page <= max_pages:
            params["page"] = page

            try:
                response = self.make_request("GET", url, params=params)
                items = response.json()

                # Handle different response formats
                if isinstance(items, dict) and "items" in items:
                    # Search API format
                    page_items = items["items"]
                    total_count = items.get("total_count", 0)
                else:
                    # Regular API format
                    page_items = items
                    total_count = None

                if not page_items:
                    break

                all_items.extend(page_items)

                # Check if we've reached the end
                if len(page_items) < per_page:
                    break

                # For search API, check if we've got all results
                if total_count is not None and len(all_items) >= total_count:
                    break

                page += 1

            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching page {page}: {str(e)}")
                break

        logger.debug(f"Retrieved {len(all_items)} items from {page-1} pages")
        return all_items

    def get_file_content_raw(self, repo: str, path: str, branch: str) -> str:
        """
        Get file content from GitHub's raw content URL.

        Args:
            repo: Repository name in format 'owner/repo'
            path: File path
            branch: Branch name

        Returns:
            File content as string

        Raises:
            ValueError: If file cannot be retrieved or decoded
        """
        raw_url = f"https://raw.githubusercontent.com/{repo}/{branch}/{path}"

        try:
            response = self.session.get(raw_url)
            response.raise_for_status()

            # Try to decode as UTF-8
            return response.text

        except requests.exceptions.RequestException as e:
            error_msg = f"Error fetching raw file content: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        except UnicodeDecodeError as e:
            error_msg = f"Error decoding file content: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg)

    def close(self):
        """Close the session."""
        self.session.close()
        logger.info("GitHub API session closed")


# Global GitHub API instance
github_api = GitHubAPI()
