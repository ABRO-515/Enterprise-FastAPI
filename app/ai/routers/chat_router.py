from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.ai.controllers.chat_controller import ChatController
from app.ai.embeddings.gemini_embeddings import GeminiEmbeddingProvider
from app.ai.mediators.chat_mediator import ChatMediator
from app.ai.retrieval.retriever import RetrieverService
from app.ai.schemas.chat_schema import ChatRequest
from app.ai.services.chat_service import ChatService
from app.ai.services.tool_service import ToolService
from app.ai.tools.calculator import CalculatorTool
from app.ai.tools.document_lookup import DocumentLookupTool
from app.ai.tools.registry import ToolRegistry
from app.ai.tools.web_search import WebSearchTool
from app.ai.vectorstore.qdrant_store import QdrantVectorStore

router = APIRouter(prefix="/ai", tags=["ai"])


def _build_tool_registry(retriever: RetrieverService) -> ToolRegistry:
    """Build and populate the tool registry with all available tools."""
    registry = ToolRegistry()
    registry.register(CalculatorTool())
    registry.register(WebSearchTool())
    registry.register(DocumentLookupTool(retriever))
    return registry


def _get_chat_controller() -> ChatController:
    """Assemble the DI chain for the chat endpoint.

    DI graph:
      Embedder + VectorStore → Retriever
      Retriever → ToolRegistry (document_lookup tool)
      ToolRegistry → ToolService
      Service + Retriever + ToolService → Mediator → Controller
    """
    service = ChatService()

    # Build retriever for RAG support
    embedder = GeminiEmbeddingProvider()
    vector_store = QdrantVectorStore()
    retriever = RetrieverService(embedder, vector_store)

    # Build tool system
    registry = _build_tool_registry(retriever)
    tool_service = ToolService(registry)

    mediator = ChatMediator(service, retriever=retriever, tool_service=tool_service)
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
    - `use_tools` — enable tool calling: calculator, web search, document lookup (default: false)
    - `top_k` — number of chunks to retrieve when use_rag=true (optional)

    **Response:** `text/event-stream`
    - Plain/RAG mode: `data: {"content": "..."}\n\n` ... `data: [DONE]\n\n`
    - Tool mode: typed events with `type` field (tool_call, tool_result, content, done)
    """
    controller = _get_chat_controller()
    return await controller.stream_chat(request)
