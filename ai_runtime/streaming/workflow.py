from pydantic import ConfigDict, Field
from typing import Any

from .event import StreamEvent
from .enums import StreamEventType


class WorkflowEvent(StreamEvent):
    """Progress event emitted by workflow / multi-agent orchestration.

    Surfaces DAG execution to clients so a UI can render step status
    (queued → running → done/failed) the way agentic tools show sub-agent
    and task progress. `phase` is one of: queued, running, completed, failed.
    """

    model_config = ConfigDict(frozen=True)

    type: StreamEventType = StreamEventType.WORKFLOW

    workflow: str  # workflow / router / critic name
    step: str  # step or route or iteration label
    phase: str  # queued | running | completed | failed
    detail: dict[str, Any] = Field(default_factory=dict)
