from pydantic import ConfigDict

from .event import StreamEvent
from .enums import StreamEventType


class ErrorEvent(StreamEvent):
    """
    Indicates an error occurred while streaming.
    """

    model_config = ConfigDict(frozen=True)

    type: StreamEventType = StreamEventType.ERROR

    message: str