import pytest

from ai_runtime.providers.enums import ProviderType
from ai_runtime.providers.exceptions import ProviderNotSupportedError
from ai_runtime.providers import (
    ProviderRegistry
)


def test_registry_raises_for_unknown_provider():
    registry = ProviderRegistry()

    with pytest.raises(ProviderNotSupportedError):
        registry.get(ProviderType.OPENAI)
