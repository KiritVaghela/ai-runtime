"""Built-in tools that mirror the file/shell/grep primitives of agentic
coding tools (Claude Code, Codex, Cursor, Copilot)."""

from .file_tools import (
    ReadFileTool,
    WriteFileTool,
    EditFileTool,
    GlobTool,
    GrepTool,
)
from .shell_tool import BashTool

__all__ = [
    "ReadFileTool",
    "WriteFileTool",
    "EditFileTool",
    "GlobTool",
    "GrepTool",
    "BashTool",
]


def register_builtin_tools(registry, base_dir: str | None = None) -> None:
    """Register the standard built-in toolset on a `ToolRegistry`.

    `base_dir` scopes all file operations to a sandbox root so the agent
    cannot read/write outside the project (mirrors workspace trust).
    """
    for tool_cls in (ReadFileTool, WriteFileTool, EditFileTool, GlobTool, GrepTool):
        registry.register(tool_cls(base_dir))
    registry.register(BashTool(cwd=base_dir))
