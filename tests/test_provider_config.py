from ai_runtime.models.enums import ProviderType
from ai_runtime.providers import ProviderConfig


def test_provider_config():

    config = ProviderConfig(
        provider=ProviderType.OPENAI,
        model="gpt-4.1"
    )

    assert config.provider == ProviderType.OPENAI
    assert config.model == "gpt-4.1"