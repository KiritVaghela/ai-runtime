from ai_runtime.models import Usage
from ai_runtime.streaming import (
    CompletedEvent,
    StreamEventType,
    TextDeltaEvent,
    UsageEvent,
    ErrorEvent,
)


def test_text_delta_event():

    event = TextDeltaEvent(text="Hello")

    assert event.type == StreamEventType.TEXT_DELTA
    assert event.text == "Hello"


def test_usage_event():

    usage = Usage(
        prompt_tokens=10,
        completion_tokens=5,
        total_tokens=15,
    )

    event = UsageEvent(usage=usage)

    assert event.usage.total_tokens == 15


def test_completed_event():

    event = CompletedEvent(
        finish_reason="stop"
    )

    assert event.finish_reason == "stop"


def test_error_event():

    event = ErrorEvent(message="An error occurred")

    assert event.type == StreamEventType.ERROR
    assert event.message == "An error occurred"
