"""Slash-command / prompt-file registry (à la Copilot's `/` menu)."""

from .registry import Command, CommandRegistry, default_commands
from .builtin import (
    compact_command,
    context_command,
    clear_command,
    review_command,
    explain_command,
    test_command,
    workflow_command,
    default_builtin_commands,
)

__all__ = [
    "Command",
    "CommandRegistry",
    "default_commands",
    "compact_command",
    "context_command",
    "clear_command",
    "review_command",
    "explain_command",
    "test_command",
    "workflow_command",
    "default_builtin_commands",
]
