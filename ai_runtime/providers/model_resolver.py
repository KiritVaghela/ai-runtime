

from ai_runtime.providers.config import ProviderConfig


class ModelResolver:

    @staticmethod
    def resolve(config: ProviderConfig) -> str:

        if "/" in config.model:
            return config.model

        return f"{config.provider.value}/{config.model}"