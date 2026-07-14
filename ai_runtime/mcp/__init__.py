"""MCP (Model Context Protocol) client framework for ai_runtime."""

from .client import MCPClient, MCPTransport, StdioTransport, MCPToolSpec
from .adapter import MCPTool, register_mcp_tools

__all__ = [
    "MCPClient",
    "MCPTransport",
    "StdioTransport",
    "MCPToolSpec",
    "MCPTool",
    "register_mcp_tools",
]
