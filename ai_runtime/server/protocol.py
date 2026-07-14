from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, AsyncIterator


@dataclass
class AgentRequest:
    """A transport-agnostic request to the agent runtime server.

    Mirrors the Agent Client Protocol (ACP) / Copilot agent surface: a
    session id, a message, and optional mode/tool overrides. This is the
    wire format used by the stdio and HTTP servers so any client (VS Code,
    CLI, web, desktop) can drive the runtime.
    """

    session_id: str
    message: str
    mode: str = "chat"  # chat | stream | plan
    tools: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResponse:
    """A transport-agnostic response (for non-streaming modes)."""

    session_id: str
    content: str
    finish_reason: str | None = None
    usage: dict[str, Any] | None = None


def serialize_event(event: Any) -> str:
    """Serialize a `StreamEvent` (or dict) to a JSON line for the wire."""
    if hasattr(event, "model_dump"):
        payload = event.model_dump()
    elif isinstance(event, dict):
        payload = event
    else:
        payload = {"type": "unknown", "data": str(event)}
    return json.dumps(payload, default=str)


def parse_request(line: str) -> AgentRequest:
    data = json.loads(line)
    return AgentRequest(
        session_id=data["session_id"],
        message=data["message"],
        mode=data.get("mode", "chat"),
        tools=data.get("tools", []),
        metadata=data.get("metadata", {}),
    )
