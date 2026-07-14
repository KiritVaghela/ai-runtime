from __future__ import annotations

from typing import Dict, Iterable

from .tool import Tool


class ToolRegistry:
    """Simple in-memory registry for tools."""

    def __init__(self):
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise KeyError(f"Tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        return self._tools[name]

    def list(self) -> Iterable[Tool]:
        return list(self._tools.values())
