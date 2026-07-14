from __future__ import annotations

import pytest

from ai_runtime.conversation import ChatMessage, ChatRequest, ChatResponse
from ai_runtime.execution.context import ExecutionContext
from ai_runtime.execution.mode import ExecutionMode
from ai_runtime.execution.pipeline.planner_stage import PlannerStage
from ai_runtime.execution.plan import Plan
from ai_runtime.streaming import TextDeltaEvent, CompletedEvent


class _FakeProvider:
    def __init__(self, content: str):
        self._content = content

    async def chat(self, request):
        return ChatResponse(message=assistant(self._content))

    async def stream(self, request):
        yield TextDeltaEvent(delta=self._content)
        yield CompletedEvent()


def assistant(content: str) -> ChatMessage:
    return ChatMessage(role="assistant", content=content)


@pytest.mark.asyncio
async def test_planner_parses_markdown_plan():
    content = (
        "# Plan\nRefactor module\n\n"
        "## Steps\n"
        "- Read file (tool:read, target: a.py)\n"
        "- Edit the module (tool:edit)\n\n"
        "## Risks\n"
        "- Breaking import"
    )
    provider = _FakeProvider(content)
    ctx = ExecutionContext(
        provider=provider,
        mode=ExecutionMode.PLAN,
        request=ChatRequest(messages=[ChatMessage.user("Refactor module")]),
    )
    stage = PlannerStage()
    result = await stage.execute(ctx)

    assert isinstance(result.plan, Plan)
    assert result.plan.goal == "Refactor module"
    assert len(result.plan.steps) == 2
    assert "Read file" in result.plan.steps[0].description
    assert result.plan.risks == ["Breaking import"]


@pytest.mark.asyncio
async def test_planner_skipped_in_chat_mode():
    provider = _FakeProvider("{}")
    ctx = ExecutionContext(
        provider=provider,
        mode=ExecutionMode.CHAT,
        request=ChatRequest(messages=[ChatMessage.user("hi")]),
    )
    stage = PlannerStage()
    result = await stage.execute(ctx)
    assert result.plan is None
