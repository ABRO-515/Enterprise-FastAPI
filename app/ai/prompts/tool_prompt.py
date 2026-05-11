from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

TOOL_SYSTEM_TEMPLATE = """\
You are a helpful AI assistant with access to tools. Follow these guidelines:

1. Analyze the user's request carefully before deciding whether to use a tool.
2. If the request requires calculation, use the calculator tool.
3. If the request requires information from uploaded documents, use the document_lookup tool.
4. If the request requires current/real-time information from the web, use the web_search tool.
5. You may call multiple tools if needed to fully answer the question.
6. After receiving tool results, reason over them and provide a clear, helpful answer.
7. If no tool is needed, respond directly without calling any tool.
8. Always cite tool results when incorporating them into your response.
9. If a tool fails, acknowledge the failure and provide the best answer you can without it."""


def build_tool_prompt() -> ChatPromptTemplate:
    """Build the tool-augmented chat prompt.

    Prompt structure:
      - System: instructions for tool usage behavior
      - History: optional conversation turns
      - Human: the user's query

    The tools themselves are bound to the model via model.bind_tools(),
    not injected into the prompt text.
    """
    return ChatPromptTemplate.from_messages(
        [
            ("system", TOOL_SYSTEM_TEMPLATE),
            MessagesPlaceholder("history", optional=True),
            ("human", "{message}"),
        ]
    )
