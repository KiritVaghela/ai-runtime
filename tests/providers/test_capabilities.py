import pytest

from ai_runtime.providers.capabilities import ProviderCapabilities

from ai_runtime.providers.enums import ProviderType
from ai_runtime.runtime import AgentRuntime
import os

def test_default_capabilities():

    capabilities = ProviderCapabilities()

    assert capabilities.chat is True
    assert capabilities.streaming is True

    assert capabilities.tools is False

    assert capabilities.vision is False


from ai_runtime.providers.capabilities import (
    ProviderCapabilities,
)


def test_custom_capabilities():

    capabilities = ProviderCapabilities(
        tools=True,
        vision=True,
    )

    assert capabilities.tools

    assert capabilities.vision


@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY missing",
)
def test_openai_provider_capabilities():

    runtime = AgentRuntime.from_provider(
        provider=ProviderType.OPENAI,
        model="gpt-4.1-mini",
        api_key=os.getenv("OPENAI_API_KEY")
    )

    assert runtime.provider.info.provider == ProviderType.OPENAI

    assert runtime.provider.info.capabilities.chat

    assert runtime.provider.info.capabilities.streaming