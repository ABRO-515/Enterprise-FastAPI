from __future__ import annotations

import logging
import shutil
from pathlib import Path

from fastapi import UploadFile

from app.ai.mediators.ingest_mediator import IngestMediator
from app.ai.schemas.ingest_schema import IngestResponse
from app.core.config import settings

logger = logging.getLogger(__name__)


class IngestController:
    """HTTP-layer handler for document ingestion.

    Responsibilities:
      - Validate upload constraints (size, type).
      - Persist uploaded file to disk.
      - Delegate to mediator for processing.
      - Clean up temp files on failure.
    """

    ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md"}

    def __init__(self, mediator: IngestMediator) -> None:
        self._mediator = mediator

    async def ingest(self, file: UploadFile) -> IngestResponse:
        """Handle file upload and trigger ingestion pipeline."""
        filename = file.filename or "unknown"
        suffix = Path(filename).suffix.lower()

        # Validate extension
        if suffix not in self.ALLOWED_EXTENSIONS:
            raise ValueError(
                f"Unsupported file type: {suffix}. "
                f"Allowed: {self.ALLOWED_EXTENSIONS}"
            )

        # Ensure upload directory exists
        upload_dir = Path(settings.pdf_upload_dir)
        upload_dir.mkdir(parents=True, exist_ok=True)

        # Save file to disk
        file_path = upload_dir / filename
        try:
            with file_path.open("wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            logger.info("Saved upload to %s", file_path)

            # Delegate to mediator
            return await self._mediator.ingest_file(file_path, filename)

        except Exception:
            # Clean up on failure
            if file_path.exists():
                file_path.unlink()
            raise
        finally:
            await file.close()
