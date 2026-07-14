from __future__ import annotations

import json
import re
from typing import Any, Callable

from ai_runtime.conversation import ChatMessage

from .stage import ExecutionStage
from ..context import ExecutionContext
from ..mode import ExecutionMode


def _default_extractor(conversation) -> list[str]:
    """Heuristic extractor: pulls lines tagged as learnings from the transcript.

    Agents (or a model) can emit lines like `LEARNING: <fact>` which are
    persisted to the memory store. This is a lightweight stand-in for the
    autonomous memory extraction of agentic coding tools.
    """
    facts: list[str] = []
    for msg in conversation.messages:
        content = msg.content or ""
        for line in content.splitlines():
            m = re.match(r"^\s*LEARNING:\s*(.+)$", line)
            if m:
                facts.append(m.group(1).strip())
    return facts


class MemoryConsolidationStage(ExecutionStage):
    """Persists learnings back to the agent's `MemoryStore` after a task.

    Mirrors the autonomous memory extraction of agentic coding tools (e.g.
    Claude's auto-memory, Codex's background extraction): instead of a
    purely manual KV store, a post-task pass consolidates durable facts so
    they are available in future sessions.
    """

    def __init__(
        self,
        extractor: Callable[[Any], list[str]] = _default_extractor,
        key_prefix: str = "learning:",
    ):
        self.extractor = extractor
        self.key_prefix = key_prefix

    async def execute(self, context: ExecutionContext) -> ExecutionContext:
        # Only consolidate after a real execution turn, not in plan mode.
        if context.mode == ExecutionMode.PLAN:
            return context

        agent = getattr(context, "agent", None)
        store = getattr(agent, "memory_store", None) if agent else None
        if store is None:
            return context

        facts = self.extractor(context.conversation)
        if not facts:
            return context

        existing = await store.get("__learnings__") or []
        if isinstance(existing, str):
            try:
                existing = json.loads(existing)
            except json.JSONDecodeError:
                existing = [existing]

        merged = list(existing)
        for f in facts:
            if f not in merged:
                merged.append(f)

        await store.set("__learnings__", json.dumps(merged))
        context.metadata["consolidated_learnings"] = len(merged)
        return context
