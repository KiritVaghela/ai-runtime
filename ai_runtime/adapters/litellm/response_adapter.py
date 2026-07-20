from typing import Any

from ai_runtime.conversation import (
    ChatResponse,
    ToolCall,
    Usage,
)


class LiteLLMResponseAdapter:

    @staticmethod
    def from_response(response: Any) -> ChatResponse:
        choice = response.choices[0]
        message = choice.message

        tool_calls = LiteLLMResponseAdapter.to_tool_calls(
            getattr(message, "tool_calls", None)
        )

        return ChatResponse.assistant(
            getattr(message, "content", None) or "",
            usage=LiteLLMResponseAdapter.to_usage(
                getattr(response, "usage", None)
            ),
            finish_reason=getattr(choice, "finish_reason", None),
            tool_calls=tool_calls or None,
            raw=response,
        )

    @staticmethod
    def to_tool_calls(raw_calls: Any) -> list[ToolCall]:
        if not raw_calls:
            return []

        calls: list[ToolCall] = []
        for rc in raw_calls:
            function = getattr(rc, "function", None)
            calls.append(
                ToolCall(
                    id=getattr(rc, "id", ""),
                    name=getattr(function, "name", ""),
                    arguments=getattr(function, "arguments", ""),
                )
            )
        return calls

    @staticmethod
    def to_usage(usage: Any) -> Usage:
        if usage is None:
            return Usage()

        return Usage(
            prompt_tokens=getattr(usage, "prompt_tokens", 0) or 0,
            completion_tokens=getattr(usage, "completion_tokens", 0) or 0,
            total_tokens=getattr(usage, "total_tokens", 0) or 0,
        )
