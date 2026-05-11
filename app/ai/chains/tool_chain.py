from __future__ import annotations

from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import Runnable

from app.ai.chains.chat_chain import build_chat_model
from app.ai.prompts.tool_prompt import build_tool_prompt
from app.ai.tools.registry import ToolRegistry


def create_tool_chain(
    registry: ToolRegistry,
    *,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> Runnable:
    """LCEL chain: prompt | model_with_tools.

    Unlike the plain chat chain, this does NOT end with StrOutputParser.
    The output is an AIMessage which may contain tool_calls that the
    ToolService needs to inspect and execute.

    The execution loop lives in ToolService, not here — this chain is
    a single-shot invocation that the loop calls repeatedly.

    Args:
        registry: ToolRegistry with all available tools registered.
        temperature: Optional temperature override.
        max_tokens: Optional max tokens override.

    Returns:
        A Runnable that accepts {"message": str, "history": list}
        and returns an AIMessage (possibly with tool_calls).
    """
    prompt = build_tool_prompt()
    model = build_tool_model(registry, temperature=temperature, max_tokens=max_tokens)

    return prompt | model


def build_tool_model(
    registry: ToolRegistry,
    *,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> BaseChatModel:
    """Build a Gemini model with tools bound.

    Uses the registry's get_lc_tools() to generate the tool schemas
    that Gemini uses for function calling.
    """
    model = build_chat_model(temperature=temperature, max_tokens=max_tokens)
    lc_tools = registry.get_lc_tools()

    if not lc_tools:
        return model

    return model.bind_tools(lc_tools)
