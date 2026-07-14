import pytest

from ai_runtime import AgentRuntime
from ai_runtime.conversation import (
    ChatMessage,
    ChatResponse,
    Usage,
)
from ai_runtime.providers import (
    ProviderConfig,
    ProviderInfo,
    ProviderRegistry,
    ProviderCapabilities,
    SDKInfo,
)
from ai_runtime.providers.enums import ProviderType
from ai_runtime.streaming import (
    CompletedEvent,
    TextDeltaEvent,
    UsageEvent,
)


class FakeProvider:

    def __init__(self, config: ProviderConfig):
        self.config = config

    @property
    def info(self) -> ProviderInfo:
        return ProviderInfo(
            provider=self.config.provider,
            model=self.config.model,
            sdkInfo=SDKInfo(sdk="fake", version="0.1"),
            capabilities=ProviderCapabilities(
                chat=True,
                streaming=True,
            ),
        )

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
        yield UsageEvent(
            usage=Usage(
                prompt_tokens=5,
                completion_tokens=2,
                total_tokens=7,
            )
        )
        yield CompletedEvent(finish_reason="stop")


class StreamingOnlyProvider:

    def __init__(self, config: ProviderConfig):
        self.config = config

    async def stream(self, request):
        yield TextDeltaEvent(delta="ping")
        yield CompletedEvent(finish_reason="stop")


def _make_runtime(provider_type: ProviderType, provider_cls) -> AgentRuntime:
    registry = ProviderRegistry()
    registry.register(provider_type, provider_cls)

    return AgentRuntime.from_provider(
        provider=provider_type,
        model="test-model",
        registry=registry,
    )


@pytest.mark.asyncio
async def test_openai_provider_double_chat():
    runtime = _make_runtime(ProviderType.OPENAI, FakeProvider)
    session = runtime.create_session()

    response = await session.chat(ChatMessage.user("Hi"))

    assert response.message.content == "Hello"
    assert len(session.context.conversation.messages) == 2
    assert session.context.conversation.messages[0].content == "Hi"
    assert session.context.conversation.messages[1].content == "Hello"


@pytest.mark.asyncio
async def test_openai_provider_double_stream():
    runtime = _make_runtime(ProviderType.OPENAI, FakeProvider)
    session = runtime.create_session()

    events = []
    async for event in session.stream(ChatMessage.user("Hi")):
        events.append(event)

    assert len(events) == 4
    assert isinstance(events[0], TextDeltaEvent)
    assert isinstance(events[1], TextDeltaEvent)
    assert isinstance(events[2], UsageEvent)
    assert isinstance(events[3], CompletedEvent)
    assert session.context.assistant_text == "Hello"
    assert len(session.context.conversation.messages) == 2
    assert session.context.conversation.messages[1].content == "Hello"


@pytest.mark.asyncio
async def test_groq_provider_double_chat():
    runtime = _make_runtime(ProviderType.GROQ, FakeProvider)
    session = runtime.create_session()

    response = await session.chat(ChatMessage.user("Hi"))

    assert response.message.content == "Hello"
    assert session.context.conversation.messages[1].content == "Hello"


@pytest.mark.asyncio
async def test_anthropic_provider_double_stream():
    runtime = _make_runtime(ProviderType.ANTHROPIC, FakeProvider)
    session = runtime.create_session()

    events = []
    async for event in session.stream(ChatMessage.user("Hi")):
        events.append(event)

    assert events[-1].finish_reason == "stop"
    assert session.context.assistant_text == "Hello"


@pytest.mark.asyncio
async def test_streaming_only_provider_double():
    runtime = _make_runtime(ProviderType.OLLAMA, StreamingOnlyProvider)
    session = runtime.create_session()

    events = []
    async for event in session.stream(ChatMessage.user("Hi")):
        events.append(event)

    assert len(events) == 2
    assert events[0].delta == "ping"
    assert isinstance(events[1], CompletedEvent)
    assert session.context.assistant_text == "ping"


@pytest.mark.asyncio
async def test_multiple_providers_share_registry():
    registry = ProviderRegistry()
    registry.register(ProviderType.OPENAI, FakeProvider)
    registry.register(ProviderType.GROQ, FakeProvider)
    registry.register(ProviderType.ANTHROPIC, FakeProvider)

    for provider_type in (
        ProviderType.OPENAI,
        ProviderType.GROQ,
        ProviderType.ANTHROPIC,
    ):
        runtime = AgentRuntime.from_provider(
            provider=provider_type,
            model="test-model",
            registry=registry,
        )
        session = runtime.create_session()
        response = await session.chat(ChatMessage.user("Hi"))
        assert response.message.content == "Hello"
