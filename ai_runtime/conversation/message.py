from pydantic import BaseModel, ConfigDict
from .enums import MessageRole
from typing import Any


class ToolCall(BaseModel):
    """A single tool invocation requested by the model."""

    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    arguments: str | dict[str, Any] = ""


class ChatMessage(BaseModel):
    model_config = ConfigDict(frozen=True)

    role: MessageRole
    content: Any

    # Present on assistant messages that request tool execution.
    tool_calls: list[ToolCall] | None = None

    # Present on tool-result messages; links back to the originating call.
    tool_call_id: str | None = None

    @classmethod
    def create(
        cls,
        role: MessageRole,
        content: str,
    ) -> "ChatMessage":
        return cls(
            role=role,
            content=content,
        )

    @classmethod
    def system(cls, content: str) -> "ChatMessage":
        return cls(
            role=MessageRole.SYSTEM,
            content=content,
        )

    @classmethod
    def user(cls, content: str) -> "ChatMessage":
        return cls(
            role=MessageRole.USER,
            content=content,
        )

    @classmethod
    def assistant(
        cls,
        content: str,
        tool_calls: list[ToolCall] | None = None,
    ) -> "ChatMessage":
        return cls(
            role=MessageRole.ASSISTANT,
            content=content,
            tool_calls=tool_calls,
        )

    @classmethod
    def tool(
        cls,
        content: str,
        tool_call_id: str | None = None,
    ) -> "ChatMessage":
        return cls(
            role=MessageRole.TOOL,
            content=content,
            tool_call_id=tool_call_id,
        )