"""Transport-agnostic server API for embedding ai_runtime in web/desktop/
VS Code/CLI clients (à la Copilot's ACP surface)."""

from .protocol import AgentRequest, AgentResponse, serialize_event, parse_request
from .agent_server import AgentServer

__all__ = [
    "AgentRequest",
    "AgentResponse",
    "serialize_event",
    "parse_request",
    "AgentServer",
]
