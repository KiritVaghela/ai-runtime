from ai_runtime.models.request import ChatRequest
from ai_runtime.models.message import ChatMessage
from ai_runtime.adapters.litellm.request_adapter import LiteLLMRequestAdapter


def test_request_adapter():
    request = ChatRequest(
        model="gpt-4.1",
        messages=[
            ChatMessage.user("Hello")
        ],
    )

    payload = LiteLLMRequestAdapter.to_request(request)

    assert payload["model"] == "gpt-4.1"
    assert payload["messages"][0]["role"] == "user"
    assert payload["messages"][0]["content"] == "Hello"