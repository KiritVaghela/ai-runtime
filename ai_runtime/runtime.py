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

from ai_runtime.execution import ExecutionContext
from ai_runtime.execution import ExecutionEngine


class AgentRuntime:

    def __init__(
        self,
        registry: ProviderRegistry | None = None,
    ):
        self.registry = registry or create_default_registry()

    @classmethod
    def from_provider(
        cls,
        provider: ProviderType,
        model: str,
        api_key: str | None = None,
        base_url: str | None = None,
        registry: ProviderRegistry | None = None,
    ) -> "AgentRuntime":

        runtime = cls(registry)

        runtime._config = ProviderConfig(
            provider=provider,
            model=model,
            api_key=api_key,
            base_url=base_url,
        )

        return runtime

    def create_session(self) -> Session:

        provider = self.registry.create(
            self._config
        )

        context = ExecutionContext(
            provider=provider,
        )

        engine = ExecutionEngine()

        return Session(
            context=context,
            engine=engine
        )
    
