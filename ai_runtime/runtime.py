from ai_runtime.providers.provider import Provider

class AgentRuntime:
    """
    Entry point for the AI Runtime SDK.
    """
    def __init__(
        self,
        provider: Provider,
    ):
        self.provider = provider