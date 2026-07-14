from __future__ import annotations

import json
from typing import Any

from ai_runtime.conversation import ChatMessage, ToolCall
from ai_runtime.streaming import (
    ToolCallEvent,
    ToolResultEvent,
)

from .stage import ExecutionStage
from ..context import ExecutionContext
from ..mode import ExecutionMode
from .request_builder_stage import RequestBuilderStage
from .llm_stage import LLMStage


class ToolLoopStage(ExecutionStage):
    """
    Executes model-requested tool calls and re-invokes the LLM until the
    model produces a final answer (or `max_iterations` is reached).

    This stage must run *after* `LLMStage` in chat mode. It inspects
    `context.response.finish_reason`; when it equals ``"tool_calls"`` the
    stage extracts the calls, executes them via the injected
    `ToolExecutor`, appends the results as tool messages, and re-runs the
    request-building + LLM stages. The loop terminates when the model
    returns a non-tool-call finish reason or the iteration budget is
    exhausted.
    """

    def __init__(
        self,
        executor=None,
        max_iterations: int = 5,
    ):
        self.executor = executor
        self.max_iterations = max_iterations
        self._builder = RequestBuilderStage()
        self._llm = LLMStage()

    async def execute(
        self,
        context: ExecutionContext,
    ) -> ExecutionContext:

        # Tool execution is only meaningful in chat mode (streaming tool
        # calls are handled by the engine's event loop).
        if context.mode != ExecutionMode.CHAT:
            return context

        if context.response is None:
            return context

        executor = self.executor or context.tool_executor
        if executor is None:
            return context

        iteration = 0

        while (
            context.response is not None
            and context.response.finish_reason == "tool_calls"
            and iteration < self.max_iterations
        ):
            iteration += 1

            tool_calls = self._extract_tool_calls(context)
            if not tool_calls:
                break

            # Persist the assistant message that requested the tools so the
            # subsequent LLM turn sees the full conversation.
            context.conversation.add(context.response.message)

            # Emit a tool-call event for observers.
            context.event_bus.publish(
                ToolCallEvent(
                    calls=[
                        {
                            "id": tc.id,
                            "name": tc.name,
                            "arguments": tc.arguments,
                        }
                        for tc in tool_calls
                    ]
                )
            )

            for call in tool_calls:
                result = await self._run_tool(context, call, executor)

                context.event_bus.publish(
                    ToolResultEvent(
                        call_id=call.id,
                        name=call.name,
                        output=result.output,
                        success=result.success,
                        error=result.error,
                    )
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

            # Re-run the LLM with the tool results appended.
            context = await self._builder.execute(context)
            context = await self._llm.execute(context)

        return context

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    async def _run_tool(self, context: ExecutionContext, call: ToolCall, executor):
        from ai_runtime.tools.tool import ToolResult

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
                result = ToolResult(
                    success=True,
                    output=result,
                )
            return result
        except Exception as exc:  # noqa: BLE001
            from ai_runtime.tools.tool import ToolResult

            return ToolResult(success=False, error=str(exc))

    @staticmethod
    def _extract_tool_calls(context: ExecutionContext) -> list[ToolCall]:
        message = context.response.message
        if message.tool_calls:
            return message.tool_calls

        # Fallback: parse from raw provider payload if present.
        raw = getattr(context.response, "raw", None)
        if raw is not None:
            return ToolLoopStage._tool_calls_from_raw(raw)
        return []

    @staticmethod
    def _tool_calls_from_raw(raw: Any) -> list[ToolCall]:
        calls: list[ToolCall] = []
        try:
            choices = getattr(raw, "choices", None) or []
            message = getattr(choices[0], "message", None) if choices else None
            raw_calls = getattr(message, "tool_calls", None) or []
            for rc in raw_calls:
                calls.append(
                    ToolCall(
                        id=getattr(rc, "id", ""),
                        name=getattr(
                            getattr(rc, "function", None),
                            "name",
                            "",
                        ),
                        arguments=getattr(
                            getattr(rc, "function", None),
                            "arguments",
                            "",
                        ),
                    )
                )
        except Exception:  # noqa: BLE001
            return calls
        return calls

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
