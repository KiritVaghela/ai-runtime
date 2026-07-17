from __future__ import annotations

import pytest

from ai_runtime.agents import (
    Agent,
    AgentRunner,
    WorkflowStep,
    WorkflowAgent,
    Route,
    RouterAgent,
    CriticAgent,
    CriticResult,
)
from ai_runtime.conversation import ChatMessage, ChatResponse


class _FakeProvider:
    def __init__(self, text="answer"):
        self._text = text

    async def chat(self, request):
        return ChatResponse(message=ChatMessage(role="assistant", content=self._text))

    async def stream(self, request):
        raise NotImplementedError


def _agent(text="answer"):
    return Agent("a", _FakeProvider(text))


# --- WorkflowAgent ---------------------------------------------------------


@pytest.mark.asyncio
async def test_workflow_runs_dag_in_dependency_order():
    a = _agent("A")
    b = _agent("B")
    c = _agent("C")
    wf = WorkflowAgent(
        "pipeline",
        steps=[
            WorkflowStep(name="first", agent=a),
            WorkflowStep(name="second", agent=b, depends_on=["first"]),
            WorkflowStep(name="third", agent=c, depends_on=["second"]),
        ],
    )
    out = await wf.run("task")
    assert set(out) == {"first", "second", "third"}
    assert out["first"] == "A"


@pytest.mark.asyncio
async def test_workflow_passes_outputs_to_dependents():
    producer = _agent("data-123")
    consumer = _agent("used: data-123")
    wf = WorkflowAgent(
        "pipe",
        steps=[
            WorkflowStep(name="make", agent=producer),
            WorkflowStep(
                name="use",
                agent=consumer,
                depends_on=["make"],
                prompt_template="consume {make}",
            ),
        ],
    )
    out = await wf.run("go")
    assert out["use"] == "used: data-123"


@pytest.mark.asyncio
async def test_workflow_detects_cycle():
    wf = WorkflowAgent(
        "bad",
        steps=[
            WorkflowStep(name="x", agent=_agent(), depends_on=["y"]),
            WorkflowStep(name="y", agent=_agent(), depends_on=["x"]),
        ],
    )
    with pytest.raises(ValueError):
        await wf.run("task")


# --- RouterAgent -----------------------------------------------------------


@pytest.mark.asyncio
async def test_router_keyword_match():
    sql = _agent("sql-answer")
    gen = _agent("gen-answer")
    router = RouterAgent(
        "r",
        routes=[
            Route("sql", sql, keywords=["select", "table"]),
            Route("general", gen, keywords=["hello"]),
        ],
        default_agent=_agent("default"),
    )
    route = await router.route("write a SELECT query on the table")
    assert route is not None and route.name == "sql"


@pytest.mark.asyncio
async def test_router_falls_back_to_default():
    router = RouterAgent(
        "r",
        routes=[Route("sql", _agent(), keywords=["select"])],
        default_agent=_agent("default-answer"),
    )
    resp = await router.run("tell me a joke")
    assert resp.message.content == "default-answer"


# --- CriticAgent -----------------------------------------------------------


@pytest.mark.asyncio
async def test_critic_approves_on_first_try():
    critic = CriticAgent(
        "c",
        actor=_agent("final"),
        validator=lambda task, cand: (True, "looks good"),
        max_iterations=3,
    )
    res = await critic.run("do the thing")
    assert isinstance(res, CriticResult)
    assert res.approved is True
    assert res.iterations == 1


@pytest.mark.asyncio
async def test_critic_retries_until_approved():
    calls = {"n": 0}

    def validator(task, cand):
        calls["n"] += 1
        # Reject the first attempt, approve the second.
        return (calls["n"] >= 2, "needs work" if calls["n"] < 2 else "ok")

    critic = CriticAgent(
        "c",
        actor=_agent("attempt"),
        validator=validator,
        max_iterations=3,
    )
    res = await critic.run("task")
    assert res.approved is True
    assert res.iterations == 2
    assert res.critiques[0] == "needs work"


@pytest.mark.asyncio
async def test_critic_exhausts_iterations():
    critic = CriticAgent(
        "c",
        actor=_agent("bad"),
        validator=lambda task, cand: (False, "never good"),
        max_iterations=2,
    )
    res = await critic.run("task")
    assert res.approved is False
    assert res.iterations == 2
