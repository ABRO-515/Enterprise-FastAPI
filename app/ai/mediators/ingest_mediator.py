from __future__ import annotations

import logging
from pathlib import Path

from app.ai.schemas.ingest_schema import IngestResponse
from app.ai.services.ingest_service import IngestService

logger = logging.getLogger(__name__)


class IngestMediator:
    """Orchestration layer for ingestion.

    Currently thin — delegates to IngestService.
    Future responsibilities:
      - Validate file size/type before processing.
      - Deduplicate files (check if already ingested).
      - Publish ingestion events to RabbitMQ.
      - Track ingestion status in PostgreSQL.
    """

    def __init__(self, service: IngestService) -> None:
        self._service = service

    async def ingest_file(self, file_path: Path, filename: str) -> IngestResponse:
        """Orchestrate file ingestion."""
        logger.debug("IngestMediator.ingest_file | file=%s", filename)
        return await self._service.ingest(file_path, filename)
