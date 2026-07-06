from ai_runtime.providers.default_registry import (
    create_default_registry,
)
from ai_runtime.models.enums import ProviderType


def test_default_registry():

    registry = create_default_registry()

    provider = registry.get(
        ProviderType.OPENAI
    )

    assert provider is not None