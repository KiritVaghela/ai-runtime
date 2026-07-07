from abc import ABC, abstractmethod

from ai_runtime.conversation import (
    ChatRequest,
    ChatResponse,
)

from .config import ProviderConfig

from collections.abc import AsyncIterator
from ai_runtime.streaming import StreamEvent
from .provider_info import ProviderInfo

class LLMProvider(ABC):

    def __init__(self, config: ProviderConfig):
        self.config = config

    @property
    @abstractmethod
    def info(self) -> ProviderInfo:
        """
        Supported capabilities.
        """

    @abstractmethod
    async def chat(
        self,
        request: ChatRequest,
    ) -> ChatResponse:
        """
        Chat completion.
        """

    @abstractmethod
    async def stream(
        self,
        request: ChatRequest,
    ) -> AsyncIterator[StreamEvent]:
        """
        Streaming completion.
        """

    @abstractmethod
    async def list_models(
        self,
    ) -> list[str]:
        """
        Available models.
        """