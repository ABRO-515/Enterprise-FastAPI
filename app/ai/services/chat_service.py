from __future__ import annotations

import logging
from typing import AsyncIterator

from langchain_core.messages import AIMessage, HumanMessage

from app.ai.chains.chat_chain import create_chat_chain
from app.ai.chains.rag_chain import create_rag_chain, create_rag_no_context_chain
from app.ai.schemas.chat_schema import ChatMessage

logger = logging.getLogger(__name__)


class ChatService:
    """Thin async wrapper around the LCEL chat chain.

    Responsibilities:
      - Convert schema objects to LangChain message format.
      - Delegate to the chain's astream() for token-level streaming.
      - Provide a non-streaming ainvoke() path for internal callers.

    This is the provider boundary: swapping Gemini for another LLM means
    changing the chain factory — nothing above this layer changes.
    """

    @staticmethod
    def _to_langchain_messages(
        history: list[ChatMessage],
    ) -> list[HumanMessage | AIMessage]:
        """Map Pydantic history objects to LangChain message types."""
        messages: list[HumanMessage | AIMessage] = []
        for msg in history:
            if msg.role == "user":
                messages.append(HumanMessage(content=msg.content))
            else:
                messages.append(AIMessage(content=msg.content))
        return messages

    async def stream(
        self,
        message: str,
        history: list[ChatMessage] | None = None,
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        """Stream response tokens from the LLM.

        Yields plain-text chunks suitable for SSE event data.
        """
        chain = create_chat_chain(temperature=temperature, max_tokens=max_tokens)
        lc_history = self._to_langchain_messages(history or [])

        logger.info("Streaming chat | history_len=%d", len(lc_history))

        async for chunk in chain.astream(
            {"message": message, "history": lc_history}
        ):
            yield chunk

    async def invoke(
        self,
        message: str,
        history: list[ChatMessage] | None = None,
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """Non-streaming invocation (useful for internal pipelines)."""
        chain = create_chat_chain(temperature=temperature, max_tokens=max_tokens)
        lc_history = self._to_langchain_messages(history or [])

        logger.info("Invoking chat | history_len=%d", len(lc_history))

        return await chain.ainvoke(
            {"message": message, "history": lc_history}
        )

    async def stream_with_context(
        self,
        message: str,
        context: str,
        history: list[ChatMessage] | None = None,
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        """Stream response tokens using the RAG chain with injected context.

        If context is empty, uses the no-context chain to gracefully inform
        the user that no relevant documents were found.
        """
        lc_history = self._to_langchain_messages(history or [])

        if context:
            chain = create_rag_chain(temperature=temperature, max_tokens=max_tokens)
            input_data = {"message": message, "context": context, "history": lc_history}
            logger.info("Streaming RAG chat | context_len=%d | history_len=%d",
                        len(context), len(lc_history))
        else:
            chain = create_rag_no_context_chain(temperature=temperature, max_tokens=max_tokens)
            input_data = {"message": message, "history": lc_history}
            logger.info("Streaming RAG (no context) | history_len=%d", len(lc_history))

        async for chunk in chain.astream(input_data):
            yield chunk
