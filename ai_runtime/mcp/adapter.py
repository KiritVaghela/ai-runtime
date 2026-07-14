from __future__ import annotations

from typing import Any

from ai_runtime.tools.tool import Tool, ToolResult

from .client import MCPClient, MCPToolSpec


class MCPTool(Tool):
    """A runtime `Tool` backed by an MCP server tool.

    Defers tool loading to the MCP server (tool-search deferral), keeping
    the agent's context small — the same pattern agentic coding tools use
    to avoid bloating the prompt with every available tool's schema.
    """

    def __init__(self, client: MCPClient, spec: MCPToolSpec):
        self._client = client
        self._spec = spec
        self.name = spec.name
        self.description = spec.description

    def run(self, context: Any, input: Any) -> ToolResult:
        # MCP calls are async; the executor awaits coroutine results.
        return self._run_async(input)

    async def _run_async(self, input: Any) -> ToolResult:
        try:
            if isinstance(input, str):
                import json

                args = json.loads(input) if input else {}
            else:
                args = input or {}
            result = await self._client.call_tool(self.name, args)
            return ToolResult(success=True, output=result)
        except Exception as e:  # noqa: BLE001
            return ToolResult(success=False, error=str(e))


async def register_mcp_tools(registry, client: MCPClient) -> list[MCPTool]:
    """Fetch tool specs from an MCP server and register them as `Tool`s."""
    specs = await client.list_tools()
    tools = [MCPTool(client, spec) for spec in specs]
    for t in tools:
        registry.register(t)
    return tools
