from ai_runtime.providers.enums import ProviderType
from ai_runtime.providers import (
    ProviderConfig,
    ProviderRegistry,
)
from ai_runtime.providers.default_registry import (
    create_default_registry,
)

from ai_runtime.session import (
     Session
)

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

    def create_session(self) -> Session:
        return Session(
            provider=self.provider,
        )
    
