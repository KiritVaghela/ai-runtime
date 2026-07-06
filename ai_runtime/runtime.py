
from ai_runtime.models import ChatRequest, ChatResponse
from ai_runtime.providers.provider import LLMProvider

from ai_runtime.models.enums import ProviderType
from ai_runtime.providers import (
    ProviderConfig,
    ProviderFactory,
)

class AgentRuntime:
    """
    Entry point for the AI Runtime SDK.
    """
    def __init__(self, provider: LLMProvider):
        self.provider = provider

    async def chat(
        self,
        request: ChatRequest,
    ) -> ChatResponse:

        return await self.provider.chat(request)
    
    @classmethod
    def from_provider(
        cls,
        provider: ProviderType,
        model: str,
        api_key: str | None = None,
        base_url: str | None = None,
    ):

        config = ProviderConfig(
            provider=provider,
            model=model,
            api_key=api_key,
            base_url=base_url,
        )

        return cls(
            ProviderFactory.create(config)
        )