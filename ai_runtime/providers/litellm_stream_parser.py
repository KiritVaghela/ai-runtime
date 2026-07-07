
from typing import Any

from ai_runtime.conversation import Usage
from ai_runtime.streaming import (
    CompletedEvent,
    StreamEvent,
    TextDeltaEvent,
    UsageEvent,
)


class LiteLLMStreamParser:
    """
    Converts LiteLLM streaming chunks into AI Runtime StreamEvents.
    """

    def parse(self, chunk: Any) -> list[StreamEvent]:
        events: list[StreamEvent] = []

        # Usage
        usage = getattr(chunk, "usage", None)
        if usage is not None:
            events.append(
                UsageEvent(
                    usage=Usage(
                        prompt_tokens=usage.prompt_tokens or 0,
                        completion_tokens=usage.completion_tokens or 0,
                        total_tokens=usage.total_tokens or 0,
                    )
                )
            )

        choices = getattr(chunk, "choices", None)
        if not choices:
            return events

        choice = choices[0]

        # Text delta
        delta = getattr(choice, "delta", None)
        if delta is not None:

            text = getattr(delta, "content", None)

            if text:
                events.append(
                    TextDeltaEvent(
                        delta=text,
                    )
                )

        # Finish reason
        finish_reason = getattr(choice, "finish_reason", None)

        if finish_reason:
            events.append(
                CompletedEvent(
                    finish_reason=finish_reason,
                )
            )

        return events