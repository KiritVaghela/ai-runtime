import pytest

from ai_runtime.execution import ExecutionContext, ExecutionEngine
 
from ai_runtime.conversation import ChatMessage, ChatResponse, Usage
from ai_runtime.streaming import (
    CompletedEvent,
    TextDeltaEvent,
)


from ai_runtime.streaming.text import TextDeltaEvent

class FakeProvider:

    async def chat(self, request):
        return ChatResponse(
            message=ChatMessage.assistant("Hello"),
            usage=Usage(
                prompt_tokens=5,
                completion_tokens=1,
                total_tokens=6,
            ),
        )

    async def stream(self, request):
        yield TextDeltaEvent(delta="Hel")
        yield TextDeltaEvent(delta="lo")
        yield CompletedEvent(finish_reason="stop")

@pytest.mark.asyncio
async def test_engine_chat():

    context = ExecutionContext(
        provider=FakeProvider(),
    )

    engine = ExecutionEngine()

    response = await engine.chat(
        context,
        ChatMessage.user("Hi"),
    )

    assert response.message.content == "Hello"

    assert len(context.conversation.messages) == 2

    assert context.conversation.messages[0].content == "Hi"

    assert context.conversation.messages[1].content == "Hello"


@pytest.mark.asyncio
async def test_engine_stream():

    context = ExecutionContext(
        provider=FakeProvider(),
    )

    engine = ExecutionEngine()

    received_events = []

    async for event in engine.stream(
        context,
        ChatMessage.user("Hi"),
    ):
        received_events.append(event)

    #
    # Verify streamed events
    #
    assert len(received_events) == 3

    assert isinstance(received_events[0], TextDeltaEvent)
    assert isinstance(received_events[1], TextDeltaEvent)
    assert isinstance(received_events[2], CompletedEvent)

    #
    # Verify accumulated assistant message
    #
    assert context.assistant_text == "Hello"

    #
    # Verify conversation history
    #
    assert len(context.conversation.messages) == 2

    assert context.conversation.messages[0].role == "user"
    assert context.conversation.messages[0].content == "Hi"

    assert context.conversation.messages[1].role == "assistant"
    assert context.conversation.messages[1].content == "Hello"