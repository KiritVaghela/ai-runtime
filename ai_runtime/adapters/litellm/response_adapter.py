from typing import Any

from ai_runtime.conversation import ChatResponse, ChatMessage, Usage


class LiteLLMResponseAdapter:

    @staticmethod
    def from_response(response: Any) -> ChatResponse:
        choice = response.choices[0]

        return ChatResponse.assistant(
            choice.message.content,
            usage=LiteLLMResponseAdapter.to_usage(
                getattr(response, "usage", None)
            ),
            finish_reason=getattr(choice, "finish_reason", None),
        )

    @staticmethod
    def to_usage(usage: Any) -> Usage:
        if usage is None:
            return Usage()

        return Usage(
            prompt_tokens=getattr(usage, "prompt_tokens", 0) or 0,
            completion_tokens=getattr(usage, "completion_tokens", 0) or 0,
            total_tokens=getattr(usage, "total_tokens", 0) or 0,
        )
