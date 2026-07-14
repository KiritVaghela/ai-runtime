from typing import Any

from ai_runtime.conversation import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    Usage,
)
from .config import ProviderConfig
from .capabilities import ProviderCapabilities

class LiteLLMMapper:
    """
    Maps AI Runtime models <-> LiteLLM models.
    """

    @staticmethod
    def to_request(
        config: ProviderConfig,
        request: ChatRequest,
        capabilities: ProviderCapabilities | None = None,
    ) -> dict[str, Any]:
        capabilities = capabilities or ProviderCapabilities()

        payload: dict[str, Any] = {
            "model": config.litellm_model,
            "messages": [
                LiteLLMMapper.to_message(m)
                for m in request.messages
            ],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": request.stream,
        }

        # Forward capability-gated request fields.
        if capabilities.tools and request.tools:
            payload["tools"] = request.tools
            if request.tool_choice is not None:
                payload["tool_choice"] = request.tool_choice

        if capabilities.structured_output and request.response_format:
            payload["response_format"] = request.response_format

        # Provider-specific hints from request metadata.
        if request.metadata:
            payload["metadata"] = request.metadata

        return payload
    

    @staticmethod
    def to_message(
        message: ChatMessage,
    ) -> dict[str, Any]:
        # Multimodal-aware: if content is already a structured list
        # (e.g. text + image_url blocks), pass it through untouched so
        # vision-capable providers receive content arrays.
        if isinstance(message.content, (list, dict)):
            return {
                "role": message.role.value,
                "content": message.content,
            }

        return {
            "role": message.role.value,
            "content": message.content,
        }

    @staticmethod
    def from_response(
        response: Any,
    ) -> ChatResponse:
        from ai_runtime.adapters.litellm.response_adapter import LiteLLMResponseAdapter

        return LiteLLMResponseAdapter.from_response(response)

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