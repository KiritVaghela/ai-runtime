from pydantic import BaseModel, ConfigDict


class ProviderConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    provider: str

    model: str

    api_key: str | None = None

    base_url: str | None = None

    timeout: float = 60

    max_retries: int = 2