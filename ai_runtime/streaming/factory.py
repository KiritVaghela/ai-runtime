from .completed import CompletedEvent
from .error import ErrorEvent
from .text import TextDeltaEvent
from .usage import UsageEvent
from .enums import StreamEventType


class StreamEventFactory:

    @staticmethod
    def create(data: dict):
        event_type = StreamEventType(data["type"])

        if event_type == StreamEventType.TEXT_DELTA:
            return TextDeltaEvent.model_validate(data)

        if event_type == StreamEventType.USAGE:
            return UsageEvent.model_validate(data)

        if event_type == StreamEventType.COMPLETED:
            return CompletedEvent.model_validate(data)

        if event_type == StreamEventType.ERROR:
            return ErrorEvent.model_validate(data)

        raise ValueError(f"Unsupported event type: {event_type}")