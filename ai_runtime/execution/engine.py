import asyncio
import json
from collections.abc import AsyncIterator

from ai_runtime.conversation import ChatMessage, ToolCall
from ai_runtime.conversation import ChatRequest, ChatResponse
from ai_runtime.streaming import (
    StreamEvent,
    ErrorEvent,
    CompletedEvent,
    TextDeltaEvent,
    ToolCallEvent,
    ToolResultEvent,
)

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

    async def stream_plan(
        self,
        context: ExecutionContext,
        message: ChatMessage | ChatRequest,
    ) -> AsyncIterator[StreamEvent]:
        """Stream a plan: live text/thinking deltas, then a final plan event.

        Mirrors `stream()` but uses the read-only planner pipeline so no tools
        run. Effort / thinking / streaming controls all apply because the
        planner streams through the provider like chat does.
        """
        context.mode = ExecutionMode.PLAN

        if isinstance(message, ChatMessage):
            context.conversation.add(message)
        elif isinstance(message, ChatRequest):
            context.conversation.extend(message.messages)
            context.temperature = message.temperature
            context.max_tokens = message.max_tokens
            context.stream_timeout = message.timeout

        pipeline = (
            ExecutionPipeline()
            .add(RequestBuilderStage())
            .add(PlannerStage())
        )
        context = await pipeline.execute(context)

        # Replay the planner's streamed events to the caller.
        for event in getattr(context, "_plan_events", []):
            yield event
        yield CompletedEvent()

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

        executor = context.tool_executor

        iteration = 0
        max_iterations = 5

        while iteration < max_iterations:
            iteration += 1

            context = await self.pipeline.execute(context)

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

            # Stream the current LLM turn, accumulating any tool calls.
            pending_tool_calls: list[ToolCall] = []
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
                    # Capture completed tool calls for execution after the turn.
                    if isinstance(event, ToolCallEvent):
                        for call in event.calls:
                            if call.get("id") and call.get("name"):
                                pending_tool_calls.append(
                                    ToolCall(
                                        id=call["id"],
                                        name=call["name"],
                                        arguments=call.get("arguments", ""),
                                    )
                                )

            # No tool calls requested -> final answer, stop the loop.
            if not pending_tool_calls:
                if context.finish_reason is not None:
                    context.conversation.add(
                        ChatMessage.assistant(context.assistant_text)
                    )
                break

            # Persist the assistant message that requested the tools so the
            # next LLM turn sees the full conversation.
            context.conversation.add(
                ChatMessage.assistant(
                    context.assistant_text,
                    tool_calls=pending_tool_calls,
                )
            )

            # Execute each tool and emit a result event for the frontend.
            for call in pending_tool_calls:
                result = await self._run_tool(context, call, executor)
                yield ToolResultEvent(
                    call_id=call.id,
                    name=call.name,
                    output=result.output,
                    success=result.success,
                    error=result.error,
                )
                context.tool_results[call.id] = {
                    "name": call.name,
                    "output": result.output,
                    "success": result.success,
                    "error": result.error,
                }
                context.conversation.add(
                    ChatMessage.tool(
                        content=self._serialize(result.output),
                        tool_call_id=call.id,
                    )
                )

            # Reset streamed text for the next turn and re-run the pipeline
            # (request builder + LLM) with the tool results appended.
            context.assistant_text = ""
            context.finish_reason = None
            context.stream = None

    async def _run_tool(self, context: ExecutionContext, call: ToolCall, executor):
        """Execute a single tool call, mirroring ToolLoopStage's logic."""
        from ai_runtime.tools.tool import ToolResult

        if executor is None:
            return ToolResult(
                success=False,
                error="No tool executor configured for this session.",
            )

        try:
            arguments = call.arguments
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments) if arguments else {}
                except json.JSONDecodeError:
                    arguments = {"input": arguments}

            timeout = None
            if isinstance(arguments, dict):
                timeout = arguments.pop("timeout", None)

            result = await executor.execute(
                call.name,
                context,
                arguments,
                timeout=timeout,
            )
            if not isinstance(result, ToolResult):
                result = ToolResult(success=True, output=result)
            return result
        except Exception as exc:  # noqa: BLE001
            return ToolResult(success=False, error=str(exc))

    @staticmethod
    def _serialize(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        try:
            return json.dumps(value, default=str)
        except (TypeError, ValueError):
            return str(value)
