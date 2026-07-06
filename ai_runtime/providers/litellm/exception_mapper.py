
from litellm import (
    AuthenticationError,
    RateLimitError,
    NotFoundError,
)

from .exceptions import (
    ProviderError,
    ModelNotFoundError,
)


class LiteLLMExceptionMapper:

    @staticmethod
    def map(
        ex: Exception,
    ) -> ProviderError:

        if isinstance(ex, AuthenticationError):
            return ProviderError(
                "Authentication failed."
            )

        if isinstance(ex, RateLimitError):
            return ProviderError(
                "Rate limit exceeded."
            )

        if isinstance(ex, NotFoundError):
            return ModelNotFoundError(
                str(ex)
            )

        return ProviderError(str(ex))