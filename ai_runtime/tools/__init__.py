"""Tooling subsystem for ai_runtime."""

from .tool import Tool, ToolResult
from .registry import ToolRegistry
from .executor import ToolExecutor
from .adapters.function_adapter import FunctionTool
from .permissions import (
    PermissionPolicy,
    PermissionRule,
    PermissionDecision,
    PermissionError,
)
from .guarded_executor import GuardedToolExecutor

__all__ = [
    "Tool",
    "ToolResult",
    "ToolRegistry",
    "ToolExecutor",
    "FunctionTool",
    "PermissionPolicy",
    "PermissionRule",
    "PermissionDecision",
    "PermissionError",
    "GuardedToolExecutor",
]
