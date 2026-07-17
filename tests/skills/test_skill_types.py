from __future__ import annotations

import pytest

from ai_runtime.skills import (
    Skill,
    SkillRegistry,
    ComposedSkills,
    RetrievalSkill,
    GuardrailSkill,
    GuardrailOutcome,
)
from ai_runtime.rag import Retriever, InMemoryVectorStore, Document


class _FakeRetriever:
    """Minimal async retriever stub for tests."""

    def __init__(self, text="retrieved context"):
        self._text = text

    async def context(self, query: str) -> str:
        return self._text


def test_retrieval_skill_is_a_skill():
    skill = RetrievalSkill(
        name="kb", description="knowledge base", retriever=_FakeRetriever()
    )
    assert isinstance(skill, Skill)
    assert skill.retriever is not None


@pytest.mark.asyncio
async def test_retrieval_skill_context():
    skill = RetrievalSkill(
        name="kb",
        description="kb",
        retriever=_FakeRetriever("RAG hits"),
        retrieval_query_template="search: {task}",
    )
    ctx = await skill.retrieve_context("my task")
    assert ctx == "RAG hits"


def test_guardrail_skill_pass():
    skill = GuardrailSkill(
        name="safe",
        description="safety",
        guardrail=lambda out: (True, "ok"),
    )
    outcome = skill.evaluate("some output")
    assert isinstance(outcome, GuardrailOutcome)
    assert outcome.passed is True


def test_guardrail_skill_reject():
    skill = GuardrailSkill(
        name="no-secrets",
        description="block secrets",
        guardrail=lambda out: (False, "contains a token"),
        on_fail="reject",
    )
    outcome = skill.evaluate("api_key=xyz")
    assert outcome.passed is False
    assert outcome.action == "reject"


def test_guardrail_skill_rewrite():
    skill = GuardrailSkill(
        name="clean",
        description="clean output",
        guardrail=lambda out: (False, "CLEANED"),
        on_fail="rewrite",
    )
    outcome = skill.evaluate("dirty")
    assert outcome.passed is False
    assert outcome.rewritten == "CLEANED"


@pytest.mark.asyncio
async def test_composed_aggregates_retrieval_and_guardrails():
    reg = SkillRegistry()
    reg.register(
        Skill(name="base", description="b", system_prompt="BASE")
    )
    reg.register(
        RetrievalSkill(name="kb", description="kb", retriever=_FakeRetriever("CTX"))
    )
    reg.register(
        GuardrailSkill(
            name="safe", description="s", guardrail=lambda o: (True, "ok")
        )
    )
    composed = reg.compose(["base", "kb", "safe"])
    assert isinstance(composed, ComposedSkills)
    assert len(composed.retrieval_skills) == 1
    assert len(composed.guardrail_skills) == 1
    ctx = await composed.retrieval_context("q")
    assert "CTX" in ctx

    final, failures = composed.apply_guardrails("output")
    assert final == "output"
    assert failures == []
