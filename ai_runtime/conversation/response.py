from pydantic import BaseModel
from .message import ChatMessage
from .usage import Usage

class ChatResponse(BaseModel):

    message: ChatMessage

    usage: Usage | None = None

    finish_reason: str | None = None