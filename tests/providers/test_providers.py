import os
import pytest
from ai_runtime import AgentRuntime
from ai_runtime.models import ChatMessage, ChatRequest
from ai_runtime.models.enums import ProviderType
from ai_runtime.providers.exceptions import RateLimitError

TEST_PROVIDERS = [
    (
        ProviderType.OPENAI,
        "gpt-4.1-mini",
        "OPENAI_API_KEY",
    ),
    (
        ProviderType.GROQ,
        "groq/llama-3.3-70b-versatile",
        "GROQ_API_KEY",
    ),
]

@pytest.mark.parametrize(
    "provider,model,key",
    TEST_PROVIDERS,
)
@pytest.mark.asyncio
async def test_provider_chat(
    provider,
    model,
    key,
):

    api_key = os.getenv(key)

    if not api_key:
        pytest.skip(f"{key} not configured")

    runtime = AgentRuntime.from_provider(
        provider=provider,
        model=model,
        api_key=api_key,
    )

    try:
        response = await runtime.chat(
            ChatRequest(
                messages=[
                    ChatMessage.user("Say hello")
                ]
            )
        )

        assert response.message.content

    except RateLimitError:
        pytest.skip(f"{key} rate limit exceeded")