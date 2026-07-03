from .provider import Provider
from .config import ProviderConfig
from ..models import ChatRequest
from ..models import ChatResponse
from .exceptions import ProviderError

class BaseProvider(Provider):

    def __init__(self, config: ProviderConfig):
        super().__init__(config)

    def validate_request(
        self,
        request: ChatRequest,
    ) -> None:
        ...

    def map_exception(
        self,
        ex: Exception,
    ) -> ProviderError:
        ...