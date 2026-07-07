from .context import ExecutionContext

class LLMExecutor:

    async def chat(
        self,
        context: ExecutionContext,
    ):
        return await context.provider.chat(
            context.request
        )