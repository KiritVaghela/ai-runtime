
from ai_runtime.conversation import ChatRequest
from .provider_info import ProviderInfo

from .base import LLMProvider
from .litellm_exception_mapper import ProviderError

from abc import abstractmethod

class BaseProvider(LLMProvider):

    @property
    @abstractmethod
    def info(self) -> ProviderInfo:
        ...

    def validate_request(
        self,
        request: ChatRequest,
    ) -> None:

        if not request.messages:
            raise ProviderError(
                "Request must contain at least one message."
            )

    def map_exception(
        self,
        ex: Exception,
    ) -> ProviderError:

        if isinstance(ex, ProviderError):
            return ex

        return ProviderError(str(ex))