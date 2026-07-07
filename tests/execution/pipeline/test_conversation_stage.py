import pytest

from ai_runtime.execution import ExecutionContext
from ai_runtime.execution.pipeline import ConversationStage
from ai_runtime.conversation import (
    Conversation,
    ChatMessage,
)


class DummyProvider:
    pass


@pytest.mark.asyncio
async def test_build_request():

    conversation = Conversation()

    conversation.add(
        ChatMessage.user("Hello")
    )

    context = ExecutionContext(
        provider=DummyProvider(),
        conversation=conversation,
    )

    stage = ConversationStage()

    context = await stage.execute(context)

    assert context.request is not None

    assert len(context.request.messages) == 1

    assert context.request.messages[0].content == "Hello"

@pytest.mark.asyncio
async def test_request_is_copy():

    conversation = Conversation()

    conversation.add(
        ChatMessage.user("Hello")
    )

    context = ExecutionContext(
        provider=DummyProvider(),
        conversation=conversation,
    )

    stage = ConversationStage()

    context = await stage.execute(context)

    assert context.request.messages is not conversation.messages