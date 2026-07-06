
from ai_runtime.models import (
    ChatMessage,
    ChatRequest,
)

from ai_runtime.providers.litellm_mapper import (
    LiteLLMMapper,
)


def test_request_mapping():

    request = ChatRequest(
        model="gpt-4.1",
        messages=[
            ChatMessage.user("Hello")
        ]
    )

    payload = LiteLLMMapper.to_request(
        request
    )

    assert payload["model"] == "gpt-4.1"

    assert payload["messages"][0]["role"] == "user"

    assert payload["messages"][0]["content"] == "Hello"