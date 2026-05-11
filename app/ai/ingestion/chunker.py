from __future__ import annotations

import logging
from dataclasses import dataclass

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """A text chunk with positional metadata."""

    content: str
    index: int
    metadata: dict[str, str | int | float | bool]


class TextChunker:
    """Semantic-aware text chunking using RecursiveCharacterTextSplitter.

    Uses paragraph/sentence/word boundaries to produce coherent chunks.
    Preserves metadata (source, position) for downstream traceability.
    """

    def __init__(
        self,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ) -> None:
        self._chunk_size = chunk_size or settings.chunk_size
        self._chunk_overlap = chunk_overlap or settings.chunk_overlap

        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=self._chunk_size,
            chunk_overlap=self._chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
            length_function=len,
            is_separator_regex=False,
        )

    def chunk(
        self,
        text: str,
        *,
        source: str = "",
        extra_metadata: dict[str, str | int | float | bool] | None = None,
    ) -> list[Chunk]:
        """Split text into chunks with metadata.

        Args:
            text: The full extracted text to split.
            source: Source identifier (filename, URL, etc.)
            extra_metadata: Additional metadata to attach to every chunk.

        Returns:
            List of Chunk objects with content, index, and metadata.
        """
        raw_chunks = self._splitter.split_text(text)

        base_metadata = {"source": source, **(extra_metadata or {})}

        chunks: list[Chunk] = []
        for i, content in enumerate(raw_chunks):
            chunk_metadata = {
                **base_metadata,
                "chunk_index": i,
                "chunk_total": len(raw_chunks),
            }
            chunks.append(Chunk(content=content, index=i, metadata=chunk_metadata))

        logger.info(
            "Chunked text into %d chunks | source=%s | chunk_size=%d | overlap=%d",
            len(chunks),
            source,
            self._chunk_size,
            self._chunk_overlap,
        )
        return chunks
