from abc import ABC, abstractmethod

from ai_runtime.models import (
    ChatRequest,
    ChatResponse,
    ProviderCapabilities,
)

from .config import ProviderConfig


class LLMProvider(ABC):

    def __init__(self, config: ProviderConfig):
        self.config = config

    @property
    @abstractmethod
    def capabilities(self) -> ProviderCapabilities:
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
    ):
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