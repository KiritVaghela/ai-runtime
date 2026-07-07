
from ai_runtime.providers import (
    ProviderRegistry
) 
from ai_runtime.providers.enums import ProviderType


class Provider1:
    pass


class Provider2:
    pass


def test_override_provider():

    registry = ProviderRegistry()

    registry.register(
        ProviderType.OPENAI,
        Provider1,
    )

    registry.register(
        ProviderType.OPENAI,
        Provider2,
    )

    assert registry.get(
        ProviderType.OPENAI
    ) is Provider2