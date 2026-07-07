
from ai_runtime.conversation import (
    ChatMessage,
    ChatRequest,
)

from ai_runtime.providers.litellm_mapper import (
    LiteLLMMapper,
)

from ai_runtime.providers.config import ProviderConfig
from ai_runtime.providers.enums import ProviderType


def test_request_mapping():

    config = ProviderConfig(
        provider=ProviderType.OPENAI,
        model="gpt-4.1",
    )

    request = ChatRequest(
        messages=[
            ChatMessage.user("Hello")
        ]
    )

    payload = LiteLLMMapper.to_request(
        config,
        request
    )

    assert payload["model"] == config.litellm_model
    assert payload["messages"][0]["role"] == "user"
    assert payload["messages"][0]["content"] == "Hello"