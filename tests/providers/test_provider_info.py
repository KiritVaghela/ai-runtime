from ai_runtime.providers import (
    ProviderInfo, 
    SDKInfo,
    ProviderCapabilities,
)

from ai_runtime.models.enums import (
    ProviderType,
)


def test_provider_info():

    info = ProviderInfo(
        provider=ProviderType.OPENAI,
        model="gpt-4.1",
        sdkInfo=SDKInfo(
            sdk="LiteLLM",
            version="1.75.0"
        ),
        capabilities=ProviderCapabilities(),
    )

    assert info.provider == ProviderType.OPENAI

    assert info.model == "gpt-4.1"

    assert info.sdkInfo.sdk == "LiteLLM"