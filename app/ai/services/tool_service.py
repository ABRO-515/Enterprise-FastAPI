from __future__ import annotations

import logging
import time
from typing import AsyncIterator

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.ai.chains.tool_chain import create_tool_chain
from app.ai.schemas.chat_schema import ChatMessage
from app.ai.schemas.tool_schema import (
    ContentEvent,
    DoneEvent,
    ErrorEvent,
    SSEEvent,
    ThinkingEvent,
    ToolCallEvent,
    ToolResultEvent,
)
from app.ai.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

MAX_TOOL_ITERATIONS = 5


class ToolService:
    """Multi-turn tool execution loop with typed SSE event streaming.

    Flow:
      1. Send user message to tool-bound model
      2. If model returns tool_calls:
         - Yield ToolCallEvent for each call
         - Execute tools via registry
         - Yield ToolResultEvent for each result
         - Send tool results back to model
         - Repeat from step 2 (up to MAX_TOOL_ITERATIONS)
      3. When model returns text (no tool_calls):
         - Stream ContentEvent chunks
      4. Yield DoneEvent

    The loop is stateful (accumulates messages) but bounded.
    This design maps directly to LangGraph's ToolNode in Stage 4.
    """

    def __init__(self, registry: ToolRegistry) -> None:
        self._registry = registry

    async def stream_with_tools(
        self,
        message: str,
        history: list[ChatMessage] | None = None,
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[SSEEvent]:
        """Execute the multi-turn tool loop, yielding typed SSE events.

        This is the main entry point called by the mediator.
        """
        start_time = time.perf_counter()
        total_tool_calls = 0

        # Build the chain with tools bound
        chain = create_tool_chain(
            self._registry,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        # Build initial message list
        lc_history = self._to_langchain_messages(history or [])
        messages = [*lc_history, HumanMessage(content=message)]

        yield ThinkingEvent(message="Analyzing your request...")

        for iteration in range(MAX_TOOL_ITERATIONS):
            logger.info(
                "Tool loop iteration %d/%d | messages=%d",
                iteration + 1, MAX_TOOL_ITERATIONS, len(messages),
            )

            # Invoke the model (single-shot, not streaming — we need full response to check tool_calls)
            response: AIMessage = await chain.ainvoke({"message": message, "history": messages[:-1]})

            # Check if model wants to call tools
            if response.tool_calls:
                # Process each tool call
                for tool_call in response.tool_calls:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]
                    call_id = tool_call.get("id", "")

                    total_tool_calls += 1

                    # Emit tool_call event
                    yield ToolCallEvent(
                        name=tool_name,
                        args=tool_args,
                        call_id=call_id,
                    )

                    # Execute the tool
                    tool = self._registry.get(tool_name)
                    if tool is None:
                        error_msg = f"Tool not found: {tool_name}"
                        logger.error(error_msg)
                        yield ErrorEvent(message=error_msg, recoverable=True)
                        # Add error as tool message so model can recover
                        messages.append(response)
                        messages.append(
                            ToolMessage(content=error_msg, tool_call_id=call_id)
                        )
                        continue

                    result = await tool.execute(**tool_args)

                    # Emit tool_result event
                    yield ToolResultEvent(
                        name=tool_name,
                        result=result.output if result.success else (result.error or "Unknown error"),
                        success=result.success,
                        latency_ms=result.latency_ms,
                        call_id=call_id,
                    )

                    # Add to conversation for next iteration
                    messages.append(response)
                    messages.append(
                        ToolMessage(
                            content=result.output if result.success else f"Error: {result.error}",
                            tool_call_id=call_id,
                        )
                    )

                # Continue the loop — model will reason over tool results
                yield ThinkingEvent(message="Reasoning over tool results...")
                continue

            else:
                # No tool calls — model is ready to respond with text
                # Stream the final response content
                content = response.content or ""

                if isinstance(content, str) and content:
                    # Stream in chunks for consistent UX
                    for chunk in self._chunk_text(content):
                        yield ContentEvent(chunk=chunk)
                elif isinstance(content, list):
                    # Some models return content as list of parts
                    for part in content:
                        if isinstance(part, str):
                            for chunk in self._chunk_text(part):
                                yield ContentEvent(chunk=chunk)
                        elif isinstance(part, dict) and "text" in part:
                            for chunk in self._chunk_text(part["text"]):
                                yield ContentEvent(chunk=chunk)

                break
        else:
            # Hit max iterations
            yield ErrorEvent(
                message=f"Reached maximum tool iterations ({MAX_TOOL_ITERATIONS}). Stopping.",
                recoverable=False,
            )

        total_latency = (time.perf_counter() - start_time) * 1000

        yield DoneEvent(
            total_tool_calls=total_tool_calls,
            total_latency_ms=total_latency,
        )

        logger.info(
            "Tool service complete | tool_calls=%d | latency_ms=%.1f",
            total_tool_calls, total_latency,
        )

    @staticmethod
    def _to_langchain_messages(
        history: list[ChatMessage],
    ) -> list[HumanMessage | AIMessage]:
        """Map Pydantic history to LangChain messages."""
        messages: list[HumanMessage | AIMessage] = []
        for msg in history:
            if msg.role == "user":
                messages.append(HumanMessage(content=msg.content))
            else:
                messages.append(AIMessage(content=msg.content))
        return messages

    @staticmethod
    def _chunk_text(text: str, chunk_size: int = 20) -> list[str]:
        """Split text into chunks for streaming UX.

        Word-boundary aware chunking to avoid splitting mid-word.
        """
        if len(text) <= chunk_size:
            return [text]

        chunks: list[str] = []
        words = text.split(" ")
        current = ""

        for word in words:
            candidate = f"{current} {word}" if current else word
            if len(candidate) >= chunk_size:
                if current:
                    chunks.append(current + " ")
                current = word
            else:
                current = candidate

        if current:
            chunks.append(current)

        return chunks
