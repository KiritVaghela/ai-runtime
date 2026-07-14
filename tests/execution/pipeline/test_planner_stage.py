from __future__ import annotations

import pytest

from ai_runtime.conversation import ChatMessage, ChatRequest, ChatResponse
from ai_runtime.execution.context import ExecutionContext
from ai_runtime.execution.mode import ExecutionMode
from ai_runtime.execution.pipeline.planner_stage import PlannerStage
from ai_runtime.execution.plan import Plan


class _FakeProvider:
    def __init__(self, content: str):
        self._content = content

    async def chat(self, request):
        return ChatResponse(message=assistant(self._content))

    async def stream(self, request):
        raise NotImplementedError


def assistant(content: str) -> ChatMessage:
    return ChatMessage(role="assistant", content=content)


@pytest.mark.asyncio
async def test_planner_parses_json_plan():
    content = (
        'Here is the plan:\n{"goal": "Refactor module", '
        '"steps": [{"description": "Read file", "action": "tool:read", '
        '"target": "a.py"}, {"description": "Edit", "action": "tool:edit"}], '
        '"risks": ["Breaking import"]}'
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
    assert result.plan.steps[0].target == "a.py"
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
