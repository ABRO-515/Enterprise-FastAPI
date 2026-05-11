from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ToolCallEvent(BaseModel):
    """SSE event emitted when the model decides to call a tool."""

    type: Literal["tool_call"] = "tool_call"
    name: str = Field(..., description="Name of the tool being called")
    args: dict[str, Any] = Field(default_factory=dict, description="Arguments passed to the tool")
    call_id: str = Field(default="", description="Unique ID for this tool call")


class ToolResultEvent(BaseModel):
    """SSE event emitted after a tool execution completes."""

    type: Literal["tool_result"] = "tool_result"
    name: str = Field(..., description="Name of the tool that was executed")
    result: str = Field(..., description="Tool output string")
    success: bool = Field(default=True, description="Whether the tool succeeded")
    latency_ms: float = Field(default=0.0, description="Execution time in milliseconds")
    call_id: str = Field(default="", description="ID matching the corresponding tool_call")


class ContentEvent(BaseModel):
    """SSE event for streaming text content chunks."""

    type: Literal["content"] = "content"
    chunk: str = Field(..., description="Text chunk from the model response")


class ThinkingEvent(BaseModel):
    """SSE event for model reasoning/thinking status."""

    type: Literal["thinking"] = "thinking"
    message: str = Field(default="Processing...", description="Status message")


class ErrorEvent(BaseModel):
    """SSE event emitted when an error occurs during processing."""

    type: Literal["error"] = "error"
    message: str = Field(..., description="Error description")
    recoverable: bool = Field(default=True, description="Whether the stream can continue")


class DoneEvent(BaseModel):
    """SSE event signaling the end of the stream."""

    type: Literal["done"] = "done"
    total_tool_calls: int = Field(default=0, description="Total tools called in this response")
    total_latency_ms: float = Field(default=0.0, description="Total processing time")


# Type alias for all SSE event types
SSEEvent = (
    ToolCallEvent
    | ToolResultEvent
    | ContentEvent
    | ThinkingEvent
    | ErrorEvent
    | DoneEvent
)
