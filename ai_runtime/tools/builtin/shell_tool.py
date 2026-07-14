from __future__ import annotations

import asyncio
from typing import Any

from ..tool import Tool, ToolResult


class BashTool(Tool):
    """Run a shell command (optionally sandboxed via cwd + timeout).

    Mirrors the terminal tool of agentic coding tools. Commands run in the
    given working directory with a timeout; the permission layer (if wired
    through a `GuardedToolExecutor`) governs whether the command is allowed.
    """

    name = "Bash"
    description = "Run a shell command. Input: {command, cwd?, timeout?}"

    def __init__(self, cwd: str | None = None, default_timeout: float = 60.0):
        self._cwd = cwd
        self._timeout = default_timeout

    async def run(self, context: Any, input: Any) -> ToolResult:
        try:
            args = input if isinstance(input, dict) else {"command": str(input)}
            command = args["command"]
            cwd = args.get("cwd", self._cwd)
            timeout = float(args.get("timeout", self._timeout))
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
            )
            out, err = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            return ToolResult(
                success=proc.returncode == 0,
                output=out.decode(errors="replace"),
                error=err.decode(errors="replace") if proc.returncode != 0 else None,
            )
        except asyncio.TimeoutError:
            return ToolResult(success=False, error="command timed out")
        except Exception as e:  # noqa: BLE001
            return ToolResult(success=False, error=str(e))
