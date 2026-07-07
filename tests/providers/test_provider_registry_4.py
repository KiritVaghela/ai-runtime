
from ai_runtime.providers.enums import ProviderType
from ai_runtime.providers import (
    ProviderConfig,
    ProviderRegistry
)

class DummyProvider:

    def __init__(self, config):
        self.config = config


def test_registry_creates_registered_provider():

    registry = ProviderRegistry()

    registry.register(
        ProviderType.OPENAI,
        DummyProvider,
    )

    provider = registry.create(
        ProviderConfig(
            provider=ProviderType.OPENAI,
            model="gpt-4.1",
        )
    )

    assert isinstance(
        provider,
        DummyProvider,
    )