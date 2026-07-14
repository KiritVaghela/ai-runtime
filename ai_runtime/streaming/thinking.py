from pydantic import ConfigDict

from .event import StreamEvent
from .enums import StreamEventType


class ThinkingEvent(StreamEvent):
    """
    Incremental reasoning/thinking content produced by reasoning models
    (e.g. Anthropic Claude, OpenAI o-series). Analogous to `TextDeltaEvent`
    but for the model's private chain-of-thought.
    """

    model_config = ConfigDict(frozen=True)

    type: StreamEventType = StreamEventType.THINKING

    delta: str
