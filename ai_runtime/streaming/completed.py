from pydantic import ConfigDict

from .event import StreamEvent
from .enums import StreamEventType
from .finish_reason import FinishReason


class CompletedEvent(StreamEvent):
    """
    Indicates streaming has completed.
    """

    model_config = ConfigDict(frozen=True)

    type: StreamEventType = StreamEventType.COMPLETED

    finish_reason: FinishReason | None = None


