from typing import Any

from ai_runtime.models import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    Usage,
)
from .config import ProviderConfig

class LiteLLMMapper:
    """
    Maps AI Runtime models <-> LiteLLM models.
    """

    @staticmethod
    def to_request(
        config: ProviderConfig,
        request: ChatRequest,
    ) -> dict[str, Any]:
        return {
            "model": config.litellm_model,
            "messages": [
                LiteLLMMapper.to_message(m)
                for m in request.messages
            ],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": request.stream,
        }
    

    @staticmethod
    def to_message(
        message: ChatMessage,
    ) -> dict[str, Any]:
        return {
            "role": message.role.value,
            "content": message.content,
        }

    @staticmethod
    def from_response(
        response: Any,
    ) -> ChatResponse:

        choice = response.choices[0]

        return ChatResponse(
            message=ChatMessage.assistant(
                choice.message.content
            ),
            finish_reason=choice.finish_reason,
            usage=LiteLLMMapper.to_usage(
                response.usage
            ),
        )

    @staticmethod
    def to_usage(
        usage: Any,
    ) -> Usage:

        if usage is None:
            return Usage()

        return Usage(
            prompt_tokens=usage.prompt_tokens or 0,
            completion_tokens=usage.completion_tokens or 0,
            total_tokens=usage.total_tokens or 0,
        )