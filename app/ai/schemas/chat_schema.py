from __future__ import annotations

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """A single message in conversation history."""

    role: str = Field(..., pattern="^(user|assistant)$", description="Message role")
    content: str = Field(..., min_length=1, description="Message content")


class ChatRequest(BaseModel):
    """Incoming chat request with optional conversation history."""

    message: str = Field(..., min_length=1, max_length=10_000, description="User message")
    history: list[ChatMessage] = Field(
        default_factory=list,
        max_length=50,
        description="Previous conversation turns",
    )
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, ge=1, le=8192)
    use_rag: bool = Field(default=False, description="Enable RAG retrieval from vector store")
    top_k: int | None = Field(default=None, ge=1, le=20, description="Number of chunks to retrieve")


class ChatResponse(BaseModel):
    """Non-streaming chat response (for future use)."""

    content: str
    model: str
    finish_reason: str | None = None
