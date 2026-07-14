from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

# Patch the provider before importing the app so no real API key is needed.
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
        from ai_runtime.streaming import (
            TextDeltaEvent,
            CompletedEvent,
            StreamEvent,
        )

        yield TextDeltaEvent(text=self._text)
        yield CompletedEvent()


@pytest.fixture
def client(monkeypatch, tmp_path):
    # Force a fake provider config.
    def fake_config(*args, **kwargs):
        cfg = ProviderConfig(
            provider=ProviderType.OPENAI,
            model="fake",
            api_key="x",
        )
        cfg.provider = ProviderType.OPENAI
        return cfg

    import web.managers as managers

    monkeypatch.setattr(
        managers.Manager, "_build_agent", lambda self, project, sp=None: __import__(
            "ai_runtime.agents", fromlist=["Agent"]
        ).Agent(
            name="fake",
            provider=_FakeProvider(),
            system_prompt=project.as_system_prompt(sp),
            tool_registry=project.tool_registry,
            memory_store=project.memory_store,
        ),
    )
    from web.app import app

    return TestClient(app)


@pytest.mark.asyncio
async def test_health(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_project_session_chat(client):
    p = client.post("/api/projects", json={"root": "/tmp", "name": "demo"})
    assert p.status_code == 200
    s = client.post("/api/sessions", json={"project": "demo"})
    assert s.status_code == 200
    sid = s.json()["session_id"]

    c = client.post("/api/chat", json={"session_id": sid, "message": "hi"})
    assert c.status_code == 200
    assert "hello from web" in c.json()["content"]


@pytest.mark.asyncio
async def test_plan_mode(client):
    client.post("/api/projects", json={"root": "/tmp", "name": "demo2"})
    sid = client.post("/api/sessions", json={"project": "demo2"}).json()["session_id"]
    res = client.post("/api/chat", json={"session_id": sid, "message": "x", "mode": "plan"})
    assert res.status_code == 200
    assert res.json()["mode"] == "plan"


@pytest.mark.asyncio
async def test_permissions_and_tasks(client):
    client.post("/api/projects", json={"root": "/tmp", "name": "demo3"})
    pr = client.post(
        "/api/permissions",
        json={"project": "demo3", "tool": "Bash", "params": "rm *", "decision": "deny"},
    )
    assert pr.status_code == 200

    sid = client.post("/api/sessions", json={"project": "demo3"}).json()["session_id"]
    t = client.post("/api/tasks", json={"session_id": sid, "message": "bg"})
    assert t.status_code == 200
    assert "task_id" in t.json()
