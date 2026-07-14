import json

import pytest

from ai_runtime.conversation import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ToolCall,
    Usage,
)
from ai_runtime.execution import (
    ExecutionContext,
    ExecutionEngine,
)
from ai_runtime.execution.pipeline import ToolLoopStage
from ai_runtime.streaming import (
    CompletedEvent,
    TextDeltaEvent,
    ToolCallEvent,
    ToolResultEvent,
)
from ai_runtime.tools import ToolRegistry, ToolExecutor, FunctionTool
from ai_runtime.tools.tool import ToolResult


class ToolCallProvider:
    """Fake provider that requests a tool call on the first turn, then
    answers once the tool result is present in the conversation."""

    def __init__(self, config):
        self.config = config
        self.turn = 0

    async def chat(self, request):
        self.turn += 1

        if self.turn == 1:
            return ChatResponse.assistant(
                "",
                finish_reason="tool_calls",
                tool_calls=[
                    ToolCall(
                        id="call_1",
                        name="get_weather",
                        arguments=json.dumps({"city": "Paris"}),
                    )
                ],
            )

        # Second turn: verify the tool result reached the model.
        last = request.messages[-1]
        assert last.role.value == "tool"
        assert "Paris" in str(last.content)
        return ChatResponse.assistant(
            "It is sunny in Paris.",
            usage=Usage(
                prompt_tokens=10,
                completion_tokens=4,
                total_tokens=14,
            ),
            finish_reason="stop",
        )


def _make_executor():
    registry = ToolRegistry()
    registry.register(
        FunctionTool(
            "get_weather",
            lambda ctx, inp: f"Weather for {inp['city']}: sunny",
        )
    )
    return ToolExecutor(registry)


@pytest.mark.asyncio
async def test_tool_loop_executes_and_returns_final_answer():
    context = ExecutionContext(
        provider=ToolCallProvider(None),
        tool_executor=_make_executor(),
    )

    engine = ExecutionEngine()

    response = await engine.chat(
        context,
        ChatMessage.user("What is the weather in Paris?"),
    )

    # Final answer should come from the second LLM turn.
    assert response.message.content == "It is sunny in Paris."
    assert response.finish_reason == "stop"

    # Conversation should contain: user, assistant(tool_call), tool, assistant(answer)
    roles = [m.role.value for m in context.conversation.messages]
    assert roles == ["user", "assistant", "tool", "assistant"]


@pytest.mark.asyncio
async def test_tool_loop_emits_events():
    context = ExecutionContext(
        provider=ToolCallProvider(None),
        tool_executor=_make_executor(),
    )

    events = []

    def _listener(event):
        events.append(event)

    context.event_bus.subscribe(_listener)

    engine = ExecutionEngine()

    await engine.chat(
        context,
        ChatMessage.user("What is the weather in Paris?"),
    )

    assert any(isinstance(e, ToolCallEvent) for e in events)
    assert any(isinstance(e, ToolResultEvent) for e in events)


@pytest.mark.asyncio
async def test_tool_loop_skipped_without_executor():
    context = ExecutionContext(
        provider=ToolCallProvider(None),
        # No tool_executor provided.
    )

    engine = ExecutionEngine()

    response = await engine.chat(
        context,
        ChatMessage.user("What is the weather in Paris?"),
    )

    # Without an executor the loop is a no-op; raw tool-call response passes through.
    assert response.finish_reason == "tool_calls"
