
from ai_runtime.models.enums import ProviderType

from .litellm_provider import LiteLLMProvider
from .registry import ProviderRegistry


def create_default_registry():

    registry = ProviderRegistry()

    registry.register(
        ProviderType.OPENAI,
        LiteLLMProvider,
    )

    registry.register(
        ProviderType.GROQ,
        LiteLLMProvider,
    )

    registry.register(
        ProviderType.ANTHROPIC,
        LiteLLMProvider,
    )

    registry.register(
        ProviderType.GEMINI,
        LiteLLMProvider,
    )

    registry.register(
        ProviderType.OLLAMA,
        LiteLLMProvider,
    )

    return registry