from ai_runtime.providers.litellm_stream_parser import LiteLLMStreamParser
from ai_runtime.streaming import TextDeltaEvent,CompletedEvent

class Delta: content="Hello"
class Choice:
    delta=Delta()
    finish_reason="stop"
class Chunk:
    choices=[Choice()]
    usage=None

def test_stream_parser():
    events=LiteLLMStreamParser().parse(Chunk())
    assert any(isinstance(e,TextDeltaEvent) for e in events)
    assert any(isinstance(e,CompletedEvent) for e in events)
