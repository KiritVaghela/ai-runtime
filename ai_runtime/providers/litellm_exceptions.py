class ProviderError(Exception):
    """Base provider exception."""


class AuthenticationError(ProviderError):
    """Authentication failed."""


class RateLimitError(ProviderError):
    """Rate limit exceeded."""


class ModelNotFoundError(ProviderError):
    """Unknown model."""


class ProviderNotSupportedError(ProviderError):
    """Provider not registered."""




    