
from ai_runtime.conversation import ChatMessage
from ai_runtime.streaming import (
    CompletedEvent,
    StreamEvent,
    TextDeltaEvent,
    UsageEvent,
)

from .context import ExecutionContext


class EventProcessor:

    def __init__(
        self,
        context: ExecutionContext,
    ):
        self.context = context

    def process(
        self,
        event: StreamEvent,
    ) -> None:

        #
        # Publish first.
        #
        self.context.event_bus.publish(
            event
        )

        #
        # Update execution state.
        #
        if isinstance(event, TextDeltaEvent):
            self.context.assistant_text += (
                event.delta
            )

        elif isinstance(event, UsageEvent):
            self.context.usage = event.usage

        elif isinstance(event, CompletedEvent):
            self.context.finish_reason = (
                event.finish_reason
            )