from __future__ import annotations

import json
import logging
from typing import AsyncIterator

from fastapi.responses import StreamingResponse

from app.ai.mediators.chat_mediator import ChatMediator
from app.ai.schemas.chat_schema import ChatRequest

logger = logging.getLogger(__name__)


class ChatController:
    """HTTP-layer handler that converts mediator output into SSE responses.

    This controller owns the SSE wire format. Everything below it
    (mediator, service, chain) deals only with plain-text chunks.
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

    async def stream_chat(self, request: ChatRequest) -> StreamingResponse:
        """Return an SSE StreamingResponse for the given chat request."""
        chunks = self.mediator.stream_chat(request)

        return StreamingResponse(
            content=self._sse_generator(chunks),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
