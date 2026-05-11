from __future__ import annotations

import logging
from typing import AsyncIterator

from app.ai.retrieval.retriever import RetrieverService
from app.ai.schemas.chat_schema import ChatRequest
from app.ai.schemas.tool_schema import SSEEvent
from app.ai.services.chat_service import ChatService
from app.ai.services.tool_service import ToolService

logger = logging.getLogger(__name__)


class ChatMediator:
    """Orchestration layer between the controller and the chat service.

    Responsibilities:
      - Route between plain chat, RAG-enhanced chat, and tool-calling.
      - Retrieve context from Qdrant when use_rag is enabled.
      - Delegate to ToolService when use_tools is enabled.
      - Format and inject context into the service call.

    Future additions (no restructuring needed):
      - Load/save conversation history from Redis.
      - Enforce token-budget limits.
      - Publish analytics events to RabbitMQ.
    """

    def __init__(
        self,
        service: ChatService,
        retriever: RetrieverService | None = None,
        tool_service: ToolService | None = None,
    ) -> None:
        self.service = service
        self.retriever = retriever
        self.tool_service = tool_service

    async def stream_chat(self, request: ChatRequest) -> AsyncIterator[str]:
        """Orchestrate a streaming chat response (plain text chunks).

        Used for plain chat and RAG paths. Returns str chunks for
        backward-compatible SSE format.
        """
        logger.debug(
            "ChatMediator.stream_chat | message_len=%d | use_rag=%s | use_tools=%s",
            len(request.message),
            request.use_rag,
            request.use_tools,
        )

        if request.use_rag and self.retriever:
            # RAG path: retrieve → format context → stream with context
            results = await self.retriever.retrieve(
                query=request.message,
                top_k=request.top_k,
            )
            context = RetrieverService.format_context(results)

            logger.info(
                "RAG retrieval complete | results=%d | context_len=%d",
                len(results),
                len(context),
            )

            async for chunk in self.service.stream_with_context(
                message=request.message,
                context=context,
                history=request.history,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            ):
                yield chunk
        else:
            # Plain chat path
            async for chunk in self.service.stream(
                message=request.message,
                history=request.history,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            ):
                yield chunk

    async def stream_chat_with_tools(self, request: ChatRequest) -> AsyncIterator[SSEEvent]:
        """Orchestrate a tool-augmented chat response (typed SSE events).

        Used when use_tools=True. Returns typed SSEEvent objects that
        the controller serializes into structured SSE frames.
        """
        if not self.tool_service:
            raise RuntimeError("ToolService not configured but use_tools=True")

        logger.info(
            "ChatMediator.stream_chat_with_tools | message_len=%d",
            len(request.message),
        )

        async for event in self.tool_service.stream_with_tools(
            message=request.message,
            history=request.history,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        ):
            yield event
