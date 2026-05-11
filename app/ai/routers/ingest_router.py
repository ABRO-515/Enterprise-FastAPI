from __future__ import annotations

from fastapi import APIRouter, File, UploadFile

from app.ai.controllers.ingest_controller import IngestController
from app.ai.embeddings.gemini_embeddings import GeminiEmbeddingProvider
from app.ai.ingestion.chunker import TextChunker
from app.ai.ingestion.extractor import TextExtractor
from app.ai.ingestion.pipeline import IngestionPipeline
from app.ai.mediators.ingest_mediator import IngestMediator
from app.ai.schemas.ingest_schema import IngestResponse
from app.ai.services.ingest_service import IngestService
from app.ai.vectorstore.qdrant_store import QdrantVectorStore

router = APIRouter(prefix="/ai", tags=["ai-ingestion"])


def _get_ingest_controller() -> IngestController:
    """Assemble the DI chain for the ingest endpoint.

    Extractor → Chunker → Embedder → VectorStore → Pipeline → Service → Mediator → Controller
    """
    extractor = TextExtractor()
    chunker = TextChunker()
    embedder = GeminiEmbeddingProvider()
    vector_store = QdrantVectorStore()
    pipeline = IngestionPipeline(extractor, chunker, embedder, vector_store)
    service = IngestService(pipeline)
    mediator = IngestMediator(service)
    return IngestController(mediator)


@router.post("/ingest", response_model=IngestResponse)
async def ingest_document(
    file: UploadFile = File(..., description="PDF, TXT, or MD file to ingest"),
) -> IngestResponse:
    """Upload and ingest a document into the vector store.

    The file is extracted, chunked, embedded, and stored in Qdrant.

    **Supported formats:** PDF, TXT, MD
    **Max size:** configured via MAX_UPLOAD_MB env var
    """
    controller = _get_ingest_controller()
    return await controller.ingest(file)
