from enum import Enum

class StreamEventType(str, Enum):
    TEXT_DELTA = "text_delta"
    USAGE = "usage"
    COMPLETED = "completed"
    ERROR = "error"

    # Future
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    THINKING = "thinking"
    PERMISSION = "permission"