from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Optional

from .registry import ToolRegistry
from .tool import ToolResult


class ToolExecutor:
    """Executes registered tools with optional timeouts and threadpool isolation."""

    def __init__(self, registry: ToolRegistry, max_workers: int = 4):
        self.registry = registry
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

    async def execute(self, name: str, context: Any, input: Any, timeout: Optional[float] = None) -> ToolResult:
        tool = self.registry.get(name)

        # If the tool.run is a coroutine function, await it directly.
        coro = tool.run(context, input)
        if asyncio.iscoroutine(coro):
            try:
                if timeout:
                    result = await asyncio.wait_for(coro, timeout=timeout)
                else:
                    result = await coro
                return result
            except asyncio.TimeoutError:
                return ToolResult(success=False, error="timeout")
            except Exception as e:
                return ToolResult(success=False, error=str(e))

        # Otherwise, run in threadpool
        loop = asyncio.get_running_loop()
        try:
            if timeout:
                return await asyncio.wait_for(loop.run_in_executor(self._executor, lambda: coro), timeout=timeout)
            else:
                return await loop.run_in_executor(self._executor, lambda: coro)
        except asyncio.TimeoutError:
            return ToolResult(success=False, error="timeout")
        except Exception as e:
            return ToolResult(success=False, error=str(e))
