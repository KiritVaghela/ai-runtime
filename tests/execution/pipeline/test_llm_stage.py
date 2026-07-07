from ai_runtime.conversation import ChatMessage
from ai_runtime.conversation import ChatResponse, Usage


class FakeProvider:

    def __init__(self):
        self.request = None

    async def chat(self, request):
        self.request = request

        return ChatResponse(
            message=ChatMessage.assistant("Hello"),
            usage=Usage(
                prompt_tokens=5,
                completion_tokens=1,
                total_tokens=6,
            ),
        )
    
import pytest

from ai_runtime.execution import ExecutionContext
from ai_runtime.execution.pipeline import (
    LLMStage,
    RequestBuilderStage,
)


@pytest.mark.asyncio
async def test_llm_stage_chat():

    context = ExecutionContext(
        provider=FakeProvider(),
    )

    context.conversation.add(
        ChatMessage.user("Hi")
    )

    context = await RequestBuilderStage().execute(context)

    context = await LLMStage().execute(context)

    assert context.response is not None

    assert context.response.message.content == "Hello"

    
@pytest.mark.asyncio
async def test_provider_request():
    context = ExecutionContext(
        provider=FakeProvider(),
    )

    context.conversation.add(
        ChatMessage.user("Hi")
    )

    context = await RequestBuilderStage().execute(context)

    context = await LLMStage().execute(context)

    assert context.response is not None

    assert context.provider.request.messages[0].content == "Hi"

