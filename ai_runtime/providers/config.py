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

    # Reasoning / thinking controls (Codex's model_reasoning_effort,
    # Claude's extended thinking). Forwarded to providers that support it.
    reasoning_effort: str | None = None  # e.g. "low" | "medium" | "high"
    thinking_enabled: bool = False
    thinking_budget_tokens: int | None = None

    @computed_field
    @property
    def litellm_model(self) -> str:
        if "/" in self.model:
            return self.model
        return f"{self.provider.value}/{self.model}"