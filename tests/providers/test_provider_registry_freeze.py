import pytest

from ai_runtime.providers import ProviderRegistry
from ai_runtime.providers.enums import ProviderType


class DummyProvider:

    def __init__(self, config):
        self.config = config

    async def chat(self, request):
        return "ok"

    async def stream(self, request):
        yield "stream"


def test_registry_freeze_prevents_registration():
    registry = ProviderRegistry()
    registry.freeze()

    with pytest.raises(RuntimeError):
        registry.register(ProviderType.OPENAI, DummyProvider)


def test_registry_list_providers_returns_registered_keys():
    registry = ProviderRegistry()
    registry.register(ProviderType.OPENAI, DummyProvider)

    assert registry.list_providers() == [ProviderType.OPENAI]
