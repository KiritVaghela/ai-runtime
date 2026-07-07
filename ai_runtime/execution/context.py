from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ai_runtime.conversation import Conversation


class ExecutionContext(BaseModel):

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
    )

    provider: Any

    conversation: Conversation = Field(
        default_factory=Conversation
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict
    )

    variables: dict[str, Any] = Field(
        default_factory=dict
    )