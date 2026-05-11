from __future__ import annotations

from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import Runnable

from app.ai.chains.chat_chain import build_chat_model
from app.ai.prompts.rag_prompt import build_rag_no_context_prompt, build_rag_prompt


def create_rag_chain(
    *,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> Runnable:
    """LCEL RAG chain: rag_prompt | model | StrOutputParser.

    Expects input: {"message": str, "context": str, "history": list}

    The context string is pre-formatted by RetrieverService.format_context()
    and injected into the prompt's {context} placeholder.
    """
    prompt = build_rag_prompt()
    model = build_chat_model(temperature=temperature, max_tokens=max_tokens)
    parser = StrOutputParser()

    return prompt | model | parser


def create_rag_no_context_chain(
    *,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> Runnable:
    """LCEL chain for when retrieval returns no results.

    Expects input: {"message": str, "history": list}
    Uses a graceful "no context" prompt to avoid hallucination.
    """
    prompt = build_rag_no_context_prompt()
    model = build_chat_model(temperature=temperature, max_tokens=max_tokens)
    parser = StrOutputParser()

    return prompt | model | parser
