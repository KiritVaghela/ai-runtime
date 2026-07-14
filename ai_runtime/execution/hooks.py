from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Awaitable


class HookEvent(str, Enum):
    PRE_TOOL_USE = "PreToolUse"
    POST_TOOL_USE = "PostToolUse"
    PRE_LLM = "PreLLM"
    POST_LLM = "PostLLM"
    ON_PLAN = "OnPlan"
    ON_COMPACT = "OnCompact"
    ON_ERROR = "OnError"


@dataclass
class HookContext:
    """Context passed to a hook callback."""

    event: HookEvent
    agent: Any = None
    tool_name: str | None = None
    tool_input: Any = None
    tool_result: Any = None
    message: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class HookResult:
    """Returned by a hook; may mutate or short-circuit behavior."""

    continue_: bool = True  # if False, the action is blocked/skipped
    patch: dict[str, Any] = field(default_factory=dict)  # overrides to apply
    note: str | None = None


HookFn = Callable[[HookContext], Awaitable[HookResult]]


class HookRegistry:
    """Registry of hooks keyed by `HookEvent`.

    Mirrors the Pre/PostToolUse + lifecycle hooks of agentic coding tools.
    Hooks are a clean extension point: they can observe, mutate, or block
    tool calls and LLM turns without changing the core pipeline.
    """

    def __init__(self):
        self._hooks: dict[HookEvent, list[HookFn]] = {}

    def register(self, event: HookEvent, fn: HookFn) -> None:
        self._hooks.setdefault(event, []).append(fn)

    def clear(self, event: HookEvent | None = None) -> None:
        if event is None:
            self._hooks.clear()
        else:
            self._hooks.pop(event, None)

    async def trigger(self, ctx: HookContext) -> HookResult:
        """Run all hooks for an event, merging results.

        The first hook that sets `continue_=False` short-circuits. Patches
        from later hooks override earlier ones.
        """
        merged = HookResult()
        for fn in self._hooks.get(ctx.event, []):
            result = await fn(ctx)
            if not result.continue_:
                merged.continue_ = False
                merged.note = result.note
                return merged
            merged.patch.update(result.patch)
            if result.note:
                merged.note = result.note
        return merged
