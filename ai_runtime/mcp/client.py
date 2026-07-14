from __future__ import annotations

import asyncio
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class MCPToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]


class MCPTransport(ABC):
    """Low-level transport to an MCP server (stdio/HTTP/SSE)."""

    @abstractmethod
    async def send(self, message: dict[str, Any]) -> dict[str, Any]:
        """Send a JSON-RPC request and return the response."""

    @abstractmethod
    async def close(self) -> None:
        ...


class StdioTransport(MCPTransport):
    """Spawns an MCP server as a subprocess and speaks JSON-RPC over stdio.

    This mirrors the stdio transport used by Claude Code / Codex / Cursor
    to attach local MCP servers. Network transports (HTTP/SSE) can subclass
    `MCPTransport` with the same request/response contract.
    """

    def __init__(self, command: str, args: list[str] | None = None, env: dict | None = None):
        self._command = command
        self._args = args or []
        self._env = env
        self._proc: asyncio.subprocess.Process | None = None
        self._req_id = 0
        self._lock = asyncio.Lock()

    async def _ensure_started(self) -> None:
        if self._proc is None:
            self._proc = await asyncio.create_subprocess_exec(
                self._command,
                *self._args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                env=self._env,
            )

    async def send(self, message: dict[str, Any]) -> dict[str, Any]:
        await self._ensure_started()
        assert self._proc and self._proc.stdin and self._proc.stdout
        async with self._lock:
            self._req_id += 1
            payload = {**message, "jsonrpc": "2.0", "id": self._req_id}
            self._proc.stdin.write((json.dumps(payload) + "\n").encode())
            await self._proc.stdin.drain()
            line = await self._proc.stdout.readline()
            if not line:
                raise RuntimeError("MCP server closed connection")
            return json.loads(line.decode())

    async def close(self) -> None:
        if self._proc:
            self._proc.terminate()
            await self._proc.wait()
            self._proc = None


class MCPClient:
    """High-level MCP client: lists tools and calls them via a transport.

    Exposes server tools as a uniform surface so they can be wrapped as
    `Tool` instances in the runtime's `ToolRegistry` (see `MCPToolAdapter`).
    """

    def __init__(self, transport: MCPTransport):
        self._transport = transport

    async def initialize(self) -> dict[str, Any]:
        return await self._transport.send(
            {"method": "initialize", "params": {"protocolVersion": "2024-11-05"}}
        )

    async def list_tools(self) -> list[MCPToolSpec]:
        resp = await self._transport.send({"method": "tools/list", "params": {}})
        result = resp.get("result", {})
        tools = result.get("tools", [])
        return [
            MCPToolSpec(
                name=t["name"],
                description=t.get("description", ""),
                input_schema=t.get("inputSchema", {}),
            )
            for t in tools
        ]

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        resp = await self._transport.send(
            {"method": "tools/call", "params": {"name": name, "arguments": arguments}}
        )
        return resp.get("result")

    async def close(self) -> None:
        await self._transport.close()
