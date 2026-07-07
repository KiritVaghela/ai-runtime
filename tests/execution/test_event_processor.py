from ai_runtime.execution import (
    EventProcessor,
    ExecutionContext,
)
from ai_runtime.streaming import (
    TextDeltaEvent,
)

from ai_runtime.conversation import Usage
from ai_runtime.streaming import UsageEvent
from ai_runtime.streaming import CompletedEvent

class DummyProvider:
    pass


def test_text_delta():

    context = ExecutionContext(
        provider=DummyProvider(),
    )

    processor = EventProcessor(context)

    processor.process(
        TextDeltaEvent(delta="Hello")
    )

    assert context.assistant_text == "Hello"


def test_usage():

    context = ExecutionContext(
        provider=DummyProvider(),
    )

    usage = Usage(
        prompt_tokens=10,
        completion_tokens=5,
        total_tokens=15,
    )

    processor = EventProcessor(context)

    processor.process(
        UsageEvent(
            usage=usage
        )
    )

    assert context.usage == usage


def test_finish_reason():

    context = ExecutionContext(
        provider=DummyProvider(),
    )

    processor = EventProcessor(context)

    processor.process(
        CompletedEvent(
            finish_reason="stop"
        )
    )

    assert context.finish_reason == "stop"

def test_publish():

    context = ExecutionContext(
        provider=DummyProvider(),
    )

    received = []

    context.event_bus.subscribe(
        received.append
    )

    processor = EventProcessor(context)

    event = TextDeltaEvent(
        delta="Hi"
    )

    processor.process(event)

    assert received[0] is event