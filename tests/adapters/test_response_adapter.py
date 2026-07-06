class FakeUsage:

    prompt_tokens = 10

    completion_tokens = 5

    total_tokens = 15


class FakeMessage:

    content = "Hello"


class FakeChoice:

    message = FakeMessage()

    finish_reason = "stop"


class FakeResponse:

    choices = [FakeChoice()]

    usage = FakeUsage()


from ai_runtime.providers.litellm_mapper import (
    LiteLLMMapper,
)

def test_response_adapter():

    response = LiteLLMMapper.from_response(
        FakeResponse()
    )

    assert response.message.content == "Hello"

    assert response.usage.total_tokens == 15