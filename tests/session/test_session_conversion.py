
import os
import pytest

from ai_runtime import AgentRuntime
from ai_runtime.models import ChatMessage
from ai_runtime.models.enums import ProviderType    

@pytest.mark.asyncio
async def test_session_conversation():

    runtime = AgentRuntime.from_provider(
        provider=ProviderType.GROQ,
        model="llama-3.3-70b-versatile",
        api_key=os.getenv("GROQ_API_KEY"),
    )

    session = runtime.create_session()

    await session.chat(
        ChatMessage.user(
            "My name is Kirit."
        )
    )

    response = await session.chat(
        ChatMessage.user(
            "What is my name?"
        )
    )

    assert "Kirit" in response.message.content