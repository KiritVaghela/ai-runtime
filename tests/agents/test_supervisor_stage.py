from __future__ import annotations

import pytest

from ai_runtime.agents import Agent, AgentRunner, SubAgentSpec
from ai_runtime.conversation import ChatMessage, ChatRequest, ChatResponse
from ai_runtime.execution.context import ExecutionContext
from ai_runtime.execution.pipeline.supervisor_stage import SupervisorStage


class _FakeProvider:
    def __init__(self, text="sub answer"):
        self._text = text

    async def chat(self, request):
        return ChatResponse(message=ChatMessage(role="assistant", content=self._text))

    async def stream(self, request):
        raise NotImplementedError


@pytest.mark.asyncio
async def test_supervisor_spawns_subagents():
    child = Agent("child", _FakeProvider("child output"))
    parent = Agent("parent", _FakeProvider("parent output"))
    parent.sub_agents = [
        SubAgentSpec(name="researcher", agent=child, task_template="Do: {task}")
    ]

    ctx = ExecutionContext(
        provider=_FakeProvider(),
        agent=parent,
    )
    ctx._engine = type("E", (), {"chat": staticmethod(lambda c, m: _FakeProvider().chat(None))})()
    ctx.request = ChatRequest(messages=[ChatMessage.user("main task")])

    result = await SupervisorStage().execute(ctx)
    sys_msgs = [m for m in result.conversation.messages if m.role == "system"]
    assert any("Sub-agent results" in m.content for m in sys_msgs)
    assert result.metadata["sub_agent_results"][0]["output"] == "sub answer"


@pytest.mark.asyncio
async def test_supervisor_noop_without_subagents():
    agent = Agent("solo", _FakeProvider())
    ctx = ExecutionContext(provider=_FakeProvider(), agent=agent)
    ctx.request = ChatRequest(messages=[ChatMessage.user("x")])
    result = await SupervisorStage().execute(ctx)
    assert result.metadata.get("sub_agent_results") is None
