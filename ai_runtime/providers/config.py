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

    @classmethod
    def from_env(
        cls,
        provider_env: str = "COPILOT_PROVIDER_TYPE",
        base_url_env: str = "COPILOT_PROVIDER_BASE_URL",
        api_key_env: str = "COPILOT_PROVIDER_API_KEY",
        model_env: str = "COPILOT_MODEL",
        default_model: str = "local-model",
    ) -> "ProviderConfig":
        """Build a config from BYO-provider env vars (à la Copilot CLI).

        Reads `COPILOT_PROVIDER_TYPE` (openai/azure/anthropic), the base URL,
        API key, and model. Works with Ollama, vLLM, or any OpenAI-compatible
        endpoint. Falls back to a sensible local default when unset.
        """
        import os

        provider = os.getenv(provider_env, "openai")
        base_url = os.getenv(base_url_env)
        api_key = os.getenv(api_key_env, "not-needed")
        model = os.getenv(model_env, default_model)
        # LiteLLM expects the provider prefix for non-openai base URLs.
        litellm_model = model if "/" in model else f"{provider}/{model}"
        return cls(
            provider=ProviderType(provider),
            model=litellm_model,
            api_key=api_key,
            base_url=base_url,
        )