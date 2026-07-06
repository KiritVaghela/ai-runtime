from ai_runtime.providers.litellm_mapper import LiteLLMMapper

class Usage:
    prompt_tokens=1
    completion_tokens=2
    total_tokens=3
class Msg: content="Hello"
class Choice:
    message=Msg()
    finish_reason="stop"
class Resp:
    choices=[Choice()]
    usage=Usage()

def test_response_mapping():
    r=LiteLLMMapper.from_response(Resp())
    assert r.message.content=="Hello"
    assert r.usage.total_tokens==3
