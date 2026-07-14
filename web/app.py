from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import logging

from ai_runtime.agents.subagent import SubAgentSpec
from ai_runtime.server.protocol import serialize_event
from ai_runtime.tools.checkpoints import CheckpointManager

from .config import load_config
from .managers import Manager

logger = logging.getLogger("ai_runtime.web")

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="ai_runtime Web", version="0.1.0")
config = load_config()
manager = Manager(config)

# Basic logging so server errors are visible in the console.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"error": f"{type(exc).__name__}: {exc}"},
    )


from fastapi.responses import JSONResponse  # noqa: E402


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------
class CreateProjectReq(BaseModel):
    root: str
    name: str | None = None


class CreateSessionReq(BaseModel):
    project: str
    system_prompt: str | None = None
    name: str | None = None


class RenameSessionReq(BaseModel):
    name: str


class SetModeReq(BaseModel):
    mode: str


class ChatReq(BaseModel):
    session_id: str
    message: str
    mode: str = "chat"  # chat | plan
    reasoning_effort: str | None = None


class PermissionReq(BaseModel):
    project: str
    tool: str
    params: str = "*"
    decision: str = "allow"


class SubAgentReq(BaseModel):
    session_id: str
    name: str
    task_template: str = "{task}"


class McpReq(BaseModel):
    session_id: str
    command: str
    args: list[str] = []


class ProviderReq(BaseModel):
    provider: str
    model: str
    api_key: str | None = None
    base_url: str | None = None
    reasoning_effort: str | None = None


# ---------------------------------------------------------------------------
# Rate-limit helpers
# ---------------------------------------------------------------------------
def _is_rate_limit(exc: Exception) -> bool:
    """Detect a provider rate-limit error (litellm or mapped runtime error)."""
    from ai_runtime.providers.exceptions import RateLimitError as RuntimeRateLimitError
    from litellm.exceptions import RateLimitError as LiteRateLimitError

    return isinstance(exc, (LiteRateLimitError, RuntimeRateLimitError))


def _rate_limit_payload(session, exc: Exception) -> dict:
    agent = getattr(session, "agent", None)
    provider = getattr(agent, "provider", None)
    model = getattr(provider, "model", None) or manager.config.model
    provider_name = getattr(provider, "provider", None)
    provider_name = getattr(provider_name, "value", None) if provider_name else None
    provider_name = provider_name or manager.config.provider
    return {
        "kind": "rate_limit",
        "provider": provider_name,
        "model": model,
        "error": str(exc),
    }


def _rate_limit_detail(session, exc: Exception) -> str:
    p = _rate_limit_payload(session, exc)
    return f"Rate limit reached for {p['provider']}/{p['model']}: {p['error']}"


def _rate_limit_event(session, exc: Exception) -> dict:
    return {"type": "error", **_rate_limit_payload(session, exc)}


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def index():
    return FileResponse(str(STATIC_DIR / "index.html"))


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------
@app.post("/api/projects")
async def create_project(req: CreateProjectReq):
    proj = manager.create_project(req.root, req.name)
    return {"name": proj.name, "root": proj.root, "instructions": proj.instructions}


@app.get("/api/projects")
async def list_projects():
    return [
        {"name": p.name, "root": p.root, "tools": list(p.tool_registry._tools.keys())}
        for p in manager.projects.values()
    ]


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------
@app.post("/api/sessions")
async def create_session(req: CreateSessionReq):
    session = manager.create_session(req.project, req.system_prompt, req.name)
    return {"session_id": session.id, "project": session.project.name, "name": session.name}


@app.get("/api/sessions")
async def list_sessions():
    # Only show sessions that actually have a message (persisted ones).
    return [
        {
            "session_id": s.id,
            "project": s.project.name,
            "name": s.name,
            "mode": s.mode,
            "reasoning_effort": s.reasoning_effort,
            "thinking_enabled": s.thinking_enabled,
        }
        for s in manager.sessions.values()
        if s.history
    ]


@app.post("/api/sessions/{session_id}/rename")
async def rename_session(session_id: str, req: RenameSessionReq):
    session = manager.rename_session(session_id, req.name)
    if session is None:
        raise HTTPException(404, "session not found")
    return {"session_id": session.id, "name": session.name}


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    deleted = manager.delete_session(session_id)
    if not deleted:
        raise HTTPException(404, "session not found")
    return {"session_id": session_id, "deleted": True}


@app.post("/api/sessions/{session_id}/mode")
async def set_mode(session_id: str, req: SetModeReq):
    session = manager.set_session_mode(session_id, req.mode)
    if session is None:
        raise HTTPException(404, "session not found")
    return {"session_id": session.id, "mode": session.mode}


class SessionSettingsReq(BaseModel):
    reasoning_effort: str | None = None
    thinking_enabled: bool | None = None


@app.post("/api/sessions/{session_id}/settings")
async def set_session_settings(session_id: str, req: SessionSettingsReq):
    session = manager.set_session_settings(
        session_id, req.reasoning_effort, req.thinking_enabled
    )
    if session is None:
        raise HTTPException(404, "session not found")
    return {
        "session_id": session.id,
        "reasoning_effort": session.reasoning_effort,
        "thinking_enabled": session.thinking_enabled,
    }


@app.get("/api/sessions/{session_id}/history")
async def get_history(session_id: str):
    session = manager.get_session(session_id)
    if session is None:
        raise HTTPException(404, "session not found")
    return {"session_id": session.id, "history": session.history}


# ---------------------------------------------------------------------------
# Provider (change LLM backend at runtime)
# ---------------------------------------------------------------------------
@app.get("/api/provider")
async def get_provider():
    return {
        "provider": manager.config.provider,
        "model": manager.config.model,
        "base_url": manager.config.base_url,
        "reasoning_effort": manager.config.reasoning_effort,
        "providers": [p.value for p in __import__(
            "ai_runtime.providers.enums", fromlist=["ProviderType"]
        ).ProviderType],
    }


@app.post("/api/provider")
async def set_provider(req: ProviderReq):
    try:
        manager.set_provider(
            req.provider, req.model, req.api_key, req.base_url, req.reasoning_effort
        )
    except Exception as e:  # noqa: BLE001
        logger.exception("Failed to switch provider")
        raise HTTPException(400, f"Provider switch failed: {type(e).__name__}: {e}")
    return {
        "provider": manager.config.provider,
        "model": manager.config.model,
        "base_url": manager.config.base_url,
    }


# ---------------------------------------------------------------------------
# Chat (non-streaming) + Plan
# ---------------------------------------------------------------------------
@app.post("/api/chat")
async def chat(req: ChatReq):
    session = manager.get_session(req.session_id)
    if session is None:
        logger.warning("Chat request for unknown session %s", req.session_id)
        raise HTTPException(404, "session not found")

    try:
        if req.mode == "plan":
            logger.info("Plan request on session %s", req.session_id)
            plan = await session.runner.plan(req.message)
            return {"mode": "plan", "plan": str(plan)}

        logger.info("Chat request on session %s (mode=%s)", req.session_id, req.mode)
        response = await session.runner.run(req.message)
        session.history.append({"role": "user", "content": req.message})
        session.history.append({"role": "assistant", "content": response.message.content or ""})
        manager._save_session(session)
        return {
            "content": response.message.content or "",
            "finish_reason": response.finish_reason,
            "usage": response.usage.model_dump() if response.usage else None,
        }
    except Exception as e:  # noqa: BLE001
        logger.exception("Chat failed for session %s", req.session_id)
        if _is_rate_limit(e):
            raise HTTPException(
                429,
                _rate_limit_detail(session, e),
            )
        raise HTTPException(500, f"Chat failed: {type(e).__name__}: {e}")


# ---------------------------------------------------------------------------
# Streaming chat over WebSocket
# ---------------------------------------------------------------------------
@app.websocket("/ws/{session_id}")
async def ws_chat(websocket: WebSocket, session_id: str):
    await websocket.accept()
    session = manager.get_session(session_id)
    if session is None:
        await websocket.send_json({"type": "error", "error": "session not found"})
        await websocket.close()
        return

    try:
        while True:
            data = await websocket.receive_json()
            message = data.get("message", "")
            mode = data.get("mode", "chat")

            if mode == "plan":
                # Stream the plan live (markdown text + thinking deltas) so it
                # types out like chat. Effort / thinking / streaming all apply.
                # The plan is parsed during streaming (single LLM call); the final
                # `plan` event swaps the streamed bubble for a clean plan block.
                session.history.append({"role": "user", "content": message})
                try:
                    async for event in session.runner.stream_plan(message):
                        logger.info("[plan][ws] event=%s payload=%s", getattr(event, "type", None), serialize_event(event))
                        await websocket.send_text(serialize_event(event))
                    # The planner parsed the plan during streaming. Echo back
                    # the EXACT text that was streamed (not the reformatted
                    # Plan.__str__) so the final block matches what the user saw.
                    plan_obj = session.runner.last_plan
                    plan_text = session.runner.last_plan_text or (str(plan_obj) if plan_obj else "")
                    logger.info(
                        "[plan][ws] last_plan_text_len=%s fallback_used=%s",
                        len(session.runner.last_plan_text or ""),
                        not bool(session.runner.last_plan_text),
                    )
                    session.history.append({"role": "assistant", "content": plan_text, "plan": True})
                    manager._save_session(session)
                    await websocket.send_json({"type": "plan", "plan": plan_text})
                except Exception as e:  # noqa: BLE001
                    if session.history and session.history[-1].get("role") == "user":
                        session.history.pop()
                    manager._save_session(session)
                    if _is_rate_limit(e):
                        await websocket.send_json(_rate_limit_event(session, e))
                    else:
                        logger.exception("WebSocket plan failed for session %s", session_id)
                        await websocket.send_json({"type": "error", "error": f"{type(e).__name__}: {e}"})
                continue

            # Stream events as they arrive.
            session.history.append({"role": "user", "content": message})
            assistant_text = ""
            try:
                async for event in session.runner.stream(message):
                    await websocket.send_text(serialize_event(event))
                    if getattr(event, "type", None) is not None:
                        etype = event.type.value if hasattr(event.type, "value") else str(event.type)
                        if etype == "text_delta":
                            assistant_text += getattr(event, "delta", "")
                session.history.append({"role": "assistant", "content": assistant_text})
                manager._save_session(session)
                await websocket.send_json({"type": "done"})
            except Exception as e:  # noqa: BLE001
                # Roll back the user message we optimistically appended.
                if session.history and session.history[-1].get("role") == "user":
                    session.history.pop()
                manager._save_session(session)
                if _is_rate_limit(e):
                    await websocket.send_json(_rate_limit_event(session, e))
                else:
                    logger.exception("WebSocket stream failed for session %s", session_id)
                    await websocket.send_json({"type": "error", "error": f"{type(e).__name__}: {e}"})
    except WebSocketDisconnect:
        return
    except Exception as e:  # noqa: BLE001
        logger.exception("WebSocket stream failed for session %s", session_id)
        await websocket.send_json({"type": "error", "error": f"{type(e).__name__}: {e}"})


# ---------------------------------------------------------------------------
# Permissions
# ---------------------------------------------------------------------------
@app.post("/api/permissions")
async def set_permission(req: PermissionReq):
    manager.set_permission_rule(req.project, req.tool, req.params, req.decision)
    return {"ok": True}


# ---------------------------------------------------------------------------
# Sub-agents
# ---------------------------------------------------------------------------
@app.post("/api/subagents")
async def add_subagent(req: SubAgentReq):
    session = manager.get_session(req.session_id)
    if session is None:
        raise HTTPException(404, "session not found")
    # Build a child agent reusing the parent's provider + project tools.
    child = type(session.agent)(
        name=req.name,
        provider=session.agent.provider,
        system_prompt=f"You are {req.name}, a sub-agent.",
        tool_registry=session.project.tool_registry,
        memory_store=session.project.memory_store,
    )
    spec = SubAgentSpec(name=req.name, agent=child, task_template=req.task_template)
    manager.add_subagent(session, spec)
    return {"ok": True, "sub_agents": [s.name for s in session.agent.sub_agents]}


# ---------------------------------------------------------------------------
# Checkpoints (undo)
# ---------------------------------------------------------------------------
@app.post("/api/checkpoints/snapshot")
async def snapshot(req: dict):
    session = manager.get_session(req.get("session_id", ""))
    if session is None:
        raise HTTPException(404, "session not found")
    paths = req.get("paths", [])
    ckpt = session.project.checkpoint_manager.snapshot(paths)
    return {"checkpoint_id": ckpt.id}


@app.post("/api/checkpoints/restore")
async def restore(req: dict):
    session = manager.get_session(req.get("session_id", ""))
    if session is None:
        raise HTTPException(404, "session not found")
    # Re-create checkpoint from id (lightweight: list + restore by id).
    ckpts = session.project.checkpoint_manager.list()
    if req.get("checkpoint_id") not in ckpts:
        raise HTTPException(404, "checkpoint not found")
    # Restore all files in that checkpoint dir.
    from pathlib import Path
    import shutil

    ckpt_dir = Path(session.project.checkpoint_manager._root) / req["checkpoint_id"]
    for backup in ckpt_dir.iterdir():
        # Find the original by matching filename (best-effort).
        for original in Path(session.project.root).rglob(backup.name):
            shutil.copy2(backup, original)
            break
    return {"ok": True}


# ---------------------------------------------------------------------------
# Background tasks
# ---------------------------------------------------------------------------
@app.post("/api/tasks")
async def submit_task(req: dict):
    session = manager.get_session(req.get("session_id", ""))
    if session is None:
        raise HTTPException(404, "session not found")
    message = req.get("message", "")

    async def work():
        resp = await session.runner.run(message)
        return resp.message.content

    task = manager.background.submit(work, metadata={"session": session.id})
    manager.background.start(task)
    return {"task_id": task.id, "status": task.status.value}


@app.get("/api/tasks")
async def list_tasks():
    return [
        {"id": t.id, "status": t.status.value, "result": t.result, "error": t.error}
        for t in manager.background.list()
    ]


# ---------------------------------------------------------------------------
# Commands (slash)
# ---------------------------------------------------------------------------
@app.post("/api/commands/{name}")
async def run_command(name: str, req: dict):
    session = manager.get_session(req.get("session_id", ""))
    if session is None:
        raise HTTPException(404, "session not found")
    if name == "clear":
        session.history.clear()
        session.runner.agent.memory._conversation.messages.clear()
        return {"ok": True}
    if name == "compact":
        # Trigger compaction via the engine pipeline's CompactionStage.
        from ai_runtime.execution.pipeline.compaction_stage import CompactionStage

        await CompactionStage().execute(session.runner.agent.memory._conversation)
        return {"ok": True}
    rendered = session.commands.render(name)
    return {"command": name, "prompt": rendered}


# ---------------------------------------------------------------------------
# MCP
# ---------------------------------------------------------------------------
@app.post("/api/mcp/connect")
async def connect_mcp(req: McpReq):
    session = manager.get_session(req.session_id)
    if session is None:
        raise HTTPException(404, "session not found")
    from ai_runtime.mcp import MCPClient, StdioTransport, register_mcp_tools

    client = MCPClient(StdioTransport(req.command, req.args))
    await client.initialize()
    tools = await register_mcp_tools(session.project.tool_registry, client)
    session.agent.tool_executor = __import__(
        "ai_runtime.tools.guarded_executor", fromlist=["GuardedToolExecutor"]
    ).GuardedToolExecutor(
        __import__("ai_runtime.tools.executor", fromlist=["ToolExecutor"]).ToolExecutor(
            session.project.tool_registry
        ),
        session.project.permission_policy,
    )
    return {"ok": True, "tools": [t.name for t in tools]}


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}
