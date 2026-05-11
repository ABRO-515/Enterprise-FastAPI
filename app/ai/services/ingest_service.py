from __future__ import annotations

import logging
from pathlib import Path

from app.ai.ingestion.pipeline import IngestionPipeline
from app.ai.schemas.ingest_schema import IngestResponse

logger = logging.getLogger(__name__)


class IngestService:
    """Service layer for document ingestion.

    Delegates to the IngestionPipeline and maps the result
    to a response schema.
    """

    def __init__(self, pipeline: IngestionPipeline) -> None:
        self._pipeline = pipeline

    async def ingest(self, file_path: Path, filename: str) -> IngestResponse:
        """Run ingestion and return structured response."""
        logger.info("IngestService.ingest | file=%s", filename)

        chunks_stored = await self._pipeline.ingest_file(file_path, filename)

        return IngestResponse(
            filename=filename,
            chunks_stored=chunks_stored,
            message=(
                f"Successfully ingested {chunks_stored} chunks"
                if chunks_stored > 0
                else "No content extracted from file"
            ),
        )
