from __future__ import annotations

import logging

from langchain_google_genai import GoogleGenerativeAIEmbeddings

from app.ai.embeddings.base import EmbeddingProvider
from app.core.config import settings

logger = logging.getLogger(__name__)


class GeminiEmbeddingProvider(EmbeddingProvider):
    """Gemini embedding-001 implementation of EmbeddingProvider.

    Uses langchain-google-genai under the hood for consistent API surface
    and automatic retry/rate-limit handling.
    """

    def __init__(self) -> None:
        self._model = GoogleGenerativeAIEmbeddings(
            model=settings.embedding_model,
            google_api_key=settings.gemini_api_key,
        )
        self._dimensions = settings.embedding_dimensions

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def embed_text(self, text: str) -> list[float]:
        """Embed a single text using Gemini API."""
        logger.debug("Embedding single text | len=%d", len(text))
        result = await self._model.aembed_query(text)
        return result

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts using Gemini API.

        langchain-google-genai handles batching internally.
        """
        logger.info("Embedding batch | count=%d", len(texts))
        results = await self._model.aembed_documents(texts)
        return results
