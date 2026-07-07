
from ai_runtime.execution import (
    ExecutionContext,
    ExecutionEngine,
)

class Session:

    def __init__(
        self,
        context: ExecutionContext,
        engine: ExecutionEngine,
    ):
        self.context = context
        self.engine = engine

    async def chat(self, input):
        return await self.engine.chat(
            self.context,
            input,
        )

    async def stream(self, input):
        async for event in self.engine.stream(
            self.context,
            input,
        ):
            yield event
    
    def clear(self):
        self.context.conversation.clear()