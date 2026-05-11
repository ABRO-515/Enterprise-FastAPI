from __future__ import annotations

import time
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    """Structured result from tool execution.

    Carries the output string, success status, and observability metadata.
    This is the universal exchange format between tool execution and the
    reasoning loop.
    """

    output: str
    success: bool = True
    error: str | None = None
    latency_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseTool(ABC):
    """Abstract base class for all tools.

    Every tool is self-describing: it exposes its name, description,
    and a Pydantic schema for its arguments. The ToolRegistry reads
    these to auto-generate LangChain tool bindings.

    Subclass contract:
      - Define `name`, `description`, `args_schema`
      - Implement `_execute(**kwargs) -> str`
      - Optionally override `_validate_args()` for custom validation

    The `execute()` method wraps `_execute()` with:
      - Latency tracking
      - Error handling
      - Structured logging
    """

    name: str
    description: str
    args_schema: type[BaseModel]

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute the tool with observability wrapping.

        This is the public entry point. Never override this — override
        `_execute()` instead.
        """
        start = time.perf_counter()

        try:
            logger.info("Tool executing | name=%s | args=%s", self.name, kwargs)

            # Validate args through Pydantic schema
            validated = self.args_schema(**kwargs)
            result_str = await self._execute(**validated.model_dump())

            latency = (time.perf_counter() - start) * 1000

            logger.info(
                "Tool success | name=%s | latency_ms=%.1f | output_len=%d",
                self.name, latency, len(result_str),
            )

            return ToolResult(
                output=result_str,
                success=True,
                latency_ms=latency,
                metadata={"tool_name": self.name},
            )

        except Exception as e:
            latency = (time.perf_counter() - start) * 1000

            logger.error(
                "Tool failed | name=%s | latency_ms=%.1f | error=%s",
                self.name, latency, str(e),
            )

            return ToolResult(
                output="",
                success=False,
                error=str(e),
                latency_ms=latency,
                metadata={"tool_name": self.name},
            )

    @abstractmethod
    async def _execute(self, **kwargs: Any) -> str:
        """Core tool logic. Returns a string result for the LLM.

        Implementations should be focused and side-effect-free where possible.
        Raise exceptions on failure — the wrapper handles error formatting.
        """
        ...
