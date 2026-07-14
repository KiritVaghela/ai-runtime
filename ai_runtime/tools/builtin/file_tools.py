from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from ..tool import Tool, ToolResult


def _resolve(base: str | None, path: str) -> Path:
    """Resolve `path` against an allowed base directory (sandbox root)."""
    p = Path(path)
    if not p.is_absolute() and base:
        p = Path(base) / p
    return p.resolve()


class ReadFileTool(Tool):
    """Read a file's contents (optionally a line range)."""

    name = "Read"
    description = "Read a file from the workspace. Input: {path, start?, end?}"

    def __init__(self, base_dir: str | None = None):
        self._base = base_dir

    async def run(self, context: Any, input: Any) -> ToolResult:
        try:
            args = input if isinstance(input, dict) else {"path": str(input)}
            path = _resolve(self._base, args["path"])
            if not path.exists():
                return ToolResult(success=False, error=f"No such file: {path}")
            text = path.read_text(encoding="utf-8", errors="replace")
            lines = text.splitlines()
            start = int(args.get("start", 1)) - 1
            end = int(args.get("end", len(lines)))
            sliced = "\n".join(lines[start:end])
            return ToolResult(success=True, output=sliced)
        except Exception as e:  # noqa: BLE001
            return ToolResult(success=False, error=str(e))


class WriteFileTool(Tool):
    """Write content to a file (creating parent dirs)."""

    name = "Write"
    description = "Write content to a file. Input: {path, content}"

    def __init__(self, base_dir: str | None = None):
        self._base = base_dir

    async def run(self, context: Any, input: Any) -> ToolResult:
        try:
            args = input if isinstance(input, dict) else {}
            path = _resolve(self._base, args["path"])
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(args.get("content", ""), encoding="utf-8")
            return ToolResult(success=True, output=f"wrote {path}")
        except Exception as e:  # noqa: BLE001
            return ToolResult(success=False, error=str(e))


class EditFileTool(Tool):
    """Apply an exact old→new string replacement within a file."""

    name = "Edit"
    description = "Edit a file via exact string replace. Input: {path, old, new}"

    def __init__(self, base_dir: str | None = None):
        self._base = base_dir

    async def run(self, context: Any, input: Any) -> ToolResult:
        try:
            args = input if isinstance(input, dict) else {}
            path = _resolve(self._base, args["path"])
            text = path.read_text(encoding="utf-8")
            old, new = args["old"], args.get("new", "")
            if old not in text:
                return ToolResult(success=False, error="old string not found")
            text = text.replace(old, new, 1)
            path.write_text(text, encoding="utf-8")
            return ToolResult(success=True, output=f"edited {path}")
        except Exception as e:  # noqa: BLE001
            return ToolResult(success=False, error=str(e))


class GlobTool(Tool):
    """Find files by glob pattern."""

    name = "Glob"
    description = "Find files by glob. Input: {pattern, path?}"

    def __init__(self, base_dir: str | None = None):
        self._base = base_dir

    async def run(self, context: Any, input: Any) -> ToolResult:
        try:
            args = input if isinstance(input, dict) else {"pattern": str(input)}
            root = _resolve(self._base, args.get("path", "."))
            matches = [str(p) for p in root.glob(args["pattern"]) if p.is_file()]
            return ToolResult(success=True, output="\n".join(matches))
        except Exception as e:  # noqa: BLE001
            return ToolResult(success=False, error=str(e))


class GrepTool(Tool):
    """Search file contents with a regex."""

    name = "Grep"
    description = "Search file contents by regex. Input: {pattern, path?, glob?}"

    def __init__(self, base_dir: str | None = None):
        self._base = base_dir

    async def run(self, context: Any, input: Any) -> ToolResult:
        try:
            import re

            args = input if isinstance(input, dict) else {"pattern": str(input)}
            root = _resolve(self._base, args.get("path", "."))
            pat = re.compile(args["pattern"])
            glob = args.get("glob", "**/*")
            hits = []
            for p in root.glob(glob):
                if not p.is_file():
                    continue
                try:
                    for i, line in enumerate(p.read_text(errors="ignore").splitlines(), 1):
                        if pat.search(line):
                            hits.append(f"{p}:{i}: {line}")
                except Exception:
                    continue
            return ToolResult(success=True, output="\n".join(hits))
        except Exception as e:  # noqa: BLE001
            return ToolResult(success=False, error=str(e))
