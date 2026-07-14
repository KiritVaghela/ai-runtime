import asyncio
from collections.abc import AsyncIterator

from ai_runtime.conversation import ChatMessage
from ai_runtime.conversation import ChatRequest, ChatResponse
from ai_runtime.streaming import StreamEvent, ErrorEvent

from .pipeline import ExecutionPipeline
from .context import ExecutionContext

from ai_runtime.execution.pipeline import (
    ExecutionPipeline,
    RequestBuilderStage,
    LLMStage,
    ToolLoopStage,
)
from ai_runtime.execution.pipeline.planner_stage import PlannerStage
from ai_runtime.execution.pipeline.supervisor_stage import SupervisorStage
from ai_runtime.execution.pipeline.compaction_stage import CompactionStage
from ai_runtime.execution.pipeline.memory_consolidation_stage import (
    MemoryConsolidationStage,
)
from .mode import ExecutionMode
from .event_processor import EventProcessor
from .plan import Plan

class ExecutionEngine:

    def __init__(
        self,
        pipeline: ExecutionPipeline | None = None,
    ):
        self.pipeline = pipeline or self._create_default_pipeline()

    def _create_default_pipeline(self) -> ExecutionPipeline:
        return (
            ExecutionPipeline()
            .add(CompactionStage())
            .add(RequestBuilderStage())
            .add(SupervisorStage())
            .add(LLMStage())
            .add(ToolLoopStage())
            .add(MemoryConsolidationStage())
        )

    async def chat(
        self,
        context: ExecutionContext,
        message: ChatMessage | ChatRequest,
    ) -> ChatResponse:

        context.mode = ExecutionMode.CHAT

        context.conversation.add(message)

        context = await self.pipeline.execute(context)

        # Emit equivalent stream events so subscribers are uniform across
        # chat and stream modes.
        EventProcessor(context).process_response(context.response)

        context.conversation.add(
            context.response.message
        )

        return context.response

    async def plan(
        self,
        context: ExecutionContext,
        message: ChatMessage | ChatRequest,
    ) -> Plan:
        """Produce a reviewable plan without executing any tools.

        Mirrors the plan-mode of agentic coding tools: research and
        structuring happen before any mutating action. The returned `Plan`
        can be inspected, edited, or approved before calling `chat`/`stream`.
        """
        context.mode = ExecutionMode.PLAN
        context.conversation.add(message)

        pipeline = (
            ExecutionPipeline()
            .add(RequestBuilderStage())
            .add(PlannerStage())
        )
        context = await pipeline.execute(context)
        return context.plan

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
            context.stream_timeout = message.timeout
    

        context = await self.pipeline.execute(
            context
        )

        if context.stream is None:
            raise RuntimeError("Provider stream not initialized.")

        processor = EventProcessor(context)

        provider_timeout = None
        if hasattr(context.provider, "config"):
            provider_timeout = getattr(context.provider.config, "timeout", None)

        timeout = (
            context.stream_timeout
            if context.stream_timeout is not None
            else provider_timeout
        )

        while True:
            try:
                if timeout is not None:
                    event = await asyncio.wait_for(
                        context.stream.__anext__(),
                        timeout=timeout,
                    )
                else:
                    event = await context.stream.__anext__()
            except StopAsyncIteration:
                break
            except asyncio.TimeoutError:
                error_event = ErrorEvent(message="stream timeout")
                processor.process(error_event)
                yield error_event
                break
            except Exception as exc:
                error_event = ErrorEvent(message=str(exc))
                processor.process(error_event)
                yield error_event
                break
            else:
                processor.process(event)
                yield event

        if context.finish_reason is not None:
            context.conversation.add(
                ChatMessage.assistant(
                    context.assistant_text
                )
            )
