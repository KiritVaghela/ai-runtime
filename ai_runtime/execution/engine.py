from collections.abc import AsyncIterator

from ai_runtime.conversation import ChatMessage
from ai_runtime.conversation import ChatRequest, ChatResponse
from ai_runtime.streaming import StreamEvent, TextDeltaEvent

from .context import ExecutionContext


class ExecutionEngine:

    def _prepare_request(
        self,
        context: ExecutionContext,
        message: ChatMessage | ChatRequest,
    ) -> ChatRequest:

        if isinstance(message, ChatMessage):
            context.conversation.add(message)

            return ChatRequest(
                messages=list(context.conversation.messages)
            )

        context.conversation.extend(message.messages)

        return ChatRequest(
            messages=list(context.conversation.messages),
            temperature=message.temperature,
            max_tokens=message.max_tokens,
            stream=message.stream,
        )

    async def chat(
        self,
        context: ExecutionContext,
        message: ChatMessage | ChatRequest,
    ) -> ChatResponse:

        request = self._prepare_request(
            context,
            message,
        )

        response = await context.provider.chat(request)

        context.conversation.add(response.message)

        return response

    async def stream(
        self,
        context: ExecutionContext,
        message: ChatMessage | ChatRequest,
    ) -> AsyncIterator[StreamEvent]:

        request = self._prepare_request(
            context,
            message,
        )

        text = ""

        async for event in context.provider.stream(request):

            if isinstance(event, TextDeltaEvent):
                text += event.delta

            yield event

        context.conversation.add(
            ChatMessage.assistant(text)
        )