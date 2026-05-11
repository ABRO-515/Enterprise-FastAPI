from __future__ import annotations

import logging
import uuid

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from app.ai.vectorstore.base import SearchResult, VectorDocument, VectorStoreProvider
from app.core.config import settings

logger = logging.getLogger(__name__)


class QdrantVectorStore(VectorStoreProvider):
    """Qdrant implementation of VectorStoreProvider.

    Uses the async client for non-blocking operations.
    Automatically ensures the collection exists on first use.
    """

    def __init__(
        self,
        collection_name: str | None = None,
        url: str | None = None,
    ) -> None:
        self._collection = collection_name or settings.qdrant_collection
        self._url = url or settings.qdrant_url
        self._client = AsyncQdrantClient(url=self._url)
        self._collection_ensured = False

    async def _ensure_collection(self) -> None:
        """Create collection if it doesn't exist. Idempotent."""
        if self._collection_ensured:
            return

        collections = await self._client.get_collections()
        existing = [c.name for c in collections.collections]

        if self._collection not in existing:
            await self._client.create_collection(
                collection_name=self._collection,
                vectors_config=VectorParams(
                    size=settings.embedding_dimensions,
                    distance=Distance.COSINE,
                ),
            )
            logger.info("Created Qdrant collection: %s", self._collection)

        self._collection_ensured = True

    async def upsert(self, documents: list[VectorDocument]) -> int:
        """Upsert documents into Qdrant."""
        await self._ensure_collection()

        points = [
            PointStruct(
                id=doc.id or str(uuid.uuid4()),
                vector=doc.vector,
                payload={"content": doc.content, **doc.metadata},
            )
            for doc in documents
        ]

        await self._client.upsert(
            collection_name=self._collection,
            points=points,
        )

        logger.info("Upserted %d documents to %s", len(points), self._collection)
        return len(points)

    async def search(
        self,
        query_vector: list[float],
        *,
        top_k: int = 5,
        metadata_filter: dict[str, str | int | float | bool] | None = None,
    ) -> list[SearchResult]:
        """Similarity search in Qdrant."""
        await self._ensure_collection()

        qdrant_filter = None
        if metadata_filter:
            conditions = [
                FieldCondition(key=k, match=MatchValue(value=v))
                for k, v in metadata_filter.items()
            ]
            qdrant_filter = Filter(must=conditions)

        hits = await self._client.query_points(
            collection_name=self._collection,
            query=query_vector,
            limit=top_k,
            query_filter=qdrant_filter,
            with_payload=True,
        )

        results: list[SearchResult] = []
        for hit in hits.points:
            payload = hit.payload or {}
            content = payload.pop("content", "")
            results.append(
                SearchResult(
                    id=str(hit.id),
                    content=content,
                    score=hit.score,
                    metadata=payload,
                )
            )

        logger.debug("Search returned %d results from %s", len(results), self._collection)
        return results

    async def delete(self, ids: list[str]) -> int:
        """Delete points by ID from Qdrant."""
        await self._ensure_collection()

        await self._client.delete(
            collection_name=self._collection,
            points_selector=ids,
        )

        logger.info("Deleted %d documents from %s", len(ids), self._collection)
        return len(ids)
