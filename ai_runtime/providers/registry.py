from typing import Type

from .enums import ProviderType
from .config import ProviderConfig
from .exceptions import ProviderNotSupportedError


class ProviderRegistry:
    """
    Registry for provider implementations.
    """

    def __init__(self):
        self._providers: dict[
            ProviderType,
            Type,
        ] = {}

    def register(
        self,
        provider: ProviderType,
        provider_cls: Type,
    ) -> None:
        self._providers[provider] = provider_cls

    def get(
        self,
        provider: ProviderType,
    ) -> Type:

        if provider not in self._providers:
            raise ProviderNotSupportedError(
                f"{provider} is not registered."
            )

        return self._providers[provider]
    
    def create(
        self,
        config: ProviderConfig,
    ):

        provider_cls = self.get(
            config.provider
        )

        return provider_cls(config)