from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ai_runtime.conversation import Conversation
from ai_runtime.eventing import EventBus
from ai_runtime.providers import BaseProvider
from ai_runtime.conversation import (
    ChatRequest, ChatResponse
)

class ExecutionContext(BaseModel):

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
    )

    provider: BaseProvider

    conversation: Conversation = Field(
        default_factory=Conversation
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict
    )

    variables: dict[str, Any] = Field(
        default_factory=dict
    )

    event_bus: EventBus = Field(
        default_factory=EventBus
    )

    request: ChatRequest | None = None

    response: ChatResponse | None = None

    stream: bool = False
