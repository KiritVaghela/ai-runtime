from abc import ABC, abstractmethod

from ai_runtime.models import (
    ChatRequest,
    ChatResponse,
    ProviderCapabilities,
)

from .config import ProviderConfig

class Provider(ABC):

    def __init__(self, config: ProviderConfig):
        self.config = config

    @property
    @abstractmethod
    def capabilities(self) -> ProviderCapabilities:
        ...

    @abstractmethod
    async def chat(
        self,
        request: ChatRequest,
    ) -> ChatResponse:
        ...

    @abstractmethod
    async def stream(
        self,
        request: ChatRequest,
    ):
        ...

    @abstractmethod
    async def list_models(
        self,
    ) -> list[str]:
        ...