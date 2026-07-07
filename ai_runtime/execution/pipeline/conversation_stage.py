from ai_runtime.conversation import ChatRequest

from .stage import ExecutionStage


class ConversationStage(
    ExecutionStage
):

    async def execute(
        self,
        context,
    ):

        context.request = ChatRequest(
            messages=list(
                context.conversation.messages
            )
        )

        return context