
from ai_runtime.models import (
    ChatMessage,
    ChatRequest,
)

from ai_runtime.providers.litellm_mapper import (
    LiteLLMMapper,
)

from ai_runtime.providers.config import ProviderConfig
from ai_runtime.models.enums import ProviderType


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

    assert payload["model"] == "gpt-4.1"
    assert payload["messages"][0]["role"] == "user"
    assert payload["messages"][0]["content"] == "Hello"