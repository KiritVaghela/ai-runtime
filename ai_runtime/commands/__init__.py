"""Slash-command / prompt-file registry (à la Copilot's `/` menu)."""

from .registry import Command, CommandRegistry, default_commands

__all__ = ["Command", "CommandRegistry", "default_commands"]
