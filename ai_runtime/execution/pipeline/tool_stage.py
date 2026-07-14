from __future__ import annotations

from typing import Any

from ai_runtime.execution.context import ExecutionContext
from ai_runtime.execution.pipeline.stage import ExecutionStage


class ToolStage(ExecutionStage):
    """Pipeline stage that executes declared tool calls.

    It looks for `context.metadata['tool_calls']` which should be a list of
    dicts: {"tool": "name", "input": ...}
    Results are stored in `context.variables['tool_results']`.
    """

    def __init__(self, executor: Any):
        self.executor = executor

    async def execute(self, context: ExecutionContext) -> ExecutionContext:
        tool_calls = context.metadata.get("tool_calls") or []
        if not tool_calls:
            return context

        context.variables.setdefault("tool_results", {})

        for call in tool_calls:
            name = call.get("tool")
            input = call.get("input")
            timeout = call.get("timeout")
            try:
                result = await self.executor.execute(name, context, input, timeout=timeout)
            except Exception as e:
                result = type("R", (), {"success": False, "error": str(e), "output": None})()

            context.variables["tool_results"][name] = result

        return context
