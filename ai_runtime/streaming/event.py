from abc import ABC

from pydantic import BaseModel, ConfigDict

from .enums import StreamEventType


class StreamEvent(BaseModel, ABC):
    """
    Base class for all streaming events.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    type: StreamEventType