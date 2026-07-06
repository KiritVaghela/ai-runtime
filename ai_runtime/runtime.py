from ai_runtime.models.enums import ProviderType
from ai_runtime.providers import (
    ProviderConfig,
    ProviderRegistry,
)
from ai_runtime.providers.default_registry import (
    create_default_registry,
)
from ai_runtime.models import (
    ChatRequest,
    ChatResponse,
)
from ai_runtime.streaming import StreamEvent

from collections.abc import AsyncIterator


class AgentRuntime:

    def __init__(self, provider):
        self.provider = provider

    @classmethod
    def from_provider(
        cls,
        provider: ProviderType,
        model: str,
        api_key: str | None = None,
        base_url: str | None = None,
        registry: ProviderRegistry | None = None,
    ) -> "AgentRuntime":

        config = ProviderConfig(
            provider=provider,
            model=model,
            api_key=api_key,
            base_url=base_url,
        )

        registry = registry or create_default_registry()

        provider = registry.create(config)

        return cls(provider)

    async def chat(
        self,
        request: ChatRequest,
    ) -> ChatResponse:

        return await self.provider.chat(request)

    async def stream(
        self,
        request: ChatRequest,
    ) -> AsyncIterator[StreamEvent]:

        async for event in self.provider.stream(request):
            yield event
    
