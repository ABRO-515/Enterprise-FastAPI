from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.ai.controllers.chat_controller import ChatController
from app.ai.embeddings.gemini_embeddings import GeminiEmbeddingProvider
from app.ai.mediators.chat_mediator import ChatMediator
from app.ai.retrieval.retriever import RetrieverService
from app.ai.schemas.chat_schema import ChatRequest
from app.ai.services.chat_service import ChatService
from app.ai.vectorstore.qdrant_store import QdrantVectorStore

router = APIRouter(prefix="/ai", tags=["ai"])


def _get_chat_controller() -> ChatController:
    """Assemble the DI chain for the chat endpoint.

    DI graph:
      Embedder + VectorStore → Retriever → Mediator(Service, Retriever) → Controller

    The retriever is always injected so the mediator can use it
    when use_rag=True without needing a separate endpoint.
    """
    service = ChatService()

    # Build retriever for RAG support
    embedder = GeminiEmbeddingProvider()
    vector_store = QdrantVectorStore()
    retriever = RetrieverService(embedder, vector_store)

    mediator = ChatMediator(service, retriever=retriever)
    return ChatController(mediator)


@router.post("/chat", response_class=StreamingResponse)
async def chat(request: ChatRequest) -> StreamingResponse:
    """Stream a chat response from Gemini via SSE.

    **Request body:**
    - `message` — the user's prompt (required)
    - `history` — list of `{role, content}` turns (optional)
    - `temperature` — override model temperature (optional)
    - `max_tokens` — override max output tokens (optional)
    - `use_rag` — enable RAG retrieval from vector store (default: false)
    - `top_k` — number of chunks to retrieve when use_rag=true (optional)

    **Response:** `text/event-stream` with JSON-encoded token chunks.
    """
    controller = _get_chat_controller()
    return await controller.stream_chat(request)
