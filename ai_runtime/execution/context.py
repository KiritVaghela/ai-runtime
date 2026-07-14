from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ..conversation import Conversation
from ..eventing import EventBus
from ..conversation import (
    ChatRequest, ChatResponse
)

from .mode import ExecutionMode
from collections.abc import AsyncIterator

from ..streaming import StreamEvent
from ..conversation import Usage
from ..streaming import FinishReason
from .plan import Plan

class ExecutionContext(BaseModel):

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
    )

    provider: Any

    conversation: Conversation = Field(
        default_factory=Conversation
    )

    #
    # Built during execution
    #
    request: ChatRequest | None = None

    response: ChatResponse | None = None

    plan: Plan | None = None

    agent: Any = None

    _engine: Any = None

    hooks: Any = None  # Optional[HookRegistry]

    #
    # Execution Options
    #
    temperature: float = 0.7

    max_tokens: int | None = None

    mode: ExecutionMode = ExecutionMode.CHAT

    #
    # Runtime State
    #
    metadata: dict[str, Any] = Field(
        default_factory=dict
    )

    variables: dict[str, Any] = Field(
        default_factory=dict
    )

    event_bus: EventBus = Field(
        default_factory=EventBus
    )

    stream: AsyncIterator[
        StreamEvent
    ] | None = None

    assistant_text: str = ""

    thinking_text: str = ""

    stream_timeout: float | None = None

    usage: Usage | None = None

    finish_reason: FinishReason | None = None

    # Tooling integration
    # A place to record declared tool inputs (optional) and results
    # `metadata['tool_calls']` can be used by pipeline stages to request tool execution.
    tool_inputs: dict[str, Any] = Field(default_factory=dict)

    tool_results: dict[str, Any] = Field(default_factory=dict)

    # Optional executor used by ToolLoopStage to run model-requested tools.
    tool_executor: Any | None = None