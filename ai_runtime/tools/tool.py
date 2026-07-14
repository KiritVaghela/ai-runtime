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

    @abstractmethod
    async def run(self, context: Any, input: Any) -> ToolResult:
        """Execute the tool with given input and return a ToolResult."""
