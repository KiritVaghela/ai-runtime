from __future__ import annotations

from typing import Any, Callable

from ..tool import Tool, ToolResult


class FunctionTool(Tool):
    """Wrap a Python callable as a Tool.

    The callable may be sync or async and should accept (context, input).
    """

    def __init__(self, name: str, func: Callable[[Any, Any], Any], description: str | None = None):
        self.name = name
        self.func = func
        self.description = description

    async def run(self, context: Any, input: Any) -> ToolResult:
        try:
            result = self.func(context, input)
            if hasattr(result, "__await__"):
                result = await result
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, error=str(e))
