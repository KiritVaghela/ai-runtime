import pytest

from ai_runtime.conversation import ChatMessage, ChatResponse, Usage
from ai_runtime.execution import ExecutionContext, ExecutionEngine
from ai_runtime.providers.capabilities import ProviderCapabilities
from ai_runtime.providers.enums import ProviderType
from ai_runtime.streaming import (
    CompletedEvent,
    TextDeltaEvent,
    UsageEvent,
)


class EmbeddingProvider:
    """Fake provider supporting chat + embeddings."""

    def __init__(self, config):
        self.config = config

    @property
    def info(self):
        from ai_runtime.providers.provider_info import ProviderInfo
        from ai_runtime.providers.sdk_info import SDKInfo

        return ProviderInfo(
            provider=self.config.provider,
            model=self.config.model,
            sdkInfo=SDKInfo(sdk="fake", version="0.1"),
            capabilities=ProviderCapabilities(
                chat=True,
                embeddings=True,
            ),
        )

    async def chat(self, request):
        return ChatResponse.assistant(
            "Hi there",
            usage=Usage(prompt_tokens=3, completion_tokens=2, total_tokens=5),
            finish_reason="stop",
        )

    async def embed(self, texts, model=None):
        if not self.info.capabilities.embeddings:
            raise NotImplementedError("embeddings not supported")
        return [[0.1, 0.2, 0.3] for _ in texts]


@pytest.mark.asyncio
async def test_provider_embed_forwarded():
    from ai_runtime.providers.config import ProviderConfig

    provider = EmbeddingProvider(
        ProviderConfig(provider=ProviderType.OPENAI, model="text-embedding-3-small")
    )
    vectors = await provider.embed(["hello", "world"])
    assert len(vectors) == 2
    assert len(vectors[0]) == 3


@pytest.mark.asyncio
async def test_provider_embed_not_supported_raises():
    from ai_runtime.providers.config import ProviderConfig

    # Build a provider whose negotiated capabilities disable embeddings.
    provider = EmbeddingProvider(
        ProviderConfig(provider=ProviderType.GROQ, model="llama-3.3-70b-versatile")
    )
    provider.info.capabilities.embeddings = False

    # Patch the property so subsequent reads return the disabled capabilities.
    import types
    disabled = provider.info
    disabled.capabilities.embeddings = False
    type(provider).info = property(lambda self: disabled)

    with pytest.raises(NotImplementedError):
        await provider.embed(["x"])


@pytest.mark.asyncio
async def test_chat_mode_emits_events():
    from ai_runtime.providers.config import ProviderConfig

    context = ExecutionContext(provider=EmbeddingProvider(
        ProviderConfig(provider=ProviderType.OPENAI, model="gpt-4.1")
    ))

    events = []

    def _listener(event):
        events.append(event)

    context.event_bus.subscribe(_listener)

    engine = ExecutionEngine()
    response = await engine.chat(context, ChatMessage.user("Hello"))

    assert response.message.content == "Hi there"
    # Chat mode now emits the same event types as stream mode.
    assert any(isinstance(e, TextDeltaEvent) for e in events)
    assert any(isinstance(e, UsageEvent) for e in events)
    assert any(isinstance(e, CompletedEvent) for e in events)
    # assistant_text accumulated from the synthetic TextDeltaEvent.
    assert context.assistant_text == "Hi there"
