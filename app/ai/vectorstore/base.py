from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass
class VectorDocument:
    """A document chunk with its vector and metadata.

    This is the exchange format between ingestion, storage, and retrieval.
    Decoupled from any specific vector DB client model.
    """

    id: str
    content: str
    vector: list[float]
    metadata: dict[str, str | int | float | bool] = field(default_factory=dict)


@dataclass
class SearchResult:
    """A single search hit returned by the vector store."""

    id: str
    content: str
    score: float
    metadata: dict[str, str | int | float | bool] = field(default_factory=dict)


@runtime_checkable
class VectorStoreProvider(Protocol):
    """Provider-agnostic vector store interface.

    Hides Qdrant/Pinecone/Weaviate implementation details.
    All methods are async for non-blocking I/O.
    """

    @abstractmethod
    async def upsert(self, documents: list[VectorDocument]) -> int:
        """Insert or update documents. Returns count of upserted docs."""
        ...

    @abstractmethod
    async def search(
        self,
        query_vector: list[float],
        *,
        top_k: int = 5,
        metadata_filter: dict[str, str | int | float | bool] | None = None,
    ) -> list[SearchResult]:
        """Similarity search by vector. Returns ranked results."""
        ...

    @abstractmethod
    async def delete(self, ids: list[str]) -> int:
        """Delete documents by ID. Returns count of deleted docs."""
        ...
