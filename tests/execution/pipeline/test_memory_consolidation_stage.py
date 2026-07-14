from __future__ import annotations

import json

import pytest

from ai_runtime.agents import Agent
from ai_runtime.conversation import ChatMessage, ChatRequest, ChatResponse
from ai_runtime.execution.context import ExecutionContext
from ai_runtime.execution.pipeline.memory_consolidation_stage import (
    MemoryConsolidationStage,
)
from ai_runtime.memory import InMemoryStore


class _FakeProvider:
    async def chat(self, request):
        return ChatResponse(
            message=ChatMessage(role="assistant", content="LEARNING: use pytest -q")
        )

    async def stream(self, request):
        raise NotImplementedError


@pytest.mark.asyncio
async def test_consolidation_writes_learnings_to_store():
    store = InMemoryStore()
    agent = Agent("a", _FakeProvider(), memory_store=store)
    ctx = ExecutionContext(provider=_FakeProvider(), agent=agent)
    ctx.conversation.add(ChatMessage.assistant("LEARNING: use pytest -q"))

    result = await MemoryConsolidationStage().execute(ctx)
    assert result.metadata["consolidated_learnings"] >= 1

    raw = await store.get("__learnings__")
    learnings = json.loads(raw)
    assert "use pytest -q" in learnings


@pytest.mark.asyncio
async def test_consolidation_skipped_without_store():
    ctx = ExecutionContext(provider=_FakeProvider())
    result = await MemoryConsolidationStage().execute(ctx)
    assert "consolidated_learnings" not in result.metadata
