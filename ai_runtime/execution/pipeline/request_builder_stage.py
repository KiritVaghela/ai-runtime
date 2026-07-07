from ai_runtime.conversation import ChatRequest

from .stage import ExecutionStage
from ..mode import ExecutionMode
from ..context import ExecutionContext
from ...conversation import ChatMessage

class RequestBuilderStage(ExecutionStage):
    """
    Builds a ChatRequest from the current ExecutionContext.
    """

    async def execute(
        self,
        context: ExecutionContext,
    ):

        context.request = ChatRequest(
            messages=list(
                context.conversation.messages
            ),
            temperature=context.temperature,
            max_tokens=context.max_tokens,
            stream=context.mode == ExecutionMode.STREAM,
        )

        return context