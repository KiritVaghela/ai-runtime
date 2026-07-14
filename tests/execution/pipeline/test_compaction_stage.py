from __future__ import annotations

import pytest

from ai_runtime.conversation import ChatMessage, ChatRequest
from ai_runtime.execution.context import ExecutionContext
from ai_runtime.execution.pipeline.compaction_stage import CompactionStage


@pytest.mark.asyncio
async def test_compaction_drops_old_messages_when_over_budget():
    from ai_runtime.conversation import Conversation

    # 20 user messages of ~40 tokens each => 800 tokens; budget 200.
    msgs = [ChatMessage.user("x" * 160) for _ in range(20)]
    conv = Conversation()
    for m in msgs:
        conv.add(m)

    ctx = ExecutionContext(provider=None, conversation=conv)

    stage = CompactionStage(max_tokens=200)
    result = await stage.execute(ctx)

    # After compaction the token count should be within budget.
    total = sum(len(str(m.content)) // 4 for m in result.conversation.messages)
    assert total <= 200
    assert "compacted" in result.metadata


@pytest.mark.asyncio
async def test_compaction_noop_under_budget():
    from ai_runtime.conversation import Conversation

    conv = Conversation()
    conv.add(ChatMessage.user("short"))
    ctx = ExecutionContext(provider=None, conversation=conv)

    stage = CompactionStage(max_tokens=200)
    result = await stage.execute(ctx)
    assert len(result.conversation.messages) == 1
    assert "compacted" not in result.metadata
