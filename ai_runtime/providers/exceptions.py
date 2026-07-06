class AIRuntimeError(Exception):
    """Base exception."""


class ProviderError(AIRuntimeError):
    """Base provider exception."""
    def __init__(
        self,
        message: str,
        provider: str | None = None,
        model: str | None = None,
        status_code: int | None = None,
        retry_after: int | None = None,
    ):
        super().__init__(message)
        self.provider = provider
        self.model = model
        self.status_code = status_code
        self.retry_after = retry_after


class AuthenticationError(ProviderError):
    pass


class RateLimitError(ProviderError):
    pass


class ConnectionError(ProviderError):
    pass


class TimeoutError(ProviderError):
    pass


class ModelNotFoundError(ProviderError):
    pass


class InvalidRequestError(ProviderError):
    pass


class ContentFilterError(ProviderError):
    pass


class ServerError(ProviderError):
    pass

class ProviderNotSupportedError(ProviderError):
    pass