from __future__ import annotations

import logging

from app.ai.embeddings.base import EmbeddingProvider
from app.ai.vectorstore.base import SearchResult, VectorStoreProvider
from app.core.config import settings

logger = logging.getLogger(__name__)


class RetrieverService:
    """Async retrieval service: query → embedding → vector search → results.

    This is the single point of access for retrieval in the system.
    Chains and services call this — it handles embedding the query
    and searching the vector store.
    """

    def __init__(
        self,
        embedder: EmbeddingProvider,
        vector_store: VectorStoreProvider,
    ) -> None:
        self._embedder = embedder
        self._vector_store = vector_store

    async def retrieve(
        self,
        query: str,
        *,
        top_k: int | None = None,
        metadata_filter: dict[str, str | int | float | bool] | None = None,
    ) -> list[SearchResult]:
        """Retrieve relevant documents for a query.

        Args:
            query: The user's natural language query.
            top_k: Number of results to return (defaults to settings.top_k).
            metadata_filter: Optional metadata constraints.

        Returns:
            Ranked list of SearchResult objects.
        """
        k = top_k or settings.top_k

        logger.info("Retrieving | query_len=%d | top_k=%d", len(query), k)

        # Embed the query
        query_vector = await self._embedder.embed_text(query)

        # Search vector store
        results = await self._vector_store.search(
            query_vector=query_vector,
            top_k=k,
            metadata_filter=metadata_filter,
        )

        logger.info("Retrieved %d results | top_score=%.4f",
                    len(results),
                    results[0].score if results else 0.0)

        return results

    @staticmethod
    def format_context(results: list[SearchResult]) -> str:
        """Format search results into a context string for prompt injection.

        Each chunk is numbered and includes source metadata for traceability.
        """
        if not results:
            return ""

        context_parts: list[str] = []
        for i, result in enumerate(results, 1):
            source = result.metadata.get("source", "unknown")
            context_parts.append(
                f"[{i}] (source: {source})\n{result.content}"
            )

        return "\n\n---\n\n".join(context_parts)
