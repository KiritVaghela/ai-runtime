from ai_runtime.models import ChatRequest

from .base import LLMProvider
from .exceptions import ProviderError


class BaseProvider(LLMProvider):

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