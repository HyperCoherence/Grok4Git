"""
Search service for GitHub code search operations.
"""

import json
import urllib.parse
from typing import List, Dict, Any

from .base import BaseService


class SearchService(BaseService):
    """Service for GitHub code search operations."""

    def search_code(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for code in the user's GitHub repositories.

        Args:
            query: Search query string

        Returns:
            List of search results
        """
        encoded_query = urllib.parse.quote(f"{query} user:{self.config.github_username}")
        url = f"{self.config.github_api_base_url}/search/code"
        params = {"q": encoded_query}

        all_items = self._get_paginated_results(
            url, params, operation_name=f"search code: {query}", max_pages=10
        )

        return all_items


# Convenience function for backward compatibility
def search_github_repos(query: str) -> str:
    """Search repositories (backward compatibility wrapper)."""
    service = SearchService()
    try:
        results = service.search_code(query)
        return json.dumps(results)
    except ValueError as e:
        return str(e)

