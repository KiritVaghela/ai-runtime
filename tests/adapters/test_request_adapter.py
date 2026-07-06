from ai_runtime.models.request import ChatRequest
from ai_runtime.models.message import ChatMessage
from ai_runtime.adapters.litellm.request_adapter import LiteLLMRequestAdapter

from ai_runtime.providers.config import ProviderConfig
from ai_runtime.models.enums import ProviderType

def test_request_adapter():
        
    config = ProviderConfig(
        provider=ProviderType.OPENAI,
        model="gpt-4.1",
    )
        
    request = ChatRequest(
        model="gpt-4.1",
        messages=[
            ChatMessage.user("Hello")
        ],
    )

    payload = LiteLLMRequestAdapter.to_request(config, request)

    assert payload["model"] == "gpt-4.1"
    assert payload["messages"][0]["role"] == "user"
    assert payload["messages"][0]["content"] == "Hello"