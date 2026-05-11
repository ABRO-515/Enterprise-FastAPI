from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

from app.ai.retrieval.retriever import RetrieverService
from app.ai.tools.base import BaseTool

logger = logging.getLogger(__name__)


class DocumentLookupInput(BaseModel):
    """Input schema for the document lookup tool."""

    query: str = Field(
        ...,
        description=(
            "A natural language query to search against the knowledge base. "
            "This searches through uploaded PDF and text documents."
        ),
        min_length=1,
        max_length=2000,
    )
    top_k: int = Field(
        default=5,
        description="Number of most relevant document chunks to retrieve.",
        ge=1,
        le=20,
    )


class DocumentLookupTool(BaseTool):
    """Document lookup tool that wraps the existing RetrieverService.

    This is the bridge between the tool-calling system and Stage 2's RAG
    retrieval pipeline. It reuses RetrieverService.retrieve() and
    format_context() — no Qdrant logic is duplicated.

    When the model decides it needs information from uploaded documents,
    it calls this tool. This enables "agentic RAG" where the model chooses
    when retrieval is useful, rather than the client forcing use_rag=true.
    """

    name = "document_lookup"
    description = (
        "Search the uploaded knowledge base (PDF and text documents) for relevant "
        "information. Use this when the user asks about content that might be in "
        "their uploaded documents. Returns the most relevant text chunks with "
        "source citations."
    )
    args_schema = DocumentLookupInput

    def __init__(self, retriever: RetrieverService) -> None:
        """Initialize with the shared RetrieverService instance.

        The retriever is injected via DI from the router — same instance
        used by the RAG path. No duplication of embeddings or Qdrant connections.
        """
        self._retriever = retriever

    async def _execute(self, **kwargs: Any) -> str:
        """Search the vector store using the existing retrieval pipeline."""
        query: str = kwargs["query"]
        top_k: int = kwargs.get("top_k", 5)

        logger.info("Document lookup | query_len=%d | top_k=%d", len(query), top_k)

        # Reuse Stage 2 retrieval — embed query → search Qdrant → format
        results = await self._retriever.retrieve(query=query, top_k=top_k)

        if not results:
            return (
                "No relevant documents found in the knowledge base. "
                "The user may need to upload relevant documents first."
            )

        # Use existing format_context() for consistent output
        context = RetrieverService.format_context(results)

        # Add metadata summary
        header = (
            f"Found {len(results)} relevant document chunks "
            f"(top score: {results[0].score:.4f}):\n\n"
        )

        return header + context
