from pydantic import ConfigDict, Field
from typing import Any

from .event import StreamEvent
from .enums import StreamEventType


class ToolCallEvent(StreamEvent):
    """
    Emitted when the model requests one or more tool calls.

    `calls` mirrors the OpenAI tool-call shape: each entry has an `id`,
    a `name`, and parsed `arguments` (dict). Providers that stream tool
    calls incrementally should emit one `ToolCallEvent` per completed call.
    """

    model_config = ConfigDict(frozen=True)

    type: StreamEventType = StreamEventType.TOOL_CALL

    calls: list[dict[str, Any]] = Field(default_factory=list)
