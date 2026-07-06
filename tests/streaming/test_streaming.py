
import os

import pytest

from ai_runtime import AgentRuntime
from ai_runtime.models import ChatMessage
from ai_runtime.models import ChatRequest
from ai_runtime.models.enums import ProviderType
from ai_runtime.streaming import (
    CompletedEvent,
    TextDeltaEvent,
)


@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.getenv("GROQ_API_KEY"),
    reason="GROQ_API_KEY missing",
)
async def test_stream():

    runtime = AgentRuntime.from_provider(
        provider=ProviderType.GROQ,
        model="llama-3.3-70b-versatile",
        api_key=os.getenv("GROQ_API_KEY")
    )

    text = ""

    completed = False

    async for event in runtime.stream(
        ChatRequest(
            messages=[
                ChatMessage.user(
                    "Reply with exactly: Hello"
                )
            ]
        )
    ):

        if isinstance(event, TextDeltaEvent):
            text += event.delta

        if isinstance(event, CompletedEvent):
            completed = True

    assert completed
    assert "Hello" in text