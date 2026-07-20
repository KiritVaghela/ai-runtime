from __future__ import annotations

from typing import Any, Callable, Awaitable

from .executor import ToolExecutor
from .permissions import (
    PermissionPolicy,
    PermissionDecision,
    render_params,
)
from .tool import ToolResult


class GuardedToolExecutor:
    """Wraps a `ToolExecutor` with a permission policy.

    Before each tool runs, the policy is consulted. A DENY raises
    `PermissionError`; an ASK defers to `on_ask` (which may prompt the user
    or apply a default). This mirrors the tiered permission modes of
    agentic coding tools without coupling to any UI.
    """

    def __init__(
        self,
        executor: ToolExecutor,
        policy: PermissionPolicy,
        on_ask: Callable[[str, str], Awaitable[bool]] | None = None,
    ):
        self.executor = executor
        self.policy = policy
        self.on_ask = on_ask

    async def execute(
        self,
        name: str,
        context: Any,
        input: Any,
        timeout: float | None = None,
    ) -> ToolResult:
        param_str = render_params(input)
        decision = self.policy.decide(name, param_str)

        if decision == PermissionDecision.DENY:
            return ToolResult(
                success=False,
                error=f"Permission denied for {name}({param_str})",
            )

        if decision == PermissionDecision.ASK:
            if self.on_ask is None:
                return ToolResult(
                    success=False,
                    error=f"Permission required for {name}({param_str})",
                )
            approved = await self.on_ask(name, param_str)
            if not approved:
                return ToolResult(
                    success=False,
                    error=f"Permission denied for {name}({param_str})",
                )

        return await self.executor.execute(name, context, input, timeout)
