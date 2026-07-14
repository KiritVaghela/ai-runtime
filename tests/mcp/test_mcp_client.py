from __future__ import annotations

import pytest

from ai_runtime.mcp.client import MCPClient, MCPTransport, MCPToolSpec
from ai_runtime.mcp.adapter import MCPTool, register_mcp_tools
from ai_runtime.tools import ToolRegistry


class _FakeTransport(MCPTransport):
    def __init__(self):
        self._tools = [
            {
                "name": "search",
                "description": "search the web",
                "inputSchema": {"type": "object"},
            }
        ]

    async def send(self, message):
        method = message.get("method")
        if method == "tools/list":
            return {"result": {"tools": self._tools}}
        if method == "tools/call":
            return {"result": {"echo": message["params"]["arguments"]}}
        return {"result": {}}

    async def close(self):
        pass


@pytest.mark.asyncio
async def test_mcp_client_lists_and_calls_tools():
    client = MCPClient(_FakeTransport())
    specs = await client.list_tools()
    assert specs[0].name == "search"

    result = await client.call_tool("search", {"q": "python"})
    assert result == {"echo": {"q": "python"}}


@pytest.mark.asyncio
async def test_register_mcp_tools_wraps_as_runtime_tools():
    client = MCPClient(_FakeTransport())
    registry = ToolRegistry()
    tools = await register_mcp_tools(registry, client)
    assert len(tools) == 1
    assert tools[0].name == "search"

    # The wrapped tool is callable through the registry/executor.
    from ai_runtime.tools import ToolExecutor

    executor = ToolExecutor(registry)
    res = await executor.execute("search", None, {"q": "x"})
    assert res.success
    assert res.output == {"echo": {"q": "x"}}
