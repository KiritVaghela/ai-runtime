

from pydantic import ConfigDict

from .event import StreamEvent
from .enums import StreamEventType


class TextDeltaEvent(StreamEvent):
    """
    Incremental text produced by the model.
    """

    model_config = ConfigDict(frozen=True)

    type: StreamEventType = StreamEventType.TEXT_DELTA

    text: str