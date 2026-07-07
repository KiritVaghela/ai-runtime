from collections.abc import AsyncIterator

from ai_runtime.conversation import ChatMessage
from ai_runtime.conversation import ChatRequest, ChatResponse
from ai_runtime.streaming import StreamEvent, TextDeltaEvent

from .pipeline import ExecutionPipeline
from .context import ExecutionContext

from ai_runtime.execution.pipeline import (
    ExecutionPipeline,
    RequestBuilderStage,
    LLMStage,
)
from .mode import ExecutionMode
from .event_processor import EventProcessor

class ExecutionEngine:

    def __init__(
        self,
        pipeline: ExecutionPipeline | None = None,
    ):
        self.pipeline = pipeline or self._create_default_pipeline()

    def _create_default_pipeline(self) -> ExecutionPipeline:
        return (
            ExecutionPipeline()
            .add(RequestBuilderStage())
            .add(LLMStage())
        )

    async def chat(
        self,
        context: ExecutionContext,
        message: ChatMessage | ChatRequest,
    ) -> ChatResponse:

        context.mode = ExecutionMode.CHAT

        context.conversation.add(message)

        context = await self.pipeline.execute(context)

        context.conversation.add(
            context.response.message
        )

        return context.response

    async def stream(
        self,
        context: ExecutionContext,
        message: ChatMessage | ChatRequest,
    ) -> AsyncIterator[StreamEvent]:

        context.mode = ExecutionMode.STREAM

        if isinstance(message, ChatMessage):

            context.conversation.add(message)

        elif isinstance(message, ChatRequest):

            context.conversation.extend(
                message.messages
            )

            context.temperature = message.temperature
            context.max_tokens = message.max_tokens
    

        context = await self.pipeline.execute(
            context
        )

        processor = EventProcessor(context)
        
        async for event in context.stream:
            
            processor.process(event)

            yield event

        context.conversation.add(
            ChatMessage.assistant(
                context.assistant_text
            )
        )