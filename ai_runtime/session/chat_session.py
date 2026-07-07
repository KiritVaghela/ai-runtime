from collections.abc import AsyncIterator

from ai_runtime.conversation import (
    Conversation,
    ChatMessage,
    ChatRequest,
)
from ai_runtime.streaming.event import StreamEvent
from ai_runtime.streaming.text import TextDeltaEvent
from typing import TypeAlias
Message: TypeAlias = ChatMessage | ChatRequest

class ChatSession:

    def __init__(
        self,
        provider,
        conversation=None,
    ):
        self.provider = provider
        self.conversation = (
            conversation
            or Conversation()
        )

    def _prepare_request(
        self,
        message: Message,
    ) -> ChatRequest:

        if isinstance(message, ChatMessage):
            self.conversation.add(message)

            return ChatRequest(
                messages=list(self.conversation.messages)
            )

        # Caller supplied a ChatRequest.
        # Merge its messages into the session conversation.
        self.conversation.extend(message.messages)

        return ChatRequest(
            messages=list(self.conversation.messages),
            temperature=message.temperature,
            max_tokens=message.max_tokens,
            stream=message.stream,
        )

    async def chat(
        self,
        message: Message,
    ):

        request = self._prepare_request(message)

        response = await self.provider.chat(request)

        self.conversation.add(response.message)

        return response
    
    
    async def stream(
        self,
        message: Message,
    ) -> AsyncIterator[StreamEvent]:

        request = self._prepare_request(message)

        text = ""

        async for event in self.provider.stream(request):

            if isinstance(event, TextDeltaEvent):
                text += event.delta

            yield event

        self.conversation.add(
            ChatMessage.assistant(text)
        )

    def clear(self):
        self.conversation.clear()

