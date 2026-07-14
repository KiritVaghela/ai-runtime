from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncIterator

from ai_runtime.conversation import (
    ChatRequest,
    ChatResponse,
)

from .config import ProviderConfig
from ai_runtime.streaming import StreamEvent
from .provider_info import ProviderInfo


class LLMProvider(ABC):
    """Abstract provider contract for ai_runtime.

    Providers implement a small, async-first interface so the runtime can
    interact with different LLM backends uniformly. See
    `ai_runtime/docs/provider_contract.md` for expectations.

    Implementations MUST:
    - provide `info` describing capabilities
    - implement `chat(request)` for non-streaming responses
    - implement `stream(request)` to yield `StreamEvent` for streaming

    Optional:
    - `list_models()` may return available models or an empty list
    - `close()` lifecycle hook to free resources
    """

    def __init__(self, config: ProviderConfig):
        self.config = config

    @property
    @abstractmethod
    def info(self) -> ProviderInfo:
        """Provider information and capabilities."""

    @abstractmethod
    async def chat(self, request: ChatRequest) -> ChatResponse:
        """Perform a single chat completion for the given request."""

    @abstractmethod
    async def stream(self, request: ChatRequest) -> AsyncIterator[StreamEvent]:
        """Return an async iterator of `StreamEvent` for incremental output."""

    async def list_models(self) -> list[str]:
        """Optionally return available model identifiers. Default: empty list."""
        return []

    async def close(self) -> None:
        """Optional lifecycle hook for providers to release resources."""
        return None