from __future__ import annotations

import logging
from typing import Any

from langchain_core.tools import StructuredTool

from app.ai.tools.base import BaseTool

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Centralized registry for all available tools.

    Responsibilities:
      - Maintain a name → tool mapping.
      - Expose tools as LangChain StructuredTool objects for model.bind_tools().
      - Support future dynamic tool loading (e.g., from DB or config).

    Usage:
        registry = ToolRegistry()
        registry.register(CalculatorTool())
        registry.register(WebSearchTool())

        lc_tools = registry.get_lc_tools()  # For model.bind_tools(lc_tools)
    """

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a tool. Raises ValueError on duplicate names."""
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")

        self._tools[tool.name] = tool
        logger.info("Registered tool: %s", tool.name)

    def get(self, name: str) -> BaseTool | None:
        """Get a tool by name. Returns None if not found."""
        return self._tools.get(name)

    def get_all(self) -> list[BaseTool]:
        """Return all registered tools."""
        return list(self._tools.values())

    def get_lc_tools(self) -> list[StructuredTool]:
        """Convert registered tools to LangChain StructuredTool objects.

        These are passed to `model.bind_tools()` to enable function calling.
        The LangChain tools are thin schemas — actual execution goes through
        our BaseTool.execute() for observability and error handling.
        """
        lc_tools: list[StructuredTool] = []

        for tool in self._tools.values():
            lc_tool = StructuredTool(
                name=tool.name,
                description=tool.description,
                args_schema=tool.args_schema,
                func=self._make_sync_stub(tool.name),
                coroutine=self._make_async_stub(tool.name),
            )
            lc_tools.append(lc_tool)

        return lc_tools

    def get_tool_schemas(self) -> list[dict[str, Any]]:
        """Return tool metadata for observability/debugging."""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.args_schema.model_json_schema(),
            }
            for tool in self._tools.values()
        ]

    @staticmethod
    def _make_sync_stub(name: str):
        """Create a sync stub (not used — we always go async)."""
        def stub(**kwargs):
            raise NotImplementedError(
                f"Tool {name} must be called via async execute()"
            )
        return stub

    @staticmethod
    def _make_async_stub(name: str):
        """Create an async stub (not used directly — execution goes through ToolService)."""
        async def stub(**kwargs):
            raise NotImplementedError(
                f"Tool {name} execution is handled by ToolService, not LangChain"
            )
        return stub
