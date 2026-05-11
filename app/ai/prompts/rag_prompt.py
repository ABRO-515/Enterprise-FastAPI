from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

RAG_SYSTEM_TEMPLATE = """\
You are a knowledgeable AI assistant. Answer the user's question using ONLY \
the provided context. Follow these rules strictly:

1. Base your answer exclusively on the context provided below.
2. If the context does not contain enough information to answer, say: \
"I don't have enough information in my documents to answer that."
3. Do NOT hallucinate or invent information not present in the context.
4. Cite the source numbers [1], [2], etc. when referencing specific information.
5. Be concise and direct in your response.

---
CONTEXT:
{context}
---"""

RAG_NO_CONTEXT_SYSTEM_TEMPLATE = """\
You are a knowledgeable AI assistant. The user asked a question but no relevant \
documents were found in the knowledge base.

Respond honestly that you could not find relevant information in the uploaded documents, \
and suggest the user try rephrasing their question or uploading relevant documents first."""


def build_rag_prompt() -> ChatPromptTemplate:
    """Build the RAG prompt template.

    Prompt structure:
      - System: instructions + retrieved context
      - History: optional conversation turns
      - Human: the user's query

    The context is injected by the mediator/service before chain invocation.
    """
    return ChatPromptTemplate.from_messages(
        [
            ("system", RAG_SYSTEM_TEMPLATE),
            MessagesPlaceholder("history", optional=True),
            ("human", "{message}"),
        ]
    )


def build_rag_no_context_prompt() -> ChatPromptTemplate:
    """Prompt used when retrieval returns no results.

    Gracefully handles empty context without hallucinating.
    """
    return ChatPromptTemplate.from_messages(
        [
            ("system", RAG_NO_CONTEXT_SYSTEM_TEMPLATE),
            MessagesPlaceholder("history", optional=True),
            ("human", "{message}"),
        ]
    )
