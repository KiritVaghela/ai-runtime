from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class Command:
    """A slash command / prompt file (à la Copilot's `/` menu).

    A command is a named, reusable prompt (or hook) the user can invoke.
    `render` produces the prompt text sent to the model; `run` optionally
    executes side effects (e.g. `/compact`, `/context`).
    """

    name: str
    description: str
    prompt_template: str | None = None
    run: Callable[[Any], Any] | None = None

    def render(self, **kwargs: Any) -> str:
        if self.prompt_template:
            try:
                return self.prompt_template.format(**kwargs)
            except (KeyError, IndexError):
                return self.prompt_template
        return self.description


class CommandRegistry:
    """Registry of slash commands / prompt files."""

    def __init__(self):
        self._commands: dict[str, Command] = {}

    def register(self, command: Command) -> None:
        self._commands[command.name] = command

    def get(self, name: str) -> Command | None:
        return self._commands.get(name)

    def list(self) -> list[Command]:
        return list(self._commands.values())

    def render(self, name: str, **kwargs: Any) -> str | None:
        cmd = self._commands.get(name)
        return cmd.render(**kwargs) if cmd else None


# Built-in commands mirroring Copilot/Claude/Cursor slash commands.
def default_commands() -> CommandRegistry:
    reg = CommandRegistry()
    reg.register(
        Command("compact", "Summarize the conversation to free context", "Please summarize the conversation so far concisely.")
    )
    reg.register(
        Command("context", "Show a token/context breakdown", "List the current context window usage.")
    )
    reg.register(
        Command("clear", "Clear the conversation history", "Clear all messages from the current session.")
    )
    return reg
