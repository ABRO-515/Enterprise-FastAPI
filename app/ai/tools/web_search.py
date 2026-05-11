from __future__ import annotations

import logging
from typing import Any

import httpx
from pydantic import BaseModel, Field

from app.ai.tools.base import BaseTool
from app.core.config import settings

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
    """Web search tool backed by Firecrawl."""

    name = "web_search"
    description = (
        "Search the web for current information. Use when the user asks about "
        "recent events, real-time data, or topics not in your training data. "
        "Returns a list of relevant search results with titles, snippets, and URLs."
    )
    args_schema = WebSearchInput

    async def _execute(self, **kwargs: Any) -> str:
        """Execute web search using Firecrawl."""
        query: str = kwargs["query"]
        num_results: int = kwargs.get("num_results", 3)

        if not settings.firecrawl_api_key:
            raise RuntimeError("Firecrawl API key is not configured")

        logger.info("Web search via Firecrawl | query=%s | num_results=%d", query, num_results)

        payload = {
            "query": query,
            "limit": num_results,
        }
        headers = {
            "Authorization": f"Bearer {settings.firecrawl_api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=settings.firecrawl_timeout_seconds) as client:
            response = await client.post(
                f"{settings.firecrawl_base_url.rstrip('/')}/v1/search",
                json=payload,
                headers=headers,
            )

        if response.status_code >= 400:
            raise RuntimeError(
                f"Firecrawl search failed with status {response.status_code}: {response.text}"
            )

        data = response.json()
        results = self._extract_results(data)

        if not results:
            return f"No web results found for: {query}"

        formatted_parts: list[str] = []
        for i, result in enumerate(results[:num_results], 1):
            title = self._get_first_string(result, "title", "name") or "Untitled"
            snippet = (
                self._get_first_string(result, "description", "snippet", "markdown", "content")
                or "No snippet available."
            )
            url = self._get_first_string(result, "url", "sourceURL", "source_url") or "No URL"

            formatted_parts.append(
                f"[{i}] {title}\n"
                f"    {snippet}\n"
                f"    URL: {url}"
            )

        return "\n\n".join(formatted_parts)

    @staticmethod
    def _extract_results(data: Any) -> list[dict[str, Any]]:
        if isinstance(data, dict):
            for key in ("data", "results"):
                value = data.get(key)
                if isinstance(value, list):
                    return [item for item in value if isinstance(item, dict)]
            if isinstance(data.get("success"), bool) and isinstance(data.get("data"), dict):
                nested = data["data"].get("results")
                if isinstance(nested, list):
                    return [item for item in nested if isinstance(item, dict)]
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        return []

    @staticmethod
    def _get_first_string(data: dict[str, Any], *keys: str) -> str | None:
        for key in keys:
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None
