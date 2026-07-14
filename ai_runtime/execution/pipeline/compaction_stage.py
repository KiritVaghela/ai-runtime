from __future__ import annotations

from typing import Any, Callable

from ai_runtime.conversation import Conversation
from ai_runtime.context.window import ContextWindow, estimate_tokens

from .stage import ExecutionStage
from ..context import ExecutionContext
from ..hooks import HookEvent, HookContext


class CompactionStage(ExecutionStage):
    """Auto-compacts the conversation when it exceeds the token budget.

    Mirrors the auto-compaction behavior of agentic coding tools: when the
    context window fills, older turns are summarized (if a `summarizer` is
    provided) or dropped to keep the active window small. An `OnCompact`
    hook fires so callers can observe or override the compaction.
    """

    def __init__(
        self,
        max_tokens: int = 8000,
        summarizer: Callable[[Conversation], str] | None = None,
        estimator: Callable[[str], int] = estimate_tokens,
    ):
        self.max_tokens = max_tokens
        self.summarizer = summarizer
        self.estimator = estimator

    async def execute(self, context: ExecutionContext) -> ExecutionContext:
        window = ContextWindow(
            conversation=context.conversation,
            max_tokens=self.max_tokens,
            estimator=self.estimator,
            summarizer=self.summarizer,
        )
        if not window.is_over_budget():
            return context

        before = window.token_count()
        compacted = window.fit()
        after = sum(self.estimator(str(m.content)) for m in compacted.messages)

        context.conversation = compacted
        context.metadata["compacted"] = {
            "before_tokens": before,
            "after_tokens": after,
        }

        if context.hooks is not None:
            await context.hooks.trigger(
                HookContext(
                    event=HookEvent.ON_COMPACT,
                    agent=context.agent,
                    metadata=context.metadata["compacted"],
                )
            )
        return context
