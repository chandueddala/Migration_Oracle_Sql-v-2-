"""
Web search helper for finding SQL Server error solutions
"""

import logging
from typing import List, Dict, Optional

# Try to import Tavily SDK
try:
    from tavily import TavilyClient
    TAVILY_AVAILABLE = True
except ImportError:
    print("=" * 70)
    print("WARNING: tavily-python package not installed")
    print("=" * 70)
    print("Web search for error solutions will be DISABLED.")
    print("\nTo enable web search (recommended):")
    print("  pip install tavily-python")
    print("\nGet a free API key at: https://tavily.com/")
    print("=" * 70)
    TavilyClient = None
    TAVILY_AVAILABLE = False

from config import TAVILY_API_KEY, MAX_SEARCH_RESULTS, ENABLE_WEB_SEARCH

logger = logging.getLogger(__name__)


class WebSearchHelper:
    """Helper class for web search functionality"""

    def __init__(self):
        self.enabled = ENABLE_WEB_SEARCH and TAVILY_API_KEY and TAVILY_AVAILABLE
        self.tavily_client = None

        if self.enabled:
            try:
                self.tavily_client = TavilyClient(api_key=TAVILY_API_KEY)
                logger.info("Web search enabled with Tavily API")
            except Exception as e:
                logger.warning(f"Failed to initialize Tavily client: {e}")
                self.enabled = False
        else:
            if not TAVILY_API_KEY:
                logger.info("Web search disabled: TAVILY_API_KEY not set")
            elif not ENABLE_WEB_SEARCH:
                logger.info("Web search disabled in configuration")
            else:
                logger.info("Web search disabled: tavily-python not installed")

    def search_error_solution(self, error_message: str, object_type: str,
                             context: str = "") -> Optional[Dict]:
        """
        Search the web for solutions to SQL Server errors

        Args:
            error_message: The SQL Server error message
            object_type: Type of database object (PROCEDURE, FUNCTION, TRIGGER, TABLE)
            context: Additional context (optional)

        Returns:
            Dict with search results or None if search disabled/failed
        """
        if not self.enabled or not self.tavily_client:
            return None

        try:
            # Build search query focused on SQL Server solutions
            search_query = self._build_search_query(error_message, object_type, context)

            logger.info(f"Searching web for: {search_query}")
            print(f"    [*] Searching web for solutions...")

            # Perform search using Tavily SDK
            response = self.tavily_client.search(
                query=search_query,
                search_depth="advanced",
                max_results=MAX_SEARCH_RESULTS,
                include_answer=True,
                include_raw_content=False
            )

            if not response or 'results' not in response:
                logger.warning("Web search returned no results")
                return None

            # Process and format results
            formatted_results = self._format_search_results(response['results'])

            logger.info(f"Found {len(formatted_results['sources'])} relevant solutions")
            print(f"    [+] Found {len(formatted_results['sources'])} web resources")

            return formatted_results

        except Exception as e:
            logger.error(f"Web search failed: {e}")
            print(f"    [!] Web search failed: {e}")
            return None

    def _build_search_query(self, error_message: str, object_type: str,
                           context: str = "") -> str:
        """
        Build an optimized search query for SQL Server errors

        Args:
            error_message: The error message
            object_type: Type of object
            context: Additional context

        Returns:
            Optimized search query string
        """
        # Extract key error information
        error_snippet = error_message[:200]  # First 200 chars

        # Remove common noise words
        noise_words = ["at line", "near", "column", "row", "position"]
        clean_error = error_snippet
        for word in noise_words:
            clean_error = clean_error.replace(word, "")

        # Build query with SQL Server focus
        query_parts = [
            "SQL Server 2022",
            object_type.lower() if object_type else "",
            "error solution fix",
            f'"{clean_error[:100]}"',  # Quote the error for exact match
        ]

        if context:
            query_parts.append(context[:50])

        # Add relevant technical terms
        if "syntax" in error_message.lower():
            query_parts.append("T-SQL syntax")
        elif "function" in error_message.lower():
            query_parts.append("UDF user-defined")
        elif "procedure" in error_message.lower():
            query_parts.append("stored procedure")
        elif "trigger" in error_message.lower():
            query_parts.append("INSERTED DELETED")

        query = " ".join(filter(None, query_parts))
        return query[:500]  # Limit query length

    def _format_search_results(self, raw_results: List) -> Dict:
        """
        Format raw search results into structured output

        Args:
            raw_results: Raw results from Tavily API

        Returns:
            Formatted results dictionary
        """
        formatted = {
            "sources": [],
            "summary": "",
            "total_results": len(raw_results) if isinstance(raw_results, list) else 0
        }

        if not raw_results:
            return formatted

        # Handle list of results
        if isinstance(raw_results, list):
            for idx, result in enumerate(raw_results[:MAX_SEARCH_RESULTS], 1):
                if isinstance(result, dict):
                    source = {
                        "rank": idx,
                        "title": result.get("title", "Untitled"),
                        "url": result.get("url", ""),
                        "content": result.get("content", "")[:500],  # Limit content length
                        "score": result.get("score", 0.0)
                    }
                    formatted["sources"].append(source)

        # Extract summary if available
        if formatted["sources"]:
            # Create a brief summary from top results
            top_contents = [s["content"] for s in formatted["sources"][:3]]
            formatted["summary"] = " | ".join(top_contents)[:1000]

        return formatted

    def format_for_llm(self, search_results: Optional[Dict]) -> str:
        """
        Format search results for inclusion in LLM prompt

        Args:
            search_results: Formatted search results

        Returns:
            Formatted string for LLM prompt
        """
        if not search_results or not search_results.get("sources"):
            return ""

        output_parts = [
            "\n" + "="*70,
            "WEB SEARCH RESULTS - TOP SOLUTIONS FROM INTERNET",
            "="*70
        ]

        for source in search_results["sources"]:
            output_parts.append(f"""
Source {source['rank']}: {source['title']}
URL: {source['url']}
Relevance Score: {source['score']:.2f}

Solution/Context:
{source['content']}
""")

        output_parts.append("="*70)
        output_parts.append("""
INSTRUCTIONS FOR USING WEB SEARCH RESULTS:
1. Review the solutions above from SQL Server experts and community
2. Identify patterns and common fixes for this error
3. Apply the most relevant solution to your specific case
4. Ensure the fix is compatible with SQL Server 2022
5. Adapt the solution to match the object type and context
""")
        output_parts.append("="*70 + "\n")

        return "\n".join(output_parts)


# Global instance
_web_search_helper = None


def get_web_search_helper() -> WebSearchHelper:
    """Get or create the global WebSearchHelper instance"""
    global _web_search_helper
    if _web_search_helper is None:
        _web_search_helper = WebSearchHelper()
    return _web_search_helper


def search_for_error_solution(error_message: str, object_type: str,
                              context: str = "") -> Optional[Dict]:
    """
    Convenience function to search for error solutions

    Args:
        error_message: SQL Server error message
        object_type: Type of database object
        context: Additional context

    Returns:
        Formatted search results or None
    """
    helper = get_web_search_helper()
    return helper.search_error_solution(error_message, object_type, context)


def format_search_results_for_llm(search_results: Optional[Dict]) -> str:
    """
    Convenience function to format search results for LLM

    Args:
        search_results: Search results dictionary

    Returns:
        Formatted string for LLM prompt
    """
    helper = get_web_search_helper()
    return helper.format_for_llm(search_results)
