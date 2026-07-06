
from typing import Any

from ai_runtime.models.message import ChatMessage
from ai_runtime.models.request import ChatRequest


class LiteLLMRequestAdapter:

    @staticmethod
    def to_request(request: ChatRequest) -> dict[str, Any]:
        return {
            "model": request.model,
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