from .completed import CompletedEvent
from .error import ErrorEvent
from .text import TextDeltaEvent
from .usage import UsageEvent
from .tool_call import ToolCallEvent
from .tool_result import ToolResultEvent
from .thinking import ThinkingEvent
from .permission import PermissionEvent
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

        if event_type == StreamEventType.TOOL_CALL:
            return ToolCallEvent.model_validate(data)

        if event_type == StreamEventType.TOOL_RESULT:
            return ToolResultEvent.model_validate(data)

        if event_type == StreamEventType.THINKING:
            return ThinkingEvent.model_validate(data)

        if event_type == StreamEventType.PERMISSION:
            return PermissionEvent.model_validate(data)

        raise ValueError(f"Unsupported event type: {event_type}")