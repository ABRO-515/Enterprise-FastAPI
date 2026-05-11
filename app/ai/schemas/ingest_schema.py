from __future__ import annotations

from pydantic import BaseModel, Field


class IngestResponse(BaseModel):
    """Response after successful document ingestion."""

    filename: str = Field(..., description="Original uploaded filename")
    chunks_stored: int = Field(..., ge=0, description="Number of chunks stored in vector DB")
    message: str = Field(default="Ingestion successful")
