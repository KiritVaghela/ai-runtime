import pytest

from ai_runtime.conversation import (
    ChatMessage,
    ChatResponse,
)
from ai_runtime.session import Session
from ai_runtime.execution import ExecutionContext, ExecutionEngine

class FakeProvider:

    async def chat(self, request):
        return ChatResponse(
            message=ChatMessage.assistant("Hello")
        )


@pytest.mark.asyncio
async def test_session_updates_history():

    session = Session(
        context=ExecutionContext(
            provider=FakeProvider(),
        ),
        engine=ExecutionEngine()
    )

    response = await session.chat(
        ChatMessage.user("Hi")
    )

    assert response.message.content == "Hello"

    assert len(session.context.conversation.messages) == 2

    assert session.context.conversation.messages[0].role.value == "user"
    assert session.context.conversation.messages[0].content == "Hi"

    assert session.context.conversation.messages[1].role.value == "assistant"
    assert session.context.conversation.messages[1].content == "Hello"