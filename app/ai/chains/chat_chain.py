from __future__ import annotations

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import Runnable
from langchain_google_genai import ChatGoogleGenerativeAI

from app.core.config import settings


def build_chat_prompt() -> ChatPromptTemplate:
    """Build the chat prompt template with system message and history placeholder.

    Separated from the chain factory so prompts can be swapped or extended
    independently (e.g. inject RAG context later).
    """
    return ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a helpful AI assistant. Respond clearly and concisely.",
            ),
            MessagesPlaceholder("history", optional=True),
            ("human", "{message}"),
        ]
    )


def build_chat_model(
    *,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> ChatGoogleGenerativeAI:
    """Instantiate the Gemini chat model with project-level defaults.

    Per-request overrides (temperature, max_tokens) take precedence over
    the global settings when supplied.
    """
    return ChatGoogleGenerativeAI(
        model=settings.gemini_chat_model,
        google_api_key=settings.gemini_api_key,
        temperature=temperature if temperature is not None else settings.gemini_temperature,
        max_output_tokens=max_tokens if max_tokens is not None else settings.gemini_max_tokens,
    )


def create_chat_chain(
    *,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> Runnable:
    """LCEL chain: prompt | model | parser.

    This is the core composable unit. Every downstream layer (service,
    mediator) consumes this chain via .astream() or .ainvoke().

    Returns a Runnable that accepts {"message": str, "history": list}
    and yields string chunks.
    """
    prompt = build_chat_prompt()
    model = build_chat_model(temperature=temperature, max_tokens=max_tokens)
    parser = StrOutputParser()

    return prompt | model | parser
