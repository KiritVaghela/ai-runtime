from __future__ import annotations

import json

import pytest

from ai_runtime.agents import Agent
from ai_runtime.conversation import ChatMessage, ChatRequest, ChatResponse
from ai_runtime.server.agent_server import AgentServer
from ai_runtime.server.protocol import (
    AgentRequest,
    AgentResponse,
    serialize_event,
    parse_request,
)
from ai_runtime.streaming import TextDeltaEvent, CompletedEvent


class _FakeProvider:
    def __init__(self, text="hello from agent"):
        self._text = text

    async def chat(self, request):
        return ChatResponse(message=ChatMessage(role="assistant", content=self._text))

    async def stream(self, request):
        yield TextDeltaEvent(delta=self._text)
        yield CompletedEvent()


@pytest.mark.asyncio
async def test_server_handle_chat():
    agent = Agent("a", _FakeProvider())
    server = AgentServer(agent)
    resp = await server.handle(AgentRequest(session_id="s1", message="hi"))
    assert isinstance(resp, AgentResponse)
    assert resp.content == "hello from agent"


@pytest.mark.asyncio
async def test_server_plan_mode():
    agent = Agent("a", _FakeProvider())
    server = AgentServer(agent)
    resp = await server.handle(
        AgentRequest(session_id="s1", message="plan x", mode="plan")
    )
    assert resp.finish_reason == "plan"


@pytest.mark.asyncio
async def test_protocol_roundtrip():
    req = AgentRequest(session_id="x", message="hi", mode="chat")
    line = serialize_event(req.__dict__)
    parsed = parse_request(line)
    assert parsed.message == "hi"
    assert parsed.session_id == "x"
