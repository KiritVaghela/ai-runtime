
import os

import pytest

from ai_runtime import AgentRuntime
from ai_runtime.conversation import ( 
    ChatMessage, ChatRequest
)
from ai_runtime.providers.enums import ProviderType
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
        api_key=os.getenv("GROQ_API_KEY"),
    )

    session = runtime.create_session()

    text = ""
    completed = False

    async for event in session.stream(
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

        elif isinstance(event, CompletedEvent):
            completed = True

    assert completed
    assert "Hello" in text

    #
    # Verify session conversation
    #
    assert len(session.context.conversation.messages) == 2

    assert session.context.conversation.messages[0].role.value == "user"
    assert session.context.conversation.messages[0].content == "Reply with exactly: Hello"

    assert session.context.conversation.messages[1].role.value == "assistant"
    assert "Hello" in session.context.conversation.messages[1].content