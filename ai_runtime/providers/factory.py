from .config import ProviderConfig
from ai_runtime.providers.litellm_provider import LiteLLMProvider

class ProviderFactory:

    @staticmethod
    def create(config: ProviderConfig):
        return LiteLLMProvider(config)
    