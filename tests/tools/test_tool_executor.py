import asyncio

from ai_runtime.tools.registry import ToolRegistry
from ai_runtime.tools.executor import ToolExecutor
from ai_runtime.tools.adapters.function_adapter import FunctionTool


def test_function_tool_executor():
    registry = ToolRegistry()

    def echo(ctx, inp):
        return {"echo": inp}

    tool = FunctionTool("echo", echo, description="Echo tool")
    registry.register(tool)

    executor = ToolExecutor(registry)

    result = asyncio.run(executor.execute("echo", {}, {"msg": "hello"}, timeout=1.0))
    assert result.success
    assert result.output == {"echo": {"msg": "hello"}}
