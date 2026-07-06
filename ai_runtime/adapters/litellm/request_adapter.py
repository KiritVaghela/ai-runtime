
from typing import Any

from ai_runtime.models.message import ChatMessage
from ai_runtime.models.request import ChatRequest
from ai_runtime.providers.config import ProviderConfig
from ai_runtime.providers.model_resolver import ModelResolver

class LiteLLMRequestAdapter:

    @staticmethod
    def to_request(config: ProviderConfig, request: ChatRequest) -> dict[str, Any]:
        return {
            "model": ModelResolver.resolve(config.model),
            "messages": [
                LiteLLMRequestAdapter.to_message(message)
                for message in request.messages
            ],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": request.stream,
        }

    @staticmethod
    def to_message(message: ChatMessage) -> dict[str, Any]:
        return {
            "role": message.role.value,
            "content": message.content,
        }