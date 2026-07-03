from pydantic import BaseModel, ConfigDict

from ai_runtime.models.enums import ProviderType


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