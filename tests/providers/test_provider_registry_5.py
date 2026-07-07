from ai_runtime import AgentRuntime
from ai_runtime.providers.enums import ProviderType
from ai_runtime.providers import (
    ProviderRegistry,
)


class DummyProvider:

    def __init__(self, config):
        self.config = config

    async def chat(self, request):
        return "ok"

    async def stream(self, request):
        yield "stream"


def test_runtime_uses_registry():

    registry = ProviderRegistry()

    registry.register(
        ProviderType.OPENAI,
        DummyProvider,
    )

    runtime = AgentRuntime.from_provider(
        provider=ProviderType.OPENAI,
        model="gpt-4.1",
        registry=registry,
    )

    session = runtime.create_session()

    assert isinstance(
        session.context.provider,
        DummyProvider,
    )