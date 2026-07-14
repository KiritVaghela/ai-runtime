from pydantic import BaseModel
from typing import Any
from .message import ChatMessage, ToolCall
from .usage import Usage

class ChatResponse(BaseModel):

    message: ChatMessage

    usage: Usage | None = None

    finish_reason: str | None = None

    # Raw provider payload, retained for capability-specific extraction
    # (e.g. tool calls that were not normalized onto the message).
    raw: Any | None = None

    @classmethod
    def assistant(
        cls,
        text: str,
        usage: Usage | None = None,
        finish_reason: str | None = None,
        tool_calls: list[ToolCall] | None = None,
        raw: Any | None = None,
    ) -> "ChatResponse":
        return cls(
            message=ChatMessage.assistant(text, tool_calls=tool_calls),
            usage=usage,
            finish_reason=finish_reason,
            raw=raw,
        )