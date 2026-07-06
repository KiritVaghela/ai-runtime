from copy import deepcopy

from pydantic import BaseModel, Field

from ai_runtime.models import ChatMessage


class Conversation(BaseModel):

    messages: list[ChatMessage] = Field(
        default_factory=list
    )

    def add(
        self,
        message: ChatMessage,
    ):

        self.messages.append(message)

    def extend(
        self,
        messages: list[ChatMessage],
    ):

        self.messages.extend(messages)

    def clear(self):

        self.messages.clear()

    def copy(self):

        return deepcopy(self)