
from pydantic import ConfigDict

from ai_runtime.models import Usage

from .event import StreamEvent
from .enums import StreamEventType


class UsageEvent(StreamEvent):
    """
    Token usage information.
    """

    model_config = ConfigDict(frozen=True)

    type: StreamEventType = StreamEventType.USAGE

    usage: Usage