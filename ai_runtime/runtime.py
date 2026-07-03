from ai_runtime.providers.provider import LLMProvider

class AgentRuntime:
    """
    Entry point for the AI Runtime SDK.
    """
    def __init__(
        self,
        provider: LLMProvider,
    ):
        self.provider = provider