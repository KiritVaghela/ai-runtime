from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ToolResult:
    success: bool
    output: Any | None = None
    error: str | None = None


class Tool(ABC):
    """Abstract tool interface. Concrete tools should implement `run`.

    The tool should be safe to call from an async context. Blocking tools
    will be executed in a threadpool by the `ToolExecutor`.
    """

    name: str
    description: str | None = None

    def to_schema(self) -> dict[str, Any]:
        """Return an OpenAI-style tool schema for provider tool-calling.

        Defaults to a permissive schema (free-form object) so the model can
        still invoke the tool even when a concrete parameter schema isn't
        declared. Subclasses (and `MCPTool`) override this to expose a
        precise `parameters` object.
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description or "",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "additionalProperties": True,
                },
            },
        }

    @abstractmethod
    async def run(self, context: Any, input: Any) -> ToolResult:
        """Execute the tool with given input and return a ToolResult."""
