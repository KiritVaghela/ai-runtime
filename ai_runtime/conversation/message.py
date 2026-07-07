from pydantic import BaseModel, ConfigDict
from .enums import MessageRole
from typing import Any

class ChatMessage(BaseModel):
    model_config = ConfigDict(frozen=True)

    role: MessageRole
    content: Any

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
    def assistant(cls, content: str) -> "ChatMessage":
        return cls(
            role=MessageRole.ASSISTANT,
            content=content,
        )

    @classmethod
    def tool(cls, content: str) -> "ChatMessage":
        return cls(
            role=MessageRole.TOOL,
            content=content,
        )