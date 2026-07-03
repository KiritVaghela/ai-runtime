class AIRuntimeError(Exception):
    """Base exception."""


class ProviderError(AIRuntimeError):
    """Provider related error."""