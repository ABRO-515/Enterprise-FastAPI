from __future__ import annotations

import logging
from typing import Any

import numexpr
from pydantic import BaseModel, Field

from app.ai.tools.base import BaseTool

logger = logging.getLogger(__name__)


class CalculatorInput(BaseModel):
    """Input schema for the calculator tool."""

    expression: str = Field(
        ...,
        description=(
            "A mathematical expression to evaluate. "
            "Supports arithmetic (+, -, *, /, **), "
            "comparisons, and functions like sin, cos, sqrt, log, abs. "
            "Examples: '42 * 3.14', 'sqrt(144) + 10', '(100 * 0.15) / 2'"
        ),
    )


class CalculatorTool(BaseTool):
    """Safe mathematical expression evaluator using numexpr.

    Capabilities:
      - Basic arithmetic: +, -, *, /, %, **
      - Math functions: sin, cos, tan, sqrt, log, log10, abs, exp
      - Comparisons and logical operations
      - Percentages and financial calculations

    Safety:
      - numexpr only evaluates mathematical expressions
      - No access to builtins, file system, or network
      - No arbitrary code execution
      - Expression length capped
    """

    name = "calculator"
    description = (
        "Evaluate mathematical expressions safely. Use for arithmetic, "
        "percentages, financial calculations, and scientific math. "
        "Input should be a valid mathematical expression string."
    )
    args_schema = CalculatorInput

    MAX_EXPRESSION_LENGTH = 500

    async def _execute(self, **kwargs: Any) -> str:
        """Evaluate the expression using numexpr."""
        expression: str = kwargs["expression"]

        # Safety: cap expression length
        if len(expression) > self.MAX_EXPRESSION_LENGTH:
            raise ValueError(
                f"Expression too long ({len(expression)} chars). "
                f"Max: {self.MAX_EXPRESSION_LENGTH}"
            )

        # Clean common patterns the LLM might produce
        expression = self._sanitize(expression)

        logger.debug("Evaluating expression: %s", expression)

        result = numexpr.evaluate(expression)
        result_str = str(result.item() if hasattr(result, "item") else result)

        logger.debug("Result: %s", result_str)
        return result_str

    @staticmethod
    def _sanitize(expression: str) -> str:
        """Clean up common LLM expression patterns for numexpr compatibility."""
        # Replace common textual operators
        expression = expression.replace("^", "**")
        expression = expression.replace("×", "*")
        expression = expression.replace("÷", "/")
        # Strip trailing equals sign (LLMs sometimes append "= ?")
        expression = expression.rstrip("= ?")
        return expression.strip()
