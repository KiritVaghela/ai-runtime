from .config import ProviderConfig


class ProviderFactory:

    @staticmethod
    def create(
        config: ProviderConfig,
    ):
        """
        Provider creation is implemented in Sprint 1.4.
        """
        raise NotImplementedError(
            "No providers registered."
        )