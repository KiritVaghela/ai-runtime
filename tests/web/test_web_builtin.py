from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from ai_runtime.providers import ProviderConfig  # noqa: E402
from ai_runtime.providers.enums import ProviderType  # noqa: E402


class _FakeProvider:
    def __init__(self, text="hello from web"):
        self._text = text

    async def chat(self, request):
        from ai_runtime.conversation import ChatMessage, ChatResponse

        return ChatResponse(message=ChatMessage(role="assistant", content=self._text))

    async def stream(self, request):
        from ai_runtime.conversation import ChatMessage
        from ai_runtime.streaming import TextDeltaEvent, CompletedEvent

        yield TextDeltaEvent(delta=self._text)
        yield CompletedEvent()


@pytest.fixture
def client(monkeypatch, tmp_path):
    def fake_config(*args, **kwargs):
        cfg = ProviderConfig(provider=ProviderType.OPENAI, model="fake", api_key="x")
        cfg.provider = ProviderType.OPENAI
        return cfg

    import web.managers as managers

    monkeypatch.setattr(
        managers.Manager, "_build_agent", lambda self, *args, **kwargs: __import__(
            "ai_runtime.agents", fromlist=["Agent"]
        ).Agent(
            name="fake",
            provider=_FakeProvider(),
            system_prompt=args[0].as_system_prompt(args[1] if len(args) > 1 else None),
            tool_registry=args[0].tool_registry,
            memory_store=args[0].memory_store,
        ),
    )
    from web.app import app

    return TestClient(app)


def _make_session(client, name="demo-builtin"):
    client.post("/api/projects", json={"root": "/tmp", "name": name})
    return client.post("/api/sessions", json={"project": name}).json()["session_id"]


# ---- Catalog endpoints ----------------------------------------------------


@pytest.mark.asyncio
async def test_list_builtin_agents(client):
    res = client.get("/api/builtin/agents")
    assert res.status_code == 200
    keys = {a["key"] for a in res.json()["agents"]}
    assert {"reviewer", "explainer", "tester", "summarizer", "router", "critic"} <= keys


@pytest.mark.asyncio
async def test_list_builtin_skills(client):
    res = client.get("/api/builtin/skills")
    assert res.status_code == 200
    skills = res.json()["skills"]
    assert any(s["name"] == "self_review" for s in skills)
    assert all("category" in s for s in skills)


@pytest.mark.asyncio
async def test_list_builtin_commands(client):
    res = client.get("/api/builtin/commands")
    assert res.status_code == 200
    cmds = res.json()["commands"]
    names = {c["name"] for c in cmds}
    assert {"review", "explain", "test", "workflow", "compact", "context", "clear"} <= names
    assert all("category" in c for c in cmds)


# ---- Run built-in agents --------------------------------------------------


@pytest.mark.asyncio
async def test_run_builtin_specialist_agent(client):
    sid = _make_session(client)
    res = client.post(
        "/api/builtin/agents/run",
        json={"session_id": sid, "agent": "reviewer", "task": "review this"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["agent"] == "reviewer"
    assert "hello from web" in body["output"]


@pytest.mark.asyncio
async def test_run_builtin_router_agent(client):
    sid = _make_session(client)
    res = client.post(
        "/api/builtin/agents/run",
        json={"session_id": sid, "agent": "router", "task": "please review my code"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["agent"] == "router"
    assert "hello from web" in body["output"]


@pytest.mark.asyncio
async def test_run_builtin_critic_agent(client):
    sid = _make_session(client)
    res = client.post(
        "/api/builtin/agents/run",
        json={"session_id": sid, "agent": "critic", "task": "write a function"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["agent"] == "critic"
    assert body["approved"] is True
    assert body["iterations"] >= 1
    assert "hello from web" in body["output"]


@pytest.mark.asyncio
async def test_run_builtin_agent_unknown(client):
    sid = _make_session(client)
    res = client.post(
        "/api/builtin/agents/run",
        json={"session_id": sid, "agent": "nope", "task": "x"},
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_run_builtin_agent_missing_session(client):
    res = client.post(
        "/api/builtin/agents/run",
        json={"session_id": "missing", "agent": "reviewer", "task": "x"},
    )
    assert res.status_code == 404


# ---- Apply skills ----------------------------------------------------------


@pytest.mark.asyncio
async def test_apply_skill(client):
    sid = _make_session(client)
    res = client.post(
        "/api/builtin/skills/apply",
        json={"session_id": sid, "skill": "self_review"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert "self_review" in body["active_skills"]


@pytest.mark.asyncio
async def test_apply_skill_unknown(client):
    sid = _make_session(client)
    res = client.post(
        "/api/builtin/skills/apply",
        json={"session_id": sid, "skill": "nope"},
    )
    assert res.status_code == 404


# ---- Self-review toggle ----------------------------------------------------


@pytest.mark.asyncio
async def test_set_self_review(client):
    sid = _make_session(client)
    res = client.post(
        "/api/builtin/self-review",
        json={"session_id": sid, "enabled": True},
    )
    assert res.status_code == 200
    assert res.json()["self_review"] is True


# ---- Run built-in commands ------------------------------------------------


@pytest.mark.asyncio
async def test_run_builtin_command(client):
    sid = _make_session(client)
    res = client.post(
        "/api/builtin/commands/run",
        json={"session_id": sid, "name": "review", "args": {"diff": "auth.py"}},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["command"] == "review"
    assert "hello from web" in body["output"]
    assert "auth.py" in body["prompt"]


@pytest.mark.asyncio
async def test_run_builtin_command_unknown(client):
    sid = _make_session(client)
    res = client.post(
        "/api/builtin/commands/run",
        json={"session_id": sid, "name": "nope", "args": {}},
    )
    assert res.status_code == 404
