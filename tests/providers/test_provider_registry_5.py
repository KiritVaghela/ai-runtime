import pytest

from ai_runtime import AgentRuntime
from ai_runtime.conversation import (
    ChatMessage,
    ChatResponse,
    Usage,
)
from ai_runtime.streaming import (
    CompletedEvent,
    TextDeltaEvent,
)
from ai_runtime.providers.enums import ProviderType
from ai_runtime.providers import (
    ProviderRegistry,
)


class DummyProvider:

    def __init__(self, config):
        self.config = config

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
        yield TextDeltaEvent(delta="He")
        yield TextDeltaEvent(delta="llo")
        yield CompletedEvent(finish_reason="stop")


def test_runtime_uses_registry():

    registry = ProviderRegistry()

    registry.register(
        ProviderType.OPENAI,
        DummyProvider,
    )

    runtime = AgentRuntime.from_provider(
        provider=ProviderType.OPENAI,
        model="gpt-4.1",
        registry=registry,
    )

    session = runtime.create_session()

    assert isinstance(
        session.context.provider,
        DummyProvider,
    )


@pytest.mark.asyncio
async def test_session_chat_with_registered_provider():

    registry = ProviderRegistry()
    registry.register(ProviderType.OPENAI, DummyProvider)

    runtime = AgentRuntime.from_provider(
        provider=ProviderType.OPENAI,
        model="gpt-4.1",
        registry=registry,
    )

    session = runtime.create_session()

    response = await session.chat(
        ChatMessage.user("Hi"),
    )

    assert response.message.content == "Hello"
    assert len(session.context.conversation.messages) == 2
    assert session.context.conversation.messages[0].content == "Hi"
    assert session.context.conversation.messages[1].content == "Hello"


@pytest.mark.asyncio
async def test_session_stream_with_registered_provider():

    registry = ProviderRegistry()
    registry.register(ProviderType.OPENAI, DummyProvider)

    runtime = AgentRuntime.from_provider(
        provider=ProviderType.OPENAI,
        model="gpt-4.1",
        registry=registry,
    )

    session = runtime.create_session()

    events = []

    async for event in session.stream(
        ChatMessage.user("Hi"),
    ):
        events.append(event)

    assert len(events) == 3
    assert isinstance(events[0], TextDeltaEvent)
    assert isinstance(events[1], TextDeltaEvent)
    assert isinstance(events[2], CompletedEvent)
    assert session.context.assistant_text == "Hello"
    assert len(session.context.conversation.messages) == 2
    assert session.context.conversation.messages[1].content == "Hello"
