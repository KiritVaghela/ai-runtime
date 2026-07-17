from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse, Response
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

app = FastAPI(title="Forge Web", version="0.1.0")
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
    mode: str = "chat"
    reasoning_effort: str | None = None
    thinking_enabled: bool = False


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


class RegenerateReq(BaseModel):
    session_id: str
    # Index of the user message whose assistant reply should be regenerated.
    # If omitted, the last user message is used.
    user_index: int | None = None
    mode: str = "chat"
    reasoning_effort: str | None = None


class ContinueReq(BaseModel):
    session_id: str
    mode: str = "chat"
    reasoning_effort: str | None = None


class FeedbackReq(BaseModel):
    session_id: str | None = None
    index: int
    feedback: str  # "up" | "down"


class PinReq(BaseModel):
    pinned: bool = True


class ExportReq(BaseModel):
    format: str = "markdown"  # markdown | json


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


def _record_event(turn: list[dict[str, Any]], ev_dict: dict[str, Any], buf: dict[str, str]) -> None:
    """Coalesce streaming deltas into history records, preserving order.

    Consecutive `text_delta` events are merged into one `text` record and
    consecutive `thinking` events into one `thinking` record, so the
    persisted history mirrors what the user saw (including interleaving
    with tool calls).
    """
    t = ev_dict.get("type")
    if t == "text_delta":
        buf["text"] = buf.get("text", "") + ev_dict.get("delta", "")
        if turn and turn[-1].get("type") == "text":
            turn[-1]["content"] = buf["text"]
        else:
            # A fresh assistant turn. Keep any prior versions so the UI can
            # show them with < > arrows (only one regeneration is allowed).
            versions = []
            if turn and turn[-1].get("type") == "text" and turn[-1].get("versions"):
                versions = turn[-1]["versions"]
            turn.append({"type": "text", "content": buf["text"], "versions": versions})
    elif t == "thinking":
        buf["thinking"] = buf.get("thinking", "") + ev_dict.get("delta", "")
        if turn and turn[-1].get("type") == "thinking":
            turn[-1]["content"] = buf["thinking"]
        else:
            turn.append({"type": "thinking", "content": buf["thinking"]})
    elif t in ("completed", "error"):
        # Lifecycle markers — not persisted as content.
        pass
    else:
        turn.append(ev_dict)


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
    session = manager.create_session(
        req.project,
        req.system_prompt,
        req.name,
        mode=req.mode,
        reasoning_effort=req.reasoning_effort,
        thinking_enabled=req.thinking_enabled,
    )
    return {"session_id": session.id, "project": session.project.name, "name": session.name}


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


@app.post("/api/sessions/{session_id}/feedback")
async def set_feedback(session_id: str, req: FeedbackReq):
    session = manager.get_session(session_id)
    if session is None:
        raise HTTPException(404, "session not found")
    if 0 <= req.index < len(session.history):
        session.history[req.index]["feedback"] = req.feedback
        manager._save_session(session)
    return {"ok": True}


@app.post("/api/sessions/{session_id}/pin")
async def pin_session(session_id: str, req: PinReq):
    session = manager.pin_session(session_id, req.pinned)
    if session is None:
        raise HTTPException(404, "session not found")
    return {"session_id": session.id, "pinned": session.pinned}


@app.get("/api/sessions/{session_id}/export")
async def export_session(session_id: str, format: str = "markdown"):
    session = manager.get_session(session_id)
    if session is None:
        raise HTTPException(404, "session not found")
    if format == "json":
        return Response(content=json.dumps(session.history, indent=2), media_type="application/json")
    # Markdown export.
    lines = [f"# {session.name}", ""]
    for e in session.history:
        t = e.get("type")
        if t == "user":
            lines += ["**You:**", e.get("content", ""), ""]
        elif t == "text":
            lines += ["**Forge:**", e.get("content", ""), ""]
        elif t == "plan":
            lines += ["**Plan:**", e.get("content", ""), ""]
        elif t == "thinking":
            lines += ["*Thinking:*", e.get("content", ""), ""]
        elif t == "tool_call":
            for c in e.get("calls", []):
                lines += [f"*Tool call:* `{c.get('name')}`", "```", json.dumps(c.get("arguments", {}), indent=2), "```", ""]
        elif t == "tool_result":
            lines += [f"*Tool result ({e.get('name')}):*", "```", str(e.get("output", e.get("error", ""))), "```", ""]
    md = "\n".join(lines)
    return Response(content=md, media_type="text/markdown")


@app.get("/api/sessions")
async def list_sessions(q: str | None = None):
    # Only show sessions that actually have a message (persisted ones).
    sessions = [
        {
            "session_id": s.id,
            "project": s.project.name,
            "name": s.name,
            "mode": s.mode,
            "reasoning_effort": s.reasoning_effort,
            "thinking_enabled": s.thinking_enabled,
            "pinned": getattr(s, "pinned", False),
        }
        for s in manager.sessions.values()
        if s.history
    ]
    if q:
        ql = q.lower()
        def _matches(s):
            if ql in s["name"].lower():
                return True
            sess = manager.get_session(s["session_id"])
            if not sess:
                return False
            for e in sess.history:
                content = e.get("content") or ""
                if isinstance(content, str) and ql in content.lower():
                    return True
                # tool calls / results carry nested text
                for calls in e.get("calls", []) if isinstance(e, dict) else []:
                    if isinstance(calls, dict) and ql in json.dumps(calls.get("arguments", {}), default=str).lower():
                        return True
                if e.get("output") and isinstance(e.get("output"), str) and ql in e["output"].lower():
                    return True
            return False
        sessions = [s for s in sessions if _matches(s)]
    # Pinned first, then by recency (insertion order).
    sessions.sort(key=lambda s: (not s["pinned"],))
    return sessions


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
        "capabilities": manager.get_provider_capabilities(),
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
            session.history.append({"type": "user", "content": req.message})
            session.history.append({"type": "plan", "content": str(plan)})
            manager._save_session(session)
            return {"mode": "plan", "plan": str(plan)}

        logger.info("Chat request on session %s (mode=%s)", req.session_id, req.mode)
        response = await session.runner.run(req.message)
        session.history.append({"type": "user", "content": req.message})
        session.history.append({"type": "text", "content": response.message.content or ""})
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

    # Track the currently-running generation task so the client can stop it.
    current_task: asyncio.Task | None = None

    async def _stream_turn(prompt: str, mode: str, effort: str | None = None, atts: list | None = None, send_done: bool = True, record_user: bool = True):
        """Stream a single turn, recording events into history. Returns when done.
        When `send_done` is False the caller is responsible for sending the
        terminal `done` event (e.g. to attach regeneration metadata).
        When `record_user` is False the caller has already recorded the user
        message (e.g. during a regeneration, which reuses the existing one).
        """
        nonlocal current_task
        atts = atts or []
        if mode == "plan":
            session.history.append({"type": "user", "content": prompt, "attachments": atts})
            try:
                async def _plan():
                    async for event in session.runner.stream_plan(prompt):
                        await websocket.send_text(serialize_event(event))
                current_task = asyncio.create_task(_plan())
                await current_task
                plan_obj = session.runner.last_plan
                plan_text = session.runner.last_plan_text or (str(plan_obj) if plan_obj else "")
                session.history.append({"type": "plan", "content": plan_text})
                manager._save_session(session)
                await websocket.send_json({"type": "plan", "plan": plan_text})
            except asyncio.CancelledError:
                # Stopped by the user — keep the user message, drop the plan.
                if session.history and session.history[-1].get("type") == "user":
                    session.history.pop()
                manager._save_session(session)
                await websocket.send_json({"type": "stopped"})
                raise
            except Exception as e:  # noqa: BLE001
                if session.history and session.history[-1].get("type") == "user":
                    session.history.pop()
                manager._save_session(session)
                if _is_rate_limit(e):
                    await websocket.send_json(_rate_limit_event(session, e))
                else:
                    logger.exception("WebSocket plan failed for session %s", session_id)
                    await websocket.send_json({"type": "error", "error": f"{type(e).__name__}: {e}"})
            return

        # Chat / tool-loop turn.
        if record_user:
            session.history.append({"type": "user", "content": prompt, "attachments": atts})
        turn: list[dict[str, Any]] = []
        buf: dict[str, str] = {}
        try:
            async def _chat():
                async for event in session.runner.stream(prompt):
                    await websocket.send_text(serialize_event(event))
                    if getattr(event, "type", None) is None:
                        return
                    ev_dict = event.model_dump() if hasattr(event, "model_dump") else {"type": "unknown"}
                    if "type" in ev_dict and hasattr(ev_dict["type"], "value"):
                        ev_dict["type"] = ev_dict["type"].value
                    _record_event(turn, ev_dict, buf)
            current_task = asyncio.create_task(_chat())
            await current_task
            session.history.extend(turn)
            manager._save_session(session)
            if send_done:
                await websocket.send_json({"type": "done"})
        except asyncio.CancelledError:
            # Stopped mid-stream: keep what we have, persist partial turn.
            session.history.extend(turn)
            manager._save_session(session)
            await websocket.send_json({"type": "stopped"})
            raise
        except Exception as e:  # noqa: BLE001
            if session.history and session.history[-1].get("type") == "user":
                session.history.pop()
            manager._save_session(session)
            if _is_rate_limit(e):
                await websocket.send_json(_rate_limit_event(session, e))
            else:
                logger.exception("WebSocket stream failed for session %s", session_id)
                await websocket.send_json({"type": "error", "error": f"{type(e).__name__}: {e}"})

    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action", "send")
            message = data.get("message", "")
            mode = data.get("mode", "chat")
            effort = data.get("reasoning_effort", None)
            attachments = data.get("attachments", []) or []

            if action == "stop":
                if current_task and not current_task.done():
                    current_task.cancel()
                continue

            if action == "regenerate":
                # Re-generate the last assistant reply IN PLACE (no new bubble).
                # Each regeneration is appended as a new version so the user can
                # navigate between responses with < > arrows. Find the last
                # assistant text entry and the user entry that precedes it.
                last_text = None
                last_user = None
                for i in range(len(session.history) - 1, -1, -1):
                    if session.history[i].get("type") == "text":
                        last_text = i
                        break
                if last_text is None:
                    await websocket.send_json({"type": "error", "error": "nothing to regenerate"})
                    continue
                for i in range(last_text - 1, -1, -1):
                    if _is_user_entry(session.history[i]):
                        last_user = i
                        break
                if last_user is None:
                    await websocket.send_json({"type": "error", "error": "nothing to regenerate"})
                    continue
                # Stash the current response as a version, then re-stream.
                prev = session.history[last_text]
                versions = list(prev.get("versions") or [])
                versions.append({"content": prev.get("content", ""), "feedback": prev.get("feedback")})
                session.history = session.history[: last_text]  # drop the old text entry
                manager._save_session(session)
                prompt = session.history[last_user]["content"]
                # _stream_turn appends a new text entry; mark it as regenerated
                # and carry the prior versions so the client can switch.
                _regen_versions = versions  # captured for the post-stream patch
                await _stream_turn(prompt, mode, effort, attachments, send_done=False, record_user=False)
                # Patch the just-appended text entry with version metadata.
                if session.history and session.history[-1].get("type") == "text":
                    session.history[-1]["versions"] = _regen_versions
                    session.history[-1]["regenerated"] = True
                    session.history[-1]["version_index"] = len(_regen_versions)  # show latest
                manager._save_session(session)
                # Tell the client which bubble to update in place (no new bubble)
                # and hand back the full version list so it can render the < > nav.
                await websocket.send_json({
                    "type": "done",
                    "_action": "regenerate",
                    "_target": last_text,
                    "versions": _regen_versions,
                    "version_index": len(_regen_versions),
                })
                continue

            if action == "continue":
                # Resume the last (truncated) assistant turn.
                prompt = message or _last_user_content(session.history)
                if not prompt:
                    await websocket.send_json({"type": "error", "error": "nothing to continue"})
                    continue
                await _stream_turn(prompt, mode, effort, attachments)
                continue

            # Default: normal send.
            await _stream_turn(message, mode, effort, attachments)
    except WebSocketDisconnect:
        if current_task and not current_task.done():
            current_task.cancel()
        return
    except Exception as e:  # noqa: BLE001
        logger.exception("WebSocket stream failed for session %s", session_id)
        try:
            await websocket.send_json({"type": "error", "error": f"{type(e).__name__}: {e}"})
        except Exception:
            pass


def _is_user_entry(entry: dict[str, Any]) -> bool:
    """A history entry counts as a user turn in either the new `type`-based
    schema or the legacy `role`-based schema."""
    if not isinstance(entry, dict):
        return False
    if entry.get("type") == "user":
        return True
    return entry.get("role") == "user"


def _last_user_content(history: list[dict[str, Any]]) -> str:
    for i in range(len(history) - 1, -1, -1):
        if _is_user_entry(history[i]):
            return history[i].get("content", "")
    return ""


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
    if name == "context":
        # Produce a real context-window breakdown instead of echoing the
        # prompt. Count messages + estimated tokens and compare against
        # the session's token budget. Also break messages down by *type*
        # (system / user / assistant / tool calls / tool results / MCP
        # results) so the user can see exactly what is consuming context.
        from ai_runtime.context.window import ContextWindow, estimate_tokens
        from ai_runtime.mcp.adapter import MCPTool

        conversation = session.runner.agent.memory._conversation
        window = ContextWindow(conversation=conversation)
        msgs = conversation.messages

        # Map tool_call_id -> tool name so we can classify tool-result
        # messages as regular tools vs MCP-backed tools.
        tool_name_by_call_id: dict[str, str] = {}
        for m in msgs:
            if getattr(m.role, "value", None) == "assistant" and getattr(
                m, "tool_calls", None
            ):
                for tc in m.tool_calls:
                    tool_name_by_call_id[tc.id] = tc.name

        # Collect the set of tool names that are backed by an MCP server.
        registry = getattr(session.runner.agent, "tool_registry", None)
        mcp_tool_names: set[str] = set()
        if registry is not None:
            for tname, tool in registry._tools.items():
                if isinstance(tool, MCPTool):
                    mcp_tool_names.add(tname)

        by_role: dict[str, int] = {}
        tokens_by_role: dict[str, int] = {}
        by_type: dict[str, int] = {}
        tokens_by_type: dict[str, int] = {}
        for m in msgs:
            role = getattr(m.role, "value", str(m.role))
            by_role[role] = by_role.get(role, 0) + 1
            tok = window.estimator(str(getattr(m, "content", "")))
            tokens_by_role[role] = tokens_by_role.get(role, 0) + tok

            # Classify the message into a finer-grained type.
            if role == "system":
                t = "system"
            elif role == "user":
                t = "user"
            elif role == "assistant":
                t = "tool_call" if getattr(m, "tool_calls", None) else "assistant"
            elif role == "tool":
                name = tool_name_by_call_id.get(getattr(m, "tool_call_id", None))
                t = "mcp" if (name and name in mcp_tool_names) else "tool"
            else:
                t = role
            by_type[t] = by_type.get(t, 0) + 1
            tokens_by_type[t] = tokens_by_type.get(t, 0) + tok

        tokens = window.token_count()
        breakdown = {
            "messages": len(msgs),
            "by_role": by_role,
            "tokens_by_role": tokens_by_role,
            "by_type": by_type,
            "tokens_by_type": tokens_by_type,
            "estimated_tokens": tokens,
            "max_tokens": window.max_tokens,
            "over_budget": window.is_over_budget(),
            "utilization_pct": round(100 * tokens / max(1, window.max_tokens), 1),
        }
        return {"command": "context", "breakdown": breakdown}
    if name == "compact":
        # Trigger compaction via the engine pipeline's CompactionStage and
        # report the token usage before/after so the user can see how much
        # space was freed.
        from ai_runtime.context.window import ContextWindow
        from ai_runtime.execution.context import ExecutionContext
        from ai_runtime.execution.pipeline.compaction_stage import CompactionStage

        conversation = session.runner.agent.memory._conversation
        provider = getattr(session.runner.agent, "provider", None)

        window = ContextWindow(conversation=conversation)
        before_tokens = window.token_count()
        messages_before = len(conversation.messages)

        ctx = await CompactionStage().execute(
            ExecutionContext(provider=provider, conversation=conversation)
        )
        # Apply the compacted conversation back to the session so the change
        # actually persists for subsequent turns.
        session.runner.agent.memory._conversation = ctx.conversation

        after_tokens = window.token_count()
        messages_after = len(ctx.conversation.messages)
        return {
            "ok": True,
            "before_tokens": before_tokens,
            "after_tokens": after_tokens,
            "max_tokens": window.max_tokens,
            "messages_before": messages_before,
            "messages_after": messages_after,
            "freed_tokens": max(0, before_tokens - after_tokens),
        }
    # Agentic commands (review/explain/test/workflow) take free-form text
    # after the command name; bind it to the command's first template arg
    # (e.g. `diff` for /review) and run it through the session runner so
    # the model actually produces a result.
    cmd = session.commands.get(name)
    if cmd is None:
        raise HTTPException(404, f"Unknown command: {name}")
    arg_text = (req.get("text") or "").strip()
    if not arg_text and cmd.args:
        # Fall back to any text the user typed after "/name ".
        raw = req.get("raw", "")
        if raw.startswith("/"):
            arg_text = raw.split(" ", 1)[1] if " " in raw else ""
    if cmd.args and arg_text:
        # Bind the free-text to the LAST template arg (the snippet/task);
        # earlier args get a generic default so placeholders still render.
        args = {a: "the provided input" for a in cmd.args[:-1]}
        args[cmd.args[-1]] = arg_text
        result = await manager.run_builtin_command(session, name, args)
        return result
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


# ---------------------------------------------------------------------------
# Built-in agents / skills / commands (v0.8.1)
# ---------------------------------------------------------------------------
class BuiltinAgentReq(BaseModel):
    session_id: str
    agent: str  # reviewer | explainer | tester | summarizer | router | critic
    task: str


class BuiltinCommandReq(BaseModel):
    session_id: str
    name: str
    args: dict[str, Any] = {}


class SkillReq(BaseModel):
    session_id: str
    skill: str


class SelfReviewReq(BaseModel):
    session_id: str
    enabled: bool = True


@app.get("/api/builtin/agents")
async def list_builtin_agents():
    return {"agents": manager.list_builtin_agents()}


@app.get("/api/builtin/skills")
async def list_builtin_skills():
    return {"skills": manager.list_builtin_skills()}


@app.get("/api/builtin/commands")
async def list_builtin_commands():
    return {"commands": manager.list_builtin_commands()}


@app.post("/api/builtin/agents/run")
async def run_builtin_agent(req: BuiltinAgentReq):
    session = manager.get_session(req.session_id)
    if session is None:
        raise HTTPException(404, "session not found")
    try:
        result = await manager.run_builtin_agent(session, req.agent, req.task)
    except KeyError as e:
        raise HTTPException(404, str(e))
    except Exception as e:  # noqa: BLE001
        logger.exception("Built-in agent run failed")
        raise HTTPException(500, f"Built-in agent failed: {type(e).__name__}: {e}")
    return result


@app.post("/api/builtin/commands/run")
async def run_builtin_command(req: BuiltinCommandReq):
    session = manager.get_session(req.session_id)
    if session is None:
        raise HTTPException(404, "session not found")
    try:
        result = await manager.run_builtin_command(session, req.name, req.args)
    except KeyError as e:
        raise HTTPException(404, str(e))
    except Exception as e:  # noqa: BLE001
        logger.exception("Built-in command run failed")
        raise HTTPException(500, f"Built-in command failed: {type(e).__name__}: {e}")
    return result


@app.post("/api/builtin/skills/apply")
async def apply_skill(req: SkillReq):
    session = manager.get_session(req.session_id)
    if session is None:
        raise HTTPException(404, "session not found")
    try:
        return manager.apply_skill(session, req.skill)
    except KeyError as e:
        raise HTTPException(404, str(e))


@app.post("/api/builtin/self-review")
async def set_self_review(req: SelfReviewReq):
    session = manager.get_session(req.session_id)
    if session is None:
        raise HTTPException(404, "session not found")
    return manager.set_self_review(session, req.enabled)
