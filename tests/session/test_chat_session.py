import pytest

from ai_runtime.conversation import (
    ChatMessage,
    ChatResponse,
)
from ai_runtime.session import ChatSession


class FakeProvider:

    async def chat(self, request):

        return ChatResponse(
            message=ChatMessage.assistant(
                "Hello"
            )
        )


@pytest.mark.asyncio
async def test_session_updates_history():

    session = ChatSession(
        provider=FakeProvider()
    )

    response = await session.chat(
        ChatMessage.user("Hi")
    )

    assert response.message.content == "Hello"

    assert len(
        session.conversation.messages
    ) == 2