from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.ai.embeddings.base import EmbeddingProvider
from app.ai.ingestion.chunker import TextChunker
from app.ai.ingestion.extractor import TextExtractor
from app.ai.vectorstore.base import VectorDocument, VectorStoreProvider

logger = logging.getLogger(__name__)


class IngestionPipeline:
    """Orchestrates the full ingestion flow: extract → chunk → embed → upsert.

    Each step is delegated to its own module for testability and reuse.
    This class only coordinates the flow.
    """

    def __init__(
        self,
        extractor: TextExtractor,
        chunker: TextChunker,
        embedder: EmbeddingProvider,
        vector_store: VectorStoreProvider,
    ) -> None:
        self._extractor = extractor
        self._chunker = chunker
        self._embedder = embedder
        self._vector_store = vector_store

    async def ingest_file(self, file_path: Path, filename: str) -> int:
        """Run the full ingestion pipeline for a single file.

        Args:
            file_path: Path to the file on disk.
            filename: Original filename (for metadata tracking).

        Returns:
            Number of chunks successfully stored.
        """
        logger.info("Starting ingestion | file=%s", filename)

        # 1. Extract raw text
        raw_text = self._extractor.extract(file_path)
        if not raw_text.strip():
            logger.warning("No text extracted from %s", filename)
            return 0

        # 2. Chunk with metadata
        chunks = self._chunker.chunk(
            raw_text,
            source=filename,
            extra_metadata={
                "ingested_at": datetime.now(timezone.utc).isoformat(),
                "filename": filename,
            },
        )

        if not chunks:
            logger.warning("No chunks produced from %s", filename)
            return 0

        # 3. Embed all chunks
        texts = [c.content for c in chunks]
        vectors = await self._embedder.embed_batch(texts)

        # 4. Build vector documents
        documents = [
            VectorDocument(
                id=str(uuid.uuid4()),
                content=chunk.content,
                vector=vector,
                metadata=chunk.metadata,
            )
            for chunk, vector in zip(chunks, vectors)
        ]

        # 5. Upsert to vector store
        count = await self._vector_store.upsert(documents)

        logger.info(
            "Ingestion complete | file=%s | chunks=%d | stored=%d",
            filename,
            len(chunks),
            count,
        )
        return count
