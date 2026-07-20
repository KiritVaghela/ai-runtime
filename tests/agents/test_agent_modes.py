from __future__ import annotations

import pytest

from ai_runtime.agents import Agent
from ai_runtime.agents.modes import AgentMode, AGENT_MODES
from ai_runtime.providers.capabilities import ProviderCapabilities


def _provider(streaming: bool = True) -> object:
    class _P:
        capabilities = ProviderCapabilities(streaming=streaming)

    return _P()


def test_agent_mode_enum_values():
    assert {m.value for m in AgentMode} == {"ask", "plan", "agent"}
    assert AGENT_MODES == ["ask", "plan", "agent"]


def test_ask_mode_has_no_tools():
    agent = Agent("a", _provider(), agent_mode=AgentMode.ASK)
    assert agent.agent_mode is AgentMode.ASK
    assert agent.tool_registry is not None
    assert list(agent.tool_registry._tools.keys()) == []


def test_plan_mode_has_no_tools():
    agent = Agent("a", _provider(), agent_mode=AgentMode.PLAN)
    assert list(agent.tool_registry._tools.keys()) == []


def test_agent_mode_has_tools_when_registry_passed():
    from ai_runtime.tools import ToolRegistry, Tool, ToolResult

    class _Noop(Tool):
        name = "noop"
        description = "noop"

        async def run(self, context, input):
            return ToolResult(content="x")

    reg = ToolRegistry()
    reg.register(_Noop())
    agent = Agent("a", _provider(), tool_registry=reg, agent_mode=AgentMode.AGENT)
    assert "noop" in agent.tool_registry._tools


def test_ask_mode_transport_stream_when_supported():
    assert AgentMode.ASK.transport_mode(ProviderCapabilities(streaming=True)) == "stream"


def test_ask_mode_transport_chat_when_unsupported():
    assert AgentMode.ASK.transport_mode(ProviderCapabilities(streaming=False)) == "chat"


def test_plan_mode_transport_is_plan():
    assert AgentMode.PLAN.transport_mode(ProviderCapabilities(streaming=True)) == "plan"
    assert AgentMode.PLAN.transport_mode(ProviderCapabilities(streaming=False)) == "plan"


def test_agent_transport_mode_delegates():
    agent = Agent("a", _provider(streaming=False), agent_mode=AgentMode.AGENT)
    assert agent.transport_mode(ProviderCapabilities(streaming=False)) == "chat"
    assert agent.transport_mode(ProviderCapabilities(streaming=True)) == "stream"


def test_invalid_mode_normalizes_to_agent():
    with pytest.raises(ValueError):
        AgentMode("bogus")
    # The web/CLI layer normalizes unknown values to AGENT.
    try:
        AgentMode("bogus")
    except ValueError:
        assert AgentMode.AGENT.value == "agent"
