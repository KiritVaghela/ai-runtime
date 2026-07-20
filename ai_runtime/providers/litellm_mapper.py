import json
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
            "stream": request.stream,
        }
        # Only set max_tokens when the caller explicitly requested a limit.
        # Leaving it unset lets the provider use its own sane default instead
        # of litellm's large fallback (which free-tier accounts can't afford).
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens

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

        # Reasoning / thinking controls (capability-gated).
        if capabilities.reasoning:
            if config.reasoning_effort:
                payload["reasoning_effort"] = config.reasoning_effort
            if config.thinking_enabled:
                payload["thinking"] = {
                    "type": "enabled",
                    "budget_tokens": config.thinking_budget_tokens,
                }

        return payload
    

    @staticmethod
    def to_message(
        message: ChatMessage,
    ) -> dict[str, Any]:
        # Multimodal-aware: if content is already a structured list
        # (e.g. text + image_url blocks), pass it through untouched so
        # vision-capable providers receive content arrays.
        if isinstance(message.content, (list, dict)):
            msg = {
                "role": message.role.value,
                "content": message.content,
            }
        else:
            msg = {
                "role": message.role.value,
                "content": message.content,
            }

        # Serialize assistant tool-call requests so the provider sees the
        # full function-calling context when we re-invoke it with results.
        if message.tool_calls:
            msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.name,
                        "arguments": tc.arguments
                        if isinstance(tc.arguments, str)
                        else json.dumps(tc.arguments or {}),
                    },
                }
                for tc in message.tool_calls
            ]

        # Link tool-result messages back to their originating call.
        if message.tool_call_id is not None:
            msg["tool_call_id"] = message.tool_call_id

        return msg

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