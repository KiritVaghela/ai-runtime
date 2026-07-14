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
        self._locked = False

    def register(
        self,
        provider: ProviderType,
        provider_cls: Type,
    ) -> None:
        if self._locked:
            raise RuntimeError("ProviderRegistry is frozen and cannot be modified.")

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

    def list_providers(self) -> list[ProviderType]:
        return list(self._providers.keys())

    def freeze(self) -> None:
        """Lock the registry so no further provider registration is allowed."""
        self._locked = True

    def discover(self, entry_point_group: str) -> None:
        """Discover provider plugins from setuptools entry points."""
        try:
            from importlib.metadata import entry_points
        except ImportError:
            try:
                from importlib_metadata import entry_points
            except ImportError:
                return

        eps = entry_points(group=entry_point_group)

        for ep in eps:
            provider_cls = ep.load()
            provider_type = getattr(provider_cls, "PROVIDER_TYPE", None)
            if provider_type is None:
                continue

            self.register(provider_type, provider_cls)