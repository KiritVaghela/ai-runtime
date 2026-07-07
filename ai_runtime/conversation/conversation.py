from copy import deepcopy

from pydantic import BaseModel, Field

from .message import ChatMessage


class Conversation(BaseModel):
    """
    Stores conversation history.
    """

    messages: list[ChatMessage] = Field(
        default_factory=list
    )

    def add(
        self,
        message: ChatMessage,
    ) -> None:
        self.messages.append(message)

    def extend(
        self,
        messages: list[ChatMessage],
    ) -> None:
        self.messages.extend(messages)

    def clear(self) -> None:
        self.messages.clear()

    def copy(self) -> "Conversation":
        return deepcopy(self)