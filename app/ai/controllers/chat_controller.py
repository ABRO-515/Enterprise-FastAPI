from __future__ import annotations

import json
import logging
from typing import AsyncIterator

from fastapi.responses import StreamingResponse

from app.ai.mediators.chat_mediator import ChatMediator
from app.ai.schemas.chat_schema import ChatRequest
from app.ai.schemas.tool_schema import SSEEvent

logger = logging.getLogger(__name__)


class ChatController:
    """HTTP-layer handler that converts mediator output into SSE responses.

    This controller owns the SSE wire format. Everything below it
    (mediator, service, chain) deals only with plain-text chunks or typed events.

    Supports two SSE formats:
      - Plain text (backward compatible): data: {"content": "..."}\n\n
      - Typed events (tool-calling): data: {"type": "tool_call", ...}\n\n
    """

    def __init__(self, mediator: ChatMediator) -> None:
        self.mediator = mediator

    @staticmethod
    async def _sse_generator(chunks: AsyncIterator[str]) -> AsyncIterator[str]:
        """Wrap raw text chunks into SSE `data:` frames.

        Format follows the Server-Sent Events spec:
          data: <json-encoded chunk>\n\n
          ...
          data: [DONE]\n\n
        """
        try:
            async for chunk in chunks:
                payload = json.dumps({"content": chunk})
                yield f"data: {payload}\n\n"
            yield "data: [DONE]\n\n"
        except Exception:
            logger.exception("SSE stream error")
            error_payload = json.dumps({"error": "Stream interrupted"})
            yield f"data: {error_payload}\n\n"
            yield "data: [DONE]\n\n"

    @staticmethod
    async def _typed_sse_generator(events: AsyncIterator[SSEEvent]) -> AsyncIterator[str]:
        """Wrap typed SSE events into SSE `data:` frames.

        Each event is serialized as a JSON object with a `type` discriminator.
        The stream ends with a DoneEvent (type: "done").

        Format:
          data: {"type": "thinking", "message": "..."}\n\n
          data: {"type": "tool_call", "name": "...", "args": {...}}\n\n
          data: {"type": "tool_result", "name": "...", "result": "..."}\n\n
          data: {"type": "content", "chunk": "..."}\n\n
          data: {"type": "done", "total_tool_calls": N}\n\n
        """
        try:
            async for event in events:
                payload = event.model_dump_json()
                yield f"data: {payload}\n\n"
        except Exception:
            logger.exception("Typed SSE stream error")
            error_payload = json.dumps({"type": "error", "message": "Stream interrupted", "recoverable": False})
            yield f"data: {error_payload}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'total_tool_calls': 0, 'total_latency_ms': 0.0})}\n\n"

    async def stream_chat(self, request: ChatRequest) -> StreamingResponse:
        """Return an SSE StreamingResponse for the given chat request.

        Routes to typed event stream when use_tools=True,
        otherwise uses plain text chunk stream.
        """
        if request.use_tools:
            events = self.mediator.stream_chat_with_tools(request)
            content = self._typed_sse_generator(events)
        else:
            chunks = self.mediator.stream_chat(request)
            content = self._sse_generator(chunks)

        return StreamingResponse(
            content=content,
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
