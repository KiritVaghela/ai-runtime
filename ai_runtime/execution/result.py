
from collections.abc import AsyncIterator

from ..conversation import ChatResponse, Usage
from ..streaming import StreamEvent

class ExecutionResult:
    response: ChatResponse | None
    stream: AsyncIterator[StreamEvent] | None
    usage: Usage | None
    # tool_calls: list[ToolCall]
    # metrics: ExecutionMetrics