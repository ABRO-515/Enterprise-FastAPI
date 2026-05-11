from __future__ import annotations

from abc import abstractmethod
from typing import Protocol, runtime_checkable


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Provider-agnostic embedding interface.

    Implement this protocol to swap embedding backends (Gemini, OpenAI,
    local sentence-transformers) without touching retrieval or ingestion code.

    All methods are async to support both API-based and batched local inference.
    """

    @abstractmethod
    async def embed_text(self, text: str) -> list[float]:
        """Embed a single text string. Returns a vector of floats."""
        ...

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts in one call for throughput.

        Implementations should handle internal batching/rate-limiting.
        """
        ...

    @property
    @abstractmethod
    def dimensions(self) -> int:
        """Return the dimensionality of the embedding vectors."""
        ...
