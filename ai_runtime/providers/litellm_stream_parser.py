
from typing import Any

from ai_runtime.conversation import Usage
from ai_runtime.streaming import (
    CompletedEvent,
    StreamEvent,
    TextDeltaEvent,
    ThinkingEvent,
    ToolCallEvent,
    UsageEvent,
)


class LiteLLMStreamParser:
    """
    Converts LiteLLM streaming chunks into AI Runtime StreamEvents.

    Tool calls are streamed as multiple fragments (one chunk for the id,
    one for the name, then several for the JSON arguments). Rather than
    emitting a `ToolCallEvent` per fragment, we accumulate the fragments
    keyed by their stream index and emit a *single* `ToolCallEvent`
    containing every completed call once the stream finishes. This matches
    the contract documented on `ToolCallEvent` ("emit one `ToolCallEvent`
    per completed call") and lets the frontend render one card per tool.
    """

    def __init__(self) -> None:
        # index -> {"id", "name", "arguments"} accumulator for in-flight calls.
        self._tool_calls: dict[int, dict[str, Any]] = {}

    def _accumulate_tool_calls(self, tool_calls: list) -> None:
        for tc in tool_calls:
            idx = getattr(tc, "index", None)
            if idx is None:
                # Fall back to a stable key when index is missing.
                idx = getattr(tc, "id", None) or id(tc)
            slot = self._tool_calls.setdefault(
                idx, {"id": None, "name": None, "arguments": ""}
            )
            tc_id = getattr(tc, "id", None)
            if tc_id is not None:
                slot["id"] = tc_id
            fn = getattr(tc, "function", None)
            if fn is not None:
                name = getattr(fn, "name", None)
                if name is not None:
                    slot["name"] = name
                args = getattr(fn, "arguments", None)
                if args:
                    slot["arguments"] += args

    def _flush_tool_calls(self) -> list[StreamEvent]:
        if not self._tool_calls:
            return []
        # Emit one event with all completed calls, ordered by index.
        calls = [
            {
                "id": slot["id"],
                "name": slot["name"],
                "arguments": slot["arguments"],
            }
            for _, slot in sorted(self._tool_calls.items())
        ]
        self._tool_calls.clear()
        return [ToolCallEvent(calls=calls)]

    def parse(self, chunk: Any) -> list[StreamEvent]:
        events: list[StreamEvent] = []

        # Usage
        usage = getattr(chunk, "usage", None)
        if usage is not None:
            events.append(
                UsageEvent(
                    usage=Usage(
                        prompt_tokens=usage.prompt_tokens or 0,
                        completion_tokens=usage.completion_tokens or 0,
                        total_tokens=usage.total_tokens or 0,
                    )
                )
            )

        choices = getattr(chunk, "choices", None)
        if not choices:
            return events

        choice = choices[0]

        # Text delta
        delta = getattr(choice, "delta", None)
        if delta is not None:

            text = getattr(delta, "content", None)
            if text:
                events.append(
                    TextDeltaEvent(
                        delta=text,
                    )
                )

            # Reasoning / thinking delta (OpenAI o-series, Anthropic, etc.)
            reasoning = getattr(delta, "reasoning_content", None)
            if reasoning is None:
                reasoning = getattr(delta, "thinking", None)
            if reasoning:
                events.append(
                    ThinkingEvent(
                        delta=reasoning,
                    )
                )

            # Tool call deltas: accumulate fragments, do not emit yet.
            tool_calls = getattr(delta, "tool_calls", None)
            if tool_calls:
                self._accumulate_tool_calls(tool_calls)

        # Finish reason: flush accumulated tool calls, then emit completion.
        finish_reason = getattr(choice, "finish_reason", None)

        if finish_reason:
            events.extend(self._flush_tool_calls())
            events.append(
                CompletedEvent(
                    finish_reason=finish_reason,
                )
            )

        return events