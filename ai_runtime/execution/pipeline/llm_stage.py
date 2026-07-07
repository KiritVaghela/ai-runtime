from .stage import ExecutionStage
from ..context import ExecutionContext
from ..mode import ExecutionMode

class LLMStage(ExecutionStage):

    async def execute(
        self,
        context: ExecutionContext,
    ):

        if context.request is None:
            raise RuntimeError(
                "RequestBuilderStage must execute first."
            )

        if context.mode == ExecutionMode.CHAT:

            context.response = await context.provider.chat(
                context.request
            )

        else:

            context.stream = context.provider.stream(
                context.request
            )

        return context