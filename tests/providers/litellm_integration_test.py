import os
import pytest

from ai_runtime import AgentRuntime
from ai_runtime.models import ChatMessage, ChatRequest
from ai_runtime.models.enums import ProviderType

from ai_runtime.providers.exceptions import RateLimitError

@pytest.mark.asyncio
async def test_openai_chat():

    runtime = AgentRuntime.from_provider(
        provider=ProviderType.OPENAI,
        model="gpt-4.1-mini",
        api_key=os.getenv("OPENAI_API_KEY"),
    )

    try:
        response = await runtime.chat(
            ChatRequest(
                messages=[
                    ChatMessage.user("Say hello")
                ],
            )
        )
        assert response.message.content
    except RateLimitError:
        pytest.skip("OpenAI rate limit exceeded")