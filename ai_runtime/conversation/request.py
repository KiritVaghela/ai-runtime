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

    # Tool specifications forwarded to the provider when the provider
    # advertises `tools` capability. Each entry follows the OpenAI tool
    # schema: {"type": "function", "function": {"name", "description",
    # "parameters"}}.
    tools: list[dict[str, Any]] | None = None

    # Optional structured-output schema. When the provider advertises
    # `structured_output`, this is forwarded as `response_format`.
    response_format: dict[str, Any] | None = None

    # Optional tool-choice control: "auto", "none", "required", or a
    # specific {"type": "function", "function": {"name": ...}}.
    tool_choice: Any | None = None