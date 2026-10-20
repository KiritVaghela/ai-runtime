import pytest

from ai_runtime import AgentRuntime
from ai_runtime.conversation import ChatMessage, ChatResponse, Usage
from ai_runtime.providers import (
    ProviderCapabilities,
    ProviderConfig,
    ProviderInfo,
    ProviderRegistry,
    SDKInfo,
)
from ai_runtime.providers.enums import ProviderType


class ConversationProvider:
    """Deterministic provider double for conversation-memory behavior."""

    def __init__(self, config: ProviderConfig):
        self.config = config

    @property
    def info(self) -> ProviderInfo:
        return ProviderInfo(
            provider=self.config.provider,
            model=self.config.model,
            sdkInfo=SDKInfo(sdk="fake", version="0.1"),
            capabilities=ProviderCapabilities(chat=True, streaming=False),
        )

    async def chat(self, request):
        has_name = any(
            message.role.value == "user"
            and message.content == "My name is Kirit."
            for message in request.messages
        )
        content = (
            "Your name is Kirit."
            if has_name
            else "I don't know your name yet."
        )
        return ChatResponse(
            message=ChatMessage.assistant(content),
            usage=Usage(prompt_tokens=5, completion_tokens=3, total_tokens=8),
        )


@pytest.mark.asyncio
async def test_session_conversation():
    registry = ProviderRegistry()
    registry.register(ProviderType.GROQ, ConversationProvider)
    runtime = AgentRuntime.from_provider(
        provider=ProviderType.GROQ,
        model="test-model",
        registry=registry,
    )
    session = runtime.create_session()

    await session.chat(ChatMessage.user("My name is Kirit."))
    response = await session.chat(ChatMessage.user("What is my name?"))

    assert "Kirit" in response.message.content
