from pydantic import BaseModel, ConfigDict, computed_field

from .enums import ProviderType


class ProviderConfig(BaseModel):
    """
    Provider configuration.
    """

    model_config = ConfigDict(frozen=True)

    provider: ProviderType

    model: str

    api_key: str | None = None

    base_url: str | None = None

    timeout: float = 60.0

    max_retries: int = 2

    @computed_field
    @property
    def litellm_model(self) -> str:
        if "/" in self.model:
            return self.model
        return f"{self.provider.value}/{self.model}"