from collections.abc import AsyncIterator

from ai_runtime.execution import (
    ExecutionContext,
    ExecutionEngine,
)

from ai_runtime.conversation import (
    Conversation,
    ChatMessage,
    ChatRequest,
)
from ai_runtime.streaming import StreamEvent


class ChatSession:

    def __init__(
        self,
        provider,
        conversation=None,
    ):
        self.context = ExecutionContext(
            provider=provider,
            conversation=conversation or Conversation(),
        )

        self.engine = ExecutionEngine()

    @property
    def conversation(self):
        return self.context.conversation

    async def chat(
        self,
        message: ChatMessage | ChatRequest,
    ):
        return await self.engine.chat(
            self.context,
            message,
        )

    async def stream(
        self,
        message: ChatMessage | ChatRequest,
    ) -> AsyncIterator[StreamEvent]:

        async for event in self.engine.stream(
            self.context,
            message,
        ):
            yield event

    def clear(self):
        self.context.conversation.clear()