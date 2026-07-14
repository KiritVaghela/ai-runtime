from pydantic import ConfigDict, Field
from typing import Any

from .event import StreamEvent
from .enums import StreamEventType


class PermissionEvent(StreamEvent):
    """
    Human-in-the-loop / approval request emitted when a tool or action
    requires explicit user consent before execution. The runtime should
    pause and await a decision (approve/deny) keyed by `request_id`.
    """

    model_config = ConfigDict(frozen=True)

    type: StreamEventType = StreamEventType.PERMISSION

    request_id: str

    action: str

    detail: dict[str, Any] = Field(default_factory=dict)
