from pydantic import BaseModel
from .message import ChatMessage

class ChatRequest(BaseModel):

    messages: list[ChatMessage]

    temperature: float = 0.7

    max_tokens: int | None = None

    stream: bool = False