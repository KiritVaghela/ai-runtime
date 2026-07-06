
from ai_runtime.providers import (
    ProviderRegistry
)
from ai_runtime.models.enums import ProviderType


class DummyProvider:
    pass


def test_register_provider():
    registry = ProviderRegistry()

    registry.register(
        ProviderType.OPENAI,
        DummyProvider,
    )

    assert registry.get(
        ProviderType.OPENAI
    ) is DummyProvider