from pydantic import BaseModel
from .message import ChatMessage
from .usage import Usage

class ChatResponse(BaseModel):

    message: ChatMessage

    usage: Usage | None = None

    finish_reason: str | None = None

    @classmethod
    def assistant(
        cls,
        text: str,
        usage: Usage | None = None,
        finish_reason: str | None = None,
    ) -> "ChatResponse":
        return cls(
            message=ChatMessage.assistant(text),
            usage=usage,
            finish_reason=finish_reason,
        )