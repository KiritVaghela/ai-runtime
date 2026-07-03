from .provider import Provider
from .config import ProviderConfig

class ProviderFactory:

    @staticmethod
    def create(
        config: ProviderConfig
    ) -> Provider:
        ...