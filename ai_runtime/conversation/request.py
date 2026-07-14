from typing import Any

from pydantic import BaseModel
from .message import ChatMessage


class ChatRequest(BaseModel):

    messages: list[ChatMessage]

    temperature: float = 0.7

    max_tokens: int | None = None

    stream: bool = False

    timeout: float | None = None

    # Optional metadata bag for provider-specific or runtime hints.
    metadata: dict[str, Any] = {}

    # Optional declared tool calls. Each entry is a dict with keys
    # like {"tool": "name", "input": {...}, "timeout": 5.0}.
    tool_calls: list[dict] | None = None