
from ai_runtime.conversation import ChatMessage
from ai_runtime.streaming import (
    CompletedEvent,
    PermissionEvent,
    StreamEvent,
    TextDeltaEvent,
    ThinkingEvent,
    ToolCallEvent,
    ToolResultEvent,
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

        elif isinstance(event, ThinkingEvent):
            self.context.thinking_text += (
                event.delta
            )

        elif isinstance(event, ToolCallEvent):
            for call in event.calls:
                self.context.tool_inputs[call.get("id")] = call

        elif isinstance(event, ToolResultEvent):
            self.context.tool_results[event.call_id] = {
                "name": event.name,
                "output": event.output,
                "success": event.success,
                "error": event.error,
            }

        elif isinstance(event, UsageEvent):
            self.context.usage = event.usage

        elif isinstance(event, CompletedEvent):
            self.context.finish_reason = (
                event.finish_reason
            )