from litellm.exceptions import (
    AuthenticationError as LiteAuthError,
    RateLimitError as LiteRateLimitError,
    NotFoundError,
    APIConnectionError,
    Timeout,
    BadRequestError,
    InternalServerError,
)

from .exceptions import (
    AuthenticationError,
    RateLimitError,
    ConnectionError,
    TimeoutError,
    InvalidRequestError,
    ModelNotFoundError,
    ServerError,
    ProviderError,
)


class LiteLLMExceptionMapper:

    @staticmethod
    def map(ex: Exception) -> ProviderError:

        if isinstance(ex, LiteAuthError):
            return AuthenticationError(str(ex))

        if isinstance(ex, LiteRateLimitError):
            return RateLimitError(str(ex))

        if isinstance(ex, APIConnectionError):
            return ConnectionError(str(ex))

        if isinstance(ex, Timeout):
            return TimeoutError(str(ex))

        if isinstance(ex, BadRequestError):
            return InvalidRequestError(str(ex))

        if isinstance(ex, NotFoundError):
            return ModelNotFoundError(str(ex))

        if isinstance(ex, InternalServerError):
            return ServerError(str(ex))

        return ProviderError(str(ex))