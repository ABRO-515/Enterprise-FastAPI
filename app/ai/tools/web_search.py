from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

from app.ai.tools.base import BaseTool

logger = logging.getLogger(__name__)


class WebSearchInput(BaseModel):
    """Input schema for the web search tool."""

    query: str = Field(
        ...,
        description="The search query to look up on the web.",
        min_length=1,
        max_length=500,
    )
    num_results: int = Field(
        default=3,
        description="Number of search results to return.",
        ge=1,
        le=10,
    )


class WebSearchTool(BaseTool):
    """Web search tool with provider abstraction.

    Currently returns mock results. Designed for future integration
    with real search providers (Tavily, SerpAPI, Brave Search, etc.)
    without changing the tool interface or registry wiring.

    Future integration:
      - Add a SearchProvider protocol
      - Inject concrete provider via constructor
      - Keep this tool class as the LangChain adapter layer
    """

    name = "web_search"
    description = (
        "Search the web for current information. Use when the user asks about "
        "recent events, real-time data, or topics not in your training data. "
        "Returns a list of relevant search results with titles and snippets."
    )
    args_schema = WebSearchInput

    async def _execute(self, **kwargs: Any) -> str:
        """Execute web search (mock implementation)."""
        query: str = kwargs["query"]
        num_results: int = kwargs.get("num_results", 3)

        logger.info("Web search (mock) | query=%s | num_results=%d", query, num_results)

        # Mock results — replace with real provider in production
        mock_results = [
            {
                "title": f"Search Result {i} for: {query}",
                "snippet": (
                    f"This is a mock search result #{i}. "
                    f"In production, this would contain real web content "
                    f"relevant to '{query}'."
                ),
                "url": f"https://example.com/result-{i}",
            }
            for i in range(1, num_results + 1)
        ]

        # Format results for LLM consumption
        formatted_parts: list[str] = []
        for i, result in enumerate(mock_results, 1):
            formatted_parts.append(
                f"[{i}] {result['title']}\n"
                f"    {result['snippet']}\n"
                f"    URL: {result['url']}"
            )

        output = "\n\n".join(formatted_parts)

        # Add disclaimer for mock mode
        output += (
            "\n\n⚠️ NOTE: These are mock results. "
            "Real web search integration is pending."
        )

        return output
