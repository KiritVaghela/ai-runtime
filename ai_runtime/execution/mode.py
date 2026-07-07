
from enum import Enum


class ExecutionMode(str, Enum):
    CHAT = "chat"
    STREAM = "stream"