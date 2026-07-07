import pytest

from ai_runtime.execution import ExecutionPipeline
from ai_runtime.execution import ExecutionContext
from ai_runtime.execution.pipeline import RequestBuilderStage
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

    stage = RequestBuilderStage()

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

    context = await RequestBuilderStage().execute(context)

    assert context.request.messages is not conversation.messages

@pytest.mark.asyncio
async def test_request_options():

    conversation = Conversation()

    conversation.add(
        ChatMessage.user("Hello")
    )

    context = ExecutionContext(
        provider=DummyProvider(),
        conversation=conversation,
        temperature=0.2,
        max_tokens=100,
        stream=True,
    )

    context = await RequestBuilderStage().execute(context)

    assert context.request.temperature == 0.2

    assert context.request.max_tokens == 100

    assert context.request.stream is True

@pytest.mark.asyncio
async def test_pipeline_builds_request():

    pipeline = (
        ExecutionPipeline()
        .add(RequestBuilderStage())
    )

    context = ExecutionContext(
        provider=DummyProvider(),
    )

    context.conversation.add(
        ChatMessage.user("Hello")
    )

    context = await pipeline.execute(context)

    assert context.request is not None