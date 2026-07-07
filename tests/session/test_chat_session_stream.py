import pytest

from ai_runtime.conversation import (
    ChatMessage,
    Usage,
)
from ai_runtime.session import Session
from ai_runtime.streaming import (
    CompletedEvent,
    TextDeltaEvent,
    UsageEvent,
)

from ai_runtime.execution import ExecutionContext, ExecutionEngine


class FakeProvider:

    async def stream(self, request):

        yield TextDeltaEvent(delta="Hel")
        yield TextDeltaEvent(delta="lo")
        yield UsageEvent(
            usage=Usage(
                prompt_tokens=10,
                completion_tokens=2,
                total_tokens=12,
            )
        )
        yield CompletedEvent(
            finish_reason="stop"
        )


@pytest.mark.asyncio
async def test_session_stream():

    session = Session(
        context=ExecutionContext(
            provider=FakeProvider(),
        ),
        engine=ExecutionEngine()
    )

    events = []

    async for event in session.stream(
        ChatMessage.user("Say Hello")
    ):
        events.append(event)

    assert len(events) == 4

    assert events[0].delta == "Hel"

    assert events[1].delta == "lo"

    assert len(session.context.conversation.messages) == 2

    assert session.context.conversation.messages[0].content == "Say Hello"

    assert session.context.conversation.messages[1].content == "Hello"