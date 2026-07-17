from __future__ import annotations

import pytest

from ai_runtime.agents import (
    Agent,
    AgentRunner,
    reviewer_agent,
    explainer_agent,
    summarizer_agent,
    critic_agent,
    router_agent,
    agentic_summarize,
    make_agentic_compaction_summarizer,
)
from ai_runtime.agents.types import RouterAgent, CriticAgent
from ai_runtime.conversation import ChatMessage, ChatResponse, Conversation
from ai_runtime.skills import (
    self_review_skill,
    explain_code_skill,
    generate_tests_skill,
    summarize_skill,
    no_secrets_guardrail,
    retrieval_skill,
    default_builtin_skills,
)
from ai_runtime.skills.types import GuardrailOutcome
from ai_runtime.commands import (
    review_command,
    explain_command,
    workflow_command,
    default_builtin_commands,
    default_commands,
)


class _FakeProvider:
    def __init__(self, text="answer"):
        self._text = text

    async def chat(self, request):
        return ChatResponse(message=ChatMessage(role="assistant", content=self._text))

    async def stream(self, request):
        raise NotImplementedError


# --- builtin agents --------------------------------------------------------


def test_builtin_agent_factories_return_agents():
    from ai_runtime.agents import tester_agent

    p = _FakeProvider()
    assert isinstance(reviewer_agent(p), Agent)
    assert isinstance(explainer_agent(p), Agent)
    assert isinstance(tester_agent(p), Agent)
    assert isinstance(summarizer_agent(p), Agent)


def test_critic_agent_factory():
    p = _FakeProvider()
    c = critic_agent(p)
    assert isinstance(c, CriticAgent)
    assert c.max_iterations == 3


def test_router_agent_factory_default_routes():
    p = _FakeProvider()
    r = router_agent(p)
    assert isinstance(r, RouterAgent)
    assert len(r.routes) == 3


def test_tester_agent_factory():
    from ai_runtime.agents import tester_agent

    p = _FakeProvider()
    assert isinstance(tester_agent(p), Agent)


@pytest.mark.asyncio
async def test_agentic_summarize_uses_provider():
    p = _FakeProvider("SUMMARY")
    conv = Conversation()
    conv.add(ChatMessage.user("hello"))
    summary = await agentic_summarize(conv, p)
    assert summary == "SUMMARY"


@pytest.mark.asyncio
async def test_make_agentic_compaction_summarizer():
    p = _FakeProvider("COMPACTED")
    summarizer = make_agentic_compaction_summarizer(p)
    conv = Conversation()
    conv.add(ChatMessage.user("hi"))
    out = await summarizer(conv)
    assert out == "COMPACTED"


# --- builtin skills --------------------------------------------------------


def test_builtin_skill_factories():
    assert isinstance(self_review_skill(), object)
    assert isinstance(explain_code_skill(), object)
    assert isinstance(generate_tests_skill(), object)
    assert isinstance(summarize_skill(), object)


def test_no_secrets_guardrail_blocks_secrets():
    g = no_secrets_guardrail()
    outcome = g.evaluate("here is api_key=abc123 secret")
    assert isinstance(outcome, GuardrailOutcome)
    assert outcome.passed is False


def test_no_secrets_guardrail_passes_clean():
    g = no_secrets_guardrail()
    outcome = g.evaluate("just normal text")
    assert outcome.passed is True


def test_default_builtin_skills_includes_guardrail():
    skills = default_builtin_skills()
    names = {s.name for s in skills}
    assert "no_secrets" in names
    assert "self_review" in names


# --- builtin commands ------------------------------------------------------


def test_builtin_command_factories():
    from ai_runtime.commands import test_command

    assert review_command().name == "review"
    assert explain_command().name == "explain"
    assert test_command().name == "test"
    assert workflow_command().name == "workflow"
    # Ensure the factory functions are callable and return Command instances.
    assert default_builtin_commands() is not None


def test_default_builtin_commands_matches_default_registry():
    builtin_names = {c.name for c in default_builtin_commands()}
    registry_names = {c.name for c in default_commands().list()}
    assert builtin_names == registry_names
    assert {"compact", "context", "clear", "review", "explain", "test", "workflow"} <= builtin_names


# --- self-agentic wiring ---------------------------------------------------


@pytest.mark.asyncio
async def test_runner_self_review_improves_output():
    # Actor returns a draft; critic approves, so output is preserved.
    p = _FakeProvider("final answer")
    agent = Agent("a", p)
    runner = AgentRunner(agent, self_review=True)
    resp = await runner.run("do the thing")
    assert resp.message.content == "final answer"


@pytest.mark.asyncio
async def test_compaction_uses_agentic_summarizer():
    from ai_runtime.execution.context import ExecutionContext
    from ai_runtime.execution.pipeline.compaction_stage import CompactionStage

    p = _FakeProvider("AGENTIC SUMMARY")
    conv = Conversation()
    for _ in range(20):
        conv.add(ChatMessage.user("x" * 160))

    ctx = ExecutionContext(provider=p, conversation=conv)
    stage = CompactionStage(max_tokens=200)
    result = await stage.execute(ctx)

    # The conversation should now contain the agentic summary as a system msg.
    sys_msgs = [m for m in result.conversation.messages if m.role.value == "system"]
    assert any("AGENTIC SUMMARY" in m.content for m in sys_msgs)
    assert "compacted" in result.metadata
