from pydantic import ConfigDict
from typing import Any

from .event import StreamEvent
from .enums import StreamEventType


class ToolResultEvent(StreamEvent):
    """
    Emitted after a tool call has been executed by the runtime.

    `call_id` links back to the originating `ToolCallEvent` entry, and
    `name` identifies the tool. `output` is the serialized tool result and
    `success` reports whether execution succeeded.
    """

    model_config = ConfigDict(frozen=True)

    type: StreamEventType = StreamEventType.TOOL_RESULT

    call_id: str | None = None

    name: str

    output: Any | None = None

    success: bool = True

    error: str | None = None
