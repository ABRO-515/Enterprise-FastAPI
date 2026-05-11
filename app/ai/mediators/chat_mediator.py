from __future__ import annotations

import logging
from typing import AsyncIterator

from app.ai.retrieval.retriever import RetrieverService
from app.ai.schemas.chat_schema import ChatRequest
from app.ai.services.chat_service import ChatService

logger = logging.getLogger(__name__)


class ChatMediator:
    """Orchestration layer between the controller and the chat service.

    Responsibilities:
      - Route between plain chat and RAG-enhanced chat.
      - Retrieve context from Qdrant when use_rag is enabled.
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
    ) -> None:
        self.service = service
        self.retriever = retriever

    async def stream_chat(self, request: ChatRequest) -> AsyncIterator[str]:
        """Orchestrate a streaming chat response.

        If use_rag is True and a retriever is available, retrieves context
        from the vector store and uses the RAG chain. Otherwise falls back
        to the plain chat chain.
        """
        logger.debug(
            "ChatMediator.stream_chat | message_len=%d | use_rag=%s",
            len(request.message),
            request.use_rag,
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
